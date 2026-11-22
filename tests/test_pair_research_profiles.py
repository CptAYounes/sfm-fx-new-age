from dataclasses import replace
import pytest
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.services.rules import validate_rule


def test_pair_research_profile_is_effective_only_for_exact_pair_account(runtime):
    runtime.pump();other=runtime.analytics.snapshot('GBPUSD');a=runtime.accounts.current
    p={'key':'order_block.lookback','value':8,'expected_version':0,'symbol':'EURUSD','expected_scope_id':a.scope_id}
    assert runtime.api(3).command('3.11','PROPOSE_VERSIONED_PARAM_CHANGE',p).status.value=='ACCEPTED'
    assert runtime._analytics_dirty=={'EURUSD'}
    runtime.pump();assert runtime.analytics.snapshot('GBPUSD')==other
    rows=runtime.api(3).query('3.11',DataRequest('pair_parameters',symbol='EURUSD'))['rows'];assert rows[0]['value']==8
    assert not runtime.api(3).query('3.11',DataRequest('pair_parameters',symbol='GBPUSD'))['rows']
    assert runtime.api(3).command('3.11','PROPOSE_VERSIONED_PARAM_CHANGE',p).status.value=='REJECTED'
    assert runtime.catalogues.parameter_value('order_block.lookback')==14
    runtime.accounts.select(replace(a,account_id='DIFFERENT'))
    assert runtime.api(3).command('3.11','PROPOSE_VERSIONED_PARAM_CHANGE',dict(p,expected_version=1)).status.value=='REJECTED'
    assert not runtime.api(3).query('3.11',DataRequest('pair_parameters',symbol='EURUSD'))['rows']
    assert not runtime.orders.transport.submissions


@pytest.mark.parametrize('rule',[
    {'op':'EQ','left':{'op':'VAR','variable':'missing'},'right':{'op':'CONST','unit':'price'}},
    {'op':'EQ','left':{'op':'VAR','variable':'missing'},'right':{'op':'HISTORY','variable':'missing','bars':True}},
    {'op':'AND','children':'not a list'},
    {'op':'VAR','variable':'missing','value':'unrelated'},
    {'op':'GT','left':5,'right':{'op':'CONST','value':1,'unit':'price'}},
])
def test_unknown_inputs_cannot_hide_a_malformed_rule_shape(rule):
    with pytest.raises(ValueError):validate_rule(rule)
