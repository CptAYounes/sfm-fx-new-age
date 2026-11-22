"""Original-only replay of recovered native days/trades; no network in tests."""
from pathlib import Path
from decimal import Decimal
from datetime import timedelta
from threading import Event
from types import SimpleNamespace
import csv,json,os,sqlite3
import pytest
from sfm_fx_new_age.connector.kraken_weekly import WeeklySource
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.public_projection_inputs import optional_projection_source
from sfm_fx_new_age.services.public_projections import PublicProjectionService
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.tabs.tab3.public_genuine_data import quantity_per_bar

ROOT=Path(os.environ['SFM_WEEK_ORIGINALS']).resolve(strict=True)
PROBE=ROOT/'weekly-probe-v2'
EXPECTED=json.loads((PROBE/'partial-results.json').read_bytes())
REQUESTS=json.loads((PROBE/'requests.json').read_bytes())
PAIRS=tuple(EXPECTED['weekly_totals'])


def bars_and_hours(symbol):
    project=ROOT.parents[1]
    base=project/'.runtime/blocker-resolution-v2'
    c=sqlite3.connect((base/'source-native-v4/state/state.sqlite3').as_uri()+'?mode=ro',uri=True)
    try:
        bars={}
        for (raw,) in c.execute("SELECT body FROM records WHERE kind='bar' AND json_extract(body,'$.symbol')=? AND json_extract(body,'$.timeframe')='W1'",(symbol,)):
            row=json.loads(raw);bars[row['open_time']]=row
    finally:c.close()
    rows=sorted(bars.values(),key=lambda r:instant(r['open_time']))[-21:]
    hours={}
    from datetime import datetime,timezone
    for row in csv.reader((base/'original-history-cache'/(symbol+'-60.csv')).read_text().splitlines()):
        lo=datetime.fromtimestamp(int(row[0]),timezone.utc);hi=lo+timedelta(hours=1)
        hours[lo.isoformat().replace('+00:00','Z')]=dict(id='KRAKEN:H1:'+row[0],time=lo.isoformat().replace('+00:00','Z'),end_time=hi.isoformat().replace('+00:00','Z'),quantity=row[5],trade_count=int(row[6]))
    native_key=None
    for r in REQUESTS:
        if 'OHLC?pair='+symbol+'&interval=1440' in r['url']:
            native_key=next(k for k in json.loads((PROBE/r['file']).read_bytes())['result'] if k!='last');break
    originals=json.loads((base/'source-native-v4/native-http-originals.json').read_bytes())
    for entry in originals:
        if not entry['endpoint'].startswith('OHLC?pair='):continue
        body=json.loads(entry['raw']);key=next(k for k in body['result'] if k!='last')
        if key!=native_key:continue
        for row in body['result'][key][:-1]:
            lo=datetime.fromtimestamp(row[0],timezone.utc);hi=lo+timedelta(hours=1);at=lo.isoformat().replace('+00:00','Z')
            hours[at]=dict(id='KRAKEN:H1:'+str(row[0]),time=at,end_time=hi.isoformat().replace('+00:00','Z'),quantity=row[6],trade_count=row[7])
    return rows,tuple(hours.values())


def replay_source(tmp_path,monkeypatch):
    source=WeeklySource(tmp_path,Event())
    responses={r['url'].split('/public/',1)[1]:r for r in REQUESTS}
    def get(endpoint):
        entry=responses[endpoint];raw=(PROBE/entry['file']).read_bytes()
        source.audit.append(dict(endpoint=endpoint,received_at=entry['received_at'],raw=raw.decode(),sha256=entry['sha256']))
        return json.loads(raw,parse_float=Decimal)['result'],entry['received_at']
    monkeypatch.setattr(source,'get',get);return source


@pytest.mark.parametrize('symbol',PAIRS)
def test_exact_native_21_week_quantities_match_independent_probe(tmp_path,monkeypatch,symbol):
    source=replay_source(tmp_path,monkeypatch);bars,hours=bars_and_hours(symbol);rows,proof=source.recover(symbol,bars,hours)
    expected=EXPECTED['weekly_totals'][symbol]
    assert len(rows)==len(expected)==21
    for actual,prior in zip(rows,expected):
        assert actual['time']==prior['start'] and actual['end_time']==prior['end']
        assert Decimal(actual['quantity'])==Decimal(prior['quantity']) and actual['trade_count']==prior['trade_count']
    totals=quantity_per_bar(SimpleNamespace(bars=bars),dict(kind='EXECUTED_WEEK_QUANTITIES',records=rows))
    assert len(totals)==21 and all(v is not None for v in totals)
    assert proof['daily_source']['endpoint']=='OHLC?pair='+symbol+'&interval=1440'
    # The DST-transition week must be exact, not assumed to be 168 hours.
    assert any((instant(r['end_time'])-instant(r['time'])).total_seconds()!=7*86400 for r in rows)


@pytest.mark.parametrize('symbol',PAIRS)
def test_verified_native_boundary_cache_does_not_replay_trade_pages(tmp_path,monkeypatch,symbol):
    source=replay_source(tmp_path,monkeypatch);bars,hours=bars_and_hours(symbol);first,_=source.recover(symbol,bars,hours)
    cached=WeeklySource(tmp_path,Event());daily=next(r for r in REQUESTS if 'OHLC?pair='+symbol+'&interval=1440' in r['url'])
    def daily_only(endpoint):
        assert endpoint=='OHLC?pair='+symbol+'&interval=1440'
        cached.audit.append(dict(endpoint=endpoint,received_at=daily['received_at'],raw=(PROBE/daily['file']).read_text(),sha256=daily['sha256']))
        return json.loads((PROBE/daily['file']).read_bytes(),parse_float=Decimal)['result'],daily['received_at']
    monkeypatch.setattr(cached,'get',daily_only);second,_=cached.recover(symbol,bars,hours)
    assert [(r['quantity'],r['trade_count']) for r in first]==[(r['quantity'],r['trade_count']) for r in second]
    file=next(tmp_path.glob('*.json'));body=json.loads(file.read_bytes());body['quantity']='999999999999';file.write_text(json.dumps(body))
    with pytest.raises(ValueError):cached.recover(symbol,bars,hours)


@pytest.mark.parametrize('key',('volume_displacement','effort_result'))
def test_weekly_selection_and_cache_identity_are_frame_specific(key):
    week=dict(kind='EXECUTED_WEEK_QUANTITIES',provider_id='CONTROL',valid_until='2026-11-12T23:00:00Z')
    hour=dict(kind='EXECUTED_BAR_QUANTITIES',provider_id='CONTROL',valid_until='2026-11-12T22:59:00Z')
    evidence={'EXECUTED_WEEK_QUANTITIES':week,'EXECUTED_BAR_QUANTITIES':hour}
    assert optional_projection_source(key,'TRADED_PRINTS',evidence,'W1') is week
    assert optional_projection_source(key,'TRADED_PRINTS',evidence,'H1') is hour
    d=next(m for m in METHODS if m.key==key)
    ctx,until=PublicProjectionService.input_context(d,dict(_evaluation_at='2026-11-12T22:55:00Z',optional_evidence=evidence,frame='W1'))
    assert ctx['source'] is week and until==week['valid_until']
    external=dict(kind='TRADED_PRINTS',provider_id='EXPLICIT_EXTERNAL');evidence['TRADED_PRINTS']=external
    assert optional_projection_source(key,'TRADED_PRINTS',evidence,'W1') is external
