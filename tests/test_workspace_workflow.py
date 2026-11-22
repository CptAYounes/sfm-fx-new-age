"""Cross-workspace contracts: no GUI/network, no implicit signal/order authority."""
from dataclasses import replace
import pytest
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,FIXTURE_EPOCH,fixture_runtime


def test_inspection_is_source_bound_and_navigation_has_no_trade_side_effect(runtime):
    api=runtime.api(1);before=len(runtime.database.orders())
    context=api.inspect(symbol='EURUSD',timeframe='H4',as_of=FIXTURE_NOW)
    assert context['source_epoch']==FIXTURE_EPOCH and context['scope_id']==runtime.market.scope_id
    api.navigate('3.5',context)
    assert runtime.workflow.current['context_id']==context['context_id']
    assert len(runtime.database.orders())==before and not runtime.orders.transport.submissions
    altered=dict(context,symbol='GBPUSD')
    with pytest.raises(ValueError):api.navigate('4.2',altered)
    runtime.market.activate_source('EURUSD','OTHER', 'SYNTHETIC_FIXTURE')
    with pytest.raises(ValueError):api.navigate('3.5',context)


def test_replay_context_cannot_resolve_as_live_or_issue(runtime):
    api=runtime.api(1);bars=runtime.market.bars('EURUSD','W1',FIXTURE_NOW,FIXTURE_EPOCH)
    runtime.replay.import_dataset('source',bars,source_ref='SYNTHETIC_FIXTURE')
    runtime.replay.create('run','source',{});runtime.replay.control('run','STEP')
    ctx=api.inspect(symbol='EURUSD',timeframe='W1',run_id='run')
    assert ctx['mode']=='REPLAY' and ctx['scope_id']=='REPLAY:run'
    with pytest.raises(ValueError):api.navigate('4.2',ctx)
    with pytest.raises(ValueError):api.navigate('3.5',ctx)
    assert not runtime.orders.transport.submissions


def test_workspace_notes_restart_and_old_epoch_is_archive_not_evidence(tmp_path):
    path=tmp_path/'state.sqlite';r=fixture_runtime(path);account=r.accounts.current
    try:
        ctx=r.api(1).inspect(symbol='EURUSD',timeframe='D1')
        drawings=[{'id':'note','kind':'Level','anchors':[[FIXTURE_NOW,1.1]],'color':'#F4C66B','locked':False,'hidden':False}]
        r.api(1).save_workspace(ctx,{'style':'Line','volume':True,'drawings':drawings},expected_version=0)
        assert not r.research.query('level',scope=r.market.scope_id,epoch=FIXTURE_EPOCH,symbol='EURUSD',as_of=FIXTURE_NOW)
    finally:r.close()
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    from sfm_fx_new_age.services.orders import FixtureBroker
    r=ApplicationRuntime(path,clock=lambda:FIXTURE_NOW,transport=FixtureBroker());r.accounts.select(account)
    r.market.activate_source('EURUSD',FIXTURE_EPOCH,'SYNTHETIC_FIXTURE')
    try:
        ctx=r.api(1).inspect(symbol='EURUSD',timeframe='D1');stored=r.api(1).workspace(ctx)
        assert stored['settings']['drawings'][0]['id']=='note' and stored['version']==1
        with pytest.raises(ValueError):r.api(1).save_workspace(ctx,{'drawings':[]},expected_version=0)
        r.market.activate_source('EURUSD','NEW','SYNTHETIC_FIXTURE')
        new=r.api(1).inspect(symbol='EURUSD',timeframe='D1')
        assert not r.api(1).workspace(new)['settings'].get('drawings')
        assert r.api(1).workspace(new)['settings']['style']=='Line'
        assert len(r.api(1).workspace(new)['archives'])==1
        assert not r.database.orders()
    finally:r.close()


def test_readiness_and_paged_chart_reads_are_causal_and_scoped(runtime):
    value=runtime.api(1).query('1.3',DataRequest('chart'))
    assert value['readiness']['classification'] in {'RESEARCH_UNCALIBRATED','NOT_EVALUATED','DISABLED'}
    assert 'missing_frames' in value['readiness'] and 'unavailable_methods' in value['readiness']
    assert value['position_observation']['status']=='UNKNOWN'
