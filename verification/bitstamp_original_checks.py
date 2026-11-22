"""Original-production Bitstamp replay; mutations are refusal controls only."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import json, os
import pytest
from sfm_fx_new_age.connector.bitstamp_book import NativeChainBook, PAIRS, snapshot_orders, clock, micros
from sfm_fx_new_age.contracts.domain import instant


@pytest.fixture(scope='module')
def originals():
    path = Path(os.environ['SFM_BITSTAMP_ORIGINAL'])
    body = json.loads(path.read_bytes())
    assert body['stream_closed'] and body['orders_written'] == 0
    return body


def inputs(body, symbol):
    snapshots = {v['round']: v['raw'] for v in body['snapshots'] if v['pair'] == symbol.lower()}
    events = [(json.loads(v['raw']), v['received_at']) for v in body['events']]
    return snapshots['seed'], snapshots['corroborate'], events


@pytest.mark.parametrize('symbol', PAIRS)
def test_original_two_snapshot_full_book_and_native_chain(originals, symbol):
    seed, checkpoint, events = inputs(originals, symbol)
    book = NativeChainBook(symbol)
    book.bootstrap(seed, checkpoint, events)
    row = book.row(book.received_at)
    assert row is not None and book.updates > 5
    assert len(book.orders) > 100 and row['event_id'] == book.cursor
    assert len(row['bids']) > 10 and len(row['asks']) > 10
    assert book.parameters()['full_book_complete'] is True
    assert book.parameters()['sequence_model'] == 'NATIVE_UUID_PREDECESSOR_CHAIN'
    assert 'sequence' not in row
    assert book.row((instant(book.received_at) + timedelta(seconds=6)).isoformat()) is None


@pytest.mark.parametrize('symbol', PAIRS)
@pytest.mark.parametrize('fault', ('missing_event', 'wrong_predecessor', 'numeric_sequence', 'wrong_pair',
                                    'unknown_delete', 'checkpoint_quantity', 'no_preseed', 'no_postcheckpoint'))
def test_original_mutations_fail_closed(originals, symbol, fault):
    seed, checkpoint, original_events = inputs(originals, symbol)
    events = deepcopy(original_events)
    seed_time = snapshot_orders(seed)[0]
    check_time = snapshot_orders(checkpoint)[0]
    eligible = [i for i, (m, _) in enumerate(events) if m.get('channel') == 'live_orders_' + symbol.lower()
                and 'event_id' in m and micros(m['data']['microtimestamp']) > seed_time]
    index = eligible[1]
    if fault == 'missing_event':
        events.pop(index)
    elif fault == 'wrong_predecessor':
        events[index][0]['pre_event_id'] = events[index][0]['event_id']
    elif fault == 'numeric_sequence':
        events[index][0]['event_id'] = 1
    elif fault == 'wrong_pair':
        for i in eligible:
            events[i][0]['channel'] = 'live_orders_nzdusd'
    elif fault == 'unknown_delete':
        events[index][0]['event'] = 'order_deleted'
        events[index][0]['data']['id_str'] = '0'
    elif fault == 'checkpoint_quantity':
        changed = json.loads(checkpoint)
        changed['bids'][0][1] = '999999999'
        checkpoint = json.dumps(changed)
    elif fault == 'no_preseed':
        events = [(m, r) for m, r in events if 'event_id' not in m or m.get('channel') != 'live_orders_' + symbol.lower()
                  or micros(m['data']['microtimestamp']) > seed_time]
    elif fault == 'no_postcheckpoint':
        events = [(m, r) for m, r in events if 'event_id' not in m or m.get('channel') != 'live_orders_' + symbol.lower()
                  or micros(m['data']['microtimestamp']) <= check_time]
    book = NativeChainBook(symbol)
    with pytest.raises((ValueError, TypeError, KeyError)):
        book.bootstrap(seed, checkpoint, events)
    assert not book.ready and book.row(events[-1][1]) is None


@pytest.mark.parametrize('symbol', PAIRS)
def test_replay_poison_cannot_be_repaired_by_a_later_ordinary_event(originals, symbol):
    seed, checkpoint, events = inputs(originals, symbol)
    book = NativeChainBook(symbol)
    book.bootstrap(seed, checkpoint, events)
    message, received = next((m, r) for m, r in reversed(events) if m.get('channel') == 'live_orders_' + symbol.lower() and 'event_id' in m)
    with pytest.raises(ValueError, match='gap or replay'):
        book.apply(message, received)
    with pytest.raises(ValueError, match='bootstrap required'):
        book.apply(message, received)
    assert book.row(received) is None
    book.bootstrap(seed, checkpoint, events)
    assert book.row(book.received_at) is not None


def test_nzdusd_not_fabricated_by_public_fiat_adapter():
    with pytest.raises(ValueError, match='not qualified'):
        NativeChainBook('NZDUSD')


def envelope(originals, symbol):
    from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
    seed, checkpoint, events = inputs(originals, symbol)
    book = NativeChainBook(symbol)
    book.bootstrap(seed, checkpoint, events)
    row = book.row(book.received_at)
    stamp = instant(row['time'])
    return SupplementalEvidence(provider_id='BITSTAMP_PUBLIC_NATIVE_CHAIN_V1', kind='VENUE_NATIVE_CHAIN_BOOK',
        scope_id='RECORDED_ORIGINAL_REPLAY_CONTROL', source_epoch='RECORDED_ORIGINAL_REPLAY_CONTROL', symbol=symbol,
        origin='LIVE_OBSERVED', source_ref=str(Path(os.environ['SFM_BITSTAMP_ORIGINAL'])), venue='BITSTAMP_SPOT_FIAT',
        instrument=symbol, price_domain='SPOT_PAIR', unit='DISPLAYED_BASE_UNITS',
        window_start=(stamp-timedelta(microseconds=1)).isoformat(),window_end=(stamp+timedelta(microseconds=1)).isoformat(),
        available_at=row['available_at'],valid_until=(stamp+timedelta(seconds=5)).isoformat(),complete=True,
        records=(row,),parameters=book.parameters())


@pytest.mark.parametrize('symbol', PAIRS)
def test_original_envelope_shape_and_source_precedence(originals, symbol):
    from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
    from sfm_fx_new_age.contracts.public_projection_inputs import optional_projection_source
    from sfm_fx_new_age.contracts.domain import record
    evidence=envelope(originals,symbol)
    validate_wire_shape(evidence)
    body=record(evidence)
    alternatives={'VENUE_NATIVE_CHAIN_BOOK':body,'VENUE_L2_CHECKSUM_BOOK':{'sentinel':'LOWER_SCOPE_CONTROL'}}
    assert optional_projection_source('dom_imbalance','VENUE_BOOK',alternatives) is body
    explicit={'sentinel':'EXPLICIT_PROVIDER_CONTROL'}
    alternatives['VENUE_BOOK']=explicit
    assert optional_projection_source('dom_imbalance','VENUE_BOOK',alternatives) is explicit


@pytest.mark.parametrize('symbol', PAIRS)
@pytest.mark.parametrize('fault',('ordinal','scope','complete','checkpoint','counterfeit_sequence','source_pair'))
def test_original_envelope_semantic_refusals(originals,symbol,fault):
    from dataclasses import replace
    from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
    evidence=envelope(originals,symbol)
    parameters=dict(evidence.parameters);rows=deepcopy(evidence.records)
    if fault=='ordinal':parameters['sequence_model']='LOCAL_COUNTER'
    elif fault=='scope':parameters['scope']='TOP_10'
    elif fault=='complete':parameters['full_book_complete']=False
    elif fault=='checkpoint':parameters['checkpoint_verified']=False
    elif fault=='counterfeit_sequence':rows[0]['sequence']=1
    elif fault=='source_pair':evidence=replace(evidence,symbol='NZDUSD',instrument='NZDUSD')
    with pytest.raises(ValueError):
        validate_wire_shape(replace(evidence,parameters=parameters,records=rows))


def test_in_memory_construction_is_inert_and_disconnect_clears_cooldown():
    from types import SimpleNamespace
    from sfm_fx_new_age.connector.bitstamp_feed import ConnectedBitstampBook
    store=SimpleNamespace(providers={},admissions={})
    runtime=SimpleNamespace(analytics=SimpleNamespace(supplemental=store),database=SimpleNamespace(path=':memory:'))
    feed=ConnectedBitstampBook(SimpleNamespace(r=runtime))
    feed.poll(('NONMARKET_CONTROL',tuple((s,'CONTROL') for s in PAIRS)))
    assert feed.worker is None and feed.state=='NO_PERSISTENT_STATE'
    feed.next_start=float('inf')
    feed.disconnect()
    assert feed.next_start==0. and feed.binding is None and feed.worker is None
    feed.close()
