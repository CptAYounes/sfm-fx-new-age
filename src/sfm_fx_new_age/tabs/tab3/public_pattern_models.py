"""Causal competing Elliott hypotheses and independently confirmed harmonic PRZs."""
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from .public_sequence_features import alternating_at,structure,held,emit_setup,zone_models,higher_bias


def hypotheses(f):
    if 'document_elliott_counts' in f.cache:return f.cache['document_elliott_counts']
    from .public_algorithms import impulse_matches,abc_matches
    out=[];used=set()
    times=sorted({s['available_at'] for s in f.swings},key=instant)
    for at in times:
        points=alternating_at(f,at)[-20:]
        known=f.first_close_at_or_after(at)
        if known is None:continue
        for size in (4,5,6):
            if len(points)<size:continue
            p=points[-size:];prices=[float(s['price']) for s in p];sign=1 if prices[1]>prices[0] else -1;q=[v*sign for v in prices]
            label='ABC' if size==4 and abc_matches(p) else 'IMPULSE' if size==6 and impulse_matches(p) else 'DEVELOPING_WAVE5' if size==5 and q[0]<q[2]<q[1]<q[4]<q[3] else None
            if not label:continue
            identity=digest([label,[s['id'] for s in p]])
            if identity in used:continue
            used.add(identity);side='BUY' if (sign>0 if size==5 else p[-1]['kind']=='LOW') else 'SELL'
            invalidation=prices[1] if size==5 else prices[-1]
            terminal=next((j for j in range(known+1,f.n) if (f.c[j]<invalidation if side=='BUY' else f.c[j]>invalidation)),None)
            length=abs(prices[1]-prices[0]);direction=1 if side=='BUY' else -1
            base=prices[-1];targets=[base+direction*length*r for r in (.618,1,1.618)]
            out.append(dict(id=identity,label=label,index=known,available_at=at,points=p,side=side,invalidation=invalidation,
                            invalidated_at=terminal,targets=[t for t in targets if t>0]))
    f.cache['document_elliott_counts']=out
    return out


def harmonic_hypotheses(f):
    if 'document_harmonic_prz' in f.cache:return f.cache['document_harmonic_prz']
    from .public_algorithms import harmonic_matches
    out=[];used=set()
    for at in sorted({s['available_at'] for s in f.swings},key=instant):
        points=alternating_at(f,at)[-20:]
        index=f.first_close_at_or_after(at)
        if index is None:continue
        for n in (4,5):
            if len(points)<n:continue
            p=points[-n:];label=harmonic_matches(p)
            if not label:continue
            identity=digest([label,[s['id'] for s in p]])
            if identity in used:continue
            used.add(identity);v=[float(s['price']) for s in p];a,b,c,d=v[-4:];ab=abs(b-a);sign=1 if b>a else -1
            alternatives=(1.27,1.618) if label in {'Bat','Butterfly'} else (1.0,)
            abcd_ratio=min(alternatives,key=lambda ratio:abs(d-(c+sign*ab*ratio)))
            expected=c+sign*ab*abcd_ratio;bands=[(expected-.05*ab*abcd_ratio,expected+.05*ab*abcd_ratio)]
            if n==5:
                x,a,b,c,d=v;xa=abs(a-x);xa_sign=1 if a>x else -1
                ratio={'Gartley':.786,'Bat':.886,'Butterfly':1.27}[label];target=a-xa_sign*ratio*xa
                bands.append((target-.05*ratio*xa,target+.05*ratio*xa))
                bc=abs(c-b);rlo,rhi=(1.27,1.618) if label=='Gartley' else (1.618,2.618)
                ends=(c-xa_sign*bc*rlo,c-xa_sign*bc*rhi);bands.append(tuple(sorted(ends)))
            low=max(t[0] for t in bands);high=min(t[1] for t in bands)
            if not 0<low<=d<=high:continue
            side='BUY' if p[-1]['kind']=='LOW' else 'SELL'
            # Break of the PRZ far edge or X for non-extension patterns is invalidation.
            anchor=max(low,v[0]) if side=='BUY' and label in {'Gartley','Bat'} else min(high,v[0]) if side=='SELL' and label in {'Gartley','Bat'} else low if side=='BUY' else high
            out.append(dict(id=identity,label=label,index=index,available_at=at,low=low,high=high,side=side,anchor=anchor,abcd_ratio=abcd_ratio,points=p))
    f.cache['document_harmonic_prz']=out
    return out


def evaluate_pattern(key,f,inputs,deps):
    from .public_algorithms import blank,marker,zone
    out=blank()
    if key=='elliott_alternatives':
        counts=hypotheses(f)
        for h in counts[-8:]:
            i=h['index'];known=h['available_at'];roots=tuple(s['id'] for s in h['points']);terminal=h['invalidated_at'];state='INVALIDATED' if terminal is not None else 'CONFIRMED'
            zone(out,f,i,h['invalidation'],h['invalidation'],h['label']+' invalidation',h['side'],available=f.bars[terminal]['available_at'] if terminal is not None else known,state=state,roots=roots)
            if terminal is None:
                for ratio,t in zip((.618,1,1.618),h['targets']):zone(out,f,i,t,t,h['label']+' measured Fib '+str(ratio),h['side'],available=known,roots=roots)
            marker(out,f,terminal if terminal is not None else i,h['label']+(' invalidated' if terminal is not None else ' alternative hypothesis'),h['side'],available=known,roots=roots)
        out['metrics']=dict(competing_counts=[dict(id=h['id'],kind=h['label'],state='INVALIDATED' if h['invalidated_at'] is not None else 'CURRENT',available_at=h['available_at']) for h in counts[-16:]],recursive_all_degrees=False,confidence='UNCALIBRATED_RULE_HYPOTHESIS')
    elif key=='harmonic_prz':
        breaks=structure(f)
        for h in harmonic_hypotheses(f):
            i,side=h['index'],h['side'];visit=None
            for j in range(i+1,min(f.n,i+25)):
                if f.c[j]<h['anchor'] if side=='BUY' else f.c[j]>h['anchor']:break
                if held(f,j,h['low'],h['high'],side):visit=j;break
            if visit is None:continue
            control=next((e for e in breaks if visit<e[0]<=visit+8 and e[2]==side and instant(e[1]['available_at'])<=instant(f.bars[visit]['open_time'])),None)
            if not control:continue
            j=control[0]
            if any((f.c[k]<h['anchor'] if side=='BUY' else f.c[k]>h['anchor']) for k in range(visit+1,j+1)):continue
            emit_setup(out,f,j,h['label']+' PRZ independent confirmation',side,h['low'],h['high'],[('PIVOTS_AND_PRZ_KNOWN',i),('LATER_ZONE_RESPONSE',visit),('INDEPENDENT_STRUCTURE_BREAK',j)],roots=tuple(p['id'] for p in h['points'])+(control[1]['id'],),anchor=h['anchor'])
        out['metrics']['confirmed_prz_hypotheses']=len(harmonic_hypotheses(f))
    elif key=='macro_elliott':
        if len(inputs['bars'].get('W1',()))<13 or not inputs['bars'].get('D1'):raise ProjectionInputUnavailable('13 completed W1 bars and D1 structure required')
        linked=zone_models(f,inputs,deps);counts=hypotheses(f);accepted=[]
        for row in linked['markers']:
            start=row['stages'][0]['time'];at=row['time'];side=row['side']
            waves=[h for h in counts if instant(h['available_at'])<=instant(start) and h['side']==side and (h['invalidated_at'] is None or instant(f.bars[h['invalidated_at']]['close_time'])>instant(at))]
            weekly=[b for b in inputs['bars']['W1'] if instant(b['available_at'])<=instant(start) and instant(b['close_time'])<=instant(start)][-13:]
            d1=higher_bias(dict(inputs,frame='H4'),deps,start,'H4')
            if not waves or len(weekly)<13 or d1!=side:continue
            lo=min(float(b['low']) for b in weekly);hi=max(float(b['high']) for b in weekly);price=float(row['price']);width=hi-lo
            if width<=0 or not (price<=lo+.2*width if side=='BUY' else price>=hi-.2*width):continue
            row=dict(row,label='W1 extreme / Elliott / D1 linked retest',root_ids=row['root_ids']+[waves[-1]['id'],digest(weekly)],macro_source_timeframe='W1',cot_required=False);accepted.append(row)
        out['markers']=accepted
        out['metrics']=dict(linked_structural_setups=len(accepted),standalone_wave_entry=False,cot_optional=True)
    else:raise ValueError('Unknown document pattern profile')
    return out
