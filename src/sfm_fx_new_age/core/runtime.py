from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from threading import get_ident, RLock
from queue import Queue, Empty, Full
from typing import Any, Callable

from sfm_fx_new_age.contracts.domain import PAIRS, instant, record, symbol_check
from sfm_fx_new_age.contracts.commands import SNAPSHOT_COMMANDS, capability, validate_payload
from sfm_fx_new_age.contracts.enums import Availability, CommandStatus, Priority
from sfm_fx_new_age.contracts.models import Command, CommandResult, Event, SubtabDefinition, thaw, utc_now
from sfm_fx_new_age.contracts.registry import load_routes, load_subtabs
from sfm_fx_new_age.services.market import MarketService
from sfm_fx_new_age.services.signals import SignalService
from sfm_fx_new_age.services.orders import AccountService, OrderService, BrokerTransport
from sfm_fx_new_age.services.catalogues import CatalogueService
from sfm_fx_new_age.services.positions import PositionService
from sfm_fx_new_age.services.consumers import ConsumerService
from sfm_fx_new_age.services.research import ResearchStore
from sfm_fx_new_age.services.replay import ReplayService
from sfm_fx_new_age.services.continuity import ContinuityService
from sfm_fx_new_age.services.scanner import AnalyticsService
from sfm_fx_new_age.services.timeline import TickTimeline
from sfm_fx_new_age.storage.database import Database
from .components import ComponentRegistry
from .projections import ProjectionStore, ViewProjection
from .router import PriorityEventRouter
from .tab_api import TabApi, TabSnapshot
from .tab_data import TabDataService
from .command_handlers import SharedCommandHandlers


@dataclass(slots=True)
class SubtabRuntime:
    definition: SubtabDefinition
    components: ComponentRegistry
    projections: ProjectionStore

    def on_event(self, event: Event) -> None:
        self.projections.apply_event(self.definition.subtab_id, event)

    def dispatch(self, command_name: str, payload: dict[str, Any] | None = None) -> CommandResult:
        command = Command(command_name, self.definition.backend_owner, self.definition.subtab_id,
                          payload or {}, self.definition.priority)
        if command_name not in self.definition.commands:
            return CommandResult(command.command_id, CommandStatus.REJECTED, 'Command not allowed by subtab contract')
        return self.components.dispatch(command)

    def projection(self) -> ViewProjection:
        return self.projections.get(self.definition.subtab_id)


@dataclass(frozen=True, slots=True)
class TabRuntime:
    tab_id: int
    title: str
    subtabs: tuple[SubtabRuntime, ...]


class ApplicationRuntime:
    """Core composition root. Production starts empty; fixtures are opt-in only."""

    def __init__(self, database_path: str | Path = ':memory:', *,
                 clock: Callable[[], str] = utc_now, transport: BrokerTransport | None = None,
                 analytical_installers: tuple | None = None, supplemental_config: str | Path | None = None,
                 native_analytical_feed: bool = False, activity_alternatives: bool = False,
                 compute_workers: str | int | None = None) -> None:
        if compute_workers is not None:
            from sfm_fx_new_age.services.compute_pool import host_capacity
            host_capacity(compute_workers)  # Validate before opening any database.
        self.clock, self.definitions, self.routes = clock, load_subtabs(), load_routes()
        self.database = Database(database_path)
        self.owner_thread = get_ident()
        self._command_lock = RLock()
        self.inbox = Queue(maxsize=4096)
        self.router = PriorityEventRouter(owner_thread=self.owner_thread)
        component_ids = {d.backend_owner for d in self.definitions}
        component_ids.update(route.source for route in self.routes)
        component_ids.update(route.destination for route in self.routes)
        component_ids.update({'PROJECTION_STORE', 'GUI_STATE_CONTROLLER'})
        self.components = ComponentRegistry(component_ids)
        self.projections = ProjectionStore(self.definitions)
        self._subtabs = {d.subtab_id: SubtabRuntime(d, self.components, self.projections) for d in self.definitions}
        grouped: dict[int, list[SubtabRuntime]] = defaultdict(list)
        for definition in self.definitions:
            bridge = self._subtabs[definition.subtab_id]
            grouped[definition.main_tab].append(bridge)
            for topic in definition.subscribed_topics:
                self.router.subscribe(topic, bridge.on_event)
        self.tabs = tuple(TabRuntime(n, items[0].definition.main_tab_title, tuple(items)) for n, items in sorted(grouped.items()))
        self.router.subscribe('*', self._journal)
        self.consumers = ConsumerService(self.database, self.emit)
        for definition in self.definitions:
            self.consumers.register('display.' + definition.subtab_id, definition.backend_owner,
                                    enabled=definition.subtab_id != '1.5')
        self.consumers.register('analysis.scanner', 'STRATEGY_RECIPE_HOST')
        self.consumers.register('analysis.rules', 'LOGICTILES_TABBRIDGE')
        for symbol in PAIRS:
            self.consumers.register('analysis.pair.' + symbol, 'STRATEGY_RECIPE_HOST')
        self.accounts = AccountService(self.database, self.emit)
        self.market = MarketService(self.database, self.emit, lambda: self.accounts.current)
        self.signals = SignalService(self.database, self.emit, lambda: self.market.scope_id, lambda:self.clock())
        self.positions = PositionService(self.database, self.emit, lambda: self.accounts.current)
        self.catalogues = CatalogueService(self.database, self.emit, lambda: self.market.scope_id,
                                            lambda: self.consumers.enabled('analysis.rules'),lambda:self.clock())
        from sfm_fx_new_age.contracts.defaults import register_core_parameters
        register_core_parameters(self.catalogues)
        self.research = ResearchStore(self.database, self.emit)
        self.replay = ReplayService(self.database, self.emit)
        self.continuity = ContinuityService(self.database, self.market, self.emit, self.clock)
        self.timeline = TickTimeline(self.market, self.continuity)
        self.analytics = AnalyticsService(self.database, self.market, self.consumers, self.emit, self.clock)
        self.analytics.activity_alternatives=activity_alternatives
        self.analytics.research = self.research
        from sfm_fx_new_age.services.strategy_signals import StrategySignalService
        self.strategy_signals=StrategySignalService(self)
        self.analytics.projections.signal_sink=self.strategy_signals.observe
        from sfm_fx_new_age.services.candidate_binding import CandidateBindingService
        self.candidate_binding = CandidateBindingService(self.market,self.research,self.signals,self.accounts,
            self.analytics,self.consumers,lambda:self.clock(),lambda symbol:symbol in self._analytics_dirty)
        self.candidate_binding.strategy_signals=self.strategy_signals

        for node, definition in self.analytics.scheduler.nodes.items():
            if definition['layer'] == 'sensor' and node not in self.analytics.scheduler.handlers:
                self.consumers.register('analysis.node.' + node, 'STRATEGY_RECIPE_HOST')
        self._analytics_dirty = set()
        self.tab_data = TabDataService(self)
        self.command_handlers = SharedCommandHandlers(self)
        self.orders = OrderService(self.database, self.market, self.signals, self.accounts, self.emit, self.clock, transport)
        self.orders.candidate_validator = self.candidate_binding.validate
        self.selected_pair = (self.database.get('setting', 'selected_pair') or {}).get('value', 'EURUSD')
        if self.selected_pair not in PAIRS:
            # Retain the old stored preference/history, but never resume a
            # retired instrument as an active chart or acquisition request.
            self.selected_pair = PAIRS[0]
        from sfm_fx_new_age.services.workflow import WorkflowService
        self.workflow=WorkflowService(self)
        self._revision = 0
        self.closed = False
        self.fixture_mode = bool(transport and transport.is_fixture)
        from sfm_fx_new_age.connector.service import ConnectorService
        self.connector = ConnectorService(self)
        from sfm_fx_new_age.services.research_money import ResearchMoneyService
        self.money = ResearchMoneyService(self)
        for component_id in component_ids:
            self.components.bind_handler(component_id, self._handle_command)
            self.components.set_state(component_id, Availability.WIRED,
                'Tab API wired; use command capability results. Full domain capability is not implied.')
        for component_id in ('CT_OPEN_API_CONNECTOR', 'OPTIONAL_LOCAL_POSITION_SERVICE'):
            self.components.set_state(component_id, Availability.NOT_AVAILABLE,
                'Connector installed but not configured/authenticated; network not started' if component_id == 'CT_OPEN_API_CONNECTOR' else 'Optional addon not installed')
        self.router.subscribe('*', self._changed)
        self.router.subscribe('BAR.FINAL', lambda e: self._analytics_dirty.add(e.payload['symbol']))
        self.router.subscribe('QUOTE.UPDATED', lambda e: self._analytics_dirty.add(e.payload['symbol']))
        self.router.subscribe('ANALYTICS.INPUT', lambda e: self._analytics_dirty.add(e.payload['symbol']))
        self.router.subscribe('ACCOUNT.STATE', lambda e: self._analytics_dirty.update(PAIRS))
        self.router.subscribe('QUOTE.LKV', self._public_quote_changed)
        self.router.subscribe('DATA.AUTHORITY_CHANGE', lambda e: self._analytics_dirty.add(e.payload['symbol']))
        self.router.subscribe('DATA.AUTHORITY_CHANGE', lambda e: self.analytics.projections.invalidate(e.payload['symbol']))
        self.router.subscribe('PARAM.EFFECTIVE', lambda e: self._analytics_dirty.update(e.payload.get('symbols',PAIRS)))
        from .analytical_api import AnalyticalExtensionApi
        from sfm_fx_new_age.tabs.backend_loader import load_analytical_installers
        installation = AnalyticalExtensionApi(self.analytics, self.catalogues, self.research)
        try:
            for install in analytical_installers if analytical_installers is not None else load_analytical_installers():
                install(installation)
        except BaseException:
            self.close()
            raise
        finally:
            installation.close()
        if compute_workers is not None:self.analytics.projections.configure_compute(compute_workers)
        from sfm_fx_new_age.services.supplemental_files import SupplementalFileIngress
        try:
            self.supplemental_ingress=SupplementalFileIngress(self.analytics.supplemental,supplemental_config,allow_fixture=self.fixture_mode)
            if native_analytical_feed and not self.fixture_mode:
                from sfm_fx_new_age.connector.analytical_feed import ConnectedAnalyticalFeed
                excluded={kind for provider in self.supplemental_ingress.providers for kind in provider['kinds']}
                self.connector.analytical_feed=ConnectedAnalyticalFeed(self.connector,excluded_kinds=excluded)
        except BaseException:
            self.close();raise

    def _public_quote_changed(self,event):
        self.strategy_signals.quote_changed(event.payload['symbol'])
        method=self.analytics.projections.methods.get('previous_body_live')
        if method and self.analytics.projections.enabled(method[0]):
            self._analytics_dirty.add(event.payload['symbol'])

    def _journal(self, event: Event) -> None:
        self.database.append_event(event.event_id, event.topic, {
            'source_component': event.source_component, 'source_epoch': event.source_epoch,
            'produced_at_utc': event.produced_at_utc, 'payload': thaw(event.payload),
        })

    def _changed(self, event: Event) -> None:
        self._revision += 1

    def emit(self, topic: str, source: str, payload: dict[str, Any], priority: Priority = Priority.P2,
             partition_key: str = 'GLOBAL') -> None:
        self.router.publish(Event(topic, source, payload, priority, partition_key,
                                  str(payload.get('source_epoch', 'LOCAL-STATE')), produced_at_utc=self.clock()))
        self.flush_if_owner()

    def flush_if_owner(self) -> int:
        return self.router.drain() if get_ident() == self.owner_thread else 0

    def post(self, callback: Callable, *args, **kwargs) -> None:
        """Bounded worker-to-core ingress; Full is explicit, no silent event loss."""
        if self.closed:
            raise RuntimeError('Core is closed')
        self.inbox.put_nowait((callback, args, kwargs))

    def pump(self, limit: int = 128) -> int:
        with self._command_lock:
            return self._pump(limit)

    def _pump(self, limit: int) -> int:
        if get_ident() != self.owner_thread:
            raise RuntimeError('Core pump must run on its owning thread')
        processed = 0
        while processed < limit:
            try: callback, args, kwargs = self.inbox.get_nowait()
            except Empty: break
            callback(*args, **kwargs)
            processed += 1
        self.router.drain(limit)
        self.connector.poll()
        self.supplemental_ingress.poll()
        self.signals.expire(self.clock())
        bucket=int(instant(self.clock()).timestamp())//30
        if bucket!=getattr(self,'_analytical_clock_bucket',None):
            self._analytical_clock_bucket=bucket
            if any((self.database.get('recipe_state',key) or {}).get('enabled') for key in self.analytics.composers):
                self._analytics_dirty.update(PAIRS)
        # Defer expensive scans only for pairs with actual in-flight history.
        # COMPLETE and terminal FAILED jobs both release the wait; algorithms
        # still enforce their own source, frame and input requirements. One
        # rejected lane must never lock every other pair behind a success count.
        deferred = (set(self.connector.feed_status()['pending_history_symbols'])
                    if self.connector.analytical_feed else set())
        ready = sorted(self._analytics_dirty - deferred)
        # Calculation submission and completed-result commits take alternate
        # owner turns. Neither may chain another heavy phase before Qt paints.
        bounded=bool(self.connector.analytical_feed and self.analytics.projections.pool)
        compute_turn=not bounded or getattr(self,'_compute_commit_turn',False)
        self._compute_commit_turn=not compute_turn
        if compute_turn and bounded:ready=[]
        if self.connector.analytical_feed and ready:
            # Yield to native ingress between pair scans. Rotate even when hot
            # symbols are invalidated again on every pump; none may starve.
            last = getattr(self, '_analytics_last_symbol', None)
            after = [s for s in ready if last is not None and s > last]
            symbol = ((after or ready)[0] if last is not None
                      else self.selected_pair if self.selected_pair in ready else ready[0])
            ready = [symbol]
        for symbol in ready:
            # Preserve both in-refresh invalidations and failed pending work.
            self._analytics_dirty.discard(symbol)
            try:
                with self.database.batch_writes():
                    self.consumers.consume('analysis.pair.' + symbol, self.analytics.refresh, symbol)
            except Exception:
                self._analytics_dirty.add(symbol)
                raise
            self._analytics_last_symbol = symbol
        if compute_turn and self.analytics.projections.poll_compute():
            self.emit('ANALYTICS.REVISION','STRATEGY_RECIPE_HOST',{'compute':'COMPLETED_PURE_PROJECTIONS'})
        self.replay.tick()
        return processed

    def _handle_command(self, command: Command) -> CommandResult:
        with self._command_lock:
            return self._dispatch_command(command)

    def _dispatch_command(self, command: Command) -> CommandResult:
        p = thaw(command.payload)
        def result(message: str, status: CommandStatus = CommandStatus.ACCEPTED) -> CommandResult:
            return CommandResult(command.command_id, status, message)
        try:
            validate_payload(command.name, p)
            shared_result = self.command_handlers.dispatch(command, p)
            if shared_result is not None:
                return result(shared_result)
            if command.name == 'SELECT_PAIR':
                symbol = p.get('symbol', '')
                symbol_check(symbol)
                self.selected_pair = symbol
                self.database.put('setting', 'selected_pair', {'value': symbol})
                self.emit('UI.SELECTION', 'GUI_STATE_CONTROLLER', {'symbol': symbol})
                return result(f'Selected {symbol}')
            if command.name == 'SELECT_ACCOUNT':
                self.accounts.select_known(p['scope_id'])
                self.connector.activate_selected()
                return result('Selected existing connector account session')
            if command.name == 'ISSUE' and command.source_view == '4.1':
                order = self.orders.issue(str(p.get('signal_id', '')), int(p.get('revision', 0)),
                    user_initiated=p.get('user_initiated') is True,
                    acknowledge_research=p.get('acknowledge_research') is True)
                return result(f"{order['state']}: {order.get('broker_order_id') or 'await reconciliation'}")
            if command.name == 'CANCEL_SIGNAL':
                self.signals.cancel(str(p.get('signal_id', '')))
                return result('Local unissued signal cancelled; broker orders unchanged')
            if command.name == 'CANCEL_ALL_UNISSUED':
                count = self.signals.cancel_all()
                return result(f'Cancelled {count} local signals; broker orders unchanged')
            if command.name == 'SEPARATE_BROKER_CANCEL':
                order = self.orders.cancel_broker_order(str(p.get('order_id', '')), user_initiated=p.get('user_initiated') is True,
                    expected_order_hash=p.get('expected_order_hash'),expected_scope_id=p.get('expected_scope_id'))
                return result(f"Broker order result: {order['state']}")
            if command.name == 'REFRESH_HISTORY':
                identity = p.get('order_id')
                if identity:
                    body = self.orders.reconcile(str(identity))
                    return result(f"Reconciled: {body['state']}")
                return result('Stored history is available; supply order_id for reconciliation or start/end for read-only native history')
            if command.name == 'PROPOSE_VERSIONED_PARAM_CHANGE':
                if 'symbol' in p:
                    if 'expected_scope_id' not in p:raise ValueError('Explicit account pin required for pair profile changes')
                    body=self.catalogues.set_pair_parameter(p['key'],p['value'],symbol=p['symbol'],expected_version=p['expected_version'],expected_scope_id=p['expected_scope_id'])
                else:body = self.catalogues.set_parameter(p['key'], p['value'], expected_version=int(p.get('expected_version', 0)))
                return result(f"Parameter {body['key']} version {body['version']}")

            if command.name == 'ENABLE_OPTIONAL_H1':
                self.consumers.set_enabled('display.1.5', p['enabled'])
                return result('Optional H1 consumer changed; shared feed ownership unchanged')
            if command.name == 'SET_CONSUMER_SWITCH':
                consumer = str(p.get('consumer_id', ''))
                self.consumers.set_enabled(consumer, p['enabled'])
                self._analytics_dirty.update(PAIRS)
                return result('Registered consumer effective state changed')
            if command.name in SNAPSHOT_COMMANDS:
                return result('Read-only snapshot available through TabApi.snapshot')
            return result(f'{command.name}: domain capability not implemented at this checkpoint', CommandStatus.NOT_IMPLEMENTED)
        except (ValueError, KeyError, TypeError, OSError, Full) as exc:
            return result(str(exc), CommandStatus.REJECTED)

    def api(self, tab_id: int) -> TabApi:
        return TabApi(self, tab_id)

    def query_data(self, subtab_id: str, request) -> dict:
        with self._command_lock:
            return self.tab_data.query(subtab_id, request)

    def subtab(self, subtab_id: str) -> SubtabRuntime:
        return self._subtabs[subtab_id]

    def publish(self, event: Event) -> int:
        self.router.publish(event)
        return self.flush_if_owner()

    def affects_snapshot(self, subtab_id: str, event: Event) -> bool:
        """Shared dependency contract: tabs need not guess which events refresh their data."""
        if not self.consumers.enabled('display.' + subtab_id):
            return False
        if event.topic in {'UI.SELECTION', 'UI.NAVIGATE', 'UI.WORKSPACE', 'ACCOUNT.STATE', 'CONFIG.VERSION'}:
            return True
        scope = event.payload.get('scope_id')
        if scope is not None and scope != self.market.scope_id:
            return False
        d = self.subtab(subtab_id).definition
        if event.topic in d.subscribed_topics:
            return True
        if d.main_tab == 2 and subtab_id in {'2.1', '2.6', '2.9', '2.10'}:
            return True
        if event.topic in {'BAR.FINAL', 'DATA.AUTHORITY_CHANGE'} and d.main_tab in {1, 3}:
            return True
        if event.topic in {'ANALYTICS.REVISION','REPLAY.STATE','DATA.BACKFILL','SESSION.CONTRACT','QUOTE.LKV'} and (d.main_tab in {1,3} or subtab_id in {'4.1','4.2'}):
            return True
        if event.topic.startswith('SIGNAL.') and subtab_id in {'3.13', '4.1', '4.2'}:
            return True
        if event.topic in {'PARAM.EFFECTIVE', 'PARAM.CATALOGUE'} and subtab_id in {'2.8', '3.10', '3.11'}:
            return True
        return event.topic.startswith(('BROKER.ORDER', 'ORDER.')) and subtab_id in {'1.10', '4.3', '4.4', '4.8'}

    def snapshot(self, subtab_id: str) -> TabSnapshot:
        with self._command_lock:
            return self._snapshot(subtab_id)

    def _snapshot(self, subtab_id: str) -> TabSnapshot:
        d = self.subtab(subtab_id).definition
        account = self.accounts.current
        data: dict[str, Any] = {'symbol': self.selected_pair, 'backend_owner': d.backend_owner,
            'origin': account.origin.value if account else 'NO_SOURCE',
            'scope_id': self.market.scope_id, 'rows': [],
            'capabilities': [record(capability(name, d.backend_owner)) for name in d.commands]}
        status = 'NO_DATA'
        if not self.consumers.enabled('display.' + subtab_id):
            return TabSnapshot(subtab_id, self._revision, 'DISABLED', data)
        authority = self.market.authority(self.selected_pair)
        if d.main_tab in (1, 3) and authority:
            context = self.market.context(self.selected_pair, self.clock(), authority['source_epoch'])
            data['context'] = context; data['origin'] = context['origin']
            status = 'WARMUP' if context['missing'] else 'AVAILABLE'
        if subtab_id == '1.1':
            data['rows'] = [{'symbol': symbol, 'selected': symbol == self.selected_pair} for symbol in PAIRS]
            status = 'AVAILABLE'
        elif subtab_id in {'1.2', '1.3', '1.4', '1.5', '3.2', '3.3', '3.4'}:
            frame = {'1.2':'W1','1.3':'D1','1.4':'H4','1.5':'H1','3.2':'D1','3.3':'W1','3.4':'H4'}[subtab_id]
            if authority:
                data['rows'] = [record(bar) for bar in self.market.bars(self.selected_pair, frame, self.clock(), authority['source_epoch'])]
                status = ('AVAILABLE_BARS_ONLY' if subtab_id.startswith('3.') else 'AVAILABLE') if data['rows'] else 'NO_DATA'
        elif subtab_id in {'2.1', '2.9'}:
            data['rows'] = [record(state) for state in self.components.states()]; status = 'AVAILABLE'
        elif subtab_id == '2.2':
            data['rows'] = self.scanner_nodes(); status = 'CAPABILITY_REPORT'
        elif subtab_id == '2.3':
            data['rows'] = [{**record(account), 'scope_id': account.scope_id}] if account else []
            status = 'FIXTURE' if account and self.fixture_mode else 'AUTHENTICATED' if account and account.authenticated else 'DISCONNECTED'
        elif subtab_id == '2.4':
            data['rows'] = []
            for row in self.market.scoped_rows('quote'):
                age = (instant(self.clock()) - instant(row['available_at'])).total_seconds()
                active = self.market.authority(row['symbol'])
                freshness = ('FUTURE' if age < 0 else 'STALE' if age > self.catalogues.parameter_value('feed.quote_max_age_seconds') else 'CURRENT')
                if not active or active['source_epoch'] != row['source_epoch']:
                    freshness = 'INACTIVE_SOURCE'
                data['rows'].append({**row, 'age_seconds': age, 'freshness': freshness})
            status = 'LAST_KNOWN' if data['rows'] else 'NO_DATA'
        elif subtab_id == '2.5':
            data['rows'] = self.market.scoped_rows('spec'); status = 'AVAILABLE' if data['rows'] else 'NO_DATA'
        elif subtab_id == '2.6':
            data['rows'] = [{'from': r.source, 'to': r.destination, 'topic': r.topic, 'priority': r.priority.name,
                'status': 'DECLARED_ROUTE'} for r in self.routes]
            data['metrics'] = self.router.metrics(); status = 'AVAILABLE'
        elif subtab_id == '2.7':
            data['rows'] = self.catalogues.values(); status = 'AVAILABLE'
        elif subtab_id in {'2.8', '3.11'}:
            data['rows'] = self.database.list('parameter'); status = 'AVAILABLE'
        elif subtab_id == '2.10':
            data['rows'] = [{'storage': 'SQLite WAL', 'schema_version': 2,
                'recovered_unknown': self.orders.recovered, 'event_errors': len(self.router.errors),
                'unscoped_legacy_bars': sum('scope_id' not in row for row in self.database.list('bar')),
                'unscoped_legacy_orders': sum('scope_id' not in row for row in self.database.orders())}]; status = 'AVAILABLE'
        elif subtab_id == '3.10':
            data['rows'] = self.database.list('rule'); status = 'AVAILABLE'
        elif subtab_id in {'3.13', '4.1', '4.2'}:
            data['rows'] = self.signals.all(); status = 'AVAILABLE'
        elif subtab_id in {'1.10', '4.3', '4.4', '4.8'}:
            data['rows'] = [row for row in self.database.orders() if row.get('scope_id') == self.market.scope_id]
            if subtab_id == '4.3':
                data['rows'] = [row for row in data['rows'] if row['state'] in {'ACCEPTED_PENDING', 'PARTIALLY_FILLED', 'UNKNOWN', 'SUBMITTING', 'RESERVED'}]
            if subtab_id == '1.10':
                data['positions'] = self.positions.snapshot()
            status = 'AVAILABLE' if account else 'DISCONNECTED'
        elif subtab_id == '4.5':
            data['rows'] = [{**record(context), 'scope_id': context.scope_id, 'selected': context == account}
                            for context in self.accounts.sessions.values()]
            status = 'AVAILABLE' if data['rows'] else 'DISCONNECTED'
        elif subtab_id == '4.6':
            positions = self.positions.snapshot()
            data['rows'] = positions['rows'] if positions else []
            data['observation'] = positions
            status = 'LAST_KNOWN' if positions and positions['complete'] else 'INCOMPLETE' if positions else 'UNKNOWN'
        elif subtab_id == '4.7':
            data['rows'] = [{'capital_fraction': '0.45', 'valuation_base': 'UNCONFIGURED', 'approved_amount': None}]
            status = 'UNCONFIGURED'
        elif subtab_id == '4.9':
            status = 'NOT_AVAILABLE'
        else:
            from sfm_fx_new_age.contracts.tab_data import DATASETS, DataRequest
            domain = self.query_data(subtab_id, DataRequest(DATASETS[subtab_id][0]))
            data['rows'] = domain['rows']; status = domain['status']
        from sfm_fx_new_age.contracts.tab_data import DATASETS
        data['datasets'] = list(DATASETS[subtab_id]); data['schema_version'] = 1
        return TabSnapshot(subtab_id, self._revision, status, data)

    def scanner_nodes(self) -> list[dict[str, Any]]:
        snapshot = self.analytics.snapshot(self.selected_pair)
        if snapshot:
            return snapshot['nodes']
        return [{'id': key, 'status': 'NOT_EVALUATED', 'registered': key in self.analytics.scheduler.handlers}
                for key in self.analytics.scheduler.order]

    def architecture_summary(self) -> dict[str, Any]:
        return {'main_tabs': len(self.tabs), 'subtabs': len(self.definitions), 'routes': len(self.routes),
                'components': len(self.components.states()),
                'subtabs_by_tab': {str(tab.tab_id): len(tab.subtabs) for tab in self.tabs}}

    def close(self) -> None:
        if not self.closed:
            self.connector.close()
            self.analytics.projections.close()
            self.router.drain()
            self.database.close(); self.closed = True
