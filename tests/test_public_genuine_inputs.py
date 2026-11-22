"""Optional source computations using explicit SYNTHETIC_FIXTURE envelopes only."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import pytest
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence,UNITS
from sfm_fx_new_age.contracts.domain import instant,record,Quote,Origin
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
from sfm_fx_new_age.tabs.tab3.public_features import Features
from sfm_fx_new_age.tabs.tab3.public_genuine_data import DATA_METHODS
from sfm_fx_new_age.services.scanner import confirmed_swings
from sfm_fx_new_age.storage.database import StateConflict
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,stamp
from test_public_strategies import bars,seed,enable,chart,EPOCH
from test_document_public_strategies import context,ob_shape


def envelope(kind,rows=None,*,parameters=None,scope='UNBOUND',start=None,end=FIXTURE_NOW):
    start=start or stamp(instant(end)-timedelta(hours=1));records=[]
    for i,r in enumerate(rows or []):
        t=stamp(instant(start)+timedelta(seconds=60+i*60));records.append(dict(id=f'LABELLED-FIXTURE-OBS-{i:05}',time=t,available_at=t,**r))
    body=dict(provider_id='LABELLED_TEST_ADAPTER_NOT_A_LIVE_FEED',kind=kind,scope_id=scope,source_epoch=EPOCH,symbol='EURUSD',origin='SYNTHETIC_FIXTURE',
              source_ref='fixture://labelled-public-model-unit-inputs',venue='LABELLED_FIXTURE_VENUE',instrument='EUR_FUTURE_FIXTURE' if kind=='CFTC_REPORT' else 'EURUSD',
              price_domain='FUTURES_CONTEXT' if kind=='CFTC_REPORT' else 'EVENT_CONTEXT' if kind=='OFFICIAL_CALENDAR' else 'SPOT_PAIR',unit=UNITS[kind],
              window_start=start,window_end=end,available_at=end,valid_until=stamp(instant(end)+timedelta(hours=1)),complete=True,records=tuple(records),parameters=parameters or {})
    return body


def optional_case(key,*,scope='UNBOUND'):
    shape=ob_shape() if key=='volume_displacement' else [(1.1,1.104,1.099,1.102)]*20+[(1.0992,1.1,1.098,1.0994)] if key=='effort_result' else None
    own=bars(shape) if shape else bars(n=90);inputs,deps=context(own)
    if key in {'volume_displacement','effort_result'}:
        data=envelope('TRADED_PRINTS',scope=scope,start=own[0]['open_time'])
        data['records']=tuple(dict(id=f'LABELLED-VOLUME-{i:05}',time=stamp(instant(b['open_time'])+timedelta(minutes=1)),available_at=stamp(instant(b['open_time'])+timedelta(minutes=1)),price=b['close'],quantity='30' if i==len(own)-1 else '1') for i,b in enumerate(own))
    elif key in {'vwap_bands','volume_profile'}:
        data=envelope('TRADED_PRINTS',[dict(price='1.1',quantity='1'),dict(price='1.2',quantity='3')],scope=scope,parameters={'tick_size':'.00001'})
    elif key=='profile_tpo':
        data=envelope('INTRABAR_PRICES',scope=scope,parameters={'tick_size':'.00001','slot_coverage_complete':True})
        data['records']=tuple(dict(id=f'TPO-OBS-{i}',time=stamp(instant(data['window_start'])+timedelta(minutes=m)),available_at=stamp(instant(data['window_start'])+timedelta(minutes=m)),price=p) for i,(m,p) in enumerate([(1,'1.10000'),(15,'1.10001'),(31,'1.10001'),(59,'1.10002')]))
    elif key=='cause_effect':
        data=envelope('POINT_FIGURE_TICKS',[dict(price=p) for p in ('1.10','1.15','1.12','1.16','1.12','1.17','1.13')],scope=scope)
        data['parameters']=dict(box_size='.01',reversal_boxes=3,count_line='1.13',count_start=data['window_start'],count_end=data['window_end'],side='BUY')
    elif key=='dom_imbalance':
        data=envelope('VENUE_BOOK',[dict(sequence=1,bids=[['1.1000','10'],['1.0999','5']],asks=[['1.1002','1'],['1.1003','1']])],scope=scope)
        data['records']=(dict(data['records'][0],time=stamp(instant(FIXTURE_NOW)-timedelta(seconds=1)),available_at=FIXTURE_NOW),)
    elif key=='footprint_delta':
        data=envelope('AGGRESSOR_PRINTS',[dict(price='1.1',quantity='3',aggressor='BUY'),dict(price='1.1',quantity='1',aggressor='SELL')],scope=scope)
    elif key=='cot_macro':
        data=envelope('CFTC_REPORT',[dict(currency='EUR',report_type='LEGACY_NONCOMMERCIAL',report_as_of=stamp(instant(FIXTURE_NOW)-timedelta(days=2)),long='70',short='30',open_interest='100')],scope=scope)
    elif key=='calendar_context':
        data=envelope('OFFICIAL_CALENDAR',[dict(currency='USD',title='LABELLED OFFICIAL RELEASE FIXTURE',importance='HIGH',scheduled_at=stamp(instant(FIXTURE_NOW)+timedelta(minutes=15)))],scope=scope,
                      parameters=dict(schedule_coverage_start=stamp(instant(FIXTURE_NOW)-timedelta(days=1)),schedule_coverage_end=stamp(instant(FIXTURE_NOW)+timedelta(days=1))))
    else:raise ValueError(key)
    inputs['optional_evidence']={DATA_METHODS[key]:data}
    return own,inputs,deps,data


@pytest.mark.parametrize('key',sorted(DATA_METHODS))
def test_every_real_input_algorithm_computes_from_typed_labelled_input(key):
    rows,inputs,deps,data=optional_case(key)
    SupplementalEvidence(**data)
    result=evaluate(key,Features(rows,confirmed_swings(rows)),inputs,deps)
    assert any(result[k] for k in ('markers','zones','series')),(key,result)
    assert result['metrics']['input_origin']=='SYNTHETIC_FIXTURE'
    assert result['metrics']['source_unit']==UNITS[DATA_METHODS[key]]
    if key=='vwap_bands':
        mean=(D('1.1')*1+D('1.2')*3)/4;variance=((D('1.1')-mean)**2*1+(D('1.2')-mean)**2*3)/4
        assert D(result['metrics']['vwap'])==mean
        assert D(result['metrics']['weighted_population_sd'])==variance.sqrt()
    elif key=='profile_tpo':
        assert result['zones'][0]['low']=='1.10001'
        assert D(result['metrics']['value_coverage'])>=D('.7')
    elif key=='volume_profile':assert D(result['zones'][0]['low'])==D('1.2')
    elif key=='footprint_delta':assert D(result['metrics']['delta'])==D(3)-D(1)
    elif key=='cot_macro':assert D(result['metrics']['mapped_net_fraction'])==(D(70)-D(30))/D(100)
    elif key=='cause_effect':assert result['metrics']['completed_count_columns']>=2 and result['metrics']['incomplete_final_column_excluded']
    elif key=='dom_imbalance':assert result['metrics']['venue_only'] and not result['metrics']['executed_volume']


@pytest.mark.parametrize('key',sorted(DATA_METHODS))
def test_missing_real_source_is_not_silently_ohlc_proxy(key):
    rows,inputs,deps,data=optional_case(key);inputs['optional_evidence']={}
    if key=='cause_effect':
        result=evaluate(key,Features(rows,confirmed_swings(rows)),inputs,deps)
        assert result['metrics']['profile']=='PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1'
        assert result['metrics']['price_method']=='ORIGINAL_COMPLETED_CLOSE_ONLY'
        assert result['metrics']['intrabar_sequence_inferred'] is False
    else:
        with pytest.raises(ProjectionInputUnavailable,match='requires a configured genuine source'):evaluate(key,Features(rows,confirmed_swings(rows)),inputs,deps)


@pytest.mark.parametrize('mutation',[
 lambda d:d.update(unit='TICK_VOLUME'),lambda d:d.update(price_domain='FOREIGN_FUTURES_AS_SPOT'),
 lambda d:d.update(complete=False),lambda d:d.update(records=(d['records'][0],d['records'][0])),
 lambda d:d.update(window_end=stamp(instant(d['available_at'])+timedelta(seconds=1))),
 lambda d:d['records'][0].update(aggressor='UNKNOWN')])
def test_real_input_contract_rejects_wrong_units_domains_completeness_and_aggressors(mutation):
    _,_,_,data=optional_case('footprint_delta');mutation(data)
    with pytest.raises((ValueError,KeyError)):SupplementalEvidence(**data)


@pytest.mark.parametrize('key',['vwap_bands','volume_profile','profile_tpo','cause_effect','dom_imbalance','footprint_delta','cot_macro','calendar_context'])
def test_actual_optional_ingress_scheduler_projection_and_disable_no_orders(key):
    rows,_,_,data=optional_case(key);r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id
        store=r.analytics.supplemental
        with pytest.raises(ValueError,match='No configured matching'):store.accept(SupplementalEvidence(**data))
        enable(r,key);before=chart(r)['strategy_layers'][0]
        if key=='cause_effect':
            assert before['state'] in {'READY','NO_SETUP'} and before['metrics']['profile']=='PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1'
        else:assert before['state']=='DATA_UNAVAILABLE'
        store.register_provider(data['provider_id'],kinds=(data['kind'],),origin='SYNTHETIC_FIXTURE')
        store.accept(SupplementalEvidence(**data));r.pump()
        after=chart(r)['strategy_layers'][0];assert after['state']=='READY',(key,after)
        assert after['fingerprint']!=before['fingerprint']
        enable(r,key,False);assert not chart(r)['strategy_layers']
        assert not r.orders.transport.submissions and not r.orders.transport.cancellations
    finally:r.close()


def test_optional_source_identity_revision_publication_expiry_and_restart_authority(tmp_path):
    rows,_,_,data=optional_case('vwap_bands');r=seed(tmp_path/'source.sqlite3',rows=rows);now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        data['scope_id']=r.market.scope_id;store=r.analytics.supplemental;store.register_provider(data['provider_id'],kinds=(data['kind'],),origin='SYNTHETIC_FIXTURE')
        with pytest.raises(ValueError):store.accept(SupplementalEvidence(**dict(data,source_epoch='WRONG-EPOCH')))
        store.accept(SupplementalEvidence(**data));enable(r,'vwap_bands');old=chart(r)['strategy_layers'][0]
        changed=deepcopy(data);changed['records'][0]['quantity']='2'
        with pytest.raises(StateConflict):store.accept(SupplementalEvidence(**changed))
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(minutes=1));changed.update(revision=2,available_at=now[0]);store.accept(SupplementalEvidence(**changed));r.pump();new=chart(r)['strategy_layers'][0]
        assert old['fingerprint']!=new['fingerprint'] and old['available_at']<new['available_at']
        assert chart(r,as_of=FIXTURE_NOW)['strategy_layers']==[old]
        now[0]=stamp(instant(data['valid_until'])+timedelta(seconds=1));r.pump();assert chart(r)['strategy_layers'][0]['state']=='DATA_UNAVAILABLE'
    finally:r.close()


def test_live_body_observation_rejects_stale_source_and_does_not_rebuild_closed_features():
    rows=bars([(1.1,1.102,1.09,1.095)]*20,end=stamp(instant(FIXTURE_NOW)-timedelta(hours=1)));r=seed(rows=rows);now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        enable(r,'previous_body_live');assert chart(r)['strategy_layers'][0]['state']=='DATA_UNAVAILABLE'
        counts=dict(r.analytics.scheduler.runs)
        q=Quote(r.accounts.current.account_id,'EURUSD',D('1.105'),D('1.106'),FIXTURE_NOW,EPOCH,Origin.SYNTHETIC_FIXTURE)
        r.market.set_quote(q);r.pump();body=chart(r)['strategy_layers'][0]
        assert body['state']=='READY' and body['markers'][0]['provisional'] and body['markers'][0]['time']==FIXTURE_NOW
        assert r.analytics.scheduler.runs==counts
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(minutes=1));r.pump();assert chart(r)['strategy_layers'][0]['state']=='DATA_UNAVAILABLE'
        assert not r.orders.transport.submissions
    finally:r.close()


@pytest.mark.parametrize('key,advance',[('vwap_bands',3601),('dom_imbalance',6),('calendar_context',2700)])
def test_time_sensitive_geometry_withdraws_at_read_before_next_pump(key,advance):
    rows,_,_,data=optional_case(key);r=seed(rows=rows);now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        data['scope_id']=r.market.scope_id;store=r.analytics.supplemental;store.register_provider(data['provider_id'],kinds=(data['kind'],),origin='SYNTHETIC_FIXTURE')
        store.accept(SupplementalEvidence(**data));enable(r,key);initial=chart(r)['strategy_layers'][0];assert initial['state']=='READY'
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(seconds=advance))
        withdrawn=chart(r)['strategy_layers'][0];assert withdrawn['state']=='DATA_UNAVAILABLE' and not any(withdrawn[k] for k in ('series','zones','markers'))
        assert chart(r,as_of=FIXTURE_NOW)['strategy_layers'][0]==initial
        r.pump();after=chart(r)['strategy_layers'][0]
        assert after['state']==('NO_SETUP' if key=='calendar_context' else 'DATA_UNAVAILABLE')
    finally:r.close()


def test_expired_correction_does_not_resurrect_older_valid_evidence():
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows);now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        data['scope_id']=r.market.scope_id;store=r.analytics.supplemental;store.register_provider(data['provider_id'],kinds=(data['kind'],),origin='SYNTHETIC_FIXTURE');store.accept(SupplementalEvidence(**data))
        changed=deepcopy(data);now[0]=stamp(instant(FIXTURE_NOW)+timedelta(seconds=1));changed.update(revision=2,available_at=now[0],valid_until=stamp(instant(FIXTURE_NOW)+timedelta(seconds=2)));store.accept(SupplementalEvidence(**changed))
        assert store.snapshot('EURUSD',now[0])['TRADED_PRINTS']['revision']==2
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(seconds=3));assert store.snapshot('EURUSD',now[0])=={}
        assert store.snapshot('EURUSD',FIXTURE_NOW)['TRADED_PRINTS']['revision']==1
    finally:r.close()


def test_restart_never_restores_provider_authority(tmp_path):
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    rows,_,_,data=optional_case('vwap_bands');path=tmp_path/'restart.sqlite3';r=seed(path,rows=rows);account=r.accounts.current
    try:
        data['scope_id']=r.market.scope_id;store=r.analytics.supplemental;store.register_provider(data['provider_id'],kinds=(data['kind'],),origin='SYNTHETIC_FIXTURE');store.accept(SupplementalEvidence(**data));enable(r,'vwap_bands');assert chart(r)['strategy_layers'][0]['state']=='READY'
    finally:r.close()
    r=ApplicationRuntime(path,clock=lambda:FIXTURE_NOW)
    try:
        assert not r.analytics.supplemental.providers and r.accounts.current is None and not r.connector.workers
        r.accounts.select(account);r.pump();assert r.analytics.supplemental.snapshot('EURUSD',FIXTURE_NOW)=={}
        assert chart(r)['strategy_layers'][0]['state']=='DATA_UNAVAILABLE'
    finally:r.close()
