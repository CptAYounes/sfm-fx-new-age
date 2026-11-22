"""Bounded, price-only Wyckoff event and phase hypotheses with frozen ranges."""
from sfm_fx_new_age.contracts.analytics import digest
from .public_sequence_features import displacement,acceptance,emit_setup,stages,true_ranges
from .public_price_models import tested_range


def wyckoff_events(f):
    if 'document_wyckoff_events' in f.cache:return f.cache['document_wyckoff_events']
    events=[];active=None
    for i in range(20,f.n):
        if active is None:
            bounds=tested_range(f,i)
            if bounds is None:continue
            lo,hi=bounds;active=dict(id=digest(f.bars[i-20:i]),low=lo,high=hi,start=i,phase='B',side=None,sweep=None,test=None,breakout=None,retest=None)
            # A is only a retrospective price hypothesis and becomes available NOW.
            before=i-20;tr=true_ranges(f)
            if before>=5:
                extreme=max(range(before,i),key=lambda j:tr[j]);direction='BUY' if f.c[extreme]<f.o[extreme] else 'SELL'
                response=next((j for j in range(extreme+1,i) if (f.c[j]>f.h[extreme] if direction=='BUY' else f.c[j]<f.l[extreme])),None)
                if response is not None:events.append(dict(active,index=i,kind='A_POSSIBLE_STOPPING_ACTION',side=direction,climax=extreme,response=response))
            events.append(dict(active,index=i,kind='B_TESTED_RANGE'));continue
        a=active;lo,hi=a['low'],a['high'];tol=(hi-lo)*.1
        if i-a['start']>80:events.append(dict(a,index=i,kind='EXPIRED'));active=None;continue
        if a['sweep'] is not None:
            s=a['sweep'];side=a['side']
            if f.c[i]<f.l[s] if side=='BUY' else f.c[i]>f.h[s]:events.append(dict(a,index=i,kind='INVALIDATED'));active=None;continue
        if a['sweep'] is None:
            side='BUY' if f.l[i]<lo<f.c[i]<hi else 'SELL' if f.h[i]>hi>f.c[i]>lo else None
            if side:
                a.update(sweep=i,side=side,phase='C');events.append(dict(a,index=i,kind='SPRING' if side=='BUY' else 'UTAD'));continue
        elif a['test'] is None and i<=a['sweep']+10:
            side=a['side'];s=a['sweep']
            if (f.l[i]>=f.l[s] and f.l[i]<=lo+tol and f.c[i]>lo if side=='BUY' else f.h[i]<=f.h[s] and f.h[i]>=hi-tol and f.c[i]<hi):
                a['test']=i;events.append(dict(a,index=i,kind='SECONDARY_TEST'));continue
        if a['test'] is not None and i>a['test'] and a.get('response') is None:
            t=a['test'];side=a['side']
            if (f.c[i]>f.h[t] and f.c[i]>f.o[i] if side=='BUY' else f.c[i]<f.l[t] and f.c[i]<f.o[i]):
                a['response']=i;events.append(dict(a,index=i,kind='TEST_RESPONSE'))
        if a['test'] is not None and a['breakout'] is None:
            move=displacement(f).get(i);side=a['side']
            if move and move['side']==side and (f.c[i]>hi if side=='BUY' else f.c[i]<lo):
                a.update(breakout=i,phase='D');events.append(dict(a,index=i,kind='SOS' if side=='BUY' else 'SOW'))
        if a['breakout'] is not None and a['retest'] is None:
            result=acceptance(f,a['breakout'],lo,hi,a['side'])
            if result and result[1]==i:
                a['retest']=i;events.append(dict(a,index=i,kind='HELD_RANGE_RETEST',accepted=result[0]))
        if a['retest'] is not None and i>a['retest'] and a['phase']!='E':
            if f.c[i]>f.h[a['breakout']] if a['side']=='BUY' else f.c[i]<f.l[a['breakout']]:
                a['phase']='E';events.append(dict(a,index=i,kind='E_CONTINUATION'))
    f.cache['document_wyckoff_events']=events
    return events


def evaluate_wyckoff(key,f,inputs,deps):
    from .public_algorithms import blank,marker,zone
    out=blank();events=wyckoff_events(f)
    if key=='wyckoff_phase':
        for e in events:
            side=e['side'] or 'NEUTRAL';marker(out,f,e['index'],'Wyckoff '+e['phase']+' · '+e['kind']+' hypothesis',side,roots=(e['id'],))
        latest=events[-1] if events else None
        if latest and latest['kind'] not in {'INVALIDATED','EXPIRED'}:zone(out,f,latest['index'],latest['low'],latest['high'],'Price-only phase '+latest['phase']+' range',latest['side'] or 'NEUTRAL',roots=(latest['id'],))
        out['metrics']=dict(phase=latest['phase'] if latest else 'UNKNOWN',volume_confirmed=False,alternative_interpretation='RANGE_OR_TREND_CONTINUATION_REMAINS_POSSIBLE')
    elif key in {'wyckoff_spring_test','wyckoff_utad_test'}:
        side='BUY' if key=='wyckoff_spring_test' else 'SELL'
        for e in events:
            if e['kind']!='TEST_RESPONSE' or e['side']!=side:continue
            i,s,t=e['index'],e['sweep'],e['test'];anchor=f.l[s] if side=='BUY' else f.h[s]
            emit_setup(out,f,i,'Spring / test response' if side=='BUY' else 'UTAD / test response',side,f.l[t],f.h[t],[('TESTED_RANGE',e['start']),('SPRING' if side=='BUY' else 'UTAD',s),('SECONDARY_TEST',t),('INDEPENDENT_RESPONSE',i)],roots=(e['id'],),anchor=anchor,target=e['high'] if side=='BUY' else e['low'])
    elif key=='wyckoff_break_retest':
        for e in events:
            if e['kind']!='HELD_RANGE_RETEST':continue
            side=e['side'];level=e['high'] if side=='BUY' else e['low']
            emit_setup(out,f,e['index'],'SOS / SOW held retest',side,level,level,[('PHASE_C_EVENT',e['sweep']),('SECONDARY_TEST',e['test']),('SOS' if side=='BUY' else 'SOW',e['breakout']),('ACCEPTED_CLOSE',e['accepted']),('HELD_RANGE_RETEST',e['index'])],roots=(e['id'],),anchor=e['low'] if side=='BUY' else e['high'])
    else:raise ValueError('Unknown Wyckoff profile')
    out['metrics'].update(volume_confirmed=False,price_only_hypothesis=True)
    return out
