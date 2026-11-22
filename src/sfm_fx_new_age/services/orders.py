from __future__ import annotations

from datetime import timedelta
import json
from typing import Any, Callable, Protocol
from uuid import uuid4

from sfm_fx_new_age.contracts.domain import (
    AccountContext, BrokerOutcome, OrderState, Origin, instant, record,
)
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.services.market import MarketService
from sfm_fx_new_age.services.continuity import SessionCalendar
from sfm_fx_new_age.services.signals import SignalService
from sfm_fx_new_age.storage.database import Database, StateConflict


class BrokerTransport(Protocol):
    is_fixture: bool
    def submit(self, order: dict[str, Any]) -> BrokerOutcome: ...
    def reconcile(self, order: dict[str, Any]) -> BrokerOutcome: ...
    def cancel(self, order: dict[str, Any]) -> BrokerOutcome: ...


class FixtureBroker:
    """Explicit in-process test double. No sockets, credentials or real broker identity."""
    is_fixture = True

    def __init__(self, outcome: OrderState = OrderState.ACCEPTED_PENDING) -> None:
        self.outcome = outcome
        self.submissions: list[dict[str, Any]] = []
        self.native: dict[str, BrokerOutcome] = {}
        self.cancellations = 0

    def submit(self, order: dict[str, Any]) -> BrokerOutcome:
        self.submissions.append(dict(order))
        result = BrokerOutcome(self.outcome, None if self.outcome in {OrderState.UNKNOWN, OrderState.REJECTED}
                               else f"FIXTURE-ORDER-{len(self.submissions)}", detail="SYNTHETIC_FIXTURE")
        self.native[order['id']] = result
        return result

    def reconcile(self, order: dict[str, Any]) -> BrokerOutcome:
        return self.native.get(order['id'], BrokerOutcome(OrderState.UNKNOWN, detail='Fixture outcome unresolved'))

    def cancel(self, order: dict[str, Any]) -> BrokerOutcome:
        self.cancellations += 1
        result = BrokerOutcome(OrderState.CANCELED, order.get('broker_order_id'), detail='Explicit fixture broker cancel')
        self.native[order['id']] = result
        return result


class AccountService:
    def __init__(self, db: Database, emit: Any) -> None:
        self.db, self.emit = db, emit
        self.current: AccountContext | None = None
        self.sessions: dict[str, AccountContext] = {}

    def select(self, context: AccountContext) -> None:
        """Connector-owned registration; UI selects only already-known session identities."""
        self.current = context
        self.register(context)

    def register(self, context: AccountContext) -> None:
        """Discovery/authentication does not silently switch the human's selected account."""
        self.sessions[context.scope_id] = context
        # Persist metadata only; authentication is never restored by trusting a database row.
        body = record(context); body['authenticated'] = False
        body['scope_id'] = context.scope_id
        self.db.put('account_metadata', context.scope_id, body)
        self.emit('ACCOUNT.STATE', 'ACCOUNT_LINK', {**record(context), 'scope_id': context.scope_id}, Priority.P0, context.scope_id)

    def select_known(self, scope_id: str) -> None:
        if scope_id not in self.sessions:
            raise ValueError('Unknown connector account session; UI cannot supply authentication')
        self.select(self.sessions[scope_id])

    def disconnect(self) -> None:
        self.sessions.clear()
        self.unselect()

    def unselect(self) -> None:
        self.current = None
        self.emit('ACCOUNT.STATE', 'ACCOUNT_LINK', {'state': 'DISCONNECTED'}, Priority.P0, 'DISCONNECTED')


class OrderService:
    def __init__(self, db: Database, market: MarketService, signals: SignalService,
                 accounts: AccountService, emit: Any, clock: Callable[[], str],
                 transport: BrokerTransport | None = None) -> None:
        self.db, self.market, self.signals = db, market, signals
        self.accounts, self.emit, self.clock, self.transport = accounts, emit, clock, transport
        self.candidate_validator: Callable[[dict[str, Any]], Any] | None = None
        self.recovered = db.recover_inflight()

    def preview(self, signal_id: str, revision: int, *,
                acknowledge_research: bool = False) -> dict[str, Any]:
        """Pure preflight used identically by the detail view and Issue immediately before reservation."""
        signal = self.signals.get(signal_id)
        if signal is None or signal['revision'] != revision or signal['state'] != 'QUEUED':
            raise StateConflict('Selected signal/revision is not currently queued')
        now = instant(self.clock())
        if instant(signal['expires_at']) <= now:
            raise ValueError('Signal expired')
        if instant(signal['available_at']) > now:
            raise ValueError('Signal is not yet available')
        if signal['profile'] == 'RESEARCH_ONLY' and acknowledge_research is not True:
            raise ValueError('Research-only signal requires visible acknowledgement')
        account = self.accounts.current
        if account is None or not account.authenticated or not account.trading_scope:
            raise ValueError('Authenticated selected account with trading scope required')
        if signal.get('scope_id') != account.scope_id:
            raise ValueError('Signal belongs to a different account/source namespace')
        if signal.get('market_candidate_id'):
            if self.candidate_validator is None:raise ValueError('Analytical binding validator unavailable')
            self.candidate_validator(signal)
        if self.transport is None:
            raise ValueError('cTrader execution adapter not connected')
        if not self.transport.is_fixture and not getattr(self.transport, 'ready_for_issue', lambda scope: False)(account.scope_id):
            raise ValueError('Account reconciliation/continuity is not ready for new Issue')
        if self.transport.is_fixture:
            if account.origin is not Origin.SYNTHETIC_FIXTURE or signal['origin'] != Origin.SYNTHETIC_FIXTURE.value:
                raise ValueError('Fixture transport requires fixture account and signal')
        elif account.origin is not Origin.LIVE_OBSERVED or signal['origin'] != Origin.LIVE_OBSERVED.value:
            raise ValueError('Replay and fixture data cannot issue real orders')
        spec = self.market.spec(account.account_id, signal['symbol'])
        quote = self.market.quote(account.account_id, signal['symbol'])
        if spec is None:
            raise ValueError('Broker symbol specification required')
        authority = self.market.authority(signal['symbol'])
        if (spec.origin != account.origin or quote is not None and (quote.origin != account.origin
            or quote.source_epoch != signal['source_epoch'] or quote.scope_id != account.scope_id)
            or spec.scope_id != account.scope_id or authority is None
            or authority['source_epoch'] != signal['source_epoch']):
            raise ValueError('Source origin/epoch mismatch')
        # A pending Limit carries its own entry price; native quote streaming is
        # not an API prerequisite. During a verified closed session preserve the
        # last snapshot (or its absence) without claiming live marketability.
        # Open/unknown sessions retain the existing fresh-price admission rule.
        calendar_row=self.db.get('calendar',json.dumps([account.scope_id,signal['symbol']]))
        calendar=SessionCalendar(**{key:calendar_row[key] for key in SessionCalendar.__dataclass_fields__}) if calendar_row else None
        closed_pending=bool(account.origin is Origin.LIVE_OBSERVED and calendar
            and calendar.source_ref=='ProtoOASymbol.schedule / '+signal['source_epoch'] and not calendar.is_open(self.clock()))
        age = now - instant(quote.available_at) if quote else None
        maximum_age=(self.db.get('parameter','feed.quote_max_age_seconds') or {}).get('value',30)
        if quote is None and not closed_pending:
            raise ValueError('Broker symbol specification and quote required')
        if age is not None and (age < timedelta(0) or age > timedelta(seconds=maximum_age) and not closed_pending):
            raise ValueError('Quote is stale or future-dated')
        if self.db.get('stream_gap',json.dumps([account.scope_id,signal['symbol'],signal['source_epoch']])):
            raise ValueError('Canonical feed continuity is unresolved; new source/reconciliation required')
        from sfm_fx_new_age.contracts.domain import decimal
        entry, units = decimal(signal['entry_price']), decimal(signal['units'])
        spec.validate_order(entry, units)
        if quote is not None and ((signal['side'] == 'BUY' and entry >= quote.ask) or (signal['side'] == 'SELL' and entry <= quote.bid)):
            raise ValueError('Limit price must be on the pending side of the reference snapshot' if closed_pending else 'Limit price must be on the pending side of the current market')
        from sfm_fx_new_age.contracts.analytics import digest
        body = {'signal_id': signal_id, 'revision': revision, 'scope_id': account.scope_id,
                'symbol': signal['symbol'], 'side': signal['side'], 'order_type': 'LIMIT',
                'entry_price': str(entry), 'units': str(units), 'expires_at': signal['expires_at'],
                'source_epoch': signal['source_epoch'], 'quote': record(quote) if quote else None, 'specification': record(spec),
                'price_validation':'CLOSED_SESSION_LAST_SNAPSHOT_BROKER_VALIDATES_PENDING' if closed_pending and quote else 'CLOSED_SESSION_NO_QUOTE_BROKER_VALIDATES_PENDING' if closed_pending else 'FRESH_QUOTE',
                'research_ack_required': signal['profile'] == 'RESEARCH_ONLY',
                'invalidation_price': signal['invalidation_price'], 'broker_stop_loss': None,
                'broker_take_profit': None, 'status': 'PREFLIGHT_VALID'}
        body['preview_hash'] = digest(body)
        return body

    def issue(self, signal_id: str, revision: int, *, user_initiated: bool,
              acknowledge_research: bool = False) -> dict[str, Any]:
        if user_initiated is not True:
            raise ValueError('Issue requires a deliberate human action')
        try:
            preflight=self.preview(signal_id, revision, acknowledge_research=acknowledge_research)
        except ValueError:
            self.signals.expire(self.clock())
            raise
        signal = self.signals.get(signal_id)
        account = self.accounts.current
        assert signal is not None and account is not None and self.transport is not None
        identity = str(uuid4())
        order = {
            'id': identity, 'account_id': account.account_id, 'signal_id': signal_id,
            'revision': revision, 'symbol': signal['symbol'], 'side': signal['side'],
            'entry_price': signal['entry_price'], 'units': signal['units'], 'order_type': 'LIMIT',
            'expires_at': signal['expires_at'], 'client_order_id': identity,
            'broker_order_id': None, 'position_id': None, 'state': 'RESERVED',
            'origin': account.origin.value, 'endpoint_class': account.endpoint_class,
            'broker_id': account.broker_id, 'scope_id': account.scope_id,
            'signal_record_id': self.signals.key(signal_id),
            'created_at': self.clock(), 'updated_at': self.clock(),
            'price_validation':preflight['price_validation'],
            'reference_quote_at':preflight['quote']['available_at'] if preflight['quote'] else None,
            'preview_hash':preflight['preview_hash'],
            'broker_stop_loss': None, 'broker_take_profit': None,
        }
        self.db.reserve_order(order, revision)
        self.emit('SIGNAL.USER_ISSUE', 'GUI_STATE_CONTROLLER', {'signal_id': signal_id, 'revision': revision}, Priority.P0, signal_id)
        self.db.update_order(identity, {'state': 'SUBMITTING'})
        try:
            outcome = self.transport.submit(dict(order))
        except Exception as exc:
            # Never resend on an exception: the external operation may already have happened.
            outcome = BrokerOutcome(OrderState.UNKNOWN, detail=f'Submission outcome uncertain: {type(exc).__name__}')
        return self._apply(identity, outcome)

    def _apply(self, identity: str, outcome: BrokerOutcome) -> dict[str, Any]:
        old = self.db.order(identity)
        if old is None:
            raise KeyError(identity)
        transitions = {
            'RESERVED': {'UNKNOWN', 'REJECTED'},
            'SUBMITTING': {'UNKNOWN', 'REJECTED', 'ACCEPTED_PENDING', 'PARTIALLY_FILLED', 'FILLED'},
            'UNKNOWN': {'UNKNOWN', 'REJECTED', 'ACCEPTED_PENDING', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'EXPIRED'},
            'ACCEPTED_PENDING': {'UNKNOWN', 'ACCEPTED_PENDING', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'EXPIRED'},
            'PARTIALLY_FILLED': {'UNKNOWN', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'EXPIRED'},
            'FILLED': {'FILLED'}, 'CANCELED': {'CANCELED'}, 'EXPIRED': {'EXPIRED'}, 'REJECTED': {'REJECTED'},
        }
        if outcome.state.value not in transitions[old['state']]:
            raise StateConflict(f"Invalid native transition: {old['state']} -> {outcome.state.value}")
        if old['broker_order_id'] and outcome.broker_order_id and old['broker_order_id'] != outcome.broker_order_id:
            raise StateConflict('Broker order identity cannot be rebound')
        body = self.db.update_order(identity, {
            'state': outcome.state.value, 'broker_order_id': outcome.broker_order_id or old['broker_order_id'],
            'position_id': outcome.position_id or old.get('position_id'),
            'detail': outcome.detail, 'updated_at': self.clock(),
        }, signal_state='ISSUED' if outcome.state not in {OrderState.UNKNOWN} else 'ISSUE_RESERVED')
        self.emit('BROKER.ORDER_STATE', 'BROKER_RECONCILER', body, Priority.P0, identity)
        self.emit('ORDER.MAP_UPDATE', 'BROKER_RECONCILER', body, Priority.P0, identity)
        self.emit('ORDER.STATE', 'ORDER_CORRELATION_STORE', body, Priority.P0, identity)
        signal = self.signals.get(body['signal_id'])
        if signal:
            self.signals._changed(signal)
        return body

    def reconcile(self, identity: str) -> dict[str, Any]:
        order = self.db.order(identity)
        if not order or not self.transport:
            raise ValueError('Order and connected adapter required')
        account = self.accounts.current
        if (not account or not account.authenticated or account.account_id != order['account_id']
            or account.origin.value != order['origin'] or account.endpoint_class != order['endpoint_class']
            or account.scope_id != order.get('scope_id')):
            raise ValueError('Reauthenticate the matching account/source/endpoint before reconciliation')
        outcome = self.transport.reconcile(order)
        body = self._apply(identity, outcome)
        self.emit('BROKER.RECONCILE_RESPONSE', 'BROKER_RECONCILER', body, Priority.P0, identity)
        return body

    def cancel_broker_order(self, identity: str, *, user_initiated: bool,
                           expected_order_hash: str | None = None,expected_scope_id: str | None = None) -> dict[str, Any]:
        order = self.db.order(identity)
        account = self.accounts.current
        if user_initiated is not True or not order or not self.transport:
            raise ValueError('Explicit broker cancellation and connected adapter required')
        from sfm_fx_new_age.contracts.analytics import digest
        if (expected_order_hash is not None and digest(order)!=expected_order_hash
            or expected_scope_id is not None and order.get('scope_id')!=expected_scope_id):
            raise StateConflict('Pending order changed since confirmation; inspect and confirm again')
        if (not account or not account.authenticated or not account.trading_scope
            or account.account_id != order['account_id'] or account.scope_id != order.get('scope_id')
            or account.origin.value != order['origin'] or account.endpoint_class!=order['endpoint_class']):
            raise ValueError('Authenticated matching account with trading scope required')
        if order['state'] != 'ACCEPTED_PENDING':
            raise ValueError('Only confirmed pending orders can be cancelled here; reconcile uncertainty first')
        try:
            outcome = self.transport.cancel(order)
        except Exception as exc:
            outcome = BrokerOutcome(OrderState.UNKNOWN, detail=f'Cancel uncertain: {type(exc).__name__}')
        return self._apply(identity, outcome)
