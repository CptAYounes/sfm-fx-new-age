"""Exact broker-week executed totals from original native days and boundary trades.

No synthetic hourly zeros. Preserve DST-adjusted broker boundaries. The native
UTC daily sum is adjusted by actual original tails on the two broker edges.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from urllib.request import Request,urlopen
from threading import Event,Thread
from queue import Queue,Empty
from time import monotonic
from hashlib import sha256
import json,re
from sfm_fx_new_age.contracts.domain import instant,record


def stamp(value):return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


class WeeklySource:
    def __init__(self,cache,stop,*,request_budget=72):
        self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.stop=stop;self.request_budget=request_budget;self.requests=0;self.bytes=0;self.last_read=0.;self.audit=[]

    def get(self,endpoint):
        if not re.fullmatch(r'(OHLC\?pair=[A-Z]{6,12}&interval=1440|Trades\?pair=[A-Z]{6,12}&since=[0-9]{1,22}&count=1000)',endpoint):raise ValueError('Weekly read endpoint allowlist')
        if self.stop.is_set() or self.requests>=self.request_budget:raise InterruptedError('Weekly read budget/stop')
        if self.stop.wait(max(0.,self.last_read+1.1-monotonic())):raise InterruptedError('Weekly read stopped')
        url='https://api.kraken.com/0/public/'+endpoint
        with urlopen(Request(url,headers={'User-Agent':'SFMFXNewAge-ReadOnly/1.0'}),timeout=5) as response:
            if response.geturl()!=url:raise ValueError('Unexpected weekly source redirect')
            raw=response.read(1_000_001)
        self.last_read=monotonic();self.requests+=1;self.bytes+=len(raw)
        if len(raw)>1_000_000 or self.bytes>16_000_000:raise ValueError('Weekly original payload budget')
        at=stamp(datetime.now(timezone.utc));body=json.loads(raw,parse_float=Decimal)
        if body.get('error') or not isinstance(body.get('result'),dict):raise ValueError('Weekly native response refused')
        self.audit.append(dict(endpoint=endpoint,sha256=sha256(raw).hexdigest(),received_at=at,raw=raw.decode()))
        return body['result'],at

    def boundary(self,symbol,start,end,hours,*,cache_tag=''):
        cursor=start;quantity=Decimal(0);count=0;roots=[]
        while cursor<end:
            row=hours.get(stamp(cursor))
            if row is None or instant(row['end_time'])!=cursor+timedelta(hours=1):break
            quantity+=Decimal(row['quantity']);count+=row['trade_count'];roots.append(row['id']);cursor+=timedelta(hours=1)
        if cursor==end:return quantity,count,dict(origin='ORIGINAL_CLOSED_HOURS',ids=roots)
        if cache_tag not in ('','HOUR_GAP'):raise ValueError('Unknown boundary cache namespace')
        suffix=('-HOUR_GAP-'+str(int(end.timestamp()))) if cache_tag else ''
        path=self.cache/(symbol+'-'+str(int(start.timestamp()))+suffix+'.json')
        if path.exists():
            if path.is_symlink() or path.stat().st_size>24_000_000:raise ValueError('Unsafe native boundary cache')
            stored=json.loads(path.read_bytes());payload=stored.pop('integrity_sha256')
            if sha256(json.dumps(stored,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=payload:raise ValueError('Boundary cache integrity changed')
            if stored['symbol']!=symbol or stored['start']!=stamp(start) or stored['end']!=stamp(end):raise ValueError('Wrong native boundary cache identity')
            return Decimal(stored['quantity']),stored['trade_count'],dict(origin='ORIGINAL_EXECUTION_INTERVAL',cache_sha256=payload)
        cursor=str(int(start.timestamp())*1_000_000_000-1);last_id=None;last_row=None;last_time=None;quantity=Decimal(0);count=0;complete=False;original=[]
        for _ in range(24):
            data,at=self.get('Trades?pair='+symbol+'&since='+cursor+'&count=1000');original.append(self.audit[-1]);keys=[k for k in data if k!='last']
            if len(keys)!=1:raise ValueError('Exact native trade instrument required')
            rows=data[keys[0]]
            if not rows:break
            for row in rows:
                if len(row)!=7 or type(row[6]) is not int:raise ValueError('Native execution shape')
                native_time=Decimal(str(row[2]));identity=row[6]
                if identity==last_id:
                    if row!=last_row:raise ValueError('Conflicting duplicate execution')
                    continue
                if last_id is not None and identity!=last_id+1:raise ValueError('Native execution continuity lost')
                if last_time is not None and native_time<last_time:raise ValueError('Native execution clock reversed')
                last_id=identity;last_time=native_time;last_row=row
                if native_time>=Decimal(str(end.timestamp())):complete=True;break
                if native_time<Decimal(str(start.timestamp())):raise ValueError('Wrong native cursor start')
                q=Decimal(row[1])
                if not q.is_finite() or q<=0:raise ValueError('Actual positive executed quantity required')
                quantity+=q;count+=1
            if complete:break
            next_cursor=str(data['last'])
            if int(next_cursor)<=int(cursor):raise ValueError('No native cursor progress')
            cursor=next_cursor
        if not complete:raise ValueError('Original boundary interval incomplete')
        stored=dict(symbol=symbol,start=stamp(start),end=stamp(end),quantity=str(quantity),trade_count=count,first_verified_at=at,originals=original,
                    zero_semantics='Only a complete original execution interval can prove zero; absent hours never imply zero')
        integrity=sha256(json.dumps(stored,sort_keys=True,separators=(',',':')).encode()).hexdigest();stored['integrity_sha256']=integrity
        temporary=path.with_suffix('.new');temporary.write_text(json.dumps(stored,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)
        return quantity,count,dict(origin='ORIGINAL_EXECUTION_INTERVAL',cache_sha256=integrity)

    def repair_hours(self,symbol,hour_rows,bars):
        """Close bounded exact lookback gaps using exhausted original trades.

        Missing OHLC rows are not zeros. Only the already-validated native-ID
        cursor ending at/beyond a gap's exclusive end can prove its empty hours.
        Existing native observations and first-observation clocks are untouched.
        """
        hours={row['time']:dict(row) for row in hour_rows};needed=set()
        for bar in bars:
            start,end=instant(bar['open_time']),instant(bar['close_time'])
            if start.minute or start.second or start.microsecond or end.minute or end.second or end.microsecond:
                raise ValueError('Exact UTC-hour aligned broker intervals required')
            if not 0<(end-start).total_seconds()<=3*86400:raise ValueError('Bounded broker day required')
            while start<end:needed.add(start);start+=timedelta(hours=1)
        missing=sorted(t for t in needed if stamp(t) not in hours)
        if len(missing)>168:raise ValueError('Native hour-gap recovery budget')
        groups=[]
        for start in missing:
            if groups and start==groups[-1][1]:groups[-1][1]+=timedelta(hours=1)
            else:groups.append([start,start+timedelta(hours=1)])
        proofs=[]
        for start,end in groups:
            quantity,count,reference=self.boundary(symbol,start,end,hours,cache_tag='HOUR_GAP')
            path=self.cache/(symbol+'-'+str(int(start.timestamp()))+'-HOUR_GAP-'+str(int(end.timestamp()))+'.json')
            stored=json.loads(path.read_bytes());integrity=stored.pop('integrity_sha256')
            if sha256(json.dumps(stored,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=integrity or integrity!=reference['cache_sha256']:
                raise ValueError('Changed original execution interval')
            bins={t:[Decimal(0),0] for t in missing if start<=t<end};seen={}
            for original in stored['originals']:
                if sha256(original['raw'].encode()).hexdigest()!=original['sha256']:raise ValueError('Changed original native page')
                data=json.loads(original['raw'],parse_float=Decimal)
                data=data.get('result',data);keys=[k for k in data if k!='last']
                if len(keys)!=1:raise ValueError('Exact native execution instrument required')
                for row in data[keys[0]]:
                    at=Decimal(str(row[2]));identity=row[6]
                    if identity in seen:
                        if seen[identity]!=row:raise ValueError('Conflicting original native execution')
                        continue
                    seen[identity]=row
                    if not Decimal(str(start.timestamp()))<=at<Decimal(str(end.timestamp())):continue
                    bucket=datetime.fromtimestamp(int(at//3600)*3600,timezone.utc)
                    bins[bucket][0]+=Decimal(row[1]);bins[bucket][1]+=1
            if sum((v[0] for v in bins.values()),Decimal(0))!=quantity or sum(v[1] for v in bins.values())!=count:
                raise ValueError('Original hourly partition does not equal exhausted interval')
            for at,(q,n) in bins.items():
                hours[stamp(at)]=dict(id='KRAKEN:EXHAUSTED_H1:'+str(int(at.timestamp())),time=stamp(at),end_time=stamp(at+timedelta(hours=1)),
                    available_at=stored['first_verified_at'],quantity=str(q),trade_count=n)
            proofs.append(dict(start=stamp(start),end=stamp(end),cache_sha256=integrity,first_verified_at=stored['first_verified_at']))
        return tuple(hours[t] for t in sorted(hours)),dict(recovered_hours=len(missing),intervals=proofs,zero_semantics='ONLY_ORIGINAL_EXECUTION_EXHAUSTION')

    def recover(self,symbol,bars,hour_rows,*,frame='W1'):
        if symbol not in {'EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD'}:raise ValueError('Unsupported exact native fiat pair')
        if frame not in {'W1','D1'}:raise ValueError('Exact day/week frame required')
        daily,at=self.get('OHLC?pair='+symbol+'&interval=1440');daily_source=self.audit[-1];keys=[k for k in daily if k!='last']
        if len(keys)!=1:raise ValueError('Exact native daily instrument required')
        days={}
        for row in daily[keys[0]][:-1]:
            if len(row)!=8 or type(row[0]) is not int or row[0]%86400:raise ValueError('Original UTC daily shape')
            q=Decimal(str(row[6]));n=row[7]
            if not q.is_finite() or q<0 or type(n) is not int or n<0 or (q==0)!=(n==0):raise ValueError('Native daily execution quantity/count')
            days[row[0]]=(q,n)
        hours={row['time']:row for row in hour_rows};boundaries={instant(v[k]) for v in bars for k in ('open_time','close_time')};tails={}
        for start in sorted(boundaries):
            end=(start+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
            tails[start]=self.boundary(symbol,start,end,hours)
        rows=[];proof=[]
        for bar in bars:
            start,end=instant(bar['open_time']),instant(bar['close_time'])
            begin=(start+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0);finish=(end+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
            cursor=begin;quantity=Decimal(0);count=0;original_days=[]
            while cursor<finish:
                value=days.get(int(cursor.timestamp()))
                if value is None:raise ValueError('Original native day missing')
                quantity+=value[0];count+=value[1];original_days.append(int(cursor.timestamp()));cursor+=timedelta(days=1)
            quantity+=tails[start][0]-tails[end][0];count+=tails[start][1]-tails[end][1]
            if quantity<0 or count<0 or (quantity==0)!=(count==0):raise ValueError('Inconsistent exact native week')
            lower,upper=(6*86400,8*86400) if frame=='W1' else (20*3600,28*3600)
            if not lower<=int((end-start).total_seconds())<=upper:raise ValueError('Unexpected broker day/week interval')
            available=stamp(datetime.now(timezone.utc))
            rows.append(dict(id='KRAKEN:'+frame+':'+str(int(start.timestamp())),time=stamp(start),end_time=stamp(end),available_at=available,quantity=str(quantity),trade_count=count))
            proof.append(dict(start=stamp(start),end=stamp(end),daily_intervals=original_days,start_tail=tails[start][2],end_tail=tails[end][2]))
        return tuple(rows),dict(derivation='SUM_NATIVE_UTC_DAYS + EXACT_START_TAIL - EXACT_END_TAIL',daily_source=daily_source,weeks=proof,frame=frame)


class ConnectedWeeklyRecovery:
    def __init__(self,parent):
        self.parent=parent;self.r=parent.r;self.worker=None;self.stop=Event();self.results=Queue(maxsize=6);self.binding=None;self.next_start=0.;self.hour_inputs={};self.state='WAITING_NATIVE_HOURS';self.audit=[];self.requests=0;self.completed_pairs=[]
        self.attempted_pairs=set()
        self.recovered_hours={}

    def disconnect(self):
        self.stop.set()
        if self.worker is not None:
            self.worker.join(timeout=8)
            if self.worker.is_alive():raise RuntimeError('Weekly source worker did not stop')
        self.worker=None;self.binding=None;self.next_start=0.;self.hour_inputs.clear();self.completed_pairs=[]
        self.attempted_pairs.clear()
        self.recovered_hours.clear()
        while True:
            try:self.results.get_nowait()
            except Empty:break
        self.state='WAITING_NATIVE_HOURS'

    def _run(self,binding,inputs):
        cache=Path(self.r.database.path).parent/'market-cache/kraken-week-boundaries';source=WeeklySource(cache,self.stop)
        try:
            for symbol,(bars,hours,daily_bars) in inputs.items():
                if self.stop.is_set():break
                try:
                    rows,proof=source.recover(symbol,bars,hours)
                    if len(daily_bars)>=21:
                        try:
                            days,day_proof=source.recover(symbol,daily_bars,hours,frame='D1')
                            proof['day_derivation']=day_proof
                            proof['closed_day_rows']=days[:-6]
                        except (ValueError,OSError,ArithmeticError,KeyError,TypeError) as error:
                            proof['day_recovery_error']=type(error).__name__
                    self.results.put_nowait((binding,symbol,rows,proof,None))
                except (ValueError,OSError,ArithmeticError,KeyError,TypeError) as error:
                    self.results.put_nowait((binding,symbol,(),{},type(error).__name__))
        finally:self.audit=source.audit;self.requests=source.requests

    def poll(self,binding):
        if binding!=self.binding:
            self.disconnect();self.binding=binding;self.next_start=0.
        if binding is None or self.r.database.path==':memory:' or 'EXECUTED_WEEK_QUANTITIES' in self.parent.excluded:return
        if self.worker is None and self.parent.pairs:
            refresh_due=monotonic()>=self.next_start
            inputs={}
            for symbol in self.parent.pairs:
                if not refresh_due and symbol in self.attempted_pairs:continue
                if symbol not in dict(binding[1]) or symbol not in self.hour_inputs:continue
                authority=self.r.market.authority(symbol)
                bars=self.r.market.bars(symbol,'W1',self.r.clock(),authority['source_epoch']) if authority else ()
                if len(bars)<21:continue
                daily=self.r.market.bars(symbol,'D1',self.r.clock(),authority['source_epoch'])
                inputs[symbol]=(tuple(record(v) for v in bars[-21:]),self.hour_inputs[symbol],tuple(record(v) for v in daily[-21:]) if len(daily)>=21 else ())
            if inputs:
                self.attempted_pairs.update(inputs)
                self.stop=Event();self.state='RECOVERING_EXACT_NATIVE_WEEKS';self.worker=Thread(target=self._run,args=(binding,inputs),name='SFM-Kraken-week-read',daemon=False);self.worker.start()
        while True:
            try:identity,symbol,rows,proof,error=self.results.get_nowait()
            except Empty:break
            if identity!=binding:continue
            if error:self.state='WEEK_SOURCE_UNAVAILABLE:'+error;continue
            at=stamp(datetime.now(timezone.utc));root=sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest()
            try:
                if proof.get('closed_day_rows'):
                    recovered=tuple(proof['closed_day_rows']);split=recovered[-1]['end_time']
                    hours=recovered+tuple(r for r in self.hour_inputs[symbol] if instant(r['time'])>=instant(split))
                    self.parent._accept(symbol,self.parent.pairs[symbol],hours,at,'EXECUTED_BAR_QUANTITIES',hours[0]['time'],hours[-1]['end_time'],root)
                    self.recovered_hours[symbol]=recovered
                self.parent._accept(symbol,self.parent.pairs[symbol],rows,at,'EXECUTED_WEEK_QUANTITIES',rows[0]['time'],rows[-1]['end_time'],root)
            except (ValueError,KeyError,TypeError,ArithmeticError) as error:
                self.state='WEEK_ADMISSION_REFUSED:'+type(error).__name__;continue
            self.r.database.put('kraken_week_derivation',symbol,dict(proof,scope_id=binding[0],source_epoch=dict(binding[1])[symbol],root_sha256=root))
            if symbol not in self.completed_pairs:self.completed_pairs.append(symbol)
        if self.worker is not None and not self.worker.is_alive():
            self.worker.join();self.worker=None;self.next_start=monotonic()+300
            if len(self.completed_pairs)==len(self.parent.pairs):self.state='EXACT_WEEK_QUANTITIES_ADMITTED'

    def status(self):return dict(state=self.state,completed_pairs=list(self.completed_pairs),requests=self.requests,worker_alive=bool(self.worker and self.worker.is_alive()),gaps_zero_filled=False,lookbacks_reduced=False)
