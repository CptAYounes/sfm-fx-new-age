"""Labelled engineering controls, not original broker or full-book acceptance."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import pytest

from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.public_projection_inputs import optional_projection_source, ProjectionInputUnavailable
from sfm_fx_new_age.contracts.public_strategies import BY_KEY, METHODS
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.services.public_projections import PublicProjectionService
from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
from sfm_fx_new_age.tabs.tab3.public_features import Features
from sfm_fx_new_age.services.scanner import confirmed_swings
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW, stamp
from test_public_genuine_inputs import optional_case
from test_public_strategies import seed, enable, chart


def broker_case():
    rows, inputs, deps, old = optional_case('dom_imbalance')
    data = deepcopy(old)
    data['kind'] = 'BROKER_DEPTH'
    data['parameters'] = dict(clock_basis='LOCAL_RECEIPT_NOT_VENDOR_EVENT_TIME', native_sequence=False,
        full_book_complete=False, unknown_deleted_ids=0, subscription_acknowledged=True)
    data['records'][0].pop('sequence')
    data['valid_until'] = stamp(instant(data['records'][0]['time']) + timedelta(seconds=15))
    inputs['optional_evidence'] = {'BROKER_DEPTH': data}
    inputs['activity_alternatives'] = False
    return rows, inputs, deps, data


def compute(case):
    rows, inputs, deps, _ = case
    return evaluate('dom_imbalance', Features(rows, confirmed_swings(rows)), inputs, deps)


@pytest.mark.parametrize('alternatives', [False, True])
def test_genuine_broker_dom_is_not_a_tick_proxy_even_in_strict_mode(alternatives):
    case = broker_case()
    case[1]['activity_alternatives'] = alternatives
    before = deepcopy(case[1])
    result = compute(case)
    assert case[1] == before
    m = result['metrics']
    assert m['genuine_displayed_depth'] and m['alternative'] is False
    assert not any(m[k] for k in ('native_sequence', 'full_book_complete', 'strict_native_full_book_qualified',
        'executed_volume', 'known_aggressors', 'market_wide_volume', 'broker_fill_claim', 'venue_only'))
    assert m['measurement_unit'] == 'DISPLAYED_BASE_UNITS'
    assert m['source_kind'] == 'BROKER_DEPTH' and m['source_evidence_hash'] == digest(case[3])
    assert m['original_received_at'] == case[3]['records'][0]['time']
    assert Decimal(m['imbalance']) == (Decimal(15) - Decimal(2)) / Decimal(17)
    assert len(result['zones']) == 1 and result['zones'][0]['label'].startswith('Broker observed DOM')


@pytest.mark.parametrize('field,value', [('source_epoch', 'WRONG'), ('symbol', 'GBPUSD'),
    ('scope_id', 'WRONG'), ('origin', 'LIVE_OBSERVED')])
def test_broker_dom_cannot_cross_original_source_binding(field, value):
    case = broker_case()
    case[3][field] = value
    with pytest.raises(ValueError):
        compute(case)


@pytest.mark.parametrize('mutation', [
    lambda d: d['parameters'].update(native_sequence=True),
    lambda d: d['parameters'].update(full_book_complete=True),
    lambda d: d['parameters'].update(subscription_acknowledged=False),
    lambda d: d['parameters'].update(clock_basis='NATIVE_EVENT_TIME'),
    lambda d: d['records'][0].update(sequence=1),
    lambda d: d['records'][0].update(asks=[]),
    lambda d: d['records'][0]['bids'][0].__setitem__(0, '2'),
    lambda d: d['records'][0]['bids'][0].__setitem__(1, '0'),
])
def test_broker_dom_rejects_invented_native_fields_and_invalid_books(mutation):
    case = broker_case()
    mutation(case[3])
    with pytest.raises((ValueError, KeyError)):
        compute(case)


def test_receipt_age_not_envelope_publication_clock_controls_freshness():
    case = broker_case()
    case[3]['records'][0]['time'] = stamp(instant(FIXTURE_NOW) - timedelta(seconds=16))
    case[3]['records'][0]['available_at'] = case[3]['records'][0]['time']
    case[3]['valid_until'] = stamp(instant(FIXTURE_NOW) + timedelta(seconds=30))
    with pytest.raises(ProjectionInputUnavailable, match='original broker receipt'):
        compute(case)


def test_cache_identity_expiry_use_the_same_selected_broker_evidence():
    _, inputs, _, data = broker_case()
    data['valid_until'] = stamp(instant(FIXTURE_NOW) + timedelta(seconds=60))
    definition = BY_KEY['dom_imbalance']
    extra, until = PublicProjectionService.input_context(definition, inputs)
    assert extra['source'] is data and 'alternative_source' not in extra
    assert instant(until) == instant(data['records'][0]['time']) + timedelta(seconds=15)
    before = digest(extra)
    data['records'][0]['bids'][0][1] = '20'
    assert digest(PublicProjectionService.input_context(definition, inputs)[0]) != before


def test_explicit_bad_venue_evidence_is_not_hidden_by_broker_fallback():
    case = broker_case()
    _, _, _, explicit = optional_case('dom_imbalance')
    case[1]['optional_evidence']['VENUE_BOOK'] = explicit
    assert optional_projection_source('dom_imbalance', 'VENUE_BOOK', case[1]['optional_evidence']) is explicit
    explicit['records'][0]['sequence'] = 0
    with pytest.raises(ValueError):
        compute(case)


def test_checksum_and_native_chain_sources_keep_precedence_over_broker():
    case = broker_case()
    evidence = case[1]['optional_evidence']
    checksum = {'kind': 'VENUE_L2_CHECKSUM_BOOK'}
    chain = {'kind': 'VENUE_NATIVE_CHAIN_BOOK'}
    evidence['VENUE_L2_CHECKSUM_BOOK'] = checksum
    assert optional_projection_source('dom_imbalance', 'VENUE_BOOK', evidence) is checksum
    evidence['VENUE_NATIVE_CHAIN_BOOK'] = chain
    assert optional_projection_source('dom_imbalance', 'VENUE_BOOK', evidence) is chain


def test_genuine_broker_dom_does_not_satisfy_footprint_or_executed_volume():
    rows, inputs, deps, _ = broker_case()
    for key in ('footprint_delta', 'vwap_bands', 'volume_profile', 'volume_displacement', 'effort_result'):
        with pytest.raises(ProjectionInputUnavailable):
            evaluate(key, Features(rows, confirmed_swings(rows)), inputs, deps)


def test_ingress_strict_projection_read_expiry_and_disable_are_effective():
    rows, _, _, data = broker_case()
    r = seed(rows=rows)
    try:
        r.analytics.activity_alternatives = False
        data['scope_id'] = r.market.scope_id
        store = r.analytics.supplemental
        store.register_provider(data['provider_id'], kinds=['BROKER_DEPTH'], origin='SYNTHETIC_FIXTURE')
        store.accept(SupplementalEvidence(**data))
        enable(r, 'dom_imbalance')
        row = chart(r)['strategy_layers'][0]
        assert row['state'] == 'READY' and row['metrics']['genuine_displayed_depth']
        assert row['classification'] == 'BROKER_SCOPED_DISPLAYED_DEPTH_NOT_EXECUTED_VOLUME'
        assert row['name'] == 'Broker DOM · displayed-size imbalance'
        assert len(METHODS) == 83
        expires = instant(row['valid_until']) + timedelta(microseconds=1)
        expired = r.analytics.projections.read('EURUSD', 'H4', as_of=stamp(expires))
        target = next(v for v in expired if v['strategy_id'] == 'dom_imbalance')
        assert target['state'] == 'DATA_UNAVAILABLE' and not target['zones']
        enable(r, 'dom_imbalance', False)
        assert not chart(r)['strategy_layers']
        assert not r.orders.transport.submissions and not r.orders.transport.cancellations
    finally:
        r.close()
