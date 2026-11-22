"""Checks on retained original Kraken observations, not fabricated market sessions."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from types import SimpleNamespace
import json,os,sqlite3
import pytest

from sfm_fx_new_age.connector.kraken_public import NativeTrades,discover,closed_hours
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.tabs.tab3.public_genuine_data import quantity_per_bar

ROOT=Path(os.environ['SFM_KRAKEN_ORIGINALS']).resolve(strict=True)
HTTP=json.loads((ROOT/'native-http-originals.json').read_bytes())
ENVELOPES=json.loads((ROOT/'first-connection-envelope-originals.json').read_bytes())
EVENTS=json.loads((ROOT/'native-ws-originals.json').read_bytes())
SYMBOLS=('EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD')


def envelope(symbol,kind):
    return deepcopy(next(e for e in ENVELOPES if e['symbol']==symbol and e['kind']==kind))


def test_native_instrument_denominator():
    raw=next(h['raw'] for h in HTTP if h['endpoint']=='AssetPairs')
    pairs=discover(json.loads(raw)['result'])
    assert set(pairs)==set(SYMBOLS) and 'NZDUSD' not in pairs


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_native_stream_round_trip_and_documented_sides(symbol):
    book=NativeTrades();seen=0
    for event in EVENTS:
        m=event['message']
        if m.get('channel')!='trade':continue
        rows=[r for r in m['data'] if r['symbol'].replace('/','')==symbol]
        if not rows:continue
        book.apply(rows,m['type'],event['received_at']);seen+=len(rows)
        assert book.rows[-1]['aggressor']==rows[-1]['side'].upper()
        assert Decimal(book.rows[-1]['quantity'])==Decimal(str(rows[-1]['qty']))
        assert Decimal(book.rows[-1]['price'])==Decimal(str(rows[-1]['price']))
    assert seen>=50 and book.closed_interval() is not None


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_native_snapshots_reject_update_before_snapshot_and_duplicate_sequence(symbol):
    e=next(e for e in EVENTS if e['message'].get('channel')=='trade' and e['message'].get('type')=='snapshot' and e['message']['data'][0]['symbol'].replace('/','')==symbol)
    rows=e['message']['data'];book=NativeTrades()
    with pytest.raises(ValueError):book.apply(rows,'update',e['received_at'])
    book.apply(rows,'snapshot',e['received_at'])
    with pytest.raises(ValueError):book.apply([rows[-1]],'update',e['received_at'])


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_original_envelopes_validate_and_are_not_ordinary_quote_alternatives(symbol):
    for kind in ('TRADED_PRINTS','AGGRESSOR_PRINTS','EXECUTED_BAR_QUANTITIES'):
        e=envelope(symbol,kind);e['records']=tuple(e['records']);value=SupplementalEvidence(**e);validate_wire_shape(value)
        assert value.venue=='KRAKEN_SPOT_FIAT' and value.unit=='EXECUTED_BASE_UNITS'
        assert value.parameters.get('native_sequence') is None
        if kind=='EXECUTED_BAR_QUANTITIES':assert all('price' not in r for r in value.records)


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_native_hour_totals_exclude_uncommitted_candle_and_keep_exact_volume(symbol):
    e=envelope(symbol,'EXECUTED_BAR_QUANTITIES')
    candidates=[h for h in HTTP if h['endpoint'].startswith('OHLC?pair=')]
    original=next(h for h in candidates if h['sha256'] in e['source_ref'])
    body=json.loads(original['raw']);key=next(k for k in body['result'] if k!='last');native=body['result'][key]
    rows=closed_hours(body['result'],key,e['available_at'])
    assert len(rows)==len(native)-1==len(e['records'])
    for source,row in zip(native[:-1],e['records']):
        assert Decimal(row['quantity'])==Decimal(source[6]) and row['trade_count']==source[7]
        assert instant(row['time']).timestamp()==source[0]
    assert all(instant(r['end_time']).timestamp()<=native[-1][0] for r in rows)


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_native_hour_totals_only_cover_exact_broker_intervals(symbol):
    e=envelope(symbol,'EXECUTED_BAR_QUANTITIES');first=e['records'][0]
    f=SimpleNamespace(bars=[dict(open_time=first['time'],close_time=first['end_time'])])
    assert quantity_per_bar(f,e)==[Decimal(first['quantity'])]
    missing=deepcopy(e);missing['records']=missing['records'][1:]
    assert quantity_per_bar(f,missing)==[None]
    shifted=SimpleNamespace(bars=[dict(open_time=(instant(first['time'])+timedelta(minutes=1)).isoformat(),close_time=first['end_time'])])
    assert quantity_per_bar(shifted,e)==[None]
    overlap=deepcopy(e);overlap['records']=overlap['records']+overlap['records'][:1]
    with pytest.raises(ValueError):quantity_per_bar(f,overlap)


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_unknown_aggressor_is_rejected_from_original_envelope(symbol):
    e=envelope(symbol,'AGGRESSOR_PRINTS');e['records'][0]['aggressor']='UNKNOWN';e['records']=tuple(e['records'])
    with pytest.raises(ValueError):SupplementalEvidence(**e)


@pytest.mark.parametrize('symbol',SYMBOLS)
def test_normalized_original_archives_do_not_duplicate_on_publication_or_reconnect(tmp_path,symbol):
    from sfm_fx_new_age.connector.kraken_public import ConnectedKrakenFeed
    from sfm_fx_new_age.storage.database import Database
    db=Database(tmp_path/'original-archive.sqlite3')
    try:
        r=SimpleNamespace(database=db,analytics=SimpleNamespace(supplemental=None))
        feed=ConnectedKrakenFeed(SimpleNamespace(r=r))
        trades=envelope(symbol,'AGGRESSOR_PRINTS')['records'];hours=envelope(symbol,'EXECUTED_BAR_QUANTITIES')['records']
        for _ in range(2):
            feed._archive(symbol,trades,'TRADES');feed._archive(symbol,hours,'HOURS')
        feed.archived_print_ids.clear();feed.archived_hours.clear()
        feed._archive(symbol,trades,'TRADES');feed._archive(symbol,hours,'HOURS')
        assert len(db.list('kraken_native_execution'))==len(trades)
        assert len(db.list('kraken_native_hour_quantity'))==len(hours)
    finally:db.close()


def test_explicit_execution_provider_excludes_automatic_quantity_override():
    from sfm_fx_new_age.connector.kraken_public import ConnectedKrakenFeed
    r=SimpleNamespace(analytics=SimpleNamespace(supplemental=None))
    feed=ConnectedKrakenFeed(SimpleNamespace(r=r),excluded_kinds={'TRADED_PRINTS'})
    assert {'TRADED_PRINTS','EXECUTED_BAR_QUANTITIES'}<=feed.excluded and feed.worker is None


@pytest.mark.parametrize('symbol',SYMBOLS)
@pytest.mark.parametrize('frame',('H1','H4','D1'))
def test_original_broker_bar_coverage_matches_independent_native_hour_sum(symbol,frame):
    layers=json.loads((ROOT/'first-connection-layers.json').read_bytes())
    layer=next(v for v in layers if v['symbol']==symbol and v['timeframe']==frame and v['strategy_id']=='volume_displacement')
    data=envelope(symbol,'EXECUTED_BAR_QUANTITIES')
    c=sqlite3.connect((ROOT/'state/state.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:
        rows=[json.loads(v) for (v,) in c.execute("SELECT body FROM records WHERE kind='bar' AND json_extract(body,'$.symbol')=? AND json_extract(body,'$.timeframe')=? AND json_extract(body,'$.source_epoch')=?",(symbol,frame,layer['source_epoch']))]
    finally:c.close()
    by_time={}
    for row in rows:
        old=by_time.get(row['open_time'])
        if old is None or (instant(row['available_at']),row['revision'])>(instant(old['available_at']),old['revision']):by_time[row['open_time']]=row
    bars=sorted(by_time.values(),key=lambda v:instant(v['open_time']))
    assert len(bars)>20
    actual=quantity_per_bar(SimpleNamespace(bars=bars),data)
    expected=[]
    native={instant(r['time']):r for r in data['records']}
    for bar in bars:
        start,end=instant(bar['open_time']),instant(bar['close_time']);cursor=start;total=Decimal(0);complete=True
        while cursor<end:
            row=native.get(cursor)
            if row is None or instant(row['end_time'])!=cursor+timedelta(hours=1):complete=False;break
            total+=Decimal(row['quantity']);cursor+=timedelta(hours=1)
        expected.append(total if complete and cursor==end else None)
    assert actual==expected and sum(q is not None for q in actual)>20
