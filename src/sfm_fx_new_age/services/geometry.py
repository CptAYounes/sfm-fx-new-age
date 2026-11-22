"""Source-attested ATR geometry and qualification. No calibration or funding is invented."""
from __future__ import annotations
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from dataclasses import dataclass
from typing import Any

from sfm_fx_new_age.contracts.analytics import Variant,Evidence,Lineage,digest
from sfm_fx_new_age.contracts.domain import decimal,record,instant
from .zone_confidence_reference import score_zone_confidence

BAND_BOUNDS=tuple(map(Decimal,('0.375','0.750','1.250','1.750','2.250')))
BAND_CODES=('SUB_050','ATR_050','ATR_100','ATR_150','ATR_200','EXTENDED')
BUFFER_VALUES=tuple(map(Decimal,('0.50','1.00','1.50','2.00')))


def risk_band(fraction:Decimal,*,bounds=BAND_BOUNDS)->str:
    fraction=decimal(fraction)
    bounds=tuple(decimal(v,positive=True) for v in bounds)
    if len(bounds)!=5 or tuple(sorted(set(bounds)))!=bounds or fraction<0:raise ValueError('Non-overlapping positive risk bands required')
    return BAND_CODES[next((i for i,v in enumerate(bounds) if fraction<v),5)]


def atr_variants(*,setup_id:str,side:str,entry:Decimal,anchor:Decimal,atr:Decimal,pip:Decimal,tick:Decimal,
                 target:Decimal|None=None,bounds=BAND_BOUNDS)->tuple[Variant,...]:
    entry,anchor,atr,pip,tick=(decimal(v,positive=True) for v in (entry,anchor,atr,pip,tick))
    if side not in {'BUY','SELL'} or (side=='BUY' and anchor>=entry) or (side=='SELL' and anchor<=entry):raise ValueError('Structural anchor must lie beyond entry on risk side')
    if entry%tick:raise ValueError('Entry must use observed tick-grid geometry')
    if target is not None:target=decimal(target,positive=True)
    results=[]
    for code,k in zip(('BUF_050','BUF_100','BUF_150','BUF_200'),BUFFER_VALUES):
        raw=anchor-k*atr if side=='BUY' else anchor+k*atr
        stop=(raw/tick).to_integral_value(rounding=ROUND_FLOOR if side=='BUY' else ROUND_CEILING)*tick
        distance=abs(entry-stop)/pip;fraction=abs(entry-stop)/atr
        blockers=[]
        if stop<=0:blockers.append('INVALID_STOP_PRICE')
        if target is None:blockers.append('TARGET_MISSING')
        elif side=='BUY' and target<=entry or side=='SELL' and target>=entry:blockers.append('TARGET_WRONG_SIDE')
        reward=None if target is None or 'TARGET_WRONG_SIDE' in blockers else abs(target-entry)/abs(entry-stop)
        results.append(Variant(digest([setup_id,code]),code,k,stop,distance,fraction,risk_band(fraction,bounds=bounds),target,reward,tuple(blockers)))
    return tuple(results)


def confidence(zone:dict,evidence:tuple[Evidence,...],*,lineage:Lineage,as_of:str,pip:Decimal,profile:dict|None=None)->dict:
    rows=[]
    for e in evidence:
        if (e.lineage.source_scope,e.lineage.source_epoch,e.lineage.origin)!=(lineage.source_scope,lineage.source_epoch,lineage.origin):
            raise ValueError('Cross-source evidence cannot enter confidence calculation')
        rows.append({'evidence_id':e.evidence_id,'symbol':e.lineage.symbol,'direction':e.side,
            'source_epoch':e.lineage.source_epoch,'timeframe':e.lineage.timeframe,
            'state':'CONFIRMED' if e.confirmed else 'PROVISIONAL','zone_kind':e.locality,
            'zone_low':str(e.low),'zone_high':str(e.high),'available_at_utc':e.lineage.available_at,
            'valid_until_utc':e.expires_at,'strength':str(e.strength),'source_reliability':str(e.reliability),
            'root_event_id':e.root_id,'correlation_cluster_id':e.cluster_id,'event_fingerprint':e.fingerprint,
            'producer_id':e.lineage.method_version,'independence_domain':e.domain})
    return score_zone_confidence(zone,rows,as_of_utc=as_of,pip_size=float(pip),source_epoch=lineage.source_epoch,profile=profile)


def qualify(gates:dict[str,bool|None],*,zone_confidence:Decimal,geometry_points:Decimal|None,
            target_points:Decimal|None,cost_points:Decimal|None,profile_id:str)->dict:
    required={f'QG{i:02d}' for i in range(1,15)}
    if set(gates)!=required or any(type(v) is not bool and v is not None for v in gates.values()):raise ValueError('All 14 explicit recipe/variant gates required')
    if not profile_id:raise ValueError('Versioned qualification profile required')
    blockers=[key+('_UNKNOWN' if gates[key] is None else '_FAILED') for key in sorted(gates) if gates[key] is not True]
    score=decimal(zone_confidence)
    if not 0<=score<=100:raise ValueError('Confidence index must be 0..100')
    points=(geometry_points,target_points,cost_points)
    for value,maximum in zip(points,(20,20,10)):
        if value is not None and not 0<=decimal(value)<=maximum:raise ValueError('Invalid quality component')
    if any(v is None for v in points):blockers.append('QUALITY_COMPONENT_MISSING')
    quality=None if blockers else score*Decimal('0.5')+sum(decimal(v) for v in points)
    return {'status':'WITHHELD' if blockers else 'ELIGIBLE_RESEARCH','blockers':blockers,
            'quality_score':None if quality is None else str(quality),'zone_confidence':str(score),
            'profile_id':profile_id,'classification':'RESEARCH_UNCALIBRATED','is_win_probability':False,
            'account_permission':False}
