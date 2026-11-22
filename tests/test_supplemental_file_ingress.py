"""Production local adapter paths with labelled input; no external feed is mocked as real."""
import hashlib,json,os,subprocess,sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import pytest
from sfm_fx_new_age.services.supplemental_files import SupplementalFileIngress,load_config,read_bytes
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW
from sfm_fx_new_age.testing.fixtures import stamp
from sfm_fx_new_age.contracts.domain import instant
from datetime import timedelta
from test_public_genuine_inputs import optional_case,DATA_METHODS
from test_public_strategies import seed,enable,chart


def write_json(path,data):
    path.write_text(json.dumps(data,allow_nan=False));path.chmod(0o600)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publication(folder,data,*,provider=None):
    folder.mkdir(parents=True,exist_ok=True);data=deepcopy(data);provider=provider or data['provider_id'];data['provider_id']=provider
    source=folder/'source.json';h=write_json(source,data)
    manifest=folder/'manifest.json';write_json(manifest,dict(schema_version=1,entries=[dict(file=source.name,sha256=h)]))
    config=folder/'config.json';write_json(config,dict(schema_version=1,providers=[dict(provider_id=provider,kinds=[data['kind']],origin=data['origin'],manifest_path=str(manifest))]))
    return config,manifest,source


def attach(r,config):
    r.supplemental_ingress=SupplementalFileIngress(r.analytics.supplemental,config,allow_fixture=True)
    r.supplemental_ingress.poll(force=True);r.pump()


@pytest.mark.parametrize('key',sorted(DATA_METHODS))
def test_every_optional_method_works_via_real_file_adapter_and_chart_no_manual_registration(tmp_path,key):
    rows,_,_,data=optional_case(key);r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id;config,manifest,source=publication(tmp_path,data)
        enable(r,key);before=chart(r)['strategy_layers'][0]
        if key=='cause_effect':
            assert before['state'] in {'READY','NO_SETUP'} and before['metrics']['profile']=='PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1'
        else:assert before['state']=='DATA_UNAVAILABLE'
        attach(r,config);body=chart(r)['strategy_layers'][0]
        assert body['state']=='READY',(key,body)
        assert body['metrics']['input_origin']=='SYNTHETIC_FIXTURE'
        status=r.supplemental_ingress.status();assert status['providers'][0]['state']=='ADMITTED' and status['providers'][0]['admitted']==1
        assert not status['network_enabled'] and status['read_only_files']
        assert 'manifest_path' not in str(status) and str(tmp_path) not in str(status)
        # Disabling the strategy is still a display/producer decision, not adapter authority.
        enable(r,key,False);assert not chart(r)['strategy_layers']
        assert source.read_bytes() and not r.orders.transport.submissions and not r.orders.transport.cancellations
    finally:r.close()


def test_batch_rollback_no_partial_database_records_or_events(tmp_path):
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id;store=r.analytics.supplemental;store.register_provider(data['provider_id'],kinds=[data['kind']],origin=data['origin'])
        second=deepcopy(data);second['revision']=2 # Does not advance publication availability.
        before=len(r.database.list('supplemental_evidence'))
        with pytest.raises(ValueError):store.accept_many([SupplementalEvidence(**data),SupplementalEvidence(**second)])
        assert len(r.database.list('supplemental_evidence'))==before
        assert store.snapshot('EURUSD',FIXTURE_NOW)=={}
    finally:r.close()


def test_corruption_withdrawal_recovery_and_published_membership(tmp_path):
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id;config,manifest,source=publication(tmp_path,data);attach(r,config);enable(r,'vwap_bands');old=chart(r)['strategy_layers'][0]
        source.write_text(source.read_text()+' ');r.supplemental_ingress.poll(force=True);r.pump()
        assert r.supplemental_ingress.status()['providers'][0]['state']=='REJECTED'
        assert not r.analytics.supplemental.providers and chart(r)['strategy_layers'][0]['state']=='DATA_UNAVAILABLE'
        publication(tmp_path,data);r.supplemental_ingress.poll(force=True);r.pump();assert chart(r)['strategy_layers']==[old]
        # A manifest omitting a previously admitted kind must not keep it available.
        other=deepcopy(data);other.update(kind='INTRABAR_PRICES',unit='OBSERVED_PRICE',parameters={'tick_size':'.00001','slot_coverage_complete':True})
        for row in other['records']:row.pop('quantity')
        conf=json.loads(config.read_text());conf['providers'][0]['kinds'].append('INTRABAR_PRICES');write_json(config,conf)
        publication(tmp_path,other);write_json(config,conf)
        r.supplemental_ingress._withdraw(data['provider_id']);attach(r,config)
        assert 'TRADED_PRINTS' not in r.analytics.supplemental.snapshot('EURUSD',FIXTURE_NOW)
        assert chart(r)['strategy_layers'][0]['state']=='DATA_UNAVAILABLE'
    finally:r.close()


@pytest.mark.parametrize('mutation',[
 lambda m:m['entries'][0].update(file='../source.json'),
 lambda m:m['entries'][0].update(sha256='X'*64),
 lambda m:m.update(unknown='unsupported'),
 lambda m:m['entries'].append(m['entries'][0]),
 lambda m:m.update(schema_version=True),
 lambda m:m.update(entries=[]),
])
def test_invalid_manifest_is_never_admitted(tmp_path,mutation):
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id;config,manifest,source=publication(tmp_path,data);body=json.loads(manifest.read_text());mutation(body);write_json(manifest,body);attach(r,config)
        assert r.supplemental_ingress.status()['providers'][0]['state']=='REJECTED'
        assert not r.database.list('supplemental_evidence') and not r.analytics.supplemental.providers
    finally:r.close()


@pytest.mark.parametrize('mutation',[
 lambda d:d.update(source_epoch='OTHER'),lambda d:d.update(scope_id='OTHER'),lambda d:d.update(origin='LIVE_OBSERVED')])
def test_source_mismatch_does_not_relabel_or_select_any_account(tmp_path,mutation):
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows)
    try:
        account=r.accounts.current;data['scope_id']=r.market.scope_id;mutation(data);config,_,_=publication(tmp_path,data);attach(r,config)
        assert r.supplemental_ingress.status()['providers'][0]['state']=='WAITING_SCOPE'
        assert r.accounts.current==account and not r.database.list('supplemental_evidence')
    finally:r.close()


def test_restart_requires_explicit_configuration_and_current_scope(tmp_path):
    rows,_,_,data=optional_case('vwap_bands');path=tmp_path/'state.sqlite3';r=seed(path,rows=rows);account=r.accounts.current
    data['scope_id']=r.market.scope_id;config,manifest,source=publication(tmp_path/'inputs',data);attach(r,config);enable(r,'vwap_bands');assert chart(r)['strategy_layers'][0]['state']=='READY';r.close()
    for explicit in (False,True):
        r=ApplicationRuntime(path,clock=lambda:FIXTURE_NOW,supplemental_config=None)
        try:
            if explicit:
                # Synthetic acceptance is deliberately injected only in this labelled test.
                r.supplemental_ingress=SupplementalFileIngress(r.analytics.supplemental,config,allow_fixture=True)
            r.pump();assert r.accounts.current is None and not r.analytics.supplemental.providers and not r.connector.workers
            r.accounts.select(account);r.supplemental_ingress.poll(force=True);r.pump()
            assert chart(r)['strategy_layers'][0]['state']==('READY' if explicit else 'DATA_UNAVAILABLE')
        finally:r.close()


@pytest.mark.parametrize('body',[
 b'{"schema_version":1,"schema_version":1,"providers":[]}',
 b'{"schema_version":1,"providers":NaN}',
 b'{"schema_version":true,"providers":[]}',
 b'{"schema_version":1,"providers":[]}',
])
def test_config_rejects_duplicate_nonfinite_bool_and_empty(tmp_path,body):
    p=tmp_path/'config.json';p.write_bytes(body);p.chmod(0o600)
    with pytest.raises(ValueError):load_config(p)


def test_private_regular_files_only_and_no_fixture_authority_by_default(tmp_path):
    _,_,_,data=optional_case('vwap_bands');config,manifest,source=publication(tmp_path,data)
    with pytest.raises(ValueError,match='explicit fixture'):load_config(config)
    assert load_config(config,allow_fixture=True)
    config.chmod(0o666)
    with pytest.raises(ValueError):load_config(config,allow_fixture=True)
    config.chmod(0o600);link=tmp_path/'link.json';link.symlink_to(config)
    with pytest.raises(ValueError):load_config(link,allow_fixture=True)
    pipe=tmp_path/'pipe.json';os.mkfifo(pipe,0o600)
    with pytest.raises(ValueError):read_bytes(pipe,100)
    with pytest.raises(ValueError):read_bytes(source,2)


def test_manifest_swap_during_read_no_admission(tmp_path,monkeypatch):
    import sfm_fx_new_age.services.supplemental_files as mod
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id;config,manifest,source=publication(tmp_path,data);actual=mod.read_bytes
        def racing(path,budget):
            b=actual(path,budget)
            if Path(path)==source:manifest.write_text(manifest.read_text()+' ')
            return b
        monkeypatch.setattr(mod,'read_bytes',racing);attach(r,config)
        assert r.supplemental_ingress.status()['providers'][0]['state']=='REJECTED' and not r.database.list('supplemental_evidence')
    finally:r.close()


@pytest.mark.parametrize('key',['dom_imbalance','cot_macro','calendar_context'])
def test_semantically_malformed_source_batch_rejected_before_persistence(tmp_path,key):
    rows,_,_,data=optional_case(key);r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id
        if key=='dom_imbalance':data['records'][0]['bids'][0][0]='2'
        elif key=='cot_macro':data['records'][0]['long']='-1'
        else:data['records'][0]['title']=''
        config,_,_=publication(tmp_path,data);attach(r,config)
        assert r.supplemental_ingress.status()['providers'][0]['state']=='REJECTED' and not r.database.list('supplemental_evidence')
    finally:r.close()


def test_cli_configuration_validation_has_no_qt_database_or_ingestion(tmp_path):
    _,_,_,data=optional_case('vwap_bands');config,_,_=publication(tmp_path,data)
    code="import sys; from sfm_fx_new_age.__main__ import main; code=main(); assert 'PySide6' not in sys.modules and 'sfm_fx_new_age.app' not in sys.modules; raise SystemExit(code)"
    run=subprocess.run([sys.executable,'-c',code,'--fixture-session','--validate-supplemental-config',str(config)],capture_output=True,text=True,timeout=15)
    assert run.returncode==0,run.stderr
    body=json.loads(run.stdout);assert body['result']=='VALID_CONFIGURATION_ONLY' and not body['network_started'] and not body['input_files_read'] and body['records_admitted']==0
    bad=subprocess.run([sys.executable,'-c',code,'--validate-supplemental-config',str(config)],capture_output=True,text=True,timeout=15)
    assert bad.returncode==2 and str(tmp_path) not in bad.stdout


def test_catalogue_has_frozen_read_only_source_status_not_ingestion_handle(tmp_path):
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id;config,_,_=publication(tmp_path,data);attach(r,config)
        result=thaw(r.api(3).query('3.1',DataRequest('strategy_catalogue',symbol='EURUSD',timeframe='H4')))
        assert result['input_sources']['configured'] and result['input_sources']['providers'][0]['state']=='ADMITTED'
        assert r.architecture_summary()['subtabs_by_tab']=={'1':10,'2':10,'3':13,'4':9}
    finally:r.close()


def test_file_correction_cannot_roll_back_or_resurrect_older_publication(tmp_path):
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows);now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        data['scope_id']=r.market.scope_id;config,_,_=publication(tmp_path,data);attach(r,config);enable(r,'vwap_bands')
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(seconds=1));changed=deepcopy(data);changed.update(revision=2,available_at=now[0]);changed['records'][0]['quantity']='2'
        publication(tmp_path,changed);r.supplemental_ingress.poll(force=True);r.pump();assert r.analytics.supplemental.snapshot('EURUSD',now[0])['TRADED_PRINTS']['revision']==2
        publication(tmp_path,data);r.supplemental_ingress.poll(force=True);r.pump()
        assert r.supplemental_ingress.status()['providers'][0]['state']=='REJECTED' and r.analytics.supplemental.snapshot('EURUSD',now[0])=={}
        assert chart(r)['strategy_layers'][0]['state']=='DATA_UNAVAILABLE'
    finally:r.close()


@pytest.mark.parametrize('payload_mutation',[
 lambda d:d.update(schema_version=True),
 lambda d:d['records'][0].update(orders=[{'command':'ISSUE'}]),
 lambda d:d.update(parameters={'arbitrary_python':'not executable'}),
 lambda d:d.update(window_start=1),
 lambda d:d['records'][0].update(time={}),
 lambda d:d.update(source_ref={'not':'a source reference'}),
])
def test_exact_wire_schema_has_no_extra_record_or_execution_fields(tmp_path,payload_mutation):
    rows,_,_,data=optional_case('vwap_bands');r=seed(rows=rows)
    try:
        data['scope_id']=r.market.scope_id;payload_mutation(data);config,_,_=publication(tmp_path,data);attach(r,config)
        assert r.supplemental_ingress.status()['providers'][0]['state']=='REJECTED' and not r.database.list('supplemental_evidence')
    finally:r.close()
