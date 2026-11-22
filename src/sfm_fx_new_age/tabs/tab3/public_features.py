"""Shared closed-bar math for public projection profiles. No GUI or execution."""
from __future__ import annotations
from bisect import bisect_left,bisect_right
import math
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest


def sma(values,n):
    out=[None]*len(values);total=0.0;count=0
    for i,value in enumerate(values):
        if value is None:total=0.0;count=0;continue
        total+=value;count+=1
        if count>n:total-=values[i-n]
        if count>=n:out[i]=total/n
    return out


def ema(values,n,*,wilder=False):
    out=[None]*len(values);seed=[];value=None;alpha=1/n if wilder else 2/(n+1)
    for i,x in enumerate(values):
        if x is None:seed=[];value=None;continue
        if value is None:
            seed.append(x)
            if len(seed)==n:value=sum(seed)/n
        else:value+=alpha*(x-value)
        out[i]=value
    return out


def rolling(values,n,op,*,lag=0):
    return [op(values[i-n+1-lag:i+1-lag]) if i>=n-1+lag else None for i in range(len(values))]


def cross(a,b,i):
    if i<1 or any(v is None for v in (a[i-1],a[i],b[i-1],b[i])):return None
    before=a[i-1]-b[i-1];after=a[i]-b[i]
    tolerance=max(abs(a[i]),abs(b[i]),1)*1e-12
    if before<=tolerance and after>tolerance:return 'BUY'
    if before>=-tolerance and after<-tolerance:return 'SELL'
    return None


class Features:
    def __init__(self,bars,swings):
        self.bars=list(bars);self.swings=list(swings);self.n=len(bars);self.cache={}
        self.o=[float(b['open']) for b in bars];self.h=[float(b['high']) for b in bars]
        self.l=[float(b['low']) for b in bars];self.c=[float(b['close']) for b in bars]
        self.index={b['open_time']:i for i,b in enumerate(bars)}
    def get(self,name):
        if name not in self.cache:self.cache[name]=getattr(self,'_'+name)()
        return self.cache[name]
    def _bar_clocks(self):
        opens=tuple(instant(b['open_time']) for b in self.bars)
        prefix=[];times=[];known=None;known_at=None
        for b in self.bars:
            at=instant(b['available_at'])
            # max() preserves the first original spelling on equal instants.
            if known_at is None or at>known_at:known,known_at=b['available_at'],at
            prefix.append(known);times.append(known_at)
        return opens,all(a<=b for a,b in zip(opens,opens[1:])),tuple(prefix),tuple(times)
    def known_at(self,i,available=None):
        """Prefix knowledge time; cache belongs only to this refresh/frame."""
        clocks=self.get('bar_clocks');known=clocks[2][i]
        return available if available and instant(available)>clocks[3][i] else known
    def open_at(self,i):return self.get('bar_clocks')[0][i]
    def first_open_at_or_after(self,at):
        opens,ordered,_,_=self.get('bar_clocks');at=instant(at) if isinstance(at,str) else at
        if ordered:
            i=bisect_left(opens,at);return i if i<self.n else None
        # Preserve first-in-input semantics for noncanonical caller ordering.
        return next((i for i,t in enumerate(opens) if t>=at),None)
    def _close_clock_index(self):
        closes=tuple(instant(b['close_time']) for b in self.bars)
        return closes,all(a<=b for a,b in zip(closes,closes[1:]))
    def first_close_at_or_after(self,at):
        closes,ordered=self.get('close_clock_index');at=instant(at) if isinstance(at,str) else at
        if ordered:
            i=bisect_left(closes,at);return i if i<self.n else None
        return next((i for i,t in enumerate(closes) if t>=at),None)
    def root_id(self,i):
        roots=self.cache.setdefault('bar_root_ids',{})
        if i not in roots:roots[i]=digest(self.bars[i])
        return roots[i]
    def _swing_clocks(self):
        entries=[(s,instant(s['available_at']),instant(s['pivot_time']),i) for i,s in enumerate(self.swings)]
        latest={}
        for kind in {s['kind'] for s in self.swings}:
            rows=sorted((r for r in entries if r[0]['kind']==kind),key=lambda r:(r[1],r[3]))
            stamps=[];best=[];chosen=None
            for row in rows:
                if chosen is None or row[2]>chosen[2] or row[2]==chosen[2] and row[3]<chosen[3]:chosen=row
                stamps.append(row[1]);best.append(chosen[0])
            latest[kind]=(tuple(stamps),tuple(best))
        return entries,sorted(entries,key=lambda r:(r[2],r[0]['kind'])),latest
    def swings_at(self,at,kind=None,*,pivot_before=False):
        at=instant(at) if isinstance(at,str) else at
        return [s for s,available,pivot,_ in self.get('swing_clocks')[0]
                if (kind is None or s['kind']==kind) and available<=at and (not pivot_before or pivot<at)]
    def latest_swing_at(self,at,kind):
        at=instant(at) if isinstance(at,str) else at
        stamps,rows=self.get('swing_clocks')[2].get(kind,((),()))
        i=bisect_right(stamps,at)-1
        return rows[i] if i>=0 else None
    def _sma(self):return (sma(self.c,20),sma(self.c,50))
    def _ema(self):return (ema(self.c,20),ema(self.c,50))
    def _macd(self):
        fast,slow=ema(self.c,12),ema(self.c,26)
        m=[a-b if a is not None and b is not None else None for a,b in zip(fast,slow)]
        return m,ema(m,9)
    def _rsi(self):
        up=[None]+[max(0,self.c[i]-self.c[i-1]) for i in range(1,self.n)]
        down=[None]+[max(0,self.c[i-1]-self.c[i]) for i in range(1,self.n)]
        return [None if a is None or b is None else 50.0 if a==b==0 else 100.0 if b==0 else 100-100/(1+a/b)
                for a,b in zip(ema(up,14,wilder=True),ema(down,14,wilder=True))]
    def _stochastic(self):
        hi,lo=rolling(self.h,14,max),rolling(self.l,14,min)
        raw=[None if h is None else 50.0 if h==l else 100*(c-l)/(h-l) for c,h,l in zip(self.c,hi,lo)]
        k=sma(raw,3);return k,sma(k,3)
    def _adx(self):
        tr=[None];plus=[None];minus=[None]
        for i in range(1,self.n):
            up=self.h[i]-self.h[i-1];down=self.l[i-1]-self.l[i]
            plus.append(up if up>down and up>0 else 0.0);minus.append(down if down>up and down>0 else 0.0)
            tr.append(max(self.h[i]-self.l[i],abs(self.h[i]-self.c[i-1]),abs(self.l[i]-self.c[i-1])))
        atr=ema(tr,14,wilder=True)
        pos=[None if a is None else 100*d/a if a else 0.0 for d,a in zip(ema(plus,14,wilder=True),atr)]
        neg=[None if a is None else 100*d/a if a else 0.0 for d,a in zip(ema(minus,14,wilder=True),atr)]
        dx=[None if p is None else 100*abs(p-m)/(p+m) if p+m else 0.0 for p,m in zip(pos,neg)]
        return pos,neg,ema(dx,14,wilder=True)
    def _bollinger(self):
        mid=sma(self.c,20);upper=[None]*self.n;lower=[None]*self.n
        for i,m in enumerate(mid):
            if m is not None:
                sd=math.sqrt(sum((v-m)**2 for v in self.c[i-19:i+1])/20);upper[i]=m+2*sd;lower[i]=m-2*sd
        return mid,upper,lower
    def _donchian(self):return rolling(self.h,20,max,lag=1),rolling(self.l,20,min,lag=1)
    def _ichimoku(self):
        def mid(n):return [(a+b)/2 if a is not None else None for a,b in zip(rolling(self.h,n,max),rolling(self.l,n,min))]
        ten,base,wide=mid(9),mid(26),mid(52)
        span=[(a+b)/2 if a is not None and b is not None else None for a,b in zip(ten,base)]
        return ten,base,[None]*min(26,self.n)+span[:max(0,self.n-26)],[None]*min(26,self.n)+wide[:max(0,self.n-26)]
    def alternating(self):
        from sfm_fx_new_age.contracts.domain import instant
        result=[]
        for p in sorted(self.swings,key=lambda p:(instant(p['pivot_time']),p['kind'])):
            if p['pivot_time'] not in self.index:continue
            # Ambiguous same-candle high+low ordering cannot form a valid leg.
            if result and result[-1]['pivot_time']==p['pivot_time']:
                result.pop();continue
            if result and result[-1]['kind']==p['kind']:
                if (float(p['price'])-float(result[-1]['price']))*(1 if p['kind']=='HIGH' else -1)>0:result[-1]=p
            else:result.append(p)
        return result
