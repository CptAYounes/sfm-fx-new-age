"""Original-provider integrity tests and clearly labelled corrupt-input negatives."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from threading import Event
from types import SimpleNamespace
import json,os,pytest,sqlite3

from sfm_fx_new_age.connector.kraken_book import NativeBook,book_checksum
from sfm_fx_new_age.connector.kraken_history import history_rows,acquire_hour_history,RangeArchive
from sfm_fx_new_age.connector.kraken_public import native_get,ConnectedKrakenFeed,KINDS
from sfm_fx_new_age.contracts.public_projection_inputs import optional_projection_source
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.services.public_projections import PublicProjectionService
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.tabs.tab3.public_genuine_data import quantity_per_bar

ROOT=Path(os.environ['SFM_BLOCKER_ORIGINALS']).resolve(strict=True)
EVENTS=json.loads((ROOT/'standalone-book-originals.json').read_bytes())
CACHE=ROOT/'original-history-cache'
META=json.loads((CACHE/'hour-history.json').read_bytes())
SYMBOLS=tuple(META['pairs'])


def snapshot(symbol):
    for event in EVENTS:
        m=json.loads(event['raw'],parse_float=Decimal)
        if m.get('type')=='snapshot' and m['data'][0]['symbol'].replace('/','')==symbol:return event,m
    raise AssertionError('Missing original native snapshot')


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_all_native_book_messages_crc_and_native_clocks(symbol):
    book=NativeBook();count=0
    for e in EVENTS:
        m=json.loads(e['raw'],parse_float=Decimal)
        for row in m['data']:
            if row['symbol'].replace('/','')!=symbol:continue
            book.apply(row,m['type'],e['received_at'],e['raw']);count+=1
            assert book.checksum==row['checksum']==book_checksum(book.bids,book.asks)
            assert book.time==row['timestamp'] and book.row(e['received_at']) is not None
    assert count>=1 and book.ready and len(book.bids)<=10 and len(book.asks)<=10


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_corrupted_crc_withdraws_and_requires_new_snapshot(symbol):
    event,m=snapshot(symbol);book=NativeBook();book.apply(m['data'][0],'snapshot',event['received_at'],event['raw'])
    corrupted=deepcopy(m['data'][0]);corrupted['checksum']^=1
    with pytest.raises(ValueError):book.apply(corrupted,'update',event['received_at'],event['raw'])
    assert not book.ready and book.row(event['received_at']) is None
    book.apply(m['data'][0],'snapshot',event['received_at'],event['raw']);assert book.ready


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_snapshot_first_and_no_freshening_native_clock(symbol):
    event,m=snapshot(symbol);book=NativeBook()
    with pytest.raises(ValueError):book.apply(m['data'][0],'update',event['received_at'],event['raw'])
    book.apply(m['data'][0],'snapshot',event['received_at'],event['raw'])
    later=(instant(event['received_at'])+timedelta(seconds=6)).isoformat()
    assert book.row(later) is None


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_archived_hours_preserve_original_totals_and_missing_intervals(symbol):
    rows=history_rows(CACHE,symbol,META,'2026-11-12T19:00:00Z');assert len(rows)>2000
    assert all(Decimal(r['quantity'])>0 for r in rows)  # No synthetic zero fill.
    original=list(__import__('csv').reader(__import__('io').StringIO((CACHE/(symbol+'-60.csv')).read_text())))
    by={int(r[0]):r for r in original}
    for row in rows:
        native=by[int(instant(row['time']).timestamp())]
        assert Decimal(row['quantity'])==Decimal(native[5]) and row['trade_count']==int(native[6])
    first=rows[0];f=SimpleNamespace(bars=[dict(open_time=first['time'],close_time=first['end_time'])])
    assert quantity_per_bar(f,dict(kind='EXECUTED_BAR_QUANTITIES',records=rows))==[Decimal(first['quantity'])]
    assert quantity_per_bar(f,dict(kind='EXECUTED_BAR_QUANTITIES',records=rows[1:]))==[None]


def test_cached_history_integrity_and_no_network(tmp_path,monkeypatch):
    import shutil
    dest=tmp_path/'cache';shutil.copytree(CACHE,dest)
    def deny(*args,**kw):raise AssertionError('Cache verification must not fetch')
    monkeypatch.setattr(RangeArchive,'_request',deny)
    assert acquire_hour_history(SYMBOLS,dest,Event())['pairs']==META['pairs']
    path=dest/(SYMBOLS[0]+'-60.csv');path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError):acquire_hour_history(SYMBOLS,dest,Event())


@pytest.mark.parametrize('endpoint',['OHLC?pair=EURUSD&since=0&interval=60','OHLC?pair=../../&interval=60','Balance','OHLC?pair=EURUSD#frag&interval=60'])
def test_native_endpoint_query_injection_refused_before_io(endpoint):
    with pytest.raises(ValueError):native_get(endpoint,Event())


@pytest.mark.parametrize('key',('volume_displacement','effort_result','dom_imbalance'))
def test_cache_and_calculation_share_chosen_source_and_expiry(key):
    # Nonmarket source-selection control, not a positive market acceptance.
    kind='VENUE_BOOK' if key=='dom_imbalance' else 'TRADED_PRINTS'
    chosen='VENUE_L2_CHECKSUM_BOOK' if key=='dom_imbalance' else 'EXECUTED_BAR_QUANTITIES'
    source=dict(kind=chosen,provider_id='CONTROL_ONLY',valid_until='2026-11-12T19:00:05Z',records=[dict(time='2026-11-12T19:00:00Z',available_at='2026-11-12T19:00:00Z')])
    evidence={chosen:source};definition=next(m for m in METHODS if m.key==key)
    extra,until=PublicProjectionService.input_context(definition,dict(_evaluation_at='2026-11-12T19:00:01Z',optional_evidence=evidence,activity_alternatives=False))
    assert extra['source']==source and until==source['valid_until']
    assert optional_projection_source(key,kind,evidence)==source
    if key!='dom_imbalance':
        external=dict(provider_id='EXPLICIT_OTHER',kind=kind);evidence[kind]=external
        assert optional_projection_source(key,kind,evidence) is external


def test_status_does_not_count_expired_admissions():
    clock=lambda:'2026-11-12T19:00:06Z'
    r=SimpleNamespace(clock=clock,analytics=SimpleNamespace(supplemental=None))
    f=ConnectedKrakenFeed(SimpleNamespace(r=r));f.admitted['TRADED_PRINTS'].add('EURUSD');f.validity[('TRADED_PRINTS','EURUSD')]='2026-11-12T19:00:05Z'
    assert not f.status()['admitted_pairs']['TRADED_PRINTS']
    f.validity[('TRADED_PRINTS','EURUSD')]='2026-11-12T19:00:07Z'
    assert f.status()['admitted_pairs']['TRADED_PRINTS']==['EURUSD']
