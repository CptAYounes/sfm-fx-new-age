from dataclasses import replace
from decimal import Decimal

import pytest

from sfm_fx_new_age.contracts.domain import PAIRS, Bar, Candidate, Origin, SymbolSpec, record
from sfm_fx_new_age.contracts.models import Event
from sfm_fx_new_age.services.catalogues import Truth, evaluate_rule
from sfm_fx_new_age.testing.fixtures import FIXTURE_EPOCH, FIXTURE_NOW


@pytest.mark.parametrize('symbol', PAIRS)
def test_each_pair_has_causal_context_and_completed_w1_atr(runtime, symbol):
    context = runtime.market.context(symbol, FIXTURE_NOW, FIXTURE_EPOCH)
    assert context['missing'] == []
    expected = Decimal('4') if symbol.endswith('JPY') else Decimal('0.04')
    assert Decimal(context['w1_atr14']) == expected
    for frame in ('W1','D1','H4'):
        assert context['bars'][frame]['origin'] == 'SYNTHETIC_FIXTURE'


def test_future_availability_and_source_epochs_do_not_leak(runtime):
    assert runtime.market.context('EURUSD', '2025-01-01T00:00:00Z', FIXTURE_EPOCH)['w1_atr14'] is None
    assert runtime.market.context('EURUSD', FIXTURE_NOW, 'other-epoch')['missing']
    bar = Bar(**runtime.database.list('bar')[0])
    assert runtime.market.bars(bar.symbol, bar.timeframe, '2020-01-01T00:00:00Z', bar.source_epoch) == ()


def test_ohlc_validation_and_invalid_symbol(runtime):
    body = runtime.database.list('bar')[0]
    with pytest.raises(ValueError): Bar(**(body | {'low':'1000000'}))
    with pytest.raises(ValueError): Bar(**(body | {'symbol':'XAUUSD'}))
    with pytest.raises(ValueError): Bar(**(body | {'close_time':body['open_time']}))


def test_decimal_nan_and_off_grid_rejected(runtime):
    spec = runtime.market.spec('FIXTURE-ACCOUNT','EURUSD')
    with pytest.raises(ValueError): spec.validate_order(Decimal('NaN'),Decimal('1000'))
    with pytest.raises(ValueError): spec.validate_order(Decimal('1.100001'),Decimal('1000'))
    with pytest.raises(ValueError): spec.validate_order(Decimal('1.1'),Decimal('1500'))


def test_event_payload_is_recursively_immutable():
    source = {'nested':{'items':[1,2]}}
    event = Event('TEST','TEST',source)
    source['nested']['items'].append(3)
    assert event.payload['nested']['items'] == (1,2)
    with pytest.raises(TypeError): event.payload['nested']['new'] = 1


def test_three_valued_rule_unknown_and_type_units(runtime):
    node={'op':'EQ','variable':'missing','unit':'boolean','value':True}
    assert evaluate_rule(node,{}) is Truth.UNKNOWN
    assert evaluate_rule({'op':'NOT','child':node},{}) is Truth.UNKNOWN
    assert evaluate_rule({'op':'AND','children':[node, node]}, {}) is Truth.UNKNOWN
    fresh={'missing':{'value':True,'unit':'boolean','freshness':'CURRENT'}}
    assert evaluate_rule(node,fresh) is Truth.TRUE
    assert evaluate_rule(node,{'missing':fresh['missing'] | {'freshness':'STALE'}}) is Truth.UNKNOWN
    with pytest.raises(ValueError): evaluate_rule(node,{'missing':fresh['missing'] | {'unit':'pips'}})
    with pytest.raises(ValueError): evaluate_rule({'op':'PYTHON','value':'arbitrary'}, {})


def test_parameters_use_compare_and_swap_and_persist(runtime):
    from sfm_fx_new_age.contracts.analytics import ParameterDefinition
    runtime.catalogues.register_parameter(ParameterDefinition('risk.test','TEST_OWNER','number','ratio'))
    body=runtime.catalogues.set_parameter('risk.test','0.5',expected_version=0)
    assert body['version']==1
    with pytest.raises(ValueError): runtime.catalogues.set_parameter('risk.test','0.6',expected_version=0)
    with pytest.raises(ValueError): runtime.catalogues.set_parameter('oauth.token','unsafe',expected_version=0)
    assert runtime.database.get('parameter','risk.test')['value']=='0.5'


def test_signal_revisions_and_history_cannot_rebind_identity(runtime):
    body=runtime.signals.get('FIXTURE-SIGNAL-1')
    body.pop('state')
    candidate=Candidate(**(body | {'revision':2}))
    runtime.signals.propose(candidate)
    assert len(runtime.database.list('signal_revision'))==2
    with pytest.raises(ValueError): runtime.signals.propose(candidate)
    with pytest.raises(ValueError): runtime.signals.propose(replace(candidate,revision=3,symbol='GBPUSD'))
