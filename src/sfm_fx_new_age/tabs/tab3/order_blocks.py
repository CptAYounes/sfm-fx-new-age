"""Causal source-backed research zones, not a qualified executable M21A strategy."""
from __future__ import annotations

from decimal import Decimal
from importlib.resources import files
import json
from sfm_fx_new_age.contracts.analytics import Level,Lineage,digest
from sfm_fx_new_age.contracts.domain import instant,Origin,record
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.extensions import AnalyticalResult

PROFILE=json.loads(files('sfm_fx_new_age.contracts.data').joinpath('order_block_profile.json').read_text())
METHOD=PROFILE['method_version']
RECIPE_ID=PROFILE['recipe_id']
SOURCE_REF=PROFILE['source_document']+'#6.2;sha256='+PROFILE['source_document_sha256']


def detect_structure(bars,swings,profile):
    """Completed-bar break + explicit displacement, using the shared confirmed swings."""
    period=profile['lookback'];fraction=Decimal(profile['body_fraction']);multiple=Decimal(profile['range_multiple'])
    if type(period) is not int or not 2<=period<=100 or not 0<fraction<=1 or not 0<multiple<=10:
        raise ValueError('Bounded explicit research displacement profile required')
    events=[];used=set()
    for i in range(period+1,len(bars)):
        bar=bars[i];o,h,l,c=(Decimal(bar[k]) for k in ('open','high','low','close'))
        if h==l or c==o or abs(c-o)/(h-l)<fraction:continue
        ranges=[max(Decimal(bars[j]['high'])-Decimal(bars[j]['low']),
                    abs(Decimal(bars[j]['high'])-Decimal(bars[j-1]['close'])),
                    abs(Decimal(bars[j]['low'])-Decimal(bars[j-1]['close']))) for j in range(i-period,i)]
        baseline=sum(ranges,Decimal(0))/period
        if baseline<=0 or abs(c-o)<baseline*multiple:continue
        side='BUY' if c>o else 'SELL';kind='HIGH' if side=='BUY' else 'LOW'
        eligible=[p for p in swings if p['kind']==kind and instant(p['available_at'])<=instant(bar['open_time'])
                  and instant(p['pivot_time'])<instant(bar['open_time'])]
        if not eligible:continue
        pivot=max(eligible,key=lambda p:instant(p['pivot_time']));price=Decimal(pivot['price']);previous=Decimal(bars[i-1]['close'])
        if (side=='BUY' and not previous<=price<c) or (side=='SELL' and not previous>=price>c) or (pivot['id'],side) in used:continue
        used.add((pivot['id'],side))
        stamp=max([b['available_at'] for b in bars[max(0,i-period-1):i+1]]+[pivot['available_at']],key=instant)
        events.append({'id':digest([pivot['id'],thaw(bar),side]),'side':side,'pivot_id':pivot['id'],
                       'pivot_time':pivot['pivot_time'],'break_index':i,'break_time':bar['open_time'],
                       'available_at':stamp,'body':str(abs(c-o)),'prior_mean_true_range':str(baseline)})
    return events[-64:]


def structure_producer(inputs,deps):
    p=profile_values(inputs);result={};has_data=False
    swings=deps['SWING_MAP']['output'] or {}
    for frame,raw in inputs['bars'].items():
        bars=list(raw)[-2048:]
        if len(bars)>=p['lookback']+2:has_data=True
        result[frame]=detect_structure(bars,swings.get(frame,()),p)
    return AnalyticalResult('EVALUATED',result) if has_data else AnalyticalResult('WARMUP',reason='Completed bars for displacement baseline and confirmed swings required')


def profile_values(inputs):
    p=dict(PROFILE['parameters'])
    for row in inputs['parameters']:
        if row['key'].startswith('order_block.'):
            p[row['key'].removeprefix('order_block.')]=row['value']
    return p


def order_block_producer(inputs,deps):
    events=deps['SMC_STRUCTURE']['output'] or {};p=profile_values(inputs)
    # Another parameter profile remains archived, not re-emitted under new ownership.
    prior={row['level_id']:row for row in inputs['prior_objects']['level'] if row['lineage']['profile_hash']==inputs['profile_hash']}
    objects=[];output={};seen=set()
    for frame,raw in inputs['bars'].items():
        bars=list(raw)[-2048:];zones=[]
        for event in events.get(frame,()):
            index=event['break_index'];side=event['side'];source=None
            for j in range(index-1,max(-1,index-1-p['source_lookback']),-1):
                row=bars[j];o,c=Decimal(row['open']),Decimal(row['close'])
                if (side=='BUY' and c<o) or (side=='SELL' and c>o):source=row;break
            if source is None:continue
            low,high=Decimal(source['low']),Decimal(source['high']);state='CONFIRMED';touches=0
            available=event['available_at']
            for later in bars[index+1:]:
                close=Decimal(later['close'])
                if (side=='BUY' and close<low) or (side=='SELL' and close>high):
                    state='INVALIDATED';available=max(available,later['available_at'],key=instant);break
                if Decimal(later['low'])<=high and Decimal(later['high'])>=low:
                    touches+=1;state='TOUCHED';available=max(available,later['available_at'],key=instant)
            root=digest(thaw(source));identity=digest([inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],
                    frame,inputs['profile_hash'],event['id'],root,METHOD]);seen.add(identity)
            old=prior.get(identity);revision=(old['revision']+1) if old else 1
            # Immutable body identity does not advance merely because the scanner reran.
            if old and (old['state'],old['low'],old['high'])==(state,str(low),str(high)):
                revision=old['revision'];available=old['lineage']['available_at']
            elif old:available=max(available,old['lineage']['available_at'],key=instant)
            lineage=Lineage(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],frame,available,
                            Origin(inputs['authority']['origin']),METHOD,inputs['profile_hash'])
            level=Level(identity,revision,'ORDER_BLOCK',low,high,side,state,(root,event['pivot_id'],event['id']),lineage)
            objects.append(level)
            from .candidates import order_block_evidence,settings
            policy=settings(inputs)
            # Evidence remains a correlated PRICE_STRUCTURE interpretation of
            # this exact displacement, not a second independent indicator vote.
            from datetime import timedelta
            if instant(event['available_at'])+timedelta(seconds=policy['expiry_seconds'])>instant(lineage.available_at):
                objects.append(order_block_evidence(record(level),confirmation=event['available_at'],
                    expiry_seconds=policy['expiry_seconds'],reliability=policy['evidence_reliability']))
            zones.append({'level_id':identity,'source_candle_time':source['open_time'],'confirmation_time':event['available_at'],
                          'proximal':str(high if side=='BUY' else low),'distal':str(low if side=='BUY' else high),
                          'touch_count':touches,'state':state,'side':side,'method':METHOD})
        output[frame]=zones
    for identity,old in prior.items():
        if identity not in seen and old['state'] not in {'INVALIDATED','EXPIRED'}:
            lineage=Lineage(**dict(old['lineage'],available_at=inputs['_evaluation_at']))
            objects.append(Level(identity,old['revision']+1,old['kind'],Decimal(old['low']),Decimal(old['high']),old['side'],
                                 'INVALIDATED',tuple(old['root_ids']),lineage))
    return AnalyticalResult('EVALUATED',{'classification':'RESEARCH_UNCALIBRATED_PROJECTION_ONLY','frames':output,
                                      'profile':p,'source_ref':SOURCE_REF},tuple(objects))
