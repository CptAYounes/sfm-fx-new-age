"""Public tab integration API v1. No Qt, SQL, broker SDK or credentials exposed."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from sfm_fx_new_age.contracts.models import CommandResult, Event, freeze
from sfm_fx_new_age.contracts.commands import CommandCapability, capability
from sfm_fx_new_age.contracts.tab_data import DataRequest, DATASETS

if TYPE_CHECKING:
    from .runtime import ApplicationRuntime

API_VERSION = 1


@dataclass(frozen=True, slots=True)
class TabSnapshot:
    subtab_id: str
    version: int
    status: str
    data: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'data', freeze(self.data))


class TabApi:
    def __init__(self, runtime: ApplicationRuntime, tab_id: int) -> None:
        if tab_id not in (1, 2, 3, 4):
            raise ValueError('Unknown main tab')
        self._runtime, self.tab_id = runtime, tab_id
        self.version = API_VERSION
        self.definitions = tuple(d for d in runtime.definitions if d.main_tab == tab_id)
        self._ids = frozenset(d.subtab_id for d in self.definitions)
        self._releases: list[Callable[[], None]] = []
        self._closed = False

    def _check(self, subtab_id: str) -> None:
        if self._closed:
            raise RuntimeError('Tab API has been disposed')
        if subtab_id not in self._ids:
            raise ValueError(f'Tab {self.tab_id} cannot operate on {subtab_id}')

    def snapshot(self, subtab_id: str) -> TabSnapshot:
        self._check(subtab_id)
        return self._runtime.snapshot(subtab_id)

    def command(self, subtab_id: str, name: str, payload: dict[str, Any] | None = None) -> CommandResult:
        self._check(subtab_id)
        result = self._runtime.subtab(subtab_id).dispatch(name, payload)
        self._runtime.flush_if_owner()
        return result

    def datasets(self, subtab_id: str) -> tuple[str, ...]:
        self._check(subtab_id)
        return DATASETS[subtab_id]

    def query(self, subtab_id: str, request: DataRequest) -> Mapping[str, Any]:
        """Read-only, bounded, current-scope domain API; research lanes have no execution datasets."""
        self._check(subtab_id)
        if type(request) is not DataRequest or request.dataset not in DATASETS[subtab_id]:
            raise ValueError('Dataset not owned by this subtab')
        return freeze(self._runtime.query_data(subtab_id, request))

    def subscribe(self, subtab_id: str, callback: Callable[[Event], None]) -> Callable[[], None]:
        """Callbacks run on core drain thread. UI marshals through Qt/timer, never touches workers."""
        self._check(subtab_id)
        def changed(event: Event) -> None:
            if self._runtime.affects_snapshot(subtab_id, event):
                callback(event)
        release = self._runtime.router.subscribe('*', changed)
        def close() -> None:
            release()
            if close in self._releases:
                self._releases.remove(close)
        self._releases.append(close)
        return close

    def subscribe_snapshots(self, subtab_id: str, callback: Callable[[TabSnapshot], None], *,
                            initial: bool = True) -> Callable[[], None]:
        """Additive v1 convenience; same core-thread rule as subscribe()."""
        self._check(subtab_id)
        release = self.subscribe(subtab_id, lambda event: callback(self.snapshot(subtab_id)))
        if initial:
            try:
                callback(self.snapshot(subtab_id))
            except BaseException:
                release()
                raise
        return release

    def capabilities(self, subtab_id: str) -> tuple[CommandCapability, ...]:
        self._check(subtab_id)
        definition = next(d for d in self.definitions if d.subtab_id == subtab_id)
        return tuple(capability(name, definition.backend_owner) for name in definition.commands)

    def close(self) -> None:
        """Release this tab consumer's subscriptions, never shared services or feed ownership."""
        for release in tuple(self._releases):
            release()
        self._closed = True

    def _workflow(self):
        if self._closed:raise RuntimeError('Tab API has been disposed')
        return self._runtime.workflow

    def inspect(self,**selection):
        if self.tab_id in {2,3} and selection.get('object_kind') in {'order','broker_pending','position'}:raise ValueError('Broker inspection is not owned by this research/tool consumer')
        return freeze(self._workflow().capture(**selection))

    def validate_inspection(self,context):
        from sfm_fx_new_age.contracts.models import thaw
        return freeze(self._workflow().validate(thaw(context)))

    def inspection_object(self,context):
        from sfm_fx_new_age.contracts.models import thaw
        service=self._workflow();body=service.validate(thaw(context))
        if self.tab_id in {2,3} and body['object_kind'] in {'order','broker_pending','position'}:raise ValueError('Broker inspection is not owned by this research/tool consumer')
        return freeze(service.resolve(body) or {}) if body['object_id'] else freeze({})

    def navigate(self,target,context):
        from sfm_fx_new_age.contracts.models import thaw
        self._workflow().navigate(target,thaw(context))

    def scenario_context(self,context,scenario):
        from sfm_fx_new_age.contracts.models import thaw
        return freeze(self._workflow().with_scenario(thaw(context),thaw(scenario)))

    def inspection_projection(self,context):
        from sfm_fx_new_age.contracts.models import thaw
        from sfm_fx_new_age.services.chart_projection import setup_projection
        body=thaw(self.validate_inspection(context));row=thaw(self.inspection_object(context))
        if not row:return freeze({})
        r=self._runtime;candidate=None
        if row.get('market_candidate_id'):
            candidates=r.research.query('market_candidate',scope=body['scope_id'],epoch=body['source_epoch'],symbol=body['symbol'],as_of=body['as_of'],history=True,limit=5000)
            candidate=next((v for v in candidates if v['candidate_id']==row['market_candidate_id'] and v['revision']==row['market_candidate_revision']),None)
        return freeze(setup_projection(row,scope=body['scope_id'],epoch=body['source_epoch'],symbol=body['symbol'],as_of=body['as_of'],candidate=candidate) or {})

    def workspace(self,context):
        from sfm_fx_new_age.contracts.models import thaw
        return freeze(self._workflow().workspace(thaw(context)))

    def save_workspace(self,context,settings,expected_version):
        from sfm_fx_new_age.contracts.models import thaw
        if self.tab_id!=1:raise ValueError('Chart owner required to save local display notes')
        return freeze(self._workflow().save_workspace(thaw(context),thaw(settings),expected_version))

    def create_inspection_replay(self,context,run_id):
        from sfm_fx_new_age.contracts.models import thaw
        if self.tab_id not in {1,3}:raise ValueError('Chart/research owner required for isolated replay')
        return freeze(self._workflow().replay_from_context(thaw(context),run_id))

    def request_older_history(self,context,days=30):
        from sfm_fx_new_age.contracts.models import thaw
        if self.tab_id not in {1,3}:raise ValueError('Chart/research history consumer required')
        return freeze(self._workflow().older_history(thaw(context),days))

    def control_replay(self,run_id,action,*,cursor=None):
        self._workflow()
        if self.tab_id not in {1,3}:raise ValueError('Replay control requires chart or research consumer')
        return freeze(self._runtime.replay.control(run_id,action,cursor=cursor))

    def run_research_study(self,request):
        self._check('3.12')
        return freeze(self._runtime.replay.study(request,self._runtime.analytics.projections.methods))

    def research_study(self,study_id):
        self._check('3.12')
        return freeze(self._runtime.replay.study_result(study_id))

    def calculator_context(self,context):
        from sfm_fx_new_age.contracts.models import thaw
        from sfm_fx_new_age.contracts.domain import record
        body=self._workflow().validate(thaw(context))
        if self.tab_id!=2 or body['mode']!='MARKET' or body['object_kind'] in {'order','broker_pending','position'}:raise ValueError('Non-broker market calculator handoff required')
        r=self._runtime;a=r.accounts.current
        spec=r.market.spec(a.account_id,body['symbol']) if a else None
        quote=r.market.quote(a.account_id,body['symbol']) if a else None
        quotes=[]
        from sfm_fx_new_age.contracts.domain import PAIRS,instant
        for pair in PAIRS:
            q=r.market.quote(a.account_id,pair) if a else None;authority=r.market.authority(pair)
            if q and authority and q.source_epoch==authority['source_epoch'] and instant(q.available_at)<=instant(body['as_of']):
                quotes.append(record(q)|{'state':'CURRENT' if 0<=(instant(r.clock())-instant(q.available_at)).total_seconds()<=r.catalogues.parameter_value('feed.quote_max_age_seconds') else 'STALE'})
        return freeze({'context':body,'specification':record(spec) if spec else None,'quote':record(quote) if quote and quote.source_epoch==body['source_epoch'] and instant(quote.available_at)<=instant(body['as_of']) else None,
                       'quotes':quotes,'account_currency':a.currency if a else None})
