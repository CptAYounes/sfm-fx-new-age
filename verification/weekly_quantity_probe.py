"""Bounded official daily + exact original trade-boundary feasibility probe.

Not a product publisher. No synthetic hour filling and no fixed daily-to-broker
week shift: exact weekly quantity = native UTC daily totals + original boundary
prefix/suffix differences. Preserve all fetched original payloads and cursors.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from urllib.request import Request,urlopen
from collections import defaultdict
import csv,hashlib,json,sqlite3,time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/native-recovery-v3/weekly-probe-v2'
PAIRS=('EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD')
BUDGET=72


def iso(value):return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
def instant(value):return datetime.fromisoformat(value.replace('Z','+00:00'))


def run():
    OUT.mkdir(mode=0o700,exist_ok=False);requests=[];last_read=0.;results={};holes={};counters={}
    def get(endpoint):
        nonlocal last_read
        if len(requests)>=BUDGET:raise RuntimeError('Explicit public-request budget exhausted')
        delay=last_read+1.1-time.monotonic()
        if delay>0:time.sleep(delay)
        url='https://api.kraken.com/0/public/'+endpoint
        with urlopen(Request(url,headers={'User-Agent':'SFMFXNewAge-ReadOnlyResearch/1.0'}),timeout=10) as response:
            raw=response.read(1000001);assert len(raw)<=1000000
        last_read=time.monotonic();name=f'http-{len(requests):03d}.json';(OUT/name).write_bytes(raw)
        entry=dict(url=url,file=name,sha256=hashlib.sha256(raw).hexdigest(),received_at=iso(datetime.now(timezone.utc)))
        requests.append(entry);(OUT/'requests.json').write_text(json.dumps(requests,indent=2)+'\n')
        value=json.loads(raw,parse_float=Decimal)
        if value.get('error'):raise ValueError('Native API refused source request')
        return value['result']
    state=ROOT/'.runtime/blocker-resolution-v2/source-native-v4/state/state.sqlite3'
    db=sqlite3.connect(state.as_uri()+'?mode=ro',uri=True)
    try:
        for symbol in PAIRS:
            bars={}
            for (raw,) in db.execute("SELECT body FROM records WHERE kind='bar' AND json_extract(body,'$.symbol')=? AND json_extract(body,'$.timeframe')='W1'",(symbol,)):
                bar=json.loads(raw);bars[bar['open_time']]=bar
            bars=sorted(bars.values(),key=lambda v:instant(v['open_time']))[-21:]
            archive=ROOT/'.runtime/blocker-resolution-v2/original-history-cache'/(symbol+'-60.csv')
            hours={int(r[0]):(Decimal(r[5]),int(r[6])) for r in csv.reader(archive.read_text().splitlines())}
            native=get('OHLC?pair='+symbol+'&interval=1440');native_key=next(k for k in native if k!='last')
            daily={int(row[0]):(Decimal(row[6]),row[7]) for row in native[native_key][:-1]}
            original=json.loads((ROOT/'.runtime/blocker-resolution-v2/source-native-v4/native-http-originals.json').read_text())
            for record in original:
                if record['endpoint'].startswith('OHLC?pair='):
                    body=json.loads(record['raw']);key=next(k for k in body['result'] if k!='last')
                    # The original native pair can contain the X/Z legacy prefix.
                    if key!=native_key:continue
                    for row in body['result'][key][:-1]:hours[row[0]]=(Decimal(row[6]),row[7])

            boundaries={instant(v[k]) for v in bars for k in ('open_time','close_time')};tails={};missing=[]
            for start in sorted(boundaries):
                end=(start+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
                quantity=Decimal(0);count=0;cursor=start
                while cursor<end:
                    item=hours.get(int(cursor.timestamp()))
                    if item is None:break
                    quantity+=item[0];count+=item[1];cursor+=timedelta(hours=1)
                if cursor==end:tails[start]=(quantity,count,'ORIGINAL_HOURLY')
                else:missing.append((start,end))
            holes[symbol]=[iso(v[0]) for v in missing];counters[symbol]=dict(needed_boundary_intervals=len(missing),recovered_from_hours=len(tails),weekly_bars=len(bars))
            for start,end in missing:
                cursor=str(int(start.timestamp())*1000000000-1);last_id=None;last_time=None;last_row=None;quantity=Decimal(0);count=0;complete=False;page_refs=[]
                for page in range(24):
                    data=get('Trades?pair='+symbol+'&since='+cursor+'&count=1000');key=next(k for k in data if k!='last');rows=data[key];page_refs.append(requests[-1]['file'])
                    if not rows:break
                    for row in rows:
                        assert len(row)==7 and type(row[6]) is int
                        at=Decimal(str(row[2]));identity=row[6]
                        if identity==last_id:
                            if row!=last_row:raise ValueError('Conflicting duplicate native trade ID')
                            continue  # Exact documented-page-boundary overlap only.
                        if last_id is not None and identity!=last_id+1:raise ValueError('Noncontiguous native historical trade IDs')
                        if last_time is not None and at<last_time:raise ValueError('Historical native clock reversal')
                        last_id=identity;last_time=at;last_row=row
                        if at>=Decimal(str(end.timestamp())):complete=True;break
                        if at<Decimal(str(start.timestamp())):raise ValueError('Wrong historical cursor start')
                        value=Decimal(row[1]);assert value>0;quantity+=value;count+=1
                    if complete:break
                    next_cursor=str(data['last']);assert int(next_cursor)>int(cursor);cursor=next_cursor
                if complete:
                    tails[start]=(quantity,count,'ORIGINAL_EXECUTIONS')
                    (OUT/(symbol+'-'+str(int(start.timestamp()))+'-boundary.json')).write_text(json.dumps(dict(symbol=symbol,start=iso(start),end=iso(end),quantity=str(quantity),trade_count=count,pages=page_refs),indent=2)+'\n')
            weekly=[]
            for bar in bars:
                start,end=instant(bar['open_time']),instant(bar['close_time'])
                if start not in tails or end not in tails:continue
                begin=(start+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0);finish=(end+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
                cursor=begin;quantity=Decimal(0);count=0
                while cursor<finish:
                    item=daily.get(int(cursor.timestamp()))
                    if item is None:break
                    quantity+=item[0];count+=item[1];cursor+=timedelta(days=1)
                if cursor!=finish:continue
                quantity+=tails[start][0]-tails[end][0];count+=tails[start][1]-tails[end][1]
                assert quantity>0 and count>0
                weekly.append(dict(start=iso(start),end=iso(end),quantity=str(quantity),trade_count=count,derivation='SUM_NATIVE_DAYS + EXACT_START_TAIL - EXACT_END_TAIL'))
            results[symbol]=weekly;counters[symbol]['complete_original_weeks']=len(weekly)
            (OUT/'partial-results.json').write_text(json.dumps(dict(counts=counters,missing_hour_boundaries=holes,weekly_totals=results,requests=len(requests)),indent=2)+'\n')
    except Exception as error:
        (OUT/'stopped.json').write_text(json.dumps(dict(error_type=type(error).__name__,message=str(error),counts=counters,missing_hour_boundaries=holes,weekly_totals=results,requests=len(requests)),indent=2)+'\n');raise
    finally:db.close()
    print(json.dumps(dict(counts=counters,requests=len(requests)),indent=2))


if __name__=='__main__':run()
