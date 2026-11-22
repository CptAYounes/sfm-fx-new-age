"""Shared causal event primitives for document-backed public projection models.

All numerical cutoffs are explicit uncalibrated engineering choices. Events are
observations only. No fills, orders, institution identity or performance implied.
"""
from __future__ import annotations
from bisect import bisect_right
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from .public_features import Features,ema


def cached(f,key,build):
    if key not in f.cache:f.cache[key]=build()
    return f.cache[key]


def true_ranges(f):
    return cached(f,'sequence_tr',lambda:[f.h[0]-f.l[0]]+[max(f.h[i]-f.l[i],abs(f.h[i]-f.c[i-1]),abs(f.l[i]-f.c[i-1])) for i in range(1,f.n)] if f.n else [])


def atr(f):return cached(f,'sequence_atr',lambda:ema([None]+true_ranges(f)[1:],14,wilder=True))


def displacement(f):
    def build():
        tr=true_ranges(f);out={}
        for i in range(15,f.n):
            span=f.h[i]-f.l[i];body=abs(f.c[i]-f.o[i]);baseline=sum(tr[i-14:i])/14
            if span>0 and baseline>0 and body>=.6*span and body>=baseline:
                out[i]=dict(index=i,side='BUY' if f.c[i]>f.o[i] else 'SELL',baseline=baseline,body=body)
        return out
    return cached(f,'sequence_displacement',build)


def known_swings(f,i,kind=None):
    return f.swings_at(f.open_at(i),kind,pivot_before=True)


def alternating_at(f,at):
    points=[]
    cutoff=instant(at)
    eligible=[s for s,available,_,_ in f.get('swing_clocks')[1] if available<=cutoff and s['pivot_time'] in f.index]
    for s in eligible:
        if points and s['pivot_time']==points[-1]['pivot_time']:points.pop();continue
        if points and s['kind']==points[-1]['kind']:
            if (float(s['price'])-float(points[-1]['price']))*(1 if s['kind']=='HIGH' else -1)>0:points[-1]=s
        else:points.append(s)
    return points


def structure(f):
    def build():
        from .public_algorithms import structure_events
        return structure_events(f)
    return cached(f,'sequence_structure',build)


def pivot_pools(f,inputs):
    """Freeze an individual swing or equal-extreme pair; never revise its roots."""
    def build():
        tick=float((inputs.get('spec') or {}).get('tick_size') or 0)
        pools=[];previous={}
        for s in sorted(f.swings,key=lambda s:(instant(s['available_at']),s['id'])):
            if s['pivot_time'] not in f.index:continue
            price=float(s['price']);roots=[s['id']];lo=hi=price
            old=previous.get(s['kind'])
            if old and tick>0 and abs(float(old['price'])-price)<=2*tick:
                lo=min(price,float(old['price']));hi=max(price,float(old['price']));roots.insert(0,old['id'])
            previous[s['kind']]=s
            known=s['available_at'];start=f.first_open_at_or_after(known)
            if start is None:continue
            pools.append(dict(id=digest(roots),low=lo,high=hi,side='SELL' if s['kind']=='HIGH' else 'BUY',start=start,
                              available_at=known,roots=tuple(roots),label='EQH' if len(roots)>1 and s['kind']=='HIGH' else 'EQL' if len(roots)>1 else 'Swing '+s['kind']))
        return pools
    return cached(f,'sequence_pools',build)


def sweeps(f,pools):
    out=[]
    for p in pools:
        side=p['side'];price=p['low'] if side=='BUY' else p['high']
        for i in range(p['start'],min(f.n,p['start']+129,p.get('expiry',f.n-1)+1)):
            if side=='BUY' and f.c[i]<p['low'] or side=='SELL' and f.c[i]>p['high']:break
            if f.l[i]<price<f.c[i] if side=='BUY' else f.h[i]>price>f.c[i]:
                out.append(dict(index=i,side=side,pool=p,extreme=f.l[i] if side=='BUY' else f.h[i]));break
    return sorted(out,key=lambda e:(e['index'],e['pool']['id']))


def origin(f,i,side,*,after=-1):
    source=next((j for j in range(i-1,max(-1,i-21,after-1),-1) if (f.c[j]<f.o[j] if side=='BUY' else f.c[j]>f.o[j])),None)
    if source is None:return None
    return dict(low=f.l[source],high=f.h[source],side=side,source=source,confirmed=i,roots=(digest(f.bars[source]),),kind='OB')


def gaps(f):
    def build():
        out=[]
        for i in range(2,f.n):
            if f.h[i-2]<f.l[i]:low,high,side=f.h[i-2],f.l[i],'BUY'
            elif f.h[i]<f.l[i-2]:low,high,side=f.h[i],f.l[i-2],'SELL'
            else:continue
            out.append(dict(low=low,high=high,side=side,source=i-1,confirmed=i,roots=tuple(digest(b) for b in f.bars[i-2:i+1]),kind='FVG'))
        return out
    return cached(f,'sequence_gaps',build)


def held(f,i,lo,hi,side):
    contact=f.l[i]<=hi and f.h[i]>=lo
    return contact and (f.c[i]>hi and f.c[i]>f.o[i] if side=='BUY' else f.c[i]<lo and f.c[i]<f.o[i])


def retest(f,start,lo,hi,side,*,deadline=16,anchor=None,full_fill=False):
    """First contact, strictly after confirmation. Bad first contact is terminal."""
    for i in range(start+1,min(f.n,start+deadline+1)):
        if anchor is not None and (f.c[i]<anchor if side=='BUY' else f.c[i]>anchor):break
        if f.c[i]<lo if side=='BUY' else f.c[i]>hi:break
        if full_fill and (f.l[i]<=lo if side=='BUY' else f.h[i]>=hi):break
        if f.l[i]<=hi and f.h[i]>=lo:return i if held(f,i,lo,hi,side) else None
    return None


def stages(f,items):
    return [dict(stage=name,time=f.bars[i]['close_time'],available_at=f.known_at(i),root_id=f.root_id(i)) for name,i in items]


def emit_setup(out,f,i,label,side,lo,hi,sequence,*,roots=(),anchor=None,target=None,available=None):
    from .public_algorithms import marker,zone
    marker(out,f,i,label,side,available=available,roots=roots)
    row=out['markers'][-1];row['stages']=stages(f,sequence);row['invalidation']=str(anchor) if anchor else None
    row['correlation_id']=digest([s['root_id'] for s in row['stages']])
    known=row['available_at']
    zone(out,f,i,lo,hi,label+' origin',side,available=known,roots=roots)
    if anchor and anchor>0:zone(out,f,i,anchor,anchor,label+' invalidation',side,available=known,roots=roots)
    if target and target>0:zone(out,f,i,target,target,label+' measured objective',side,available=known,roots=roots)


def sweep_models(f,inputs,*,pools=None,setup=True,label='Sweep reversal'):
    from .public_algorithms import blank,marker
    out=blank();pools=pivot_pools(f,inputs) if pools is None else pools
    breaks=structure(f);pressure=displacement(f);used=set()
    for sweep in sweeps(f,pools):
        i,side=sweep['index'],sweep['side'];p=sweep['pool']
        controlling=known_swings(f,i,'HIGH' if side=='BUY' else 'LOW')
        if not controlling:continue
        control=controlling[-1]
        for j in range(i+1,min(f.n,i+9)):
            if f.c[j]<sweep['extreme'] if side=='BUY' else f.c[j]>sweep['extreme']:break
            prior_pressure=[k for k,v in pressure.items() if i<k<=j and v['side']==side]
            broken=next((e for e in breaks if e[0]==j and e[2]==side and e[1]['id']==control['id']),None)
            if not prior_pressure or not broken:continue
            dis=prior_pressure[0]
            if not setup:
                marker(out,f,j,'MSS · sweep / displacement',side,roots=p['roots']+(control['id'],));out['markers'][-1]['stages']=stages(f,[('SWEEP_RECLAIM',i),('DISPLACEMENT',dis),('STRUCTURE_BREAK',j)]);break
            block=origin(f,j,side,after=max(0,i-2))
            zones=([block] if block else [])+[g for g in gaps(f) if i<g['confirmed']<=j and g['side']==side]
            for z in zones:
                touch=retest(f,j,z['low'],z['high'],side,anchor=sweep['extreme'],full_fill=z['kind']=='FVG')
                if touch is None:continue
                identity=(i,j,touch,z['kind'],side)
                if identity in used:continue
                used.add(identity)
                emit_setup(out,f,touch,label+' '+z['kind'],side,z['low'],z['high'],[('SWEEP_RECLAIM',i),('DISPLACEMENT',dis),('STRUCTURE_BREAK',j),('HELD_RETEST',touch)],roots=p['roots']+(control['id'],)+z['roots'],anchor=sweep['extreme'])
            break
    return out


def acceptance(f,i,lo,hi,side,*,deadline=16):
    boundary=hi if side=='BUY' else lo;accepted=None
    for j in range(i+1,min(f.n,i+deadline+1)):
        beyond=f.c[j]>boundary if side=='BUY' else f.c[j]<boundary
        if not beyond:break
        if accepted is None:accepted=j;continue
        if held(f,j,boundary,boundary,side):return accepted,j
    return None


def breakout_models(f,inputs,*,kind='pools',pools=None,micro=False):
    from .public_algorithms import blank
    out=blank();pressure=displacement(f);consumed=set()
    if pools is None and kind=='pools':pools=[dict(p,side='BUY' if p['side']=='SELL' else 'SELL') for p in pivot_pools(f,inputs)]
    for i,move in pressure.items():
        side=move['side']
        if kind=='compression':
            if i<40:continue
            lo,hi=min(f.l[i-10:i]),max(f.h[i-10:i]);prior=max(f.h[i-40:i-10])-min(f.l[i-40:i-10])
            if not 0<hi-lo<=.5*prior:continue
            eligible=[dict(id=digest([f.bars[i-10],f.bars[i-1]]),low=lo,high=hi,roots=(digest(f.bars[i-10]),digest(f.bars[i-1])),start=i,label='Compression')]
        elif kind=='rolling':
            if i<20:continue
            eligible=[dict(id=digest(f.bars[i-20:i]),low=min(f.l[i-20:i]),high=max(f.h[i-20:i]),roots=(digest(f.bars[i-20]),),start=i,label='Prior 20 range')]
        else:eligible=[p for p in pools or () if p['start']<=i<=p['start']+128 and (p.get('expiry') is None or i<=p['expiry']) and (p.get('side') in {None,side})]
        for p in eligible:
            if p['id'] in consumed:continue
            boundary=p['high'] if side=='BUY' else p['low']
            if not (f.c[i-1]<=boundary<f.c[i] if side=='BUY' else f.c[i-1]>=boundary>f.c[i]):continue
            consumed.add(p['id']);result=acceptance(f,i,p['low'],p['high'],side)
            if not result:continue
            a,j=result;seq=[('DISPLACEMENT_BREAK',i),('ACCEPTED_CLOSE',a),('HELD_RETEST',j)];k=j
            if micro:
                k=next((t for t in range(j+1,min(f.n,j+9)) if (f.c[t]>f.h[j] if side=='BUY' else f.c[t]<f.l[j])),None)
                if k is None:continue
                if any((f.c[t]<boundary if side=='BUY' else f.c[t]>boundary) for t in range(j+1,k)):continue
                seq.append(('POST_RETEST_MICRO_BREAK',k))
            emit_setup(out,f,k,p['label']+' acceptance / retest',side,boundary,boundary,seq,roots=p['roots'],anchor=f.l[j] if side=='BUY' else f.h[j])
    return out


def prior_day_pools(f,inputs):
    rows=inputs['bars'].get('D1',())
    if not rows:raise ProjectionInputUnavailable('Prior available native D1 bars required')
    pools=[];closes=[instant(b['close_time']) for b in rows];ordered=sorted(set(closes))
    for b,closed in zip(rows,closes):
        start=f.first_open_at_or_after(max(instant(b['available_at']),closed))
        if start is None:continue
        # The last D1 completed before interaction owns it, not a future D1 close.
        following=bisect_right(ordered,closed);end=ordered[following] if following<len(ordered) else None
        boundary=f.first_open_at_or_after(end) if end is not None else None
        expiry=boundary-1 if boundary is not None else f.n-1
        for side,k in [('BUY','low'),('SELL','high')]:
            p=float(b[k]);pools.append(dict(id=digest([b,k]),start=start,expiry=expiry,low=p,high=p,side=side,available_at=b['available_at'],roots=(digest(b),),label='Previous D1 '+k))
    return pools


def higher_bias(inputs,deps,at,frame):
    parent='W1' if frame in {'D1','W1'} else 'D1'
    rows=[b for b in inputs['bars'].get(parent,()) if instant(b['available_at'])<=instant(at) and instant(b['close_time'])<=instant(at)]
    if len(rows)<6:return None
    events=(deps.get('SMC_STRUCTURE',{}).get('output') or {}).get(parent,())
    valid=[e for e in events if instant(e['available_at'])<=instant(at)]
    return max(valid,key=lambda e:instant(e['available_at']))['side'] if valid else None


def zone_models(f,inputs,deps,*,kind=None,trend=False):
    from .public_algorithms import blank
    out=blank();events=(deps.get('SMC_STRUCTURE',{}).get('output') or {}).get(inputs['frame'],())
    if trend and not inputs['bars'].get('W1' if inputs['frame'] in {'D1','W1'} else 'D1'):raise ProjectionInputUnavailable('Causal higher-frame structure context required')
    for event in events:
        i=f.index.get(event['break_time']);side=event['side']
        if i is None:continue
        if trend and higher_bias(inputs,deps,f.bars[i]['open_time'],inputs['frame'])!=side:continue
        ob=origin(f,i,side);zones=([ob] if ob else [])+[g for g in gaps(f) if g['side']==side and i-2<=g['confirmed']<=i]
        for z in zones:
            if kind and z['kind']!=kind:continue
            j=retest(f,i,z['low'],z['high'],side,full_fill=z['kind']=='FVG')
            if j is None:continue
            targets=[float(s['price']) for s in known_swings(f,j,'HIGH' if side=='BUY' else 'LOW') if (float(s['price'])>f.c[j] if side=='BUY' else float(s['price'])<f.c[j])]
            # A target crossed in the intervening bars is already consumed.
            targets=[t for t in targets if not any((f.h[k]>=t if side=='BUY' else f.l[k]<=t) for k in range(i+1,j+1))]
            if trend and not targets:continue
            emit_setup(out,f,j,('Trend ' if trend else 'SMC ')+z['kind']+' held retest',side,z['low'],z['high'],[('DISPLACEMENT_STRUCTURE',i),('HELD_RETEST',j)],roots=(event['id'],)+z['roots'],anchor=z['low'] if side=='BUY' else z['high'],target=(min(targets) if side=='BUY' else max(targets)) if targets else None,available=event['available_at'])
    return out
