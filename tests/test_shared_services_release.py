from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from threading import get_ident
import pytest

from sfm_fx_new_age.contracts.domain import Bar,Origin,record
from sfm_fx_new_age.contracts.tab_data import DATASETS,DataRequest
from sfm_fx_new_age.services.continuity import SessionCalendar
from sfm_fx_new_age.services.geometry import atr_variants,risk_band,qualify
from sfm_fx_new_age.services.scanner import ScannerScheduler,confirmed_swings
from sfm_fx_new_age.testing.fixtures import FIXTURE_EPOCH,FIXTURE_NOW


@pytest.mark.parametrize('key',DATASETS)
def test_every_subtab_has_working_domain_read_adapters(runtime,key):
    api=runtime.api(int(key[0])); runtime.pump()
    for dataset in api.datasets(key):
        response=api.query(key,DataRequest(dataset,limit=2))
        assert response['dataset']==dataset
        assert response['schema_version']==1
        assert len(response['rows'])<=2
        assert response['total']>=len(response['rows'])
        assert response['scope_id']==runtime.market.scope_id
        with pytest.raises(TypeError):response['status']='changed'
    assert not runtime.router.errors


def test_research_api_cannot_read_execution_or_other_tab_data(runtime):
    with pytest.raises(ValueError):runtime.api(3).query('3.1',DataRequest('orders'))
    with pytest.raises(ValueError):runtime.api(3).query('4.1',DataRequest('signals'))
    with pytest.raises(ValueError):runtime.api(1).query('1.3',DataRequest('bars',as_of='2099-01-01T00:00:00Z'))


def test_worker_events_only_deliver_on_core_owner_and_expiry_runs_without_issue(runtime):
    seen=[];runtime.api(4).subscribe('4.1',lambda e:seen.append(get_ident()))
    with ThreadPoolExecutor(1) as pool:
        pool.submit(runtime.emit,'SIGNAL.TEST','TEST',{'scope_id':runtime.market.scope_id}).result()
        with pytest.raises(RuntimeError):pool.submit(runtime.router.drain).result()
    assert seen==[]
    runtime.clock=lambda:'2026-11-08T12:00:00Z'
    runtime.pump()
    assert seen and set(seen)=={runtime.owner_thread}
    assert runtime.signals.get('FIXTURE-SIGNAL-1')['state']=='EXPIRED'


def test_source_shared_scheduler_is_cached_disabled_and_has_truthful_capabilities(runtime):
    runtime.pump();first=dict(runtime.analytics.scheduler.runs)
    for _ in range(4):
        runtime.analytics.refresh('EURUSD')
        runtime.api(1).query('1.3',DataRequest('bars'))
    assert runtime.analytics.scheduler.runs==first
    nodes={r['id']:r for r in runtime.analytics.snapshot('EURUSD')['nodes']}
    assert len(nodes)==44
    assert nodes['OHLC_GEOM']['status']=='READY'
    assert nodes['DOM_BOOK']['status']=='UNAVAILABLE'
    assert nodes['WYCKOFF']['status']=='UNAVAILABLE'
    runtime.consumers.set_enabled('analysis.scanner',False)
    runtime.analytics.refresh('EURUSD')
    assert all(n['status']=='DISABLED' for n in runtime.analytics.snapshot('EURUSD')['nodes'])
    assert runtime.analytics.scheduler.runs==first


def test_backfill_is_source_bound_and_deduplicated(runtime):
    s=runtime.continuity
    args=('EURUSD','H4','2026-11-05T08:00:00Z','2026-11-05T12:00:00Z')
    a=s.request_backfill(*args);assert s.request_backfill(*args)['id']==a['id']
    bar=runtime.market.bars('EURUSD','H4',FIXTURE_NOW,FIXTURE_EPOCH)[-1]
    with pytest.raises(ValueError):s.apply_page(a['id'],[replace(bar,source_epoch='other')],complete=True)
    assert s.apply_page(a['id'],[bar],complete=True)['status']=='COMPLETE'
    assert s.coverage('EURUSD','H4',FIXTURE_NOW)['status']=='CALENDAR_UNKNOWN'
    s.set_calendar('EURUSD',SessionCalendar('test','UTC',((0,604800),),source_ref='SYNTHETIC_TEST'))
    assert s.coverage('EURUSD','H4',FIXTURE_NOW)['status']=='OBSERVED_CONTIGUOUS'


def test_calendar_dst_and_closed_dates():
    calendar=SessionCalendar('test','America/New_York',((0,604800),),('2026-11-05',),source_ref='SYNTHETIC_TEST')
    assert calendar.is_open('2026-11-05T12:00:00Z') is False
    # A local day spanning US autumn DST lasts 25 real hours.
    assert calendar.next_close('2026-11-01T04:00:00Z','D1')=='2026-11-02T05:00:00Z'
    with pytest.raises(ValueError):SessionCalendar('bad','UTC',((0,10),(5,20)),source_ref='test')


def test_replay_rewind_and_corrections_are_isolated_and_reproducible(runtime):
    bars=runtime.market.bars('EURUSD','W1',FIXTURE_NOW,FIXTURE_EPOCH)
    replay=runtime.replay
    replay.import_dataset('dataset',bars,source_ref='SYNTHETIC_FIXTURE')
    replay.create('run','dataset',{'profile':'research'})
    replay.control('run','SEEK',cursor=4)
    first=replay.snapshot('run')
    replay.control('run','SEEK',cursor=12)
    replay.control('run','SEEK',cursor=4)
    assert replay.snapshot('run')==first
    assert len(first['rows'])==5
    assert all(b['origin']=='HISTORICAL_REPLAY' for b in first['rows'])
    assert first['execution_allowed'] is False
    assert runtime.market.authority('EURUSD')['source_epoch']==FIXTURE_EPOCH
    assert runtime.orders.transport.submissions==[]
    windows=replay.walk_forward('dataset',5,2)
    assert windows and all(w['train_through']<w['test_from'] for w in windows)
    assert len(replay.parameter_sweep({'a':[1,2],'b':[3,4]}))==4
    with pytest.raises(ValueError):replay.parameter_sweep({'a':list(range(300))})


def test_atr_variants_match_supplied_source_crosscheck():
    v=atr_variants(setup_id='source-synthetic',side='BUY',entry=Decimal('1.0850'),anchor=Decimal('1.0820'),
        atr=Decimal('0.0120'),pip=Decimal('0.0001'),tick=Decimal('0.00001'))
    assert [x.stop_price for x in v]==list(map(Decimal,['1.0760','1.0700','1.0640','1.0580']))
    assert [x.distance_pips for x in v]==list(map(Decimal,['90','150','210','270']))
    assert [x.actual_band for x in v]==['ATR_100','ATR_150','ATR_200','EXTENDED']


@pytest.mark.parametrize('fraction,code',[('0.37499','SUB_050'),('0.375','ATR_050'),('0.750','ATR_100'),('1.250','ATR_150'),('1.750','ATR_200'),('2.250','EXTENDED')])
def test_exact_band_boundaries(fraction,code):assert risk_band(Decimal(fraction))==code


def test_qualification_cannot_override_missing_gate_or_cost_component():
    gates={f'QG{i:02d}':True for i in range(1,15)}
    args=dict(zone_confidence=Decimal('100'),geometry_points=20,target_points=20,cost_points=10,profile_id='RESEARCH_V1')
    assert qualify(gates,**args)['status']=='ELIGIBLE_RESEARCH'
    assert qualify(gates|{'QG06':None},**args)['quality_score'] is None
    assert qualify(gates,**(args|{'cost_points':None}))['status']=='WITHHELD'
    assert qualify(gates,**args)['is_win_probability'] is False


def test_issue_preview_is_pure_and_shared_with_issue(runtime):
    changes=runtime.database.connection.total_changes
    preview=runtime.api(4).query('4.2',DataRequest('issue_preview',object_id='FIXTURE-SIGNAL-1'))
    assert preview['rows'][0]['status']=='BLOCKED'
    assert 'acknowledgement' in preview['rows'][0]['blocker']
    preview=runtime.api(4).query('4.2',DataRequest('issue_preview',object_id='FIXTURE-SIGNAL-1',acknowledge_research=True))
    assert preview['rows'][0]['status']=='PREFLIGHT_VALID'
    assert runtime.database.connection.total_changes==changes
    assert runtime.database.orders()==[]
