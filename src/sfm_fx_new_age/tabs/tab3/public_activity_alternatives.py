"""Explicit quote-activity interpretations, never executed-volume/aggressor data.

Enabled only by the runtime's disclosed activity-alternatives policy. Original
strict methods remain independently selectable via --strict-genuine-data.
"""
from collections import defaultdict
from decimal import Decimal
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable

ACTIVITY_NAMES={
 'volume_displacement':'Tick-activity displacement · not traded volume',
 'effort_result':'Tick effort / price result · activity proxy',
 'volume_profile':'Quote-activity profile · not volume profile',
 'vwap_bands':'Quote-sample weighted price / bands · not traded VWAP',
 'footprint_delta':'Quote-direction footprint · not aggressor delta',
 'dom_imbalance':'Broker observed DOM · displayed-size imbalance'}


def alternative_kind(key):
    return 'BROKER_DEPTH' if key=='dom_imbalance' else 'INTRABAR_PRICES' if key in {'volume_profile','vwap_bands','footprint_delta'} else ''


def evaluate_activity(key,f,inputs):
    from .public_algorithms import blank,marker
    from .public_genuine_data import source_zone,value_area
    from .public_sequence_features import displacement
    out=blank();out['metrics'].update(interpretation_id='NATIVE_ACTIVITY_'+key.upper()+'_V1',interpretation_name=ACTIVITY_NAMES[key],
        alternative=True,executed_volume=False,known_aggressors=False,measurement_unit='QUOTE_UPDATES',
        semantic_warning='Quote activity is not traded quantity or aggressor flow. No strict-method qualification is claimed.')
    if key in {'volume_displacement','effort_result'}:
        window=14 if key=='volume_displacement' else 20;eligible=0
        volumes=[b.get('tick_volume') for b in f.bars]
        if any(v is not None and (type(v) is not int or v<0) for v in volumes):raise ValueError('Native nonnegative integral tick counts required')
        for i in range(window,f.n):
            prior=volumes[i-window:i];current=volumes[i]
            if current is None or any(v is None for v in prior):continue
            total=sum(prior)
            if total<=0:continue
            eligible+=1
            if current*window<total*1.5:continue
            if key=='volume_displacement':
                move=displacement(f).get(i)
                if move:marker(out,f,i,'Tick-activity displacement (proxy)',move['side'])
            else:
                mean=sum(abs(f.c[j]-f.o[j]) for j in range(i-window,i))/window;lo=min(f.l[i-window:i]);hi=max(f.h[i-window:i]);width=hi-lo
                if mean<=0 or abs(f.c[i]-f.o[i])>.5*mean or width<=0:continue
                side='BUY' if f.l[i]<=lo+.1*width and f.c[i]>f.o[i] else 'SELL' if f.h[i]>=hi-.1*width and f.c[i]<f.o[i] else None
                if side:marker(out,f,i,'Tick effort / low price result (proxy)',side)
        if not eligible:raise ProjectionInputUnavailable('Native tick-activity lookback required','WARMUP')
        out['metrics'].update(eligible_tick_activity_bars=eligible,weight_source='ProtoOATrendbar.volume: quote ticks, not executed units')
        return out
    kind=alternative_kind(key);data=inputs.get('optional_evidence',{}).get(kind)
    if not data:raise ProjectionInputUnavailable(kind+' input absent; activity alternative cannot invent observations')
    # Reuse identical identity/availability/wire validation with its real kind.
    from sfm_fx_new_age.contracts.models import thaw
    from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
    from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
    raw=thaw(data);raw['records']=tuple(raw['records']);e=SupplementalEvidence(**raw);validate_wire_shape(e)
    if (e.scope_id,e.source_epoch,e.symbol,e.origin)!=(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],inputs['authority']['origin']):raise ValueError('Activity source mismatch')
    if not instant(e.available_at)<=instant(inputs['_evaluation_at'])<=instant(e.valid_until):raise ProjectionInputUnavailable('Activity source expired or not yet available')
    rows=raw['records'];root=(digest(raw),)
    out['metrics'].update(source_kind=kind,source_evidence_hash=root[0],source_venue=e.venue,source_unit=e.unit,
        observed_interval_start=e.window_start,observed_interval_end=e.window_end,source_available_at=e.available_at)
    if key=='dom_imbalance':
        row=rows[-1];age=(instant(inputs['_evaluation_at'])-instant(row['time'])).total_seconds()
        if not 0<=age<=15:raise ProjectionInputUnavailable('Broker depth local receipt older than 15 seconds')
        bids=row['bids'][:5];asks=row['asks'][:5];buy=sum(Decimal(q) for p,q in bids);sell=sum(Decimal(q) for p,q in asks)
        imbalance=(buy-sell)/(buy+sell);side='BUY' if imbalance>=Decimal('.2') else 'SELL' if imbalance<=Decimal('-.2') else 'NEUTRAL'
        source_zone(out,f,(Decimal(bids[0][0])+Decimal(asks[0][0]))/2,'Observed broker DOM '+str(round(imbalance,3)),raw,side)
        out['metrics'].update(imbalance=str(imbalance),measurement_unit='DISPLAYED_BASE_UNITS',full_book_complete=False,native_sequence=False,
            clock_basis=raw['parameters']['clock_basis'],unknown_deleted_ids=raw['parameters']['unknown_deleted_ids'],
            semantic_warning='Observed broker subscription only; local receipt clock, no native event time/sequence or full-book claim.')
    elif key=='volume_profile':
        # Count actual observations, not fabricated quantity fields or traversed prices.
        tick=Decimal(str(inputs['spec']['tick_size']));declared=Decimal(str(raw['parameters']['tick_size']))
        if declared!=tick:raise ProjectionInputUnavailable('Quote/native tick-grid mismatch')
        bins=defaultdict(Decimal)
        for row in rows:bins[int(Decimal(row['price'])//tick)]+=1
        poc,val,vah,coverage=value_area(bins)
        for p,label in ((poc,'Quote-count POC'),(val,'Quote-count value low 70%'),(vah,'Quote-count value high 70%')):source_zone(out,f,Decimal(p)*tick,label,raw)
        out['metrics'].update(observations=len(rows),value_coverage=str(coverage),profile_bins=[dict(price=str(Decimal(p)*tick),quote_updates=str(v)) for p,v in sorted(bins.items())[-256:]])
    elif key=='vwap_bands':
        total=Decimal(0);mean=Decimal(0);m2=Decimal(0)
        for row in rows:
            p=Decimal(row['price']);total+=1;delta=p-mean;mean+=delta/total;m2+=delta*(p-mean)
        sd=(max(Decimal(0),m2/total)).sqrt()
        for multiple in (-2,-1,0,1,2):
            p=mean+multiple*sd
            if p>0:source_zone(out,f,p,'Quote-sample mean '+str(multiple)+'σ (not VWAP)',raw)
        out['metrics'].update(quote_sample_mean=str(mean),sample_weighted_population_sd=str(sd),observations=len(rows),weight_per_quote=1)
    elif key=='footprint_delta':
        bins=defaultdict(lambda:dict(UP=0,DOWN=0,UNCHANGED=0,UNCLASSIFIED=0));previous=None
        for row in rows:
            p=Decimal(row['price']);direction='UNCLASSIFIED' if previous is None else 'UNCHANGED' if p==previous else 'UP' if p>previous else 'DOWN'
            bins[row['price']][direction]+=1;previous=p
        up=sum(v['UP'] for v in bins.values());down=sum(v['DOWN'] for v in bins.values());flat=sum(v['UNCHANGED'] for v in bins.values())
        strongest=max(bins,key=lambda p:(abs(bins[p]['UP']-bins[p]['DOWN']),Decimal(p)));delta=up-down
        source_zone(out,f,Decimal(strongest),'Quote-direction count difference '+str(delta)+' (proxy)',raw,'BUY' if delta>0 else 'SELL' if delta<0 else 'NEUTRAL')
        out['metrics'].update(up_quote_changes=up,down_quote_changes=down,unchanged_quotes=flat,quote_direction_difference=delta,
            aggressor_inferred=False,first_observation_unclassified=True,unclassified_quotes=1,levels=[dict(price=p,**v) for p,v in sorted(bins.items(),key=lambda x:Decimal(x[0]))[-256:]])
    else:raise ValueError('Unknown activity interpretation')
    return out
