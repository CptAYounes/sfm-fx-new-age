"""Deterministic public-method projections, not calibrated trading instructions."""
from __future__ import annotations
from decimal import Decimal
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from .public_features import Features,cross


def blank():return {'series':[],'zones':[],'markers':[],'metrics':{}}


def marker(out,f,i,label,side,price=None,*,available=None,roots=()):
    bar=f.bars[i];known=f.known_at(i,available)
    out['markers'].append({'time':bar['close_time'],'available_at':known,'price':str(price if price is not None else bar['close']),
                          'label':label,'side':side,'root_ids':list(roots) or [f.root_id(i)]})


def zone(out,f,i,low,high,label,side,*,available=None,state='CONFIRMED',roots=()):
    if low<=0 or high<=0 or low>high:return
    out['zones'].append({'low':str(low),'high':str(high),'label':label,'side':side,'state':state,
                        'available_at':available or f.known_at(i),
                        'root_ids':list(roots) or [f.root_id(i)]})


def series(out,f,values,label):
    points=[]
    for i,(b,value) in enumerate(zip(f.bars,values)):
        known=f.known_at(i)
        if value is not None and value>0:points.append({'time':b['close_time'],'available_at':known,'price':str(value)})
    out['series'].append({'label':label,'points':points[-256:]})


def indicator_method(key,f,inputs,deps):
    out=blank();n=f.n
    if key in {'sma_cross','ema_cross'}:
        a,b=f.get('sma' if key=='sma_cross' else 'ema');series(out,f,a,'Fast 20');series(out,f,b,'Slow 50')
        for i in range(1,n):
            if side:=cross(a,b,i):marker(out,f,i,key,side)
    elif key=='macd':
        a,b=f.get('macd')
        for i in range(1,n):
            if side:=cross(a,b,i):marker(out,f,i,'MACD cross',side)
        out['metrics']={'macd':a[-1] if n else None,'signal':b[-1] if n else None}
    elif key=='rsi':
        a=f.get('rsi')
        for i in range(1,n):
            if a[i-1] is None or a[i] is None:continue
            if a[i-1]<=30<a[i]:marker(out,f,i,'RSI re-entry', 'BUY')
            if a[i-1]>=70>a[i]:marker(out,f,i,'RSI re-entry', 'SELL')
        out['metrics']={'rsi14':a[-1] if n else None}
    elif key=='stochastic':
        a,b=f.get('stochastic')
        for i in range(1,n):
            side=cross(a,b,i)
            if side and (side=='BUY' and a[i-1]<=20 or side=='SELL' and a[i-1]>=80):marker(out,f,i,'Stochastic cross',side)
        out['metrics']={'slow_k':a[-1] if n else None,'d':b[-1] if n else None}
    elif key=='adx':
        pos,neg,adx=f.get('adx')
        for i in range(1,n):
            if adx[i] is not None and adx[i]>=25 and (side:=cross(pos,neg,i)):marker(out,f,i,'DI cross / ADX>=25',side)
        out['metrics']={'plus_di':pos[-1] if n else None,'minus_di':neg[-1] if n else None,'adx14':adx[-1] if n else None}
    elif key=='bollinger':
        mid,up,down=f.get('bollinger')
        for label,a in [('BB mid',mid),('BB upper',up),('BB lower',down)]:series(out,f,a,label)
        for i in range(1,n):
            if up[i-1] is None:continue
            if f.c[i-1]<down[i-1] and f.c[i]>=down[i] and f.c[i]<=up[i]:marker(out,f,i,'BB re-entry','BUY')
            if f.c[i-1]>up[i-1] and f.c[i]<=up[i] and f.c[i]>=down[i]:marker(out,f,i,'BB re-entry','SELL')
    elif key=='donchian':
        up,down=f.get('donchian');series(out,f,up,'Prior 20 high');series(out,f,down,'Prior 20 low')
        for i in range(20,n):
            previous_up=up[i-1] if up[i-1] is not None else up[i]
            previous_down=down[i-1] if down[i-1] is not None else down[i]
            if f.c[i-1]<=previous_up and f.c[i]>up[i]:marker(out,f,i,'Donchian breakout','BUY',up[i])
            if f.c[i-1]>=previous_down and f.c[i]<down[i]:marker(out,f,i,'Donchian breakout','SELL',down[i])
    elif key=='momentum':
        a=[None if i<20 else f.c[i]/f.c[i-20]-1 for i in range(n)]
        for i in range(21,n):
            if side:=cross(a,[0.0]*n,i):marker(out,f,i,'20-bar momentum',side)
        out['metrics']={'return20':a[-1] if n else None}
    elif key=='ichimoku':
        ten,base,sa,sb=f.get('ichimoku')
        for a,label in [(ten,'Tenkan 9'),(base,'Kijun 26'),(sa,'Causal cloud A'),(sb,'Causal cloud B')]:series(out,f,a,label)
        for i in range(78,n):
            if None in (sa[i-1],sb[i-1],sa[i],sb[i]):continue
            if f.c[i-1]<=max(sa[i-1],sb[i-1]) and f.c[i]>max(sa[i],sb[i]) and ten[i]>base[i]:marker(out,f,i,'Cloud breakout','BUY')
            if f.c[i-1]>=min(sa[i-1],sb[i-1]) and f.c[i]<min(sa[i],sb[i]) and ten[i]<base[i]:marker(out,f,i,'Cloud breakout','SELL')
    else:raise ValueError('Unknown indicator method')
    return out


def candle_method(key,f,inputs,deps):
    out=blank()
    for i in range(f.n):
        o,h,l,c=f.o[i],f.h[i],f.l[i],f.c[i];span=h-l;body=abs(c-o)
        if key=='engulfing' and i:
            po,pc=f.o[i-1],f.c[i-1]
            if pc<po and c>o and o<=pc and c>=po and body>abs(pc-po):marker(out,f,i,'Bull engulfing','BUY')
            elif pc>po and c<o and o>=pc and c<=po and body>abs(pc-po):marker(out,f,i,'Bear engulfing','SELL')
        elif key=='pinbar' and span>0 and body<=span*.3:
            upper=h-max(o,c);lower=min(o,c)-l
            if lower>=max(2*body,.6*span) and upper<=.2*span:marker(out,f,i,'Hammer shape','BUY')
            if upper>=max(2*body,.6*span) and lower<=.2*span:marker(out,f,i,'Shooting-star shape','SELL')
        elif key=='inside_break' and i>=2 and f.h[i-1]<f.h[i-2] and f.l[i-1]>f.l[i-2]:
            if c>f.h[i-2]:marker(out,f,i,'Inside mother break','BUY',f.h[i-2])
            elif c<f.l[i-2]:marker(out,f,i,'Inside mother break','SELL',f.l[i-2])
        elif key=='compression' and i>=40:
            near=max(f.h[i-10:i])-min(f.l[i-10:i]);prior=max(f.h[i-40:i-10])-min(f.l[i-40:i-10])
            if 0<near<=.5*prior and span>0 and body/span>=.6:
                if c>max(f.h[i-10:i]) and c>o:marker(out,f,i,'Compression break','BUY')
                elif c<min(f.l[i-10:i]) and c<o:marker(out,f,i,'Compression break','SELL')
    return out


def structure_events(f):
    events=[];used=set();trend=None
    for i in range(1,f.n):
        for kind,side in [('HIGH','BUY'),('LOW','SELL')]:
            s=f.latest_swing_at(f.open_at(i),kind)
            if s is None:continue
            p=float(s['price'])
            if s['id'] in used:continue
            if f.c[i-1]<=p<f.c[i] if side=='BUY' else f.c[i-1]>=p>f.c[i]:
                events.append((i,s,side,'CHoCH' if trend and trend!=side else 'BOS'));used.add(s['id']);trend=side
    return events


def gap_zones(f):
    zones=[]
    for i in range(2,f.n):
        if f.h[i-2]<f.l[i]:lo,hi,side=f.h[i-2],f.l[i],'BUY'
        elif f.h[i]<f.l[i-2]:lo,hi,side=f.h[i],f.l[i-2],'SELL'
        else:continue
        state='CONFIRMED';first=None;terminal=None
        for j in range(i+1,f.n):
            if (f.c[j]<lo if side=='BUY' else f.c[j]>hi):state='INVALIDATED';terminal=j;break
            if (f.l[j]<=lo if side=='BUY' else f.h[j]>=hi):state='FILLED';terminal=j;break
            if f.l[j]<=hi and f.h[j]>=lo:
                state='TOUCHED'
                if first is None:first=j
        zones.append(dict(index=i,low=lo,high=hi,side=side,state=state,first=first,terminal=terminal))
    return zones


def structural_method(key,f,inputs,deps):
    out=blank()
    if key=='structure':
        for i,s,side,label in structure_events(f):marker(out,f,i,label,side,s['price'],roots=(s['id'],))
    elif key=='liquidity':
        used=set()
        for i in range(f.n):
            eligible=f.swings_at(f.open_at(i))
            for kind,side in [('LOW','BUY'),('HIGH','SELL')]:
                pivots=[s for s in eligible if s['kind']==kind]
                if not pivots:continue
                s=pivots[-1];p=float(s['price'])
                if s['id'] in used:continue
                if f.l[i]<p<f.c[i] if side=='BUY' else f.h[i]>p>f.c[i]:
                    marker(out,f,i,'Sweep / reclaim',side,p,roots=(s['id'],));used.add(s['id'])
        for kind in ('LOW','HIGH'):
            pivots=[s for s in f.swings if s['kind']==kind][-12:]
            tick=float((inputs.get('spec') or {}).get('tick_size') or 0)
            for a,b in zip(pivots,pivots[1:]):
                if tick>0 and abs(float(a['price'])-float(b['price']))<=2*tick:
                    zone(out,f,f.index[b['pivot_time']],min(float(a['price']),float(b['price'])),max(float(a['price']),float(b['price'])),
                         'EQL' if kind=='LOW' else 'EQH','BUY' if kind=='LOW' else 'SELL',available=b['available_at'],roots=(a['id'],b['id']))
    elif key in {'fvg','pullback_fvg'}:
        for g in gap_zones(f):
            i,lo,hi,side=g['index'],g['low'],g['high'],g['side']
            if key=='fvg':
                # Current state is known only at the last observed close; initial geometry is separately stamped.
                known=f.known_at(g['terminal'] or f.n-1)
                zone(out,f,i,lo,hi,'FVG',side,available=known,state=g['state'])
            elif g['first'] is not None:
                j=g['first']
                if (g['terminal'] is None or j<g['terminal']) and (f.c[j]>hi and f.c[j]>f.o[j] if side=='BUY' else f.c[j]<lo and f.c[j]<f.o[j]):marker(out,f,j,'FVG mitigation',side)
    elif key in {'support_resistance','fibonacci','ote'}:
        if key=='support_resistance':
            for s in f.swings[-8:]:
                if s['pivot_time'] in f.index:zone(out,f,f.index[s['pivot_time']],float(s['price']),float(s['price']),'Swing '+s['kind'],'NEUTRAL',available=s['available_at'],roots=(s['id'],))
        else:
            pivots=f.alternating()
            if len(pivots)>=2:
                a,b=pivots[-2:];start,end=float(a['price']),float(b['price']);known=max(a['available_at'],b['available_at'],key=instant);i=f.index[b['pivot_time']];side='BUY' if end>start else 'SELL'
                if key=='ote':
                    prices=[end-(end-start)*r for r in (.62,.79)];zone(out,f,i,min(prices),max(prices),'OTE 62–79%',side,available=known,roots=(a['id'],b['id']))
                    price=end-(end-start)*.705;zone(out,f,i,price,price,'OTE 70.5%',side,available=known,roots=(a['id'],b['id']))
                else:
                    for ratio in (.382,.5,.618,.786):
                        price=end-(end-start)*ratio;zone(out,f,i,price,price,'Fib '+str(ratio),side,available=known,roots=(a['id'],b['id']))
    elif key in {'previous_extremes','open_midpoint'}:
        for frame in ('D1','W1'):
            rows=inputs['bars'].get(frame,())
            if not rows:continue
            b=rows[-1]
            for name,p in ([('high',b['high']),('low',b['low'])] if key=='previous_extremes' else [('open',b['open']),('midpoint',str((Decimal(b['high'])+Decimal(b['low']))/2))]):
                z={'low':str(p),'high':str(p),'label':'Last completed '+frame+' '+name,'side':'NEUTRAL','state':'CONFIRMED','available_at':b['available_at'],'root_ids':[digest(b)],'source_timeframe':frame};out['zones'].append(z)
    elif key in {'order_block','pullback_ob'}:
        frame=inputs['frame'];events=(deps.get('SMC_STRUCTURE',{}).get('output') or {}).get(frame,())
        for event in events:
            # Find break by timestamp rather than a bounded-window-relative integer from another owner.
            i=f.index.get(event['break_time']);side=event['side']
            if i is None:continue
            source=next((j for j in range(i-1,max(-1,i-21),-1) if (f.c[j]<f.o[j] if side=='BUY' else f.c[j]>f.o[j])),None)
            if source is None:continue
            lo,hi=f.l[source],f.h[source]
            if key=='order_block':continue # Existing typed ORDER_BLOCK levels own its chart geometry.
            for j in range(i+1,f.n):
                if f.c[j]<lo if side=='BUY' else f.c[j]>hi:break
                if f.l[j]<=hi and f.h[j]>=lo:
                    if f.c[j]>hi and f.c[j]>f.o[j] if side=='BUY' else f.c[j]<lo and f.c[j]<f.o[j]:marker(out,f,j,'OB mitigation',side,available=event['available_at'],roots=(event['id'],))
                    break
    else:raise ValueError('Unknown structural method')
    return out


def wyckoff(f,inputs,deps):
    out=blank();used=set()
    for i in range(20,f.n):
        low=min(f.l[i-20:i]);high=max(f.h[i-20:i]);width=high-low
        if width<=0:continue
        tol=.1*width
        def tests(values,boundary):
            hits=[j for j,v in enumerate(values) if abs(v-boundary)<=tol]
            return sum(j==0 or hits[j]-hits[j-1]>=2 for j in range(len(hits)))
        if tests(f.l[i-20:i],low)<2 or tests(f.h[i-20:i],high)<2:continue
        side=None;label=None
        if f.l[i]<low<f.c[i]<high:side,label='BUY','Spring hypothesis'
        elif f.h[i]>high>f.c[i]>low:side,label='SELL','UTAD hypothesis'
        elif f.c[i]>high and f.c[i]>f.o[i] and abs(f.c[i]-f.o[i])>=.6*(f.h[i]-f.l[i]):side,label='BUY','SOS hypothesis'
        elif f.c[i]<low and f.c[i]<f.o[i] and abs(f.c[i]-f.o[i])>=.6*(f.h[i]-f.l[i]):side,label='SELL','SOW hypothesis'
        if not side:continue
        identity=(label,round(low,10),round(high,10))
        if identity in used:continue
        used.add(identity);marker(out,f,i,label,side);zone(out,f,i,low,high,'Wyckoff range hypothesis',side)
        if label.startswith(('Spring','UTAD')):
            for j in range(i+1,min(f.n,i+11)):
                if (f.l[j]<f.l[i] if side=='BUY' else f.h[j]>f.h[i]):break
                if (f.l[j]<=low+tol and f.c[j]>low if side=='BUY' else f.h[j]>=high-tol and f.c[j]<high):marker(out,f,j,'Secondary TEST hypothesis',side);break
    return out


def impulse_matches(points):
    if len(points)!=6:return False
    p=[float(x['price']) for x in points];sign=1 if p[1]>p[0] else -1;p=[v*sign for v in p]
    w1,w3,w5=p[1]-p[0],p[3]-p[2],p[5]-p[4]
    return p[0]<p[2]<p[1]<p[4]<p[3]<p[5] and w3>=min(w1,w5)


def abc_matches(points):
    if len(points)!=4:return False
    p=[float(x['price']) for x in points];sign=1 if p[1]>p[0] else -1;p=[v*sign for v in p]
    return p[0]<p[2]<p[1]<p[3]


def harmonic_matches(points):
    p=[float(x['price']) for x in points];near=lambda v,target:abs(v/target-1)<=.05
    if len(p)==4:
        a,b,c,d=p;ab=abs(b-a);bc=abs(c-b);cd=abs(d-c)
        sign=1 if b>a else -1;a,b,c,d=[v*sign for v in p]
        if not a<c<b<d:return None
        if min(ab,bc,cd)>0 and .382<=bc/ab<=.886 and 1.13<=cd/bc<=2.618 and near(cd/ab,1):return 'AB=CD'
    if len(p)==5:
        x,a,b,c,d=p;sign=1 if a>x else -1;x,a,b,c,d=[v*sign for v in p]
        if not x<b<c<a or not d<c:return None
        xa,ab,bc,cd=a-x,a-b,c-b,c-d
        if min(xa,ab,bc,cd)<=0 or not .382<=bc/ab<=.886:return None
        r=cd/ab;bd=(a-d)/xa;bcproj=cd/bc
        if near(ab/xa,.618) and near(bd,.786) and 1.27<=bcproj<=1.618 and near(r,1):return 'Gartley'
        if .382<=ab/xa<=.5 and near(bd,.886) and 1.618<=bcproj<=2.618 and r>=.95:return 'Bat'
        if near(ab/xa,.786) and near(bd,1.27) and 1.618<=bcproj<=2.618 and .95<=r<=1.27*1.05:return 'Butterfly'
    return None


def pattern_method(key,f,inputs,deps):
    out=blank();pivots=f.alternating()[-32:]
    sizes={'elliott':(4,6),'elliott_impulse':(6,),'elliott_abc':(4,),'harmonic':(4,5),'abcd':(4,),'gartley':(5,),'bat':(5,),'butterfly':(5,)}
    target={'abcd':'AB=CD','gartley':'Gartley','bat':'Bat','butterfly':'Butterfly'}.get(key)
    for size in sizes[key]:
        for k in range(len(pivots)-size+1):
            p=pivots[k:k+size]
            label=('Impulse hypothesis' if size==6 and impulse_matches(p) else 'ABC hypothesis' if size==4 and abc_matches(p) else None) if key.startswith('elliott') else harmonic_matches(p)
            if target and label!=target:continue
            if not label:continue
            i=f.index[p[-1]['pivot_time']];known=max((x['available_at'] for x in p),key=instant);price=float(p[-1]['price']);side='BUY' if p[-1]['kind']=='LOW' else 'SELL'
            marker(out,f,i,label,side,price,available=known,roots=tuple(x['id'] for x in p))
            zone(out,f,i,price,price,label+' observed completion',side,available=known,roots=tuple(x['id'] for x in p))
    return out

INDICATORS={'sma_cross','ema_cross','macd','rsi','stochastic','adx','bollinger','donchian','momentum','ichimoku'}
CANDLES={'engulfing','pinbar','inside_break','compression'}


def evaluate(key,f,inputs,deps):
    from .public_price_models import PRICE_CONTEXT,PRICE_SEQUENCES,evaluate_price
    from .public_genuine_data import DATA_METHODS,evaluate_genuine,evaluate_live_body
    if key in PRICE_CONTEXT|PRICE_SEQUENCES:out=evaluate_price(key,f,inputs,deps)
    elif key in DATA_METHODS:out=evaluate_genuine(key,f,inputs,deps)
    elif key=='previous_body_live':out=evaluate_live_body(f,inputs)
    elif key in {'session_asia','session_london','session_new_york','session_sweep','session_breakout','killzones'}:
        from .public_sessions import evaluate_session
        out=evaluate_session(key,f,inputs,deps)
    elif key in {'wyckoff_phase','wyckoff_spring_test','wyckoff_utad_test','wyckoff_break_retest'}:
        from .public_wyckoff import evaluate_wyckoff
        out=evaluate_wyckoff(key,f,inputs,deps)
    elif key in {'elliott_alternatives','macro_elliott','harmonic_prz'}:
        from .public_pattern_models import evaluate_pattern
        out=evaluate_pattern(key,f,inputs,deps)
    elif key in INDICATORS:out=indicator_method(key,f,inputs,deps)
    elif key in CANDLES:out=candle_method(key,f,inputs,deps)
    elif key=='wyckoff':out=wyckoff(f,inputs,deps)
    elif key in {'elliott','elliott_impulse','elliott_abc','harmonic','abcd','gartley','bat','butterfly'}:out=pattern_method(key,f,inputs,deps)
    else:out=structural_method(key,f,inputs,deps)
    out['markers']=out['markers'][-32:];out['zones']=out['zones'][-16:]
    return out
