"""Source, age, invalidation, persistence and human-approval negative controls."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import pytest
from sfm_fx_new_age.contracts.domain import Quote,Bar,Origin,PAIRS,FRAMES,instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,stamp,fixture_runtime
from test_public_strategies import EPOCH,enable,bars
from test_strategy_signal_pipelines import rows
from test_strategy_signal_positive import bindable_runtime


def selected(r):return next(x for x in rows(r) if x['strategy_id']=='engulfing')

def request(row,**changes):
    return dict(candidate_id=row['opportunity_id'],candidate_revision=row['revision'],variant_id='native-stop',units='1000',expected_version=0,user_initiated=True,**changes)


def test_complete_six_pair_four_frame_83_method_routing_set_not_only_a_count():
    r=fixture_runtime()
    try:
        for m in METHODS:
            result=r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True))
            assert result.status.value=='ACCEPTED'
        r.pump();observed=[]
        for symbol in PAIRS:
            values=thaw(r.api(4).query('4.1',DataRequest('strategy_signals',symbol=symbol,limit=5000)))['rows']
            observed.extend((x['strategy_id'],x['symbol'],x['timeframe']) for x in values)
            assert all(x['enabled'] and x['state'] not in {'OFF','ERROR'} for x in values)
        expected={(m.key,p,f) for m in METHODS for p in PAIRS for f in FRAMES}
        assert len(observed)==len(set(observed))==1992 and set(observed)==expected
        assert set(observed[:-1])!=expected  # One missing lane must not pass.
        assert not r.orders.transport.submissions and not r.database.orders()
    finally:r.close()


@pytest.mark.parametrize('change',['disable','dirty','quote_stale','expiry','source_withdrawal','source_epoch','account','continuity','profile','spread','scanner_off','pair_off'])
def test_binding_rechecks_current_source_state_without_side_effects(change):
    r=bindable_runtime()
    try:
        row=selected(r);assert row['state']=='SIGNAL'
        if change=='disable':enable(r,'engulfing',False)
        elif change=='dirty':r._analytics_dirty.add('EURUSD')
        elif change=='quote_stale':r.clock=lambda:stamp(instant(FIXTURE_NOW)+timedelta(seconds=31))
        elif change=='expiry':r.clock=lambda:row['expires_at']
        elif change=='source_withdrawal':r.market.withdraw_source('EURUSD',EPOCH)
        elif change=='source_epoch':r.market.activate_source('EURUSD','NEW-EXPLICIT-FIXTURE-EPOCH',Origin.SYNTHETIC_FIXTURE.value)
        elif change=='account':r.accounts.select(replace(r.accounts.current,account_id='OTHER-EXPLICIT-FIXTURE'))
        elif change=='continuity':r.database.put('stream_gap',json.dumps([r.market.scope_id,'EURUSD',EPOCH]),{'reason':'EXPLICIT_FIXTURE_GAP'})
        elif change=='profile':
            snap=r.analytics.latest[digest([r.market.scope_id,EPOCH,'EURUSD'])]
            snap['profile_hash']='EXPLICIT_DIFFERENT_FIXTURE_PROFILE'
        elif change=='spread':
            now=stamp(instant(FIXTURE_NOW)+timedelta(milliseconds=1));r.clock=lambda:now
            r.market.set_quote(Quote(r.accounts.current.account_id,'EURUSD',D('1.1031'),D('1.1041'),now,EPOCH,Origin.SYNTHETIC_FIXTURE))
        elif change=='scanner_off':r.consumers.set_enabled('analysis.scanner',False)
        elif change=='pair_off':r.consumers.set_enabled('analysis.pair.EURUSD',False)
        result=r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',request(row))
        assert result.status.value=='REJECTED',result
        assert not r.database.orders() and not r.orders.transport.submissions
        assert not any(s.get('market_candidate_id')==row['opportunity_id'] for s in r.signals.all())
    finally:r.close()


@pytest.mark.parametrize('which',['stop','objective'])
def test_observed_invalidation_or_objective_cannot_be_revived_by_quote_recovery(which):
    r=bindable_runtime()
    try:
        row=selected(r);assert row['state']=='SIGNAL'
        at=stamp(instant(FIXTURE_NOW)+timedelta(milliseconds=1));r.clock=lambda:at
        price=D(row['stop'])-D('.0001') if which=='stop' else D(row['target'])+D('.0001')
        r.market.set_quote(Quote(r.accounts.current.account_id,'EURUSD',price,price+D('.0002'),at,EPOCH,Origin.SYNTHETIC_FIXTURE));r.pump()
        assert selected(r)['state']=='INVALIDATED'
        later=stamp(instant(at)+timedelta(milliseconds=1));r.clock=lambda:later
        r.market.set_quote(Quote(r.accounts.current.account_id,'EURUSD',D('1.1031'),D('1.1033'),later,EPOCH,Origin.SYNTHETIC_FIXTURE));r.pump()
        assert selected(r)['state']=='INVALIDATED'
        assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',request(row)).status.value=='REJECTED'
        assert len(r.database.list('strategy_signal_revoked'))==1
    finally:r.close()


def test_original_expiry_never_renews_on_repeated_evaluation_or_reenable():
    r=bindable_runtime()
    try:
        before=selected(r)
        for _ in range(3):r._analytics_dirty.add('EURUSD');r.pump()
        enable(r,'engulfing',False);enable(r,'engulfing')
        after=selected(r)
        assert (after['opportunity_id'],after['available_at'],after['expires_at'])==(before['opportunity_id'],before['available_at'],before['expires_at'])
        r.clock=lambda:after['expires_at']
        assert selected(r)['state']=='EXPIRED'
    finally:r.close()


def test_support_change_revises_signal_context_even_when_method_projection_is_cached():
    r=bindable_runtime()
    try:
        before=selected(r);old_count=r.analytics.projections.runs['engulfing']
        for b in bars([1.1]*20,frame='W1',end=bars()[0]['open_time']):r.market.ingest(Bar(**b))
        r.pump();after=selected(r)
        assert after['projection_fingerprint']==before['projection_fingerprint']
        assert after['context_fingerprint']!=before['context_fingerprint'] and after['opportunity_id']!=before['opportunity_id']
        assert r.analytics.projections.runs['engulfing']==old_count+1  # Newly available W1 only; cached H4 was not recomputed.
        assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',request(before)).status.value=='REJECTED'
    finally:r.close()


def test_persisted_signals_do_not_restore_authentication_or_market_authority(tmp_path):
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    from sfm_fx_new_age.services.orders import FixtureBroker
    from test_strategy_signal_positive import method_runtime
    path=tmp_path/'state.sqlite3';r,frame,now=method_runtime('engulfing',targets=True,path=path)
    before=selected(r);r.close()
    restored=ApplicationRuntime(path,clock=lambda:now,transport=FixtureBroker())
    try:
        assert restored.accounts.current is None and not restored.market.authority('EURUSD')
        values=rows(restored);assert all(x['state']!='SIGNAL' for x in values)
        assert restored.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',request(before)).status.value=='REJECTED'
        assert not restored.orders.transport.submissions
    finally:restored.close()


@pytest.mark.parametrize('field,value',[('symbol','USDJPY'),('side','SELL'),('expires_at','2099-01-01T00:00:00Z'),('entry_price','1.5'),('source_candidate_hash','DIFFERENT')])
def test_bound_geometry_and_lineage_tampering_fails_at_order_preview(field,value):
    r=bindable_runtime()
    try:
        row=selected(r);assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',request(row)).status.value=='ACCEPTED'
        signal=r.signals.get(r.strategy_signals.signal_id(row));signal[field]=value
        with pytest.raises(ValueError):r.strategy_signals.validate(signal)
        assert not r.orders.transport.submissions
    finally:r.close()


def test_tab4_current_state_queries_are_read_only_and_cannot_fake_historical_status():
    r=bindable_runtime()
    try:
        before=r.database.connection.total_changes
        for _ in range(3):values=rows(r)
        assert r.database.connection.total_changes==before
        with pytest.raises(ValueError):r.api(4).query('4.1',DataRequest('strategy_signals',symbol='EURUSD',as_of=FIXTURE_NOW))
    finally:r.close()


def test_custom_runtime_without_public_installers_is_explicitly_unavailable_not_a_callback_error():
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    r=ApplicationRuntime(analytical_installers=())
    try:
        assert len(rows(r))==83 and all(x['state']=='UNAVAILABLE' and not x['enabled'] for x in rows(r))
    finally:r.close()


def test_late_synthetic_backfill_cannot_restart_an_old_completed_event_lifetime():
    from test_public_strategies import seed
    shape=[(1.1,1.101,1.099,1.1)]*60+[(1.1,1.101,1.09,1.095),(1.094,1.103,1.093,1.102)]
    old=bars(shape,end=stamp(instant(FIXTURE_NOW)-timedelta(days=2)))
    old[-1]['available_at']=FIXTURE_NOW  # Explicitly labelled late fixture receipt.
    r=seed(rows=old)
    try:
        enable(r,'engulfing');row=selected(r)
        assert row['state']=='EXPIRED' and row['opportunity_id'] is None
        assert 'backfill does not renew' in row['reason']
        assert not r.orders.transport.submissions
    finally:r.close()


def test_new_ask_does_not_make_an_old_bid_fresh_for_binding():
    r=bindable_runtime()
    try:
        row=selected(r);at=stamp(instant(FIXTURE_NOW)+timedelta(seconds=31));r.clock=lambda:at
        r.market.set_quote(Quote(r.accounts.current.account_id,'EURUSD',D('1.1031'),D('1.1033'),FIXTURE_NOW,EPOCH,Origin.SYNTHETIC_FIXTURE,
                                bid_at=FIXTURE_NOW,ask_at=at,sequence=1))
        assert selected(r)['state']=='STALE' and not selected(r)['gates']['FRESH_TWO_SIDED_QUOTE']
        assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',request(row)).status.value=='REJECTED'
    finally:r.close()
