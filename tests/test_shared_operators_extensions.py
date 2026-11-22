from dataclasses import replace
from decimal import Decimal
import pytest

from sfm_fx_new_age.contracts.analytics import Lineage,Level,ParameterDefinition,MutableSurface,Recipe
from sfm_fx_new_age.contracts.domain import Origin,Bar
from sfm_fx_new_age.contracts.enums import CommandStatus
from sfm_fx_new_age.contracts.extensions import AnalyticalResult
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.services.orders import FixtureBroker
from sfm_fx_new_age.services.continuity import SessionCalendar
from sfm_fx_new_age.services.timeline import Tick
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,FIXTURE_EPOCH,populate_fixture


def test_command_rule_lifecycle_and_disabled_rule_consumption(runtime):
    api=runtime.api(3);rule={'op':'EQ','variable':'fixture.d1_ready','unit':'boolean','value':True}
    p={'rule_id':'rule-api','rule':rule}
    before=runtime.database.connection.total_changes
    assert api.command('3.10','SAVE_PREVIEW_ACTIVATE_RULE',p).status is CommandStatus.ACCEPTED
    assert runtime.database.connection.total_changes==before
    assert api.command('3.10','SAVE_PREVIEW_ACTIVATE_RULE',p|{'action':'save','expected_version':0}).status is CommandStatus.ACCEPTED
    assert api.command('3.10','SAVE_PREVIEW_ACTIVATE_RULE',p|{'action':'activate','version':1,'expected_version':1}).status is CommandStatus.ACCEPTED
    assert runtime.catalogues.evaluate_active('fixture.d1_ready')
    runtime.api(2).command('2.1','SET_CONSUMER_SWITCH',{'consumer_id':'analysis.rules','enabled':False})
    assert runtime.catalogues.evaluate_active('fixture.d1_ready')==[]
    assert api.command('3.10','SAVE_PREVIEW_ACTIVATE_RULE',p|{'action':'save','expected_version':0}).status is CommandStatus.REJECTED


def test_parameter_commands_have_effect_and_bands_cannot_overlap(runtime):
    api=runtime.api(3);runtime.pump();old=runtime.analytics.snapshot('EURUSD')['nodes']
    result=api.command('3.11','PROPOSE_VERSIONED_PARAM_CHANGE',{'key':'scanner.pivot_right','value':3,'expected_version':0})
    assert result.status is CommandStatus.ACCEPTED
    runtime.pump();new=runtime.analytics.snapshot('EURUSD')['nodes']
    lookup=lambda rows:next(v['fingerprint'] for v in rows if v['id']=='SWING_MAP')
    assert lookup(new)!=lookup(old)
    assert api.command('3.8','TUNE_BANDS',{'key':'geometry.band_0','value':'0.9','expected_version':0}).status is CommandStatus.REJECTED
    assert runtime.database.get('parameter','geometry.band_0') is None


def test_configuration_import_is_atomic_conflict_checked_and_cannot_activate_rules(runtime):
    api=runtime.api(2)
    configuration={'schema_version':1,'parameters':[{'key':'scanner.pivot_left','value':3}],
        'rules':[{'rule_id':'imported','rule':{'op':'EQ','variable':'fixture.d1_ready','unit':'boolean','value':True},'output':'DISPLAY'}]}
    p={'action':'import','configuration':configuration,'expected_versions':{'parameter:scanner.pivot_left':0,'rule:imported':1}}
    assert api.command('2.10','EXPORT_IMPORT_CONFIG',p).status is CommandStatus.REJECTED
    assert runtime.database.get('parameter','scanner.pivot_left') is None
    p['expected_versions']['rule:imported']=0
    assert api.command('2.10','EXPORT_IMPORT_CONFIG',p).status is CommandStatus.ACCEPTED
    assert runtime.database.get('rule','imported')['active'] is False
    assert runtime.catalogues.parameter_value('scanner.pivot_left')==3
    configuration['parameters'].append({'key':'oauth.token','value':'NEVER_A_REAL_SECRET'})
    assert api.command('2.10','EXPORT_IMPORT_CONFIG',p).status is CommandStatus.REJECTED
    assert runtime.database.get('parameter','scanner.pivot_left')['version']==1


def test_variable_values_do_not_cross_account_scopes(runtime):
    original=runtime.accounts.current
    assert runtime.catalogues.values()
    runtime.accounts.select(replace(original,account_id='OTHER'))
    assert runtime.catalogues.values()==[]
    runtime.catalogues.set_variable('fixture.d1_ready',False,'boolean')
    assert runtime.catalogues.values()[0]['value'] is False
    runtime.accounts.select(original)
    assert runtime.catalogues.values()[0]['value'] is True


def test_tick_timeline_never_publishes_initial_partial_or_fills_missing_bars(runtime):
    runtime.continuity.set_calendar('EURUSD',SessionCalendar('test','UTC',((0,604800),),source_ref='SYNTHETIC_ONLY'))
    make=lambda when,price:Tick('EURUSD',Decimal(price),when,when,FIXTURE_EPOCH,runtime.market.scope_id,Origin.SYNTHETIC_FIXTURE)
    runtime.timeline.ingest(make('2026-11-05T12:00:01Z','1.10'))
    runtime.timeline.ingest(make('2026-11-05T12:30:00Z','1.11'))
    runtime.timeline.ingest(make('2026-11-05T13:00:00Z','1.12'))
    rows=runtime.market.bars('EURUSD','H1','2026-11-05T13:00:00Z',FIXTURE_EPOCH)
    assert not any(b.open_time=='2026-11-05T12:00:00Z' for b in rows)
    runtime.timeline.ingest(make('2026-11-05T13:15:00Z','1.13'))
    runtime.timeline.ingest(make('2026-11-05T14:00:00Z','1.14'))
    closed=runtime.market.bars('EURUSD','H1','2026-11-05T14:00:00Z',FIXTURE_EPOCH)[-1]
    assert closed.open_time=='2026-11-05T13:00:00Z'
    assert (closed.open,closed.high,closed.close)==(Decimal('1.12'),Decimal('1.13'),Decimal('1.13'))
    assert closed.construction=='CANONICAL_BID_TICKS'
    runtime.timeline.ingest(make('2026-11-05T17:00:00Z','1.15'))
    assert runtime.continuity.coverage('EURUSD','H1','2026-11-05T17:00:00Z')['open_stream_gap']


def test_tab3_can_install_source_backed_producer_without_access_to_execution():
    retained=[]
    def installer(api):
        retained.append(api)
        assert not hasattr(api,'orders') and not hasattr(api,'database') and not hasattr(api,'command')
        def producer(inputs,deps):
            with pytest.raises(TypeError):inputs['symbol']='OTHER'
            line=Lineage(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],'D1',inputs['cutoff'],
                Origin.SYNTHETIC_FIXTURE,'TEST_SENSOR_V1',inputs['profile_hash'])
            return AnalyticalResult('EVALUATED',{'method':'SYNTHETIC_TEST_SENSOR'},
                (Level('test-level-'+inputs['symbol'],1,'TEST_LEVEL',Decimal('1'),Decimal('2'),'NEUTRAL','CONFIRMED',('test-root',),line),))
        api.register_producer('SMC_STRUCTURE',producer,method_version='TEST_SENSOR_V1',source_ref='SYNTHETIC_TEST_NOT_A_STRATEGY',trigger_frames=('D1',))
    r=ApplicationRuntime(clock=lambda:FIXTURE_NOW,transport=FixtureBroker(),analytical_installers=(installer,))
    try:
        populate_fixture(r);r.pump()
        rows=r.api(1).query('1.6',DataRequest('levels'))['rows']
        assert rows and rows[0]['level_id']=='test-level-EURUSD'
        assert r.analytics.snapshot('EURUSD')['outputs']['SMC_STRUCTURE']['method']=='SYNTHETIC_TEST_SENSOR'
        assert r.orders.transport.submissions==[]
        with pytest.raises(RuntimeError):retained[0].register_parameter(ParameterDefinition('too.late','STRATEGY_RECIPE_HOST','boolean','boolean'))
        before=r.analytics.scheduler.runs['SMC_STRUCTURE']
        old=r.market.bars('EURUSD','H1',FIXTURE_NOW,FIXTURE_EPOCH)[-1]
        r.market.ingest(replace(old,revision=2,available_at='2026-11-05T12:01:00Z'))
        r.analytics.clock=lambda:'2026-11-05T12:02:00Z'
        r.analytics.refresh('EURUSD')
        assert r.analytics.scheduler.runs['SMC_STRUCTURE']==before
    finally:r.close()


def test_execution_nodes_cannot_be_replaced_by_analytical_extension():
    def installer(api):api.register_producer('BAR_TIMELINE',lambda i,d:AnalyticalResult('EVALUATED',{}),method_version='test',source_ref='test',trigger_frames=('D1',))
    with pytest.raises(ValueError):ApplicationRuntime(analytical_installers=(installer,))


def test_bounded_query_pagination_requires_stable_hash(runtime):
    api=runtime.api(1);first=api.query('1.1',DataRequest('watchlist',limit=2))
    with pytest.raises(ValueError):DataRequest('watchlist',cursor=2,limit=2)
    second=api.query('1.1',DataRequest('watchlist',cursor=first['next_cursor'],limit=2,expected_hash=first['data_hash']))
    assert first['rows'][0]['symbol']!=second['rows'][0]['symbol']
    with pytest.raises(ValueError):api.query('1.1',DataRequest('watchlist',cursor=2,expected_hash='wrong'))


def test_analytical_variables_have_owned_causal_ingress_and_expire_across_epochs():
    from sfm_fx_new_age.contracts.analytics import VariableDefinition
    from sfm_fx_new_age.contracts.extensions import VariableUpdate
    def install(api):
        api.register_variable('SMC_STRUCTURE',VariableDefinition('synthetic.eurusd.ready','STRATEGY_RECIPE_HOST','boolean','boolean','SOURCE',
            symbol='EURUSD',timeframe='D1',max_age_seconds=10))
        def producer(inputs,deps):
            if inputs['symbol']!='EURUSD' or not inputs['bars'].get('D1'):return AnalyticalResult('NO_DATA')
            return AnalyticalResult('EVALUATED',{'synthetic':True},variables=(VariableUpdate('synthetic.eurusd.ready',True,FIXTURE_NOW),))
        api.register_producer('SMC_STRUCTURE',producer,method_version='SYNTHETIC_VARIABLE_V1',source_ref='SYNTHETIC_TEST_ONLY',trigger_frames=('D1',))
    r=ApplicationRuntime(clock=lambda:FIXTURE_NOW,transport=FixtureBroker(),analytical_installers=(install,))
    try:
        populate_fixture(r);r.pump()
        rule={'op':'EQ','variable':'synthetic.eurusd.ready','unit':'boolean','value':True}
        assert r.catalogues.preview_rule('test',rule,as_of=FIXTURE_NOW)['preview']=='TRUE'
        assert r.catalogues.preview_rule('test',rule,as_of='2026-11-05T12:00:11Z')['preview']=='UNKNOWN'
        r.market.activate_source('EURUSD','CHANGED_EPOCH',Origin.SYNTHETIC_FIXTURE.value)
        assert r.catalogues.preview_rule('test',rule,as_of=FIXTURE_NOW)['preview']=='UNKNOWN'
    finally:r.close()


def test_analytical_result_cannot_hide_a_variable_write_in_unavailable_state():
    from sfm_fx_new_age.contracts.extensions import VariableUpdate
    with pytest.raises(ValueError):AnalyticalResult('NO_DATA',variables=(VariableUpdate('test',True,FIXTURE_NOW),))
