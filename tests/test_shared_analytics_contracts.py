from dataclasses import replace
from decimal import Decimal
import json
import pytest

from sfm_fx_new_age.contracts.analytics import (Lineage,Level,Evidence,MarketCandidate,Overlay,Recipe,VariableDefinition,ParameterDefinition,MutableSurface)
from sfm_fx_new_age.contracts.domain import Origin,record
from sfm_fx_new_age.services.rules import evaluate_rule,Truth,validate_rule
from sfm_fx_new_age.services.research import ResearchStore


def line(**changes):
    return Lineage(**(dict(source_scope='market-feed-A',source_epoch='epoch-A',symbol='EURUSD',timeframe='D1',
        available_at='2026-01-01T00:00:00Z',origin=Origin.SYNTHETIC_FIXTURE,method_version='test-v1',profile_hash='test-profile')|changes))


@pytest.mark.parametrize('change',[{'source_scope':''},{'timeframe':'M2'},{'available_at':'2026-01-01'}, {'symbol':'XAUUSD'}])
def test_lineage_rejects_invalid_scope(change):
    with pytest.raises(ValueError): line(**change)


def test_analytical_revisions_are_immutable_causal_and_not_account_bound(runtime):
    store=ResearchStore(runtime.database,runtime.emit)
    original=Level('level',1,'SWING',Decimal('1.1'),Decimal('1.2'),'BUY','CONFIRMED',('event',),line())
    store.publish(original);store.publish(original)
    with pytest.raises(ValueError):store.publish(replace(original,high=Decimal('1.3')))
    store.publish(replace(original,revision=2,state='INVALIDATED',lineage=line(available_at='2026-01-02T00:00:00Z')))
    q=dict(scope='market-feed-A',epoch='epoch-A',symbol='EURUSD')
    assert store.query('level',**q,as_of='2026-01-01T12:00:00Z')[0]['state']=='CONFIRMED'
    assert store.query('level',**q,as_of='2026-01-03T00:00:00Z')[0]['state']=='INVALIDATED'
    assert store.query('level',**(q|{'epoch':'other'}),as_of='2026-01-03T00:00:00Z')==[]
    assert len(store.query('level',**q,as_of='2026-01-03T00:00:00Z',history=True))==2


@pytest.mark.parametrize('unit',['price','pips','ATR_MULTIPLE','confidence_index'])
def test_owner_parameter_registry_validation_atomicity_and_surface(runtime,unit):
    c=runtime.catalogues
    c.register_parameter(ParameterDefinition('test.bound','TEST_OWNER','number',unit,minimum=Decimal('0'),maximum=Decimal('2')))
    c.register_parameter(ParameterDefinition('test.enabled','TEST_OWNER','boolean','boolean'))
    c.register_surface(MutableSurface('test.surface','TEST_OWNER',('test.bound','test.enabled'),'3.11'))
    c.set_parameter('test.bound','1.2',expected_version=0)
    with pytest.raises(ValueError):c.set_parameter('test.bound','3',expected_version=1)
    with pytest.raises(ValueError):c.set_parameter('unknown','value',expected_version=0)
    with pytest.raises(ValueError):c.set_parameters({'test.enabled':(True,0),'test.bound':('1.3',0)})
    assert runtime.database.get('parameter','test.enabled') is None
    assert runtime.database.get('parameter','test.bound')['version']==1
    with pytest.raises(ValueError): c.register_surface(MutableSurface('bad','OTHER',('test.bound',),'3.11'))


def const(value,unit='ratio'):return {'op':'CONST','value':value,'unit':unit}

def comparison(op='GT'):
    return {'op':op,'left':{'op':'VAR','variable':'test.number'},'right':const(2)}


@pytest.mark.parametrize('op,expected',[('GT',True),('GE',True),('LT',False),('LE',False),('EQ',False),('NE',True)])
def test_typed_comparisons(op,expected):
    assert evaluate_rule(comparison(op),{'test.number':{'value':3,'unit':'ratio','freshness':'CURRENT'}}) is (Truth.TRUE if expected else Truth.FALSE)


@pytest.mark.parametrize('op,result',[('ADD',5),('SUB',1),('MUL',6),('DIV',Decimal('1.5'))])
def test_arithmetic_and_units(op,result):
    node={'op':'EQ','left':{'op':op,'left':const(3),'right':const(2)},'right':const(str(result))}
    assert evaluate_rule(node,{}) is Truth.TRUE
    bad={'op':'GT','left':{'op':'ADD','left':const(1,'price'),'right':const(2,'pips')},'right':const(0,'price')}
    with pytest.raises(ValueError): evaluate_rule(bad,{})


def test_temporal_rules_are_causal_and_bounded():
    values={'test.number':{'value':3,'unit':'ratio','freshness':'CURRENT','history':[
        {'value':1,'available_at':'2026-01-01T00:00:00Z'}, {'value':3,'available_at':'2026-01-02T00:00:00Z'}]}}
    cross={'op':'CROSSES_ABOVE','left':{'op':'VAR','variable':'test.number'},'right':const(2)}
    assert evaluate_rule(cross,values) is Truth.TRUE
    assert evaluate_rule(cross,values,as_of='2025-12-31T00:00:00Z') is Truth.UNKNOWN
    assert evaluate_rule({'op':'FOR_BARS','bars':2,'child':comparison()},values) is Truth.FALSE
    assert evaluate_rule({'op':'WITHIN_BARS','bars':2,'child':comparison()},values) is Truth.TRUE
    with pytest.raises(ValueError):evaluate_rule({'op':'FOR_BARS','bars':1000,'child':comparison()},values)
    with pytest.raises(ValueError):validate_rule({'op':'PYTHON','value':'bad'})


def test_explicit_rule_activation_history_and_dependency_outputs(runtime):
    c=runtime.catalogues
    c.register_variable_definition(VariableDefinition('test.number','TEST_OWNER','number','ratio','GLOBAL'))
    c.register_variable('test.number',3,'ratio',owner='TEST_OWNER')
    first=c.save_rule('test.rule',comparison(),expected_version=0)
    assert not c.evaluate_active('test.number')
    c.activate_rule('test.rule',first['version'],expected_version=1)
    assert c.evaluate_active('unrelated')==[]
    assert c.evaluate_active('test.number')[0]['result']=='TRUE'
    second=c.save_rule('test.rule',comparison('LT'),expected_version=1)
    assert c.evaluate_active('test.number')[0]['result']=='TRUE' # draft does not change active content
    c.activate_rule('test.rule',second['version'],expected_version=2)
    assert c.evaluate_active('test.number')[0]['result']=='FALSE'
    c.activate_rule('test.rule',1,expected_version=2) # explicit rollback
    assert c.evaluate_active('test.number')[0]['result']=='TRUE'
    c.suspend_rule('test.rule');assert c.evaluate_active('test.number')==[]
    with pytest.raises(ValueError): c.save_rule('broker-output',comparison(),output='ISSUE')
