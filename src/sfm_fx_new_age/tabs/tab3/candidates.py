"""Explicit research-only OB→MTF candidate composition. Never a calibrated model.
QG meanings come from supplied ATR scanner v1.2 §10; unsupported predicates
stay failed/unknown. Correlated price interpretations are never independent votes.
"""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D,ROUND_FLOOR,ROUND_CEILING
from sfm_fx_new_age.contracts.analytics import Evidence,Lineage,MarketCandidate,digest
from sfm_fx_new_age.contracts.domain import Origin,instant,record
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.services.geometry import atr_variants,confidence,qualify
from .order_blocks import METHOD

CANDIDATE_RECIPE='sfm.ob.mtf.research.v1'
CANDIDATE_METHOD='SFM_OB_MTF_QUALIFICATION_RESEARCH_V1'


def settings(inputs):
    values={'expiry_seconds':14400,'max_spread_pips':'3','min_reward_r':'1','evidence_reliability':'0.75'}
    for row in inputs['parameters']:
        if row['key'].startswith('ob_candidate.'):values[row['key'].removeprefix('ob_candidate.')]=row['value']
    return values


def order_block_evidence(level,*,confirmation,expiry_seconds,reliability):
    """Same displacement/root, regardless of how many interpretations describe it."""
    line=Lineage(**dict(level['lineage']))
    expires=(instant(confirmation)+timedelta(seconds=expiry_seconds)).isoformat().replace('+00:00','Z')
    cluster=digest([line.source_scope,line.source_epoch,line.symbol,confirmation,'PRICE_STRUCTURE'])
    return Evidence(digest([level['level_id'],level['revision'],'OB_EVIDENCE']),level['level_id'],level['root_ids'][-1],
        cluster,level['root_ids'][-1],'PRICE_STRUCTURE',level['side'],D(level['low']),D(level['high']),
        D('1'),D(reliability),expires,line,confirmed=level['state'] in {'CONFIRMED','TOUCHED'})


def compose_candidates(inputs,deps):
    p=settings(inputs);now=inputs['_evaluation_at'];spec=inputs['spec'];atr=inputs.get('atr')
    if not spec or atr is None or D(atr)<=0:return ()
    bars=inputs['bars'];levels=[r for r in inputs['analytical_objects']['level'] if r['kind']=='ORDER_BLOCK'
        and r['lineage']['method_version']==METHOD and r['lineage']['profile_hash']==inputs['profile_hash']]
    evidence=[]
    for raw in inputs['analytical_objects']['evidence']:
        line=Lineage(**dict(raw['lineage']));evidence.append(Evidence(**dict(raw,lineage=line)))
    by_id={e.evidence_id:e for e in evidence};quote=inputs.get('quote');pip,tick=D(spec['pip_size']),D(spec['tick_size'])
    previous={r['candidate_id']:r for r in inputs.get('prior_candidates',()) if r['recipe_id']==CANDIDATE_RECIPE}
    swings=deps['SWING_MAP']['output'];structures=deps['SMC_STRUCTURE']['output'];zones=deps['ORDER_BLOCK']['output']['frames']
    bounds=tuple(D(next((r['value'] for r in inputs['parameters'] if r['key']==f'geometry.band_{i}'),default))
        for i,default in enumerate(('0.375','0.750','1.250','1.750','2.250')))
    results=[]
    for zone in levels:
        if zone['lineage']['timeframe']!='H4' or zone['state'] not in {'CONFIRMED','TOUCHED'}:continue
        z=next((v for v in zones.get('H4',()) if v['level_id']==zone['level_id']),None)
        if not z:continue
        confirmation=z['confirmation_time'];expiry=(instant(confirmation)+timedelta(seconds=p['expiry_seconds'])).isoformat().replace('+00:00','Z')
        if instant(expiry)<=instant(now):continue
        side=zone['side'];low,high=D(zone['low']),D(zone['high'])
        entry=(high/tick).to_integral_value(rounding=ROUND_FLOOR)*tick if side=='BUY' else (low/tick).to_integral_value(rounding=ROUND_CEILING)*tick
        anchor=low if side=='BUY' else high
        if side=='BUY' and anchor>=entry or side=='SELL' and anchor<=entry:continue
        valid_evidence={digest([l['level_id'],l['revision'],'OB_EVIDENCE']) for l in levels if l['state'] in {'CONFIRMED','TOUCHED'}}
        relevant=[e for e in evidence if e.evidence_id in valid_evidence and e.confirmed and instant(e.expires_at)>instant(now)
                  and e.lineage.profile_hash==inputs['profile_hash']]
        own=[e for e in relevant if e.level_id==zone['level_id'] and e.confirmed]
        if not own:continue
        # Target is a traceable opposite pivot, never a made-up fixed-R price.
        target_kind='HIGH' if side=='BUY' else 'LOW';targets=[]
        for frame in ('D1','H4'):
            for s in swings.get(frame,()):
                price=D(s['price'])
                if s['kind']!=target_kind or (price<=entry if side=='BUY' else price>=entry):continue
                later=[b for b in bars.get(frame,()) if instant(b['open_time'])>instant(s['available_at'])]
                if any(D(b['high'])>=price if side=='BUY' else D(b['low'])<=price for b in later):continue
                targets.append((abs(price-entry),price,s['id']))
        target=sorted(targets)[0][1] if targets else None
        setup=digest([inputs['scope_id'],inputs['authority']['source_epoch'],CANDIDATE_RECIPE,zone['level_id']])
        variants=atr_variants(setup_id=setup,side=side,entry=entry,anchor=anchor,atr=D(atr),pip=pip,tick=tick,target=target,bounds=bounds)
        available=max([zone['lineage']['available_at']]+[e.lineage.available_at for e in relevant],key=instant)
        line=Lineage(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],'H4',available,
            Origin(inputs['authority']['origin']),CANDIDATE_METHOD,inputs['profile_hash'])
        score=confidence({'zone_id':zone['level_id'],'symbol':inputs['symbol'],'side':side,'timeframe':'H4','low':str(low),'high':str(high)},
            tuple(relevant),lineage=line,as_of=now,pip=pip)
        fresh=False;pending=False;spread=None
        if quote:
            age=(instant(now)-instant(quote['available_at'])).total_seconds()
            fresh=0<=age<=inputs['quote_max_age_seconds'] and quote['source_epoch']==line.source_epoch and quote['scope_id']==line.source_scope
            spread=(D(quote['ask'])-D(quote['bid']))/pip
            pending=entry<D(quote['ask']) if side=='BUY' else entry>D(quote['bid'])
        d1=structures.get('D1',());campaign=bool(d1 and d1[-1]['side']==side)
        # Gross geometry alone cannot satisfy the source's after-cost reward gate.
        # Spread is observed; commissions/swaps are excluded, not fabricated.
        spread_cost=spread*pip if fresh and spread is not None and spread>=0 else None
        reward_after_spread={v.variant_id:(abs(target-entry)-spread_cost)/(v.distance_pips*pip+spread_cost)
            if target is not None and spread_cost is not None else None for v in variants}
        gates={f'QG{i:02d}':True for i in range(1,15)}
        gates.update(QG01=bool(bars.get('W1') and bars.get('D1') and bars.get('H4') and campaign),
            QG02=True,QG03=pending,QG04=D(atr)>0,QG05=all(v.distance_pips>0 for v in variants),
            QG06=bool(fresh and spread is not None and 0<=spread<=D(p['max_spread_pips']) and not inputs.get('stream_gap')),
            QG07=bool(target and any(rr is not None and rr>=D(p['min_reward_r']) for rr in reward_after_spread.values())),
            QG08=zone['state'] in {'CONFIRMED','TOUCHED'},QG09=instant(expiry)>instant(now) and pending,
            QG10=True, # RESEARCH_UNCALIBRATED, never a production/OOS-accepted label.
            QG11=True, # Profile does NOT assert account-level risk permission.
            QG12=bool(own),QG13=score['independent_support_clusters']>=3 and len(score['support_timeframes'])>=2 and score['entry_local_support_clusters']>=2,
            QG14=not score['blocked_confidence_gate'])
        qualified=qualify(gates,zone_confidence=D(str(score['score'])),geometry_points=D('20'),
            target_points=D('20') if gates['QG07'] else None,cost_points=D('10') if gates['QG06'] else None,profile_id=CANDIDATE_METHOD)
        adjusted=[]
        for v in variants:
            blockers=list(v.blockers)
            rr=reward_after_spread[v.variant_id]
            if rr is None:blockers.append('AFTER_SPREAD_REWARD_UNKNOWN')
            elif rr<D(p['min_reward_r']):blockers.append('REWARD_BELOW_RESEARCH_PROFILE_AFTER_SPREAD')
            adjusted.append(replace(v,blockers=tuple(blockers)))
        identity=digest([setup,inputs['profile_hash']]);old=previous.get(identity)
        candidate=MarketCandidate(identity,setup,(old['revision']+1 if old else 1),CANDIDATE_RECIPE,1,zone['level_id'],side,entry,anchor,target,
            tuple(e.evidence_id for e in relevant),tuple(adjusted),line,expiry,D(str(score['score'])),
            D(qualified['quality_score']) if qualified['quality_score'] is not None else None,
            tuple(sorted(set(qualified['blockers']+score['blocker_codes']))),gates=tuple(sorted(gates.items())))
        if old:
            body=record(candidate);a={k:v for k,v in body.items() if k not in {'revision','lineage'}};b={k:v for k,v in old.items() if k not in {'revision','lineage'}}
            if a==b:
                candidate=replace(candidate,revision=old['revision'],lineage=Lineage(**dict(old['lineage'])))
            else:candidate=replace(candidate,lineage=replace(line,available_at=now))
        results.append(candidate)
    return tuple(results[-64:])
