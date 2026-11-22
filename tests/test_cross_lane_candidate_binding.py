"""Explicitly synthetic cross-lane acceptance; no native strategy or broker proof."""
from decimal import Decimal
import pytest
from dataclasses import replace
from sfm_fx_new_age.contracts.analytics import Recipe,Lineage,Level,Evidence,MarketCandidate
from sfm_fx_new_age.contracts.extensions import AnalyticalResult
from sfm_fx_new_age.contracts.domain import Origin
from sfm_fx_new_age.contracts.enums import CommandStatus
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.services.geometry import atr_variants
from sfm_fx_new_age.services.orders import FixtureBroker
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,populate_fixture


@pytest.fixture
def pipeline(request):
    calls=[]
    mode=getattr(request,'param','VALID')
    def line(inputs):return Lineage(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],'D1',FIXTURE_NOW,
        Origin.SYNTHETIC_FIXTURE,'SYNTHETIC_SENSOR_V1',inputs['profile_hash'])
    def install(api):
        def sensor(inputs,deps):
            if inputs['symbol']!='EURUSD':return AnalyticalResult('NO_DATA')
            l=line(inputs)
            return AnalyticalResult('EVALUATED',{'synthetic':True},(
                Level('synthetic-zone',1,'TEST_ZONE',Decimal('1.09'),Decimal('1.11'),'BUY','CONFIRMED',('test-root',),l),
                Evidence('synthetic-evidence','synthetic-zone','test-root','test-cluster','test-fingerprint','TEST_DOMAIN','BUY',
                    Decimal('1.09'),Decimal('1.11'),Decimal('1'),Decimal('1'),'2026-11-06T12:00:00Z',l)))
        def compose(inputs,deps):
            assert inputs['analytical_objects']['level'][0]['level_id']=='synthetic-zone'
            assert inputs['analytical_objects']['evidence'][0]['evidence_id']=='synthetic-evidence'
            calls.append(inputs['symbol'])
            variants=atr_variants(setup_id='synthetic-recipe-setup',side='BUY',entry=Decimal('1.1'),anchor=Decimal('1.09'),
                atr=Decimal('0.001'),pip=Decimal('0.0001'),tick=Decimal('0.00001'),target=Decimal('1.12'))
            return (MarketCandidate('synthetic-candidate','synthetic-recipe-setup',1,'synthetic-recipe',1,'synthetic-zone','BUY',
                Decimal('1.1'),Decimal('1.09'),Decimal('1.12'),('synthetic-evidence',),variants,line(inputs),
                '2026-11-06T12:00:00Z',Decimal('80'),Decimal('80'),gates=tuple((f'QG{i:02d}',None if mode=='UNKNOWN_GATE' and i==14 else True) for i in range(1,15))),)
        api.register_producer('SMC_STRUCTURE',sensor,method_version='SYNTHETIC_SENSOR_V1',source_ref='SYNTHETIC_TEST_ONLY',trigger_frames=('D1',))
        api.register_recipe(Recipe('synthetic-recipe',1,'Synthetic acceptance, not a real strategy',('SMC_STRUCTURE',),'SYNTHETIC_TEST_ONLY','test-profile'),compose)
    r=ApplicationRuntime(clock=lambda:FIXTURE_NOW,transport=FixtureBroker(),analytical_installers=(install,))
    populate_fixture(r);r.pump()
    assert r.api(3).command('3.1','ENABLE_RECIPE',{'recipe_id':'synthetic-recipe','version':1,'enabled':True}).status is CommandStatus.ACCEPTED
    r.pump()
    candidate=r.api(4).query('4.2',DataRequest('market_candidates'))['rows'][0]
    payload={'candidate_id':candidate['candidate_id'],'candidate_revision':candidate['revision'],'variant_id':candidate['variants'][0]['variant_id'],
        'units':'1000','expected_version':0,'user_initiated':True}
    yield r,payload,calls
    r.close()


def test_analytical_candidate_binding_is_human_only_and_never_sends_an_order(pipeline):
    r,payload,calls=pipeline
    assert calls==['EURUSD']
    r.analytics.refresh('EURUSD');assert calls==['EURUSD']
    assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload|{'user_initiated':False}).status is CommandStatus.REJECTED
    assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload).status is CommandStatus.ACCEPTED
    signal=next(v for v in r.signals.all() if v['market_candidate_id'])
    assert signal['source_candidate_hash'] and signal['profile']=='RESEARCH_ONLY'
    assert r.orders.transport.submissions==[]
    before=r.database.connection.total_changes
    preview=r.orders.preview(signal['signal_id'],1,acknowledge_research=True)
    assert preview['status']=='PREFLIGHT_VALID'
    assert r.database.connection.total_changes==before
    result=r.api(4).command('4.1','ISSUE',{'signal_id':signal['signal_id'],'revision':1,'user_initiated':True,'acknowledge_research':True})
    assert result.status is CommandStatus.ACCEPTED
    assert len(r.orders.transport.submissions)==1
    assert r.database.orders()[0]['state']=='ACCEPTED_PENDING'


def test_recipe_deactivation_invalidates_bound_signal_before_issue(pipeline):
    r,payload,_=pipeline
    assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload).status is CommandStatus.ACCEPTED
    signal=next(v for v in r.signals.all() if v['market_candidate_id'])
    r.api(3).command('3.1','ENABLE_RECIPE',{'recipe_id':'synthetic-recipe','version':1,'enabled':False});r.pump()
    result=r.api(4).command('4.1','ISSUE',{'signal_id':signal['signal_id'],'revision':1,'user_initiated':True,'acknowledge_research':True})
    assert result.status is CommandStatus.REJECTED
    assert r.orders.transport.submissions==[]


def test_stale_evaluation_or_revision_cannot_bind(pipeline):
    r,payload,_=pipeline
    original=r.research.query('market_candidate',scope=r.market.scope_id,epoch='SYNTHETIC-FIXTURE-EPOCH-1',symbol='EURUSD',as_of=FIXTURE_NOW)[0]
    key=next(k for k in r.analytics.recipe_status if 'synthetic-recipe' in k and 'EURUSD' in k)
    r.analytics.recipe_status[key]['candidate_hashes']={}
    assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload).status is CommandStatus.REJECTED
    assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload|{'candidate_revision':2}).status is CommandStatus.REJECTED
    assert r.orders.transport.submissions==[]


@pytest.mark.parametrize('pipeline',['UNKNOWN_GATE'],indirect=True)
def test_unknown_qualification_gate_cannot_be_human_acknowledged_away(pipeline):
    r,payload,_=pipeline
    assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload).status is CommandStatus.REJECTED
    assert r.orders.transport.submissions==[]
