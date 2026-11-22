"""Additional price-action profiles; projection-only and strictly causal."""
from __future__ import annotations
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from .public_features import cross,sma
from .public_sequence_features import (atr,true_ranges,displacement,structure,known_swings,pivot_pools,sweeps,origin,gaps,
    held,retest,emit_setup,sweep_models,breakout_models,prior_day_pools,zone_models,alternating_at)


def pool_lifecycle(f,inputs):
    from .public_algorithms import blank,zone
    out=blank();pools=pivot_pools(f,inputs);live=0
    for p in pools:
        touches=0;state='CONFIRMED';end=min(f.n-1,p['start']+128)
        for i in range(p['start'],end+1):
            if f.c[i]<p['low'] if p['side']=='BUY' else f.c[i]>p['high']:state='BROKEN';end=i;break
            if f.l[i]<=p['high'] and f.h[i]>=p['low']:
                touches+=1;state='TOUCHED'
                if f.l[i]<p['low']<f.c[i] if p['side']=='BUY' else f.h[i]>p['high']>f.c[i]:state='SWEPT';end=i;break
        if state in {'CONFIRMED','TOUCHED'} and f.n-1>p['start']+128:state='EXPIRED'
        if state in {'CONFIRMED','TOUCHED'}:live+=1
        known=max((p['available_at'],f.known_at(end)),key=instant)
        zone(out,f,end,p['low'],p['high'],p['label'],p['side'],available=known,state=state,roots=p['roots'])
        out['zones'][-1].update(pool_id=p['id'],contact_bars=touches,age_bars=end-p['start'],price_root_count=len(p['roots']))
    out['metrics']=dict(active_pool_count=live,price_pool_count=len(pools),density_unit='CONFIRMED_PRICE_ROOTS_NOT_ORDERS')
    return out


def breaker(f,inputs):
    from .public_algorithms import blank
    out=blank();moves=displacement(f);breaks=structure(f);all_sweeps=sweeps(f,pivot_pools(f,inputs))
    for i,p,side,_ in breaks:
        if i not in moves or moves[i]['side']!=side:continue
        z=origin(f,i,side)
        if not z:continue
        opposite='SELL' if side=='BUY' else 'BUY';failure=None
        for j in range(i+1,min(f.n,i+65)):
            if f.c[j]<z['low'] if side=='BUY' else f.c[j]>z['high']:failure=j;break
        if failure is None:continue
        swe=[s for s in all_sweeps if i<s['index']<failure and s['side']==opposite]
        if not swe:continue
        s=swe[-1];shift=next((e for e in breaks if failure<=e[0]<=failure+8 and e[2]==opposite and e[0] in moves and moves[e[0]]['side']==opposite),None)
        if not shift:continue
        j=shift[0];touch=retest(f,j,z['low'],z['high'],opposite,anchor=s['extreme'])
        if touch is not None:
            emit_setup(out,f,touch,'Breaker flipped retest',opposite,z['low'],z['high'],[('ORIGINAL_OB_CONFIRMED',i),('LIQUIDITY_SWEPT',s['index']),('OB_FAILED',failure),('OPPOSITE_STRUCTURE',j),('FLIPPED_RETEST',touch)],roots=z['roots']+s['pool']['roots']+(shift[1]['id'],),anchor=s['extreme'])
    return out


def mitigation(f,inputs):
    from .public_algorithms import blank
    out=blank();used=set();moves=displacement(f)
    for i in moves:
        pts=alternating_at(f,f.bars[i]['open_time'])
        if len(pts)<3:continue
        a,b,c=pts[-3:];pa,pb,pc=map(lambda p:float(p['price']),(a,b,c))
        side='SELL' if a['kind']==c['kind']=='HIGH' and pa>pc>pb else 'BUY' if a['kind']==c['kind']=='LOW' and pa<pc<pb else None
        if not side or moves[i]['side']!=side:continue
        if not (f.c[i-1]>=pb>f.c[i] if side=='SELL' else f.c[i-1]<=pb<f.c[i]):continue
        ids=tuple(p['id'] for p in (a,b,c))
        if ids in used:continue
        used.add(ids);turn=f.index[c['pivot_time']]
        # Last opposite candle in the failure leg, not a future source chosen at retest.
        source=next((j for j in range(turn,max(-1,f.index[b['pivot_time']]-1),-1) if (f.c[j]>f.o[j] if side=='SELL' else f.c[j]<f.o[j])),None)
        if source is None:continue
        lo,hi=f.l[source],f.h[source];touch=retest(f,i,lo,hi,side,anchor=pc)
        if touch is not None:
            emit_setup(out,f,touch,'Mitigation failure-swing retest',side,lo,hi,[('FAILURE_SWING_KNOWN',next(j for j in range(i+1) if instant(f.bars[j]['close_time'])>=instant(c['available_at']))),('MSS_DISPLACEMENT',i),('HELD_RETEST',touch)],roots=ids+(digest(f.bars[source]),),anchor=pc)
    return out


def inducement(f,inputs):
    from .public_algorithms import blank
    out=blank();moves=displacement(f)
    for i,p,side,_ in structure(f):
        if i not in moves or moves[i]['side']!=side:continue
        z=origin(f,i,side)
        if not z:continue
        kind='LOW' if side=='BUY' else 'HIGH'
        for s in f.swings:
            if s['kind']!=kind or s['pivot_time'] not in f.index or f.index[s['pivot_time']]<=i:continue
            price=float(s['price'])
            if not (z['high']<price<f.h[i] if side=='BUY' else z['low']>price>f.l[i]):continue
            start=next((j for j in range(i+1,min(f.n,i+25)) if instant(f.bars[j]['open_time'])>=instant(s['available_at'])),None)
            if start is None:continue
            for j in range(start,min(f.n,i+25)):
                if f.c[j]<z['low'] if side=='BUY' else f.c[j]>z['high']:break
                if f.l[j]<price<f.c[j] if side=='BUY' else f.h[j]>price>f.c[j]:
                    touch=retest(f,j,z['low'],z['high'],side,anchor=z['low'] if side=='BUY' else z['high'])
                    if touch is not None:emit_setup(out,f,touch,'Internal inducement / origin response',side,z['low'],z['high'],[('CONTROLLING_BREAK',i),('INTERNAL_SWEEP',j),('ORIGIN_RESPONSE',touch)],roots=(p['id'],s['id'])+z['roots'],anchor=z['low'] if side=='BUY' else z['high'])
                    break
    return out


def void_return(f):
    from .public_algorithms import blank,zone
    out=blank();tr=true_ranges(f)
    for i in range(17,f.n):
        group=range(i-2,i+1);side='BUY' if all(f.c[j]>f.o[j] for j in group) else 'SELL' if all(f.c[j]<f.o[j] for j in group) else None
        if not side:continue
        bodies=[abs(f.c[j]-f.o[j]) for j in group]
        if any(f.h[j]<=f.l[j] or abs(f.c[j]-f.o[j])<.6*(f.h[j]-f.l[j]) for j in group):continue
        if any(max(0,min(max(f.o[j],f.c[j]),max(f.o[j-1],f.c[j-1]))-max(min(f.o[j],f.c[j]),min(f.o[j-1],f.c[j-1])))>.25*min(abs(f.c[j]-f.o[j]),abs(f.c[j-1]-f.o[j-1])) for j in range(i-1,i+1)):continue
        if abs(f.c[i]-f.o[i-2])<2*sum(tr[i-16:i-2])/14:continue
        lo,hi=sorted((f.c[i-2],f.o[i]));roots=tuple(digest(f.bars[j]) for j in group)
        zone(out,f,i,lo,hi,'Multi-candle low-overlap corridor',side,roots=roots)
        touch=retest(f,i,lo,hi,side,deadline=24)
        if touch is not None:emit_setup(out,f,touch,'Liquidity-void return response',side,lo,hi,[('IMPULSE_CORRIDOR_CONFIRMED',i),('RETURN_RESPONSE',touch)],roots=roots,anchor=lo if side=='BUY' else hi)
    return out


def previous_body(f,inputs,*,retest_mode=False):
    from .public_algorithms import blank,marker
    out=blank()
    if retest_mode and not any(inputs['bars'].get(fr) for fr in ('D1','W1')):raise ProjectionInputUnavailable('Completed D1/W1 contextual levels required')
    support={frame:[(b,max(instant(b['available_at']),instant(b['close_time']))) for b in inputs['bars'].get(frame,())]
             for frame in ('D1','W1')} if retest_mode else {}
    for i in range(1,f.n):
        po,pc=f.o[i-1],f.c[i-1];side='BUY' if pc<po and f.c[i]>po else 'SELL' if pc>po and f.c[i]<po else None
        if not side:continue
        boundary=po
        if not retest_mode:marker(out,f,i,'Previous-body completed recovery',side,boundary,roots=(f.root_id(i-1),f.root_id(i)));continue
        roots=[]
        opened=f.open_at(i)
        for frame in ('D1','W1'):
            rows=[b for b,known in support[frame] if known<=opened]
            if rows and any(min(po,pc)<=float(rows[-1][k])<=max(po,pc) for k in ('high','low')):roots.append(digest(rows[-1]))
        if not roots:continue
        touch=retest(f,i,boundary,boundary,side,deadline=8,anchor=min(f.l[i-1:i+1]) if side=='BUY' else max(f.h[i-1:i+1]))
        if touch is not None:emit_setup(out,f,touch,'Previous-body HTF held retest',side,boundary,boundary,[('BODY_RECOVERY',i),('HELD_RETEST',touch)],roots=tuple(roots)+(digest(f.bars[i-1]),),anchor=f.l[i] if side=='BUY' else f.h[i])
    return out


def tested_range(f,i,window=20):
    if i<window:return None
    lo,hi=min(f.l[i-window:i]),max(f.h[i-window:i]);width=hi-lo
    if width<=0:return None
    def count(values,boundary):
        hits=[j for j,v in enumerate(values) if abs(v-boundary)<=width*.1]
        return sum(k==0 or j-hits[k-1]>=2 for k,j in enumerate(hits))
    if count(f.l[i-window:i],lo)<2 or count(f.h[i-window:i],hi)<2:return None
    return lo,hi


def range_rotation(f):
    from .public_algorithms import blank
    out=blank();a=atr(f)
    for i in range(60,f.n):
        r=tested_range(f,i)
        old=[x for x in a[i-40:i] if x is not None]
        if not r or len(old)<40 or a[i] is None or a[i]>sum(old)/len(old):continue
        lo,hi=r;tol=(hi-lo)*.1
        # Neutral means an observed close-contained range, not absent data.
        if any(not lo<=x<=hi for x in f.c[i-20:i]):continue
        side='BUY' if f.l[i]<=lo+tol and f.c[i]>lo+tol and f.c[i]>f.o[i] else 'SELL' if f.h[i]>=hi-tol and f.c[i]<hi-tol and f.c[i]<f.o[i] else None
        if not side:continue
        j=next((j for j in range(i+1,min(f.n,i+9)) if f.c[j]>f.h[i] if side=='BUY'),None) if side=='BUY' else next((j for j in range(i+1,min(f.n,i+9)) if f.c[j]<f.l[i]),None)
        if j is None or any(f.c[k]<lo or f.c[k]>hi for k in range(i+1,j)):continue
        midpoint=(lo+hi)/2
        if side=='BUY' and (not lo<f.c[j]<midpoint or max(f.h[i:j+1])>=midpoint):continue
        if side=='SELL' and (not midpoint<f.c[j]<hi or min(f.l[i:j+1])<=midpoint):continue
        emit_setup(out,f,j,'Range boundary rotation',side,lo if side=='BUY' else hi,lo if side=='BUY' else hi,[('BOUNDARY_REACTION',i),('INTERNAL_CONFIRMATION',j)],roots=(digest(f.bars[i-20:i]),),anchor=f.l[i] if side=='BUY' else f.h[i],target=midpoint)
    return out


def simple_context(key,f,inputs):
    from .public_algorithms import blank,marker,zone,series
    out=blank()
    if key=='displacement':
        for i,m in displacement(f).items():marker(out,f,i,'Price displacement',m['side'])
        out['metrics']['volume_inferred']=False
    elif key=='sweep_context':
        tr=true_ranges(f)
        for s in sweeps(f,pivot_pools(f,inputs)):
            i=s['index'];p=s['pool'];baseline=sum(tr[max(0,i-14):i])/min(14,i) if i else 0
            if baseline<=0:continue
            level=p['low'] if s['side']=='BUY' else p['high'];depth=abs(level-s['extreme'])/baseline
            marker(out,f,i,'Sweep depth '+format(depth,'.2f')+' prior-TR',s['side'],level,roots=p['roots']);out['markers'][-1].update(depth_prior_tr=depth,age_bars=i-p['start'])
    elif key=='candle_pressure':
        raw=[(f.c[i]-f.o[i])/(f.h[i]-f.l[i]) if f.h[i]>f.l[i] else 0 for i in range(f.n)];a=sma(raw,14)
        for i in range(1,f.n):
            if side:=cross(a,[0]*f.n,i):marker(out,f,i,'Price-only pressure cross',side)
        out['metrics']=dict(balance_of_power14=a[-1],data_kind='OHLC_PROXY_NOT_ORDER_FLOW')
    elif key=='round_numbers':
        spec=inputs.get('spec') or {};pip=float(spec.get('pip_size') or 0);tick=float(spec.get('tick_size') or 0)
        if min(pip,tick)<=0:raise ProjectionInputUnavailable('Native PipSize and TickSize required')
        step=100*pip;centre=round(f.c[-1]/step)
        for k in range(centre-2,centre+3):
            price=round(k*step/tick)*tick
            if price>0:zone(out,f,f.n-1,price,price,'100-pip round number','NEUTRAL')
    elif key=='rolling_extremes':
        rows=inputs['bars'].get('W1',())
        if len(rows)<13:raise ProjectionInputUnavailable('At least 13 completed W1 bars required','WARMUP')
        missing=[]
        for period in (13,52,104):
            if len(rows)<period:missing.append(period);continue
            eligible=rows[-period:];known=max((b['available_at'] for b in eligible),key=instant)
            for kind,op in [('high',max),('low',min)]:
                price=op(float(b[kind]) for b in eligible);zone(out,f,f.n-1,price,price,str(period)+' observed weeks '+kind,'NEUTRAL',available=known,roots=(digest(eligible),))
        out['metrics']['warmup_periods']=missing
    elif key=='trend_persistence':
        ratios=[None]*f.n
        for i in range(20,f.n):
            gross=sum(abs(f.c[j]-f.c[j-1]) for j in range(i-19,i+1));ratios[i]=(f.c[i]-f.c[i-20])/gross if gross else 0
        for i in range(21,f.n):
            if ratios[i-1]<=.5<ratios[i]:marker(out,f,i,'Persistent positive efficiency','BUY')
            elif ratios[i-1]>=-.5>ratios[i]:marker(out,f,i,'Persistent negative efficiency','SELL')
        out['metrics']=dict(directional_efficiency20=ratios[-1],positive_fraction20=sum(f.c[i]>f.c[i-1] for i in range(f.n-20,f.n))/20)
    elif key=='atr_trail':
        a=atr(f);long=[None]*f.n;short=[None]*f.n
        for i in range(21,f.n):
            if a[i] is not None:long[i]=max(f.h[i-21:i+1])-3*a[i];short[i]=min(f.l[i-21:i+1])+3*a[i]
        series(out,f,long,'Display long Chandelier 22/3');series(out,f,short,'Display short Chandelier 22/3')
    elif key=='regime_context':
        pos,neg,adx=f.get('adx');a=atr(f);past=[v for v in a[-41:-1] if v is not None]
        if adx[-1] is None or len(past)<40:raise ProjectionInputUnavailable('ADX14 and 40 prior ATR observations required','WARMUP')
        ratio=a[-1]/(sum(past)/40) if sum(past)>0 else 1;regime='TREND' if adx[-1]>=25 else 'RANGE' if adx[-1]<=20 else 'TRANSITION'
        marker(out,f,f.n-1,regime+' / '+('EXPANSION' if ratio>=1.5 else 'CONTRACTION' if ratio<=.67 else 'NORMAL'),'NEUTRAL')
        out['metrics']=dict(adx14=adx[-1],atr_ratio=ratio,regime=regime,automatic_switching=False)
    else:raise ValueError('Unknown price context')
    return out


PRICE_CONTEXT={'displacement','sweep_context','candle_pressure','round_numbers','rolling_extremes','trend_persistence','atr_trail','regime_context'}
PRICE_SEQUENCES={'mss','liquidity_pools','pool_rejection','pool_breakout','sweep_reversal','compression_retest','break_confirmation','trend_ob','trend_fvg','smc_zone_retest','breaker','mitigation_block','inducement','liquidity_void','previous_day_sweep','previous_day_breakout','previous_body','previous_body_retest','range_rotation'}

def evaluate_price(key,f,inputs,deps):
    if key in PRICE_CONTEXT:return simple_context(key,f,inputs)
    if key=='liquidity_pools':return pool_lifecycle(f,inputs)
    if key in {'mss','pool_rejection','sweep_reversal'}:return sweep_models(f,inputs,setup=key!='mss',label='Pool rejection' if key=='pool_rejection' else 'Sweep reversal')
    if key in {'pool_breakout','compression_retest','break_confirmation'}:return breakout_models(f,inputs,kind={'pool_breakout':'pools','compression_retest':'compression','break_confirmation':'rolling'}[key],micro=key=='break_confirmation')
    if key in {'trend_ob','trend_fvg','smc_zone_retest'}:return zone_models(f,inputs,deps,kind={'trend_ob':'OB','trend_fvg':'FVG'}.get(key),trend=key!='smc_zone_retest')
    if key=='breaker':return breaker(f,inputs)
    if key=='mitigation_block':return mitigation(f,inputs)
    if key=='inducement':return inducement(f,inputs)
    if key=='liquidity_void':return void_return(f)
    if key.startswith('previous_day_'):
        pools=prior_day_pools(f,inputs)
        if key=='previous_day_sweep':return sweep_models(f,inputs,pools=pools,label='Previous D1 sweep')
        return breakout_models(f,inputs,pools=[dict(p,side='BUY' if p['side']=='SELL' else 'SELL') for p in pools],kind='previous_day')
    if key in {'previous_body','previous_body_retest'}:return previous_body(f,inputs,retest_mode=key.endswith('retest'))
    if key=='range_rotation':return range_rotation(f)
    raise ValueError('Unknown document price method')
