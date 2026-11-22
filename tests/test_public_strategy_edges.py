"""Fail-closed states, immutable corrections and exact public projection matrix."""
import math,json
from datetime import timedelta
from dataclasses import replace
from copy import deepcopy
import pytest
from test_public_strategies import bars,seed,enable,chart,run,points,EPOCH
from sfm_fx_new_age.contracts.public_strategies import METHODS,BY_KEY
from sfm_fx_new_age.contracts.domain import PAIRS,FRAMES,Bar,Origin,instant
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,stamp,fixture_runtime
from sfm_fx_new_age.services.public_projections import PublicProjectionService


def test_exact_cartesian_strategy_pair_frame_matrix_and_missing_lane_rejection():
    r=fixture_runtime()
    try:
        for pair in PAIRS:
            r.market.activate_source(pair,EPOCH,'SYNTHETIC_FIXTURE')
            for frame in FRAMES:
                for b in bars(n=90,frame=frame,symbol=pair):r.market.ingest(Bar(**b))
        for m in METHODS:r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True))
        r.pump();found=[]
        for pair in PAIRS:
            for frame in FRAMES:
                for row in chart(r,frame,pair)['strategy_layers']:
                    assert row['state'] in ({'DATA_UNAVAILABLE'} if BY_KEY[row['strategy_id']].data_kind and row['strategy_id']!='cause_effect' else {'READY','NO_SETUP'}),row
                    found.append((row['strategy_id'],row['symbol'],row['timeframe']))
        expected={(key,pair,frame) for key in BY_KEY for pair in PAIRS for frame in FRAMES}
        assert len(found)==len(set(found))==83*len(PAIRS)*len(FRAMES) and set(found)==expected
        assert set(found[:-1])!=expected
        assert not r.orders.transport.submissions and not r.orders.transport.cancellations
    finally:r.close()


def test_all_insufficient_histories_and_genuine_no_setup_are_distinct():
    r=seed(rows=bars(n=1))
    try:
        for m in METHODS:r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True))
        r.pump()
        for row in chart(r)['strategy_layers']:
            method=BY_KEY[row['strategy_id']]
            expected='NO_SETUP' if method.key=='pinbar' else 'READY' if method.key=='round_numbers' else 'DATA_UNAVAILABLE' if method.warmup==1 and method.key not in {'rolling_extremes','cause_effect'} else 'WARMUP'
            assert row['state']==expected,(method.key,row['state'],row['reason'])
            if method.key!='round_numbers':assert not any(row[k] for k in ('series','markers','zones'))
    finally:r.close()


def test_correction_keeps_old_snapshot_and_availability_and_changes_current_fingerprint():
    r=seed();now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        enable(r,'sma_cross');old=chart(r)['strategy_layers'][0]
        last=r.market.bars('EURUSD','H4',FIXTURE_NOW,EPOCH)[-1]
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(minutes=2))
        correction=replace(last,revision=last.revision+1,available_at=now[0],close=last.close+last.close/100,high=max(last.high,last.close+last.close/100))
        r.market.ingest(correction)
        assert not chart(r)['strategy_layers'] # Withdraw while shared analysis is dirty.
        r.pump();new=chart(r)['strategy_layers'][0]
        assert new['fingerprint']!=old['fingerprint'] and new['available_at']==now[0]
        assert chart(r,as_of=FIXTURE_NOW)['strategy_layers']==[old]
        # Corrected values must not be stamped as if known at the original close.
        assert new['series'][0]['points'][-1]['available_at']==now[0]
    finally:r.close()


def test_pair_scanner_version_and_account_switches_withdraw_current_only():
    r=seed()
    try:
        enable(r,'ema_cross');account=r.accounts.current;old=chart(r)['strategy_layers']
        r.consumers.set_enabled('analysis.pair.EURUSD',False);assert not chart(r)['strategy_layers']
        assert not chart(r,as_of=FIXTURE_NOW)['strategy_layers']
        assert r.analytics.projections.read('EURUSD','H4',as_of=FIXTURE_NOW)==old
        r.consumers.set_enabled('analysis.pair.EURUSD',True);assert chart(r)['strategy_layers']==old
        r.consumers.set_enabled('analysis.scanner',False);assert not chart(r)['strategy_layers']
        r.consumers.set_enabled('analysis.scanner',True)
        m=BY_KEY['ema_cross'];r.database.put('recipe_state',m.recipe_id,dict(enabled=True,version=99))
        assert not chart(r)['strategy_layers'];enable(r,m.key)
        r.accounts.select(replace(account,account_id='FIXTURE-OTHER-ACCOUNT'));assert not chart(r)['strategy_layers']
        r.accounts.select(account);r.pump();assert chart(r)['strategy_layers']==old
    finally:r.close()


def test_required_producer_unavailability_is_not_silently_no_setup_and_can_recover():
    r=seed();now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        enable(r,'pullback_ob');old=chart(r)['strategy_layers'][0]
        r.consumers.set_enabled('analysis.node.SMC_STRUCTURE',False);r._analytics_dirty.add('EURUSD');r.pump()
        assert chart(r)['strategy_layers'][0]['state']=='UNAVAILABLE'
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(seconds=40))
        r.consumers.set_enabled('analysis.node.SMC_STRUCTURE',True);r._analytics_dirty.add('EURUSD');r.pump()
        assert chart(r)['strategy_layers']==[old] # Reuse exact immutable source/config revision.
    finally:r.close()


@pytest.mark.parametrize('mutation',[
 lambda b:b['markers'].append(dict(time='2099-01-01T00:00:00Z',available_at=FIXTURE_NOW,price='1.1',side='BUY')),
 lambda b:b['zones'].append(dict(low='2',high='1',available_at=FIXTURE_NOW)),
 lambda b:b['markers'].append(dict(time=FIXTURE_NOW,available_at='2099-01-01T00:00:00Z',price='1.1',side='BUY')),
 lambda b:b['series'].append(dict(points=[dict(time=FIXTURE_NOW,available_at=FIXTURE_NOW,price='nan')])),
 lambda b:b.update(orders=['forbidden'])])
def test_projection_validator_rejects_future_nonfinite_negative_geometry_and_execution_fields(mutation):
    body=dict(available_at=FIXTURE_NOW,series=[],zones=[],markers=[],metrics={});mutation(body)
    with pytest.raises(ValueError):PublicProjectionService._validate(body,FIXTURE_NOW)


def test_donchian_one_start_not_repeated_new_highs():
    rows=bars(values=[1.1]*30+[1.11+i*.01 for i in range(6)])
    assert len(run('donchian',rows)['markers'])==1


def test_registration_is_install_time_and_rejects_duplicate_owner_and_missing_sources():
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    from sfm_fx_new_age.tabs.tab3.public_features import Features
    from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
    from functools import partial
    captured=[]
    def install(api):
        captured.append(api);m=METHODS[0]
        with pytest.raises(ValueError):api.register_projection_method(replace(m,sources=()),partial(evaluate,m.key),Features)
        api.register_projection_method(m,partial(evaluate,m.key),Features)
        with pytest.raises(ValueError):api.register_projection_method(m,partial(evaluate,m.key),Features)
    r=ApplicationRuntime(analytical_installers=(install,))
    try:
        with pytest.raises(RuntimeError):captured[0].register_projection_method(METHODS[1],evaluate,Features)
        assert r.accounts.current is None and not r.connector.workers
    finally:r.close()
