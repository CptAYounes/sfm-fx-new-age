"""Pure source-bound public-method → Limit-research trigger compositions.

No database, Qt, broker transport, account sizing or command authority.
Geometry/context uses a *prior* snapshot, not a same-bar hindsight level.
"""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.strategy_signals import POLICIES
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable

PIVOT_EVENTS={'elliott_impulse','elliott_abc','abcd','gartley','bat','butterfly'}


def stamp(value): return value.isoformat().replace('+00:00','Z')


def recovery(rows):
    if len(rows)<2:return None
    previous,last=rows[-2:];o,c=D(previous['open']),D(previous['close']);closed=D(last['close'])
    return 'BUY' if c<o<closed else 'SELL' if c>o>closed else None


def prior_output(key,inputs,deps):
    """Re-evaluate a level study using only information preceding trigger open."""
    from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
    from sfm_fx_new_age.tabs.tab3.public_features import Features
    from sfm_fx_new_age.services.scanner import confirmed_swings
    frame=inputs['frame'];own=inputs['bars'][frame]
    if len(own)<2:return None
    cutoff=instant(own[-1]['open_time'])
    mapping={fr:[b for b in bs if instant(b['available_at'])<=cutoff and instant(b['close_time'])<=cutoff]
             for fr,bs in inputs['bars'].items()}
    prefix=mapping.get(frame,())[-2048:]
    if not prefix:return None
    previous=dict(inputs,bars=mapping,_evaluation_at=stamp(cutoff))
    # Pure analytical dependencies are filtered/rebuilt at the earlier cutoff;
    # future pivot confirmations are never handed to a prior-frame study.
    pd={key:dict(v) for key,v in deps.items()}
    pd['SWING_MAP']={'state':'READY','output':{fr:confirmed_swings(bs) for fr,bs in mapping.items()}}
    if 'SMC_STRUCTURE' in pd:
        pd['SMC_STRUCTURE']=dict(pd['SMC_STRUCTURE'],output={fr:[e for e in es if instant(e['available_at'])<=cutoff]
            for fr,es in (pd['SMC_STRUCTURE'].get('output') or {}).items()})
    try:return evaluate(key,Features(prefix,pd['SWING_MAP']['output'].get(frame,())),previous,pd)
    except ProjectionInputUnavailable:return None


def level_response(out,rows):
    if not out or not rows:return None
    b=rows[-1];opened=instant(b['open_time']);o,h,l,c=(D(b[k]) for k in ('open','high','low','close'))
    hits=[]
    for z in out.get('zones',()):
        if z.get('state') not in {'CONFIRMED','TOUCHED'} or instant(z['available_at'])>opened:continue
        lo,hi=D(z['low']),D(z['high']);permitted=z.get('side','NEUTRAL')
        if l<=hi and h>=lo:
            if c>hi and c>o and permitted in {'BUY','NEUTRAL'}:
                hits.append(dict(side='BUY',entry=hi,anchor=min(lo,l),root_ids=list(z['root_ids']),context=z))
            elif c<lo and c<o and permitted in {'SELL','NEUTRAL'}:
                hits.append(dict(side='SELL',entry=lo,anchor=max(hi,h),root_ids=list(z['root_ids']),context=z))
    # Conflicting directional contexts are not resolved by arbitrary list order.
    if len({x['side'] for x in hits})>1:return None
    return min(hits,key=lambda x:(abs(x['entry']-c),digest(x['root_ids']))) if hits else None


def marker_trigger(key,projection,inputs):
    rows=inputs['bars'][inputs['frame']];last=rows[-1];events=[]
    for m in projection['markers']:
        if m['side'] not in {'BUY','SELL'}:continue
        if m.get('source_timeframe',inputs['frame'])!=inputs['frame']:continue
        # A recently received historical envelope must not resurrect an old
        # price event. Delayed *pivot confirmation* is explicitly different.
        event_current=instant(m['time'])==instant(last['close_time'])
        if key in PIVOT_EVENTS:event_current=instant(m['available_at'])==instant(last['available_at'])
        if event_current:events.append(m)
    if not events or len({m['side'] for m in events})>1:return None
    m=max(events,key=lambda x:(instant(x['available_at']),digest(x)))
    trigger=dict(side=m['side'],entry=(D(last['open'])+D(last['close']))/2,
        anchor=D(m['invalidation']) if m.get('invalidation') else
            (min(D(b['low']) for b in rows[-2:]) if m['side']=='BUY' else max(D(b['high']) for b in rows[-2:])),
        root_ids=list(m['root_ids']),event=m,available_at=m['available_at'],time=m['time'])
    if key in PIVOT_EVENTS:
        # The confirmed pattern extreme is observable and may lie outside the
        # two confirmation candles. Preserve it in the invalidation envelope.
        p=D(m['price']);trigger['anchor']=min(trigger['anchor'],p) if m['side']=='BUY' else max(trigger['anchor'],p)
    return trigger


def extract_trigger(key,projection,inputs,deps):
    policy=POLICIES[key];rows=inputs['bars'][inputs['frame']]
    if not rows:return None
    b=rows[-1];o,h,l,c=(D(b[k]) for k in ('open','high','low','close'))
    kind=policy.trigger;target=None
    if kind=='LATEST_DIRECTIONAL_EVENT':return marker_trigger(key,projection,inputs)
    if kind=='NATIVE_OB_ZONE':
        zones=(deps.get('ORDER_BLOCK',{}).get('output') or {}).get('frames',{}).get(inputs['frame'],())
        matches=[z for z in zones if z['state'] in {'CONFIRMED','TOUCHED'} and
                 instant(z['confirmation_time'])==instant(b['available_at'])]
        if not matches or len({z['side'] for z in matches})>1:return None
        z=matches[-1];side=z['side'];lo,hi=sorted((D(z['proximal']),D(z['distal'])))
        return dict(side=side,entry=hi if side=='BUY' else lo,anchor=lo if side=='BUY' else hi,
                    root_ids=[z['level_id']],context=z,available_at=z['confirmation_time'],time=b['close_time'])
    if kind in {'PRIOR_LEVEL_RESPONSE','WAVE_RESPONSE'}:
        hit=level_response(prior_output(key,inputs,deps),rows)
        if hit:hit.update(available_at=b['available_at'],time=b['close_time'])
        return hit
    if kind=='LIVE_BODY':
        m=next((m for m in reversed(projection['markers']) if m['side'] in {'BUY','SELL'}),None)
        if not m:return None
        previous=next((r for r in rows if r['open_time']==m.get('previous_body_time')),None)
        if not previous:return None
        return dict(side=m['side'],entry=D(previous['open']),anchor=D(previous['low'] if m['side']=='BUY' else previous['high']),
                    root_ids=list(m['root_ids']),event=m,available_at=m['available_at'],time=m['time'],provisional=True)
    if kind=='TRAIL_CROSS':
        prior=prior_output(key,inputs,deps)
        if not prior:return None
        hits=[];previous=D(rows[-2]['close'])
        for series in prior['series']:
            points=series['points']
            if not points:continue
            boundary=D(points[-1]['price'])
            if instant(points[-1]['available_at'])>instant(b['open_time']):continue
            if 'short' in series['label'].lower() and previous<=boundary<c:hits.append('BUY')
            if 'long' in series['label'].lower() and previous>=boundary>c:hits.append('SELL')
        if len(set(hits))!=1:return None
        side=hits[0]
    else:
        side=recovery(rows)
        if side is None:return None
        metrics=projection['metrics']
        if kind=='REGIME_RECOVERY':
            if metrics.get('regime')!='TREND':return None
        elif kind=='CALENDAR_RECOVERY':
            if metrics.get('nearby_published_events') or not metrics.get('complete_feed_interval_only'):return None
            if not metrics.get('source_evidence_hash'):return None
        elif kind=='FLOW_RECOVERY':
            zones=[z for z in projection['zones'] if z['side']==side]
            if not zones:return None
            known=max([b['available_at']]+[z['available_at'] for z in zones],key=instant)
            return dict(side=side,entry=(o+c)/2,anchor=min(D(r['low']) for r in rows[-2:]) if side=='BUY' else max(D(r['high']) for r in rows[-2:]),
                root_ids=[digest(r) for r in rows[-2:]]+[root for z in zones for root in z['root_ids']],
                available_at=known,time=b['close_time'],context=zones[-1])
        elif kind in {'COT_RECOVERY','PNF_RESPONSE'}:
            # Context values must already have been available before the
            # triggering candle. Never backfill a release into earlier bars.
            prior=prior_output(key,inputs,deps)
            if not prior:return None
            zones=[z for z in prior['zones'] if z['side']==side and instant(z['available_at'])<=instant(b['open_time'])]
            if not zones:return None
            if kind=='PNF_RESPONSE':
                objectives=[D(z['low']) for z in zones if D(z['low'])>h] if side=='BUY' else [D(z['high']) for z in zones if D(z['high'])<l]
                if not objectives:return None
                target=min(objectives) if side=='BUY' else max(objectives)
        else:raise ValueError('Unimplemented declared signal policy: '+kind)
    return dict(side=side,entry=(o+c)/2,anchor=min(D(r['low']) for r in rows[-2:]) if side=='BUY' else max(D(r['high']) for r in rows[-2:]),
                root_ids=[digest(r) for r in rows[-2:]]+[digest(projection['metrics'])],
                available_at=b['available_at'],time=b['close_time'],**({'target':target} if kind=='PNF_RESPONSE' else {}))


def build_observation(key,projection,inputs,deps):
    """One immutable observation per method/frame/projection; no sizing/Issue."""
    policy=POLICIES[key];frame=inputs['frame'];rows=inputs['bars'][frame]
    base=dict(strategy_id=key,name=projection['name'],recipe_id=projection['recipe_id'],recipe_version=projection['version'],
        policy_id=policy.policy_id,policy_hash=policy.profile_hash,policy=policy.description,
        scope_id=projection['scope_id'],source_epoch=projection['source_epoch'],symbol=projection['symbol'],timeframe=frame,
        origin=projection['origin'],profile_hash=projection['profile_hash'],projection_fingerprint=projection['fingerprint'],
        projection_classification=projection['classification'],source_metrics=deepcopy(projection['metrics']),
        available_at=projection['available_at'],opportunity_id=None,setup_id=None,trigger=None,side=None,entry=None,stop=None,target=None,
        expires_at=None,state=projection['state'],reason=projection['reason'],classification='UNCALIBRATED_SINGLE_METHOD_LIMIT_RESEARCH',revision=1)
    if projection['state'] not in {'READY','NO_SETUP'}:return base
    spec=inputs.get('spec') or {};tick=D(spec.get('tick_size','0'))
    if tick<=0:return dict(base,state='DATA_UNAVAILABLE',reason='Native TickSize required; no guessed grid')
    trigger=extract_trigger(key,projection,inputs,deps)
    if not trigger:return dict(base,state='NO_SETUP',reason='Method evaluated; no current signal-policy trigger. Context/old markers alone are not entry signals.')
    side=trigger['side'];buy=side=='BUY'
    entry=(D(trigger['entry'])/tick).to_integral_value(rounding=ROUND_FLOOR if buy else ROUND_CEILING)*tick
    anchor=D(trigger['anchor'])
    stop=(anchor/tick).to_integral_value(rounding=ROUND_FLOOR if buy else ROUND_CEILING)*tick+(-tick if buy else tick)
    if min(entry,stop)<=0 or (stop>=entry if buy else stop<=entry):return dict(base,state='NO_SETUP',reason='Trigger has no positive directional invalidation geometry')
    known=trigger['available_at']
    # Backfill receipt is not a new price event. For pivot models the final
    # confirmation candle, not the older pivot label, owns the event clock.
    event_clock=instant(known) if trigger.get('provisional') else min(instant(known),instant(rows[-1]['close_time']))
    expiry=event_clock+timedelta(seconds=14400)
    if projection.get('valid_until'):expiry=min(expiry,instant(projection['valid_until']))
    if expiry<=instant(known):return dict(base,state='EXPIRED',reason='Original trigger/confirmation lifetime elapsed before this late observation; backfill does not renew it')
    candidates=[]
    for source_frame in dict.fromkeys((frame,'D1','W1')):
        for s in (deps.get('SWING_MAP',{}).get('output') or {}).get(source_frame,()):
            price=D(s['price'])
            if s['kind']!=('HIGH' if buy else 'LOW') or instant(s['available_at'])>instant(known):continue
            if (price<=entry if buy else price>=entry):continue
            later=[b for bs in (rows,inputs['bars'].get(source_frame,())) for b in bs if instant(b['open_time'])>=instant(s['available_at'])]
            if any(D(b['high'])>=price if buy else D(b['low'])<=price for b in later):continue
            candidates.append(price)
    target=trigger.get('target') or (min(candidates) if buy and candidates else max(candidates) if candidates else None)
    if target is not None:target=(D(target)/tick).to_integral_value(rounding=ROUND_FLOOR if buy else ROUND_CEILING)*tick
    # Keep same-episode correlations explicit; multiple interpretations are not
    # independent evidence and cannot silently bypass the setup reservation.
    setup=digest([base['scope_id'],base['source_epoch'],base['symbol'],frame,side,str(entry),str(stop),trigger['time']])
    identity='strategy:'+digest([setup,key,projection['fingerprint'],policy.profile_hash])
    trigger=deepcopy(trigger);trigger.update(entry=str(entry),anchor=str(anchor))
    return dict(base,state='SIGNAL',reason='Research signal generated; current eligibility and explicit units are checked separately',
        opportunity_id=identity,setup_id=setup,side=side,entry=str(entry),stop=str(stop),target=str(target) if target else None,
        trigger=trigger,available_at=known,expires_at=stamp(expiry))
