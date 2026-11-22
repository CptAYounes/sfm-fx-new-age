"""Original reported NZDUSD replay and explicitly nonmarket refusal controls.

This is not a live session, independent source authentication, or aggressor proof.
The original native arrays/IDs/times/prices/quantities are never replaced by data
fixtures. Availability in this replay is the saved artifact-materialization clock.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import json
import os
import pytest

from sfm_fx_new_age.connector.fxopen_reported import (KINDS, SYMBOL, VENUE, addressed,
    corroborate, evidences, extend, from_ms, milliseconds, parse_range, signature, totals)
from sfm_fx_new_age.contracts.domain import instant, record
from sfm_fx_new_age.contracts.public_projection_inputs import optional_projection_source
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape


@pytest.fixture(scope='module')
def originals():
    metadata = json.loads(Path(os.environ['SFM_FXOPEN_ORIGINAL']).read_bytes())
    raw = []
    for item in metadata['originals']:
        data = Path(item['path']).read_bytes()
        assert sha256(data).hexdigest() == item['sha256']
        raw.append(data)
    times = [item['materialized_at'] for item in metadata['originals']]
    args = (metadata['start_ms'], metadata['middle_ms'], metadata['end_ms'], times)
    tape = corroborate(raw[0], raw[1], raw[2], *args)
    return metadata, raw, args, tape


def test_original_partition_parity_preserves_all_zero_and_reused_ids(originals):
    metadata, raw, args, tape = originals
    assert len(tape.native) > 2000
    assert sum(row['trade_id'] == 0 for row in tape.native) > 500
    assert len({row['trade_id'] for row in tape.native}) < len(tape.native)
    assert len(tape.prints()) == len(tape.native)
    assert len({row['id'] for row in tape.prints()}) == len(tape.native)
    assert all(row['id'].startswith('FXOPEN:LOCAL_ROW_SHA256:') for row in tape.prints())
    assert not tape.proof['native_id_uniqueness_claim']
    assert not tape.proof['native_sequence_claim']
    assert not tape.proof['aggressor_proven']
    assert not tape.proof['all_venue_execution_completeness_claim']
    assert Counter(row['quantity'] for row in tape.prints()) == Counter(str(row['base_volume']) for row in tape.native)


@pytest.mark.parametrize('fault', ('missing', 'duplicate', 'price_zero', 'quantity_zero', 'target_conflict',
    'negative_native_id', 'fractional_native_id', 'unknown_side', 'extra_field', 'wrong_time', 'regression', 'wrong_partition'))
def test_original_malformed_or_contradictory_response_refused(originals, fault):
    _, raw, args, tape = originals
    assert corroborate(raw[0], raw[1], raw[2], *args).native == tape.native
    changed = json.loads(raw[0])
    other = list(raw)
    if fault == 'missing':
        changed.pop(1)
    elif fault == 'duplicate':
        changed.insert(1, deepcopy(changed[1]))
    elif fault == 'price_zero':
        changed[1]['price'] = 0
    elif fault == 'quantity_zero':
        changed[1]['base_volume'] = 0
    elif fault == 'target_conflict':
        changed[1]['target_volume'] += 100
    elif fault == 'negative_native_id':
        changed[1]['trade_id'] = -1
    elif fault == 'fractional_native_id':
        changed[1]['trade_id'] = .5
    elif fault == 'unknown_side':
        changed[1]['type'] = 'Unknown'
    elif fault == 'extra_field':
        changed[1]['aggressor'] = 'BUY'
    elif fault == 'wrong_time':
        changed[1]['trade_timestamp'] = args[2]
    elif fault == 'regression':
        changed[0], changed[-1] = changed[-1], changed[0]
    elif fault == 'wrong_partition':
        other[1] = raw[2]
    other[0] = json.dumps(changed).encode()
    with pytest.raises(ValueError):
        corroborate(other[0], other[1], other[2], *args)


def test_exact_original_hour_totals_include_only_exhaustively_empty_zeros(originals):
    tape = originals[3]
    values = evidences(tape, 'RECORDED_REPLAY_CONTROL', 'RECORDED_REPLAY_CONTROL', '0.00001', ())
    by_kind = {value.kind: value for value in values}
    assert set(by_kind) == {'TRADED_PRINTS', 'EXECUTED_BAR_QUANTITIES'}
    for value in values:
        validate_wire_shape(value)
        assert value.venue == VENUE and value.symbol == SYMBOL
        assert not any('aggressor' in row for row in value.records)
    hours = by_kind['EXECUTED_BAR_QUANTITIES']
    assert len(hours.records) > 3000 and any(row['trade_count'] == 0 for row in hours.records)
    # Independent original-row interval inclusion, not the production prefix sum.
    total = Decimal(0)
    for hour in hours.records:
        lo, hi = milliseconds(hour['time']), milliseconds(hour['end_time'])
        native = [row for row in tape.native if lo <= row['trade_timestamp'] < hi]
        assert hour['trade_count'] == len(native)
        quantity = sum((Decimal(row['base_volume']) for row in native), Decimal(0))
        assert Decimal(hour['quantity']) == quantity
        assert (quantity == 0) == (len(native) == 0)
        total += quantity
    expected = sum((Decimal(row['base_volume']) for row in tape.native
        if milliseconds(hours.window_start) <= row['trade_timestamp'] < milliseconds(hours.window_end)), Decimal(0))
    assert total == expected


@pytest.mark.parametrize('outside', ('left', 'right', 'overlap'))
def test_no_absent_interval_can_be_promoted_to_zero(originals, outside):
    tape = originals[3]
    good = (from_ms(tape.start), from_ms(tape.start + 3600000))
    assert len(totals(tape, [good], 'CONTROL_INTERVAL')) == 1
    if outside == 'left':
        intervals = [(from_ms(tape.start - 1), good[1])]
    elif outside == 'right':
        intervals = [(good[0], from_ms(tape.end + 1))]
    else:
        intervals = [good, good]
    with pytest.raises(ValueError):
        totals(tape, intervals, 'CONTROL_INTERVAL')


def test_source_selection_unchanged_grid_and_no_aggressor_or_full_book(originals):
    tape = originals[3]
    values = {e.kind: record(e) for e in evidences(tape, 'REPLAY', 'REPLAY', '0.00001', ())}
    assert optional_projection_source('volume_profile', 'TRADED_PRINTS', values) is values['TRADED_PRINTS']
    assert optional_projection_source('volume_displacement', 'TRADED_PRINTS', values) is values['EXECUTED_BAR_QUANTITIES']
    assert optional_projection_source('footprint_delta', 'AGGRESSOR_PRINTS', values) is None
    assert optional_projection_source('dom_imbalance', 'VENUE_BOOK', values) is None
    with pytest.raises(ValueError, match='align'):
        evidences(tape, 'REPLAY', 'REPLAY', '1', ())
    assert not evidences(tape, 'REPLAY', 'REPLAY', '0.00001', (), excluded=KINDS)


def test_duplicate_occurrences_preserved_not_native_id_deduplicated(originals):
    # Nonmarket multiplicity control copies an actual record; not live acceptance.
    row = originals[3].native[0]
    values = addressed((row, row), originals[3].available_at)
    assert len(values) == 2 and values[0]['id'] != values[1]['id']
    assert values[0]['quantity'] == values[1]['quantity'] == str(row['base_volume'])


def test_reused_original_publication_does_not_retime_the_native_observations(originals):
    tape = originals[3]
    # Pure lifecycle control, not a new source receipt or live freshness proof.
    later = replace(tape, available_at=(instant(tape.available_at) + timedelta(seconds=1)).isoformat())
    successor = extend(tape, later)
    assert successor.prints() == tape.prints()
    assert successor.native == tape.native
    assert successor.available_at == later.available_at
    with pytest.raises(ValueError, match='overlapping'):
        extend(tape, replace(later, start=tape.end + 1))


@pytest.mark.parametrize('endpoint', ('trade', 'public/tick/NZDUSD', 'coingecko/trades/EURUSD?limit=0&start=1&end=2',
    'coingecko/trades/NZDUSD?limit=20&start=1&end=2', 'https://example.org', '../trade',
    'coingecko/trades/NZDUSD?limit=0&start=1&end=2&key=CONTROL'))
def test_public_read_allowlist_precedes_network(monkeypatch, endpoint):
    import sfm_fx_new_age.connector.fxopen_feed as module
    def forbidden(*args, **kwargs):
        raise AssertionError('No network permitted in this nonmarket refusal control')
    monkeypatch.setattr(module, 'urlopen', forbidden)
    with pytest.raises(ValueError, match='allowlist'):
        module.public_get(endpoint, Event())


def test_in_memory_constructor_inert_disconnect_cooldown_and_stop():
    from sfm_fx_new_age.connector.fxopen_feed import ConnectedFXOpenReported
    store = SimpleNamespace(providers={}, admissions={})
    runtime = SimpleNamespace(analytics=SimpleNamespace(supplemental=store), database=SimpleNamespace(path=':memory:'))
    feed = ConnectedFXOpenReported(SimpleNamespace(r=runtime))
    feed.poll(('NONMARKET_CONTROL', (('NZDUSD', 'NONMARKET_CONTROL'),)))
    assert feed.worker is None and feed.state == 'NO_PERSISTENT_STATE'
    feed.next_start = float('inf')
    feed.disconnect()
    assert feed.next_start == 0 and feed.binding is None and feed.worker is None
    feed.close()
