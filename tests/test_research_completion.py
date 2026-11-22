"""Product research pipeline on explicitly synthetic OHLC; never connected proof."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import json
import pytest
from sfm_fx_new_age.contracts.domain import record,instant,Origin
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.tabs.tab3.candidates import CANDIDATE_RECIPE,compose_candidates
from sfm_fx_new_age.tabs.tab3.order_blocks import RECIPE_ID
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,stamp
from test_order_block_workflow import seeded,pattern,EPOCH,enable


def complete_inputs(r):
    r.market.activate_source('EURUSD',EPOCH,'SYNTHETIC_FIXTURE')
    for frame in ('W1','D1','H4'):
        for bar in pattern(frame):r.market.ingest(bar)
    q=r.market.quote(r.accounts.current.account_id,'EURUSD');r.market.set_quote(replace(q,source_epoch=EPOCH))
    enable(r)
    result=r.api(3).command('3.1','ENABLE_RECIPE',{'recipe_id':CANDIDATE_RECIPE,'version':1,'enabled':True})
    assert result.status.value=='ACCEPTED';r.pump()


def candidates(r):return list(r.api(3).query('3.13',DataRequest('market_candidates'))['rows'])


def test_shipped_composer_generates_actual_atr_research_candidate_with_honest_gates():
    r=seeded()
    try:
        complete_inputs(r);rows=candidates(r);assert rows
        c=rows[-1]
        assert c['recipe_id']==CANDIDATE_RECIPE and c['research_state']=='RESEARCH_UNCALIBRATED'
        assert c['lineage']['origin']=='SYNTHETIC_FIXTURE' and c['lineage']['timeframe']=='H4'
        assert len(c['gates'])==14 and len(c['variants'])==4
        assert c['blockers'] and any('QG' in v for v in c['blockers'])
        # One price-structure family is not three independent confirmations.
        assert dict(c['gates'])['QG14'] is False
        assert c['confidence'] is not None and c['quality'] is None
        assert not r.database.orders() and not r.signals.all()[-1].get('market_candidate_id')
        ev=r.research.query('evidence',scope=r.market.scope_id,epoch=EPOCH,symbol='EURUSD',as_of=FIXTURE_NOW)
        assert ev and all(e['domain']=='PRICE_STRUCTURE' for e in ev)
        assert not r.orders.transport.submissions
        old=rows;r.analytics.refresh('EURUSD');assert candidates(r)==old
    finally:r.close()


def test_research_candidate_disable_and_price_staleness_cannot_bind_or_issue():
    r=seeded()
    try:
        complete_inputs(r);c=candidates(r)[-1]
        payload={'candidate_id':c['candidate_id'],'candidate_revision':c['revision'],'variant_id':c['variants'][0]['variant_id'],
            'units':'1000','expected_version':0,'user_initiated':True}
        result=r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload)
        assert result.status.value=='REJECTED' and not r.orders.transport.submissions
        r.api(3).command('3.1','ENABLE_RECIPE',{'recipe_id':CANDIDATE_RECIPE,'version':1,'enabled':False});r.pump()
        assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload).status.value=='REJECTED'
        assert not r.database.orders()
    finally:r.close()


def test_missing_w1_never_fabricates_atr_or_candidates():
    r=seeded()
    try:
        enable(r);r.api(3).command('3.1','ENABLE_RECIPE',{'recipe_id':CANDIDATE_RECIPE,'version':1,'enabled':True});r.pump()
        assert not candidates(r)
    finally:r.close()


def test_evidence_corrections_expire_without_rewriting_historical_research():
    r=seeded();now=[FIXTURE_NOW];r.clock=r.analytics.clock=lambda:now[0]
    try:
        complete_inputs(r);old=candidates(r);old_ev=r.research.query('evidence',scope=r.market.scope_id,epoch=EPOCH,symbol='EURUSD',as_of=FIXTURE_NOW)
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(minutes=1))
        last=pattern()[-1];r.market.ingest(replace(last,close=D('1.1040'),revision=2,available_at=now[0]));r.pump()
        # All prior output remains historical; the current recipe no longer owns a H4 candidate.
        key=json.dumps([r.market.scope_id,EPOCH,CANDIDATE_RECIPE,'EURUSD'])
        assert not r.analytics.recipe_status[key].get('candidate_hashes')
        assert r.research.query('evidence',scope=r.market.scope_id,epoch=EPOCH,symbol='EURUSD',as_of=FIXTURE_NOW)==old_ev
        assert not r.orders.transport.submissions
    finally:r.close()


def test_parameter_profile_change_archives_old_zones_without_illegal_republication():
    r=seeded()
    try:
        complete_inputs(r);before=r.analytics.snapshot('EURUSD')['profile_hash']
        old=r.api(1).query('1.4',DataRequest('chart',symbol='EURUSD',timeframe='H4'))['levels'];assert old
        result=r.api(3).command('3.11','PROPOSE_VERSIONED_PARAM_CHANGE',{'key':'order_block.lookback','value':12,
            'expected_version':0,'symbol':'EURUSD','expected_scope_id':r.market.scope_id})
        assert result.status.value=='ACCEPTED';r.pump()
        assert not r.router.errors and not r.analytics.scheduler.errors
        profile=r.analytics.snapshot('EURUSD')['profile_hash'];assert profile!=before
        current=r.api(1).query('1.4',DataRequest('chart',symbol='EURUSD',timeframe='H4'))['levels'];assert current
        assert all(v['lineage']['profile_hash']==profile for v in current)
        history=r.research.query('level',scope=r.market.scope_id,epoch=EPOCH,symbol='EURUSD',as_of=FIXTURE_NOW,history=True)
        assert any(v['lineage']['profile_hash']==before for v in history)
    finally:r.close()
