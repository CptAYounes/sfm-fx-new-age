"""Real-input-only profile computations. No OHLC-to-volume or order-flow fiction."""
from collections import defaultdict
from bisect import bisect_left
from decimal import Decimal,ROUND_FLOOR
from datetime import timedelta
import math
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable,optional_projection_source
from .public_sequence_features import displacement

DATA_METHODS={'volume_displacement':'TRADED_PRINTS','effort_result':'TRADED_PRINTS','cause_effect':'POINT_FIGURE_TICKS',
    'profile_tpo':'INTRABAR_PRICES','volume_profile':'TRADED_PRINTS','vwap_bands':'TRADED_PRINTS','dom_imbalance':'VENUE_BOOK',
    'footprint_delta':'AGGRESSOR_PRINTS','cot_macro':'CFTC_REPORT','calendar_context':'OFFICIAL_CALENDAR'}


def source_input(key,inputs):
    kind=DATA_METHODS[key];body=optional_projection_source(key,kind,inputs.get('optional_evidence',{}),inputs.get('frame'))
    if body:kind=body['kind']
    if not body:raise ProjectionInputUnavailable(kind+' requires a configured genuine source adapter, complete interval and matching provenance; none available')
    # Pure tests and alternative core callers use the identical validating contract.
    from sfm_fx_new_age.contracts.models import thaw
    raw=thaw(body);raw['records']=tuple(raw['records']);e=SupplementalEvidence(**raw)
    if e.kind in {'EXECUTED_BAR_QUANTITIES','EXECUTED_WEEK_QUANTITIES','VENUE_BOOK','VENUE_L2_CHECKSUM_BOOK','VENUE_NATIVE_CHAIN_BOOK','BROKER_DEPTH'}:
        from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
        validate_wire_shape(e)
    expected=(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],inputs['authority']['origin'])
    if (e.scope_id,e.source_epoch,e.symbol,e.origin)!=expected:raise ValueError('Optional source identity mismatch')
    cutoff=inputs['_evaluation_at']
    if not instant(e.available_at)<=instant(cutoff)<=instant(e.valid_until):raise ProjectionInputUnavailable('Optional source not available at cutoff or expired')
    return raw


def bins_for(data,inputs,*,tpo=False):
    tick=Decimal(str((inputs.get('spec') or {}).get('tick_size') or '0'))
    if tick<=0:raise ProjectionInputUnavailable('Native tick size required for source bins')
    declared=Decimal(str(data['parameters'].get('tick_size') or '0'))
    if declared!=tick:raise ProjectionInputUnavailable('Source price-bin/native tick-grid alignment not established')
    if tpo and data['parameters'].get('slot_coverage_complete') is not True:raise ProjectionInputUnavailable('Explicit complete 30-minute observed slot coverage required')
    bins=defaultdict(Decimal);slots=defaultdict(set);root=instant(data['window_start'])
    for r in data['records']:
        value=Decimal(r['price']);index=int((value/tick).to_integral_value(rounding=ROUND_FLOOR))
        if tpo:slots[int((instant(r['time'])-root).total_seconds()//1800)].add(index)
        else:bins[index]+=Decimal(r['quantity'])
    if tpo:
        count=int((instant(data['window_end'])-root).total_seconds()//1800)
        if count<2 or (instant(data['window_end'])-root).total_seconds()%1800 or set(slots)!=set(range(count)):raise ProjectionInputUnavailable('Missing or incomplete TPO slots; initial balance requires first two slots')
        for values in slots.values():
            for index in values:bins[index]+=1
    if not bins or len(bins)>10000:raise ProjectionInputUnavailable('Empty or over-budget observed source profile')
    return bins,tick,slots


def value_area(bins):
    prices=sorted(bins);mid=(prices[0]+prices[-1])/2
    poc=min(prices,key=lambda p:(-bins[p],abs(p-mid),p));left=right=prices.index(poc);total=sum(bins.values());included=bins[poc]
    while included<total*Decimal('.70') and (left>0 or right<len(prices)-1):
        lv=bins[prices[left-1]] if left>0 else Decimal('-1');rv=bins[prices[right+1]] if right<len(prices)-1 else Decimal('-1')
        if lv>=rv:left-=1;included+=bins[prices[left]]
        else:right+=1;included+=bins[prices[right]]
    return poc,prices[left],prices[right],included/total


def source_zone(out,f,price,label,data,side='NEUTRAL'):
    from .public_algorithms import zone
    known=max(data['available_at'],f.bars[-1]['available_at'],key=instant)
    if data['venue']=='KRAKEN_SPOT_FIAT':label='Kraken venue · '+label
    if data['venue']=='BITSTAMP_SPOT_FIAT':label='Bitstamp venue · '+label
    if data['venue']=='FXOPEN_TICKTRADER_REPORTED_FX_EXECUTIONS':label='FXOpen reported · '+label
    zone(out,f,f.n-1,float(price),float(price),label,side,available=known,roots=(digest(data),))
    out['zones'][-1].update(source_venue=data['venue'],source_instrument=data['instrument'],source_unit=data['unit'])


def quantity_per_bar(f,data):
    values=[]
    if data['kind'] in {'EXECUTED_BAR_QUANTITIES','EXECUTED_WEEK_QUANTITIES'}:
        rows=sorted(data['records'],key=lambda r:instant(r['time']))
        intervals=[(instant(r['time']),instant(r['end_time']),Decimal(r['quantity'])) for r in rows]
        for previous,current in zip(intervals,intervals[1:]):
            if current[0]<previous[1]:raise ValueError('Overlapping native executed intervals')
        starts=[row[0] for row in intervals];ends=[row[1] for row in intervals];prefix=[Decimal(0)];gaps=[0]
        for i,(lo,hi,quantity) in enumerate(intervals):
            prefix.append(prefix[-1]+quantity);gaps.append(gaps[-1]+int(i>0 and lo!=ends[i-1]))
        for b in f.bars:
            start,end=instant(b['open_time']),instant(b['close_time']);left=bisect_left(starts,start);right=bisect_left(ends,end)
            valid=left<=right<len(intervals) and starts[left]==start and ends[right]==end and gaps[right+1]==gaps[left+1]
            values.append(prefix[right+1]-prefix[left] if valid else None)
        return values
    for b in f.bars:
        start,end=instant(b['open_time']),instant(b['close_time'])
        if start<instant(data['window_start']) or end>instant(data['window_end']):values.append(None);continue
        values.append(sum((Decimal(r['quantity']) for r in data['records'] if start<=instant(r['time'])<end),Decimal(0)))
    return values


def point_figure(data,inputs):
    tick=Decimal(str((inputs.get('spec') or {}).get('tick_size') or '0'));params=data['parameters'];box=Decimal(str(params.get('box_size') or '0'))
    if tick<=0 or box<=0 or box%tick or params.get('reversal_boxes')!=3:raise ProjectionInputUnavailable('Explicit tick-aligned box size and 3-box reversal required')
    if params.get('side') not in {'BUY','SELL'} or not all(k in params for k in ('count_line','count_start','count_end')):raise ProjectionInputUnavailable('Source-owned complete count-phase interval and count line required')
    line=Decimal(str(params['count_line']));start=instant(params['count_start']);end=instant(params['count_end'])
    if not instant(data['window_start'])<=start<end<=instant(data['window_end']) or line%box:raise ValueError('P&F count interval or line invalid')
    columns=[];direction=None;lo=hi=None;first=None;last=None
    for r in data['records']:
        if not start<=instant(r['time'])<end:continue
        value=int((Decimal(r['price'])/box).to_integral_value(rounding=ROUND_FLOOR))
        if lo is None:lo=hi=value;first=last=r['time'];continue
        if direction is None:
            if value>hi:direction='X';hi=value
            elif value<lo:direction='O';lo=value
        elif direction=='X':
            if value>hi:hi=value
            elif value<=hi-3:columns.append(dict(direction=direction,low=lo,high=hi,start=first,end=last));direction='O';lo=value;hi=hi-1;first=r['time']
        else:
            if value<lo:lo=value
            elif value>=lo+3:columns.append(dict(direction=direction,low=lo,high=hi,start=first,end=last));direction='X';hi=value;lo=lo+1;first=r['time']
        last=r['time']
    if direction is not None:columns.append(dict(direction=direction,low=lo,high=hi,start=first,end=last))
    at=int(line/box);count=sum(c['low']<=at<=c['high'] for c in columns)
    if count<2:raise ProjectionInputUnavailable('Insufficient completed source P&F count columns','WARMUP')
    # The last developing column is retained for inspection but not horizontal count.
    count=sum(c['low']<=at<=c['high'] for c in columns[:-1])
    if count<2:raise ProjectionInputUnavailable('Two completed horizontal count columns required','WARMUP')
    extent=box*3*count;low=Decimal(min(c['low'] for c in columns))*box;high=Decimal(max(c['high'] for c in columns))*box
    anchors=(low,(low+line)/2) if params['side']=='BUY' else (high,(high+line)/2)
    targets=[a+extent if params['side']=='BUY' else a-extent for a in anchors]
    return columns,count,extent,targets


def evaluate_genuine(key,f,inputs,deps):
    from .public_algorithms import blank,marker,series
    from .public_activity_alternatives import ACTIVITY_NAMES,evaluate_activity
    has_native_quantities=key in {'volume_displacement','effort_result'} and (inputs.get('optional_evidence',{}).get('EXECUTED_BAR_QUANTITIES') or inputs.get('frame')=='W1' and inputs.get('optional_evidence',{}).get('EXECUTED_WEEK_QUANTITIES'))
    has_native_book=key=='dom_imbalance' and optional_projection_source(key,DATA_METHODS[key],inputs.get('optional_evidence',{})) is not None
    if key in ACTIVITY_NAMES and inputs.get('activity_alternatives') is True and not inputs.get('optional_evidence',{}).get(DATA_METHODS[key]) and not has_native_quantities and not has_native_book:
        return evaluate_activity(key,f,inputs)
    if key=='cause_effect' and not inputs.get('optional_evidence',{}).get('POINT_FIGURE_TICKS'):
        from .public_point_figure_auto import automatic_point_figure
        return automatic_point_figure(f,inputs)
    data=source_input(key,inputs);out=blank();rows=data['records']
    if key in {'volume_displacement','effort_result'}:
        quantities=quantity_per_bar(f,data);lookback=14 if key=='volume_displacement' else 20;eligible=0
        for i in range(lookback,f.n):
            prior=quantities[i-lookback:i]
            if quantities[i] is None or any(v is None for v in prior) or sum(prior)<=0:continue
            eligible+=1;heavy=quantities[i]>=sum(prior)/lookback*Decimal('1.5')
            if not heavy:continue
            if key=='volume_displacement':
                move=displacement(f).get(i)
                if move:marker(out,f,i,('Kraken venue · ' if data['venue']=='KRAKEN_SPOT_FIAT' else 'FXOpen reported · ' if data['venue']=='FXOPEN_TICKTRADER_REPORTED_FX_EXECUTIONS' else '')+'Genuine-volume displacement',move['side'],available=data['available_at'],roots=(digest(data),))
            else:
                mean=sum(abs(f.c[j]-f.o[j]) for j in range(i-20,i))/20;lo=min(f.l[i-20:i]);hi=max(f.h[i-20:i]);width=hi-lo
                if mean<=0 or abs(f.c[i]-f.o[i])>.5*mean or width<=0:continue
                side='BUY' if f.l[i]<=lo+.1*width and f.c[i]>f.o[i] else 'SELL' if f.h[i]>=hi-.1*width and f.c[i]<f.o[i] else None
                if side:marker(out,f,i,('Kraken venue · ' if data['venue']=='KRAKEN_SPOT_FIAT' else 'FXOpen reported · ' if data['venue']=='FXOPEN_TICKTRADER_REPORTED_FX_EXECUTIONS' else '')+'Genuine effort / low-result absorption hypothesis',side,available=data['available_at'],roots=(digest(data),))
        if not eligible:raise ProjectionInputUnavailable('Complete real-volume lookback and own-bar intervals required','WARMUP')
        out['metrics']['eligible_volume_bars']=eligible
        out['metrics'].update(latest_bar_quantity_covered=quantities[-1] is not None,
             latest_lookback_complete=all(v is not None for v in quantities[-lookback-1:]) and len(quantities)>=lookback+1,
             last_complete_quantity_bar=next((b['close_time'] for b,q in reversed(list(zip(f.bars,quantities))) if q is not None),None))
    elif key in {'profile_tpo','volume_profile'}:
        bins,tick,slots=bins_for(data,inputs,tpo=key=='profile_tpo');poc,val,vah,coverage=value_area(bins)
        for p,label in ((poc,'POC'),(val,'Value-area low 70%'),(vah,'Value-area high 70%')):source_zone(out,f,Decimal(p)*tick,label,data)
        if key=='profile_tpo':
            ib=slots[0]|slots[1]
            for p,label in ((min(ib),'Initial-balance low'),(max(ib),'Initial-balance high')):source_zone(out,f,Decimal(p)*tick,label,data)
        out['metrics'].update(observed_bins=len(bins),value_coverage=str(coverage),profile_bins=[dict(price=str(Decimal(k)*tick),weight=str(v)) for k,v in sorted(bins.items())[-256:]],measurement='ACTUAL_OBSERVED_TPO' if key=='profile_tpo' else 'ACTUAL_EXECUTED_QUANTITY')
    elif key=='vwap_bands':
        total=Decimal(0);mean=Decimal(0);m2=Decimal(0)
        for r in rows:
            p,w=Decimal(r['price']),Decimal(r['quantity']);next_total=total+w;delta=p-mean;mean+=delta*w/next_total;m2+=w*delta*(p-mean);total=next_total
        sd=(max(Decimal(0),m2/total)).sqrt()
        for multiple in (-2,-1,0,1,2):
            price=mean+multiple*sd
            if price>0:source_zone(out,f,price,'Genuine anchored VWAP '+str(multiple)+'σ',data)
        out['metrics'].update(vwap=str(mean),weighted_population_sd=str(sd),quantity=str(total),reset_anchor=data['window_start'])
    elif key=='cause_effect':
        columns,count,extent,targets=point_figure(data,inputs)
        for t in targets:
            if t>0:source_zone(out,f,t,'P&F conservative count objective',data,data['parameters']['side'])
        out['metrics'].update(completed_count_columns=count,box_reversal_distance=str(extent),columns=columns[-64:],incomplete_final_column_excluded=True,count_parameters=dict(data['parameters']),source_reference=data['source_ref'],count_settings_authority='SOURCE_DECLARED_RESEARCH_SETTINGS_NOT_INDEPENDENT_OPERATOR_APPROVAL')
    elif key=='dom_imbalance':
        r=rows[-1];now=instant(inputs['_evaluation_at']);time=instant(r['time'])
        broker_book=data['kind']=='BROKER_DEPTH'
        fresh=instant(r['available_at']) if data['kind']=='VENUE_L2_CHECKSUM_BOOK' else time
        maximum_age=15 if broker_book else 5
        if not 0<=(now-fresh).total_seconds()<=maximum_age:raise ProjectionInputUnavailable('Fresh <=15s original broker receipt required' if broker_book else 'Fresh <=5s native sequence event / verified L2 receipt required')
        if data['kind']=='VENUE_BOOK' and (type(r.get('sequence')) is not int or r['sequence']<1):raise ValueError('Native venue sequence required')
        bids=r.get('bids',());asks=r.get('asks',())
        maximum=4096 if data['kind']=='VENUE_NATIVE_CHAIN_BOOK' else 100
        if not bids or not asks or len(bids)>maximum or len(asks)>maximum:raise ValueError('Bounded two-sided book required')
        def levels(values,descending):
            result=[(Decimal(p),Decimal(q)) for p,q in values]
            if any(p<=0 or q<=0 or not p.is_finite() or not q.is_finite() for p,q in result) or result!=sorted(result,key=lambda v:v[0],reverse=descending) or len({p for p,q in result})!=len(result):raise ValueError('Positive uniquely ordered book levels required')
            return result
        bids,asks=levels(bids,True),levels(asks,False)
        if bids[0][0]>=asks[0][0]:raise ValueError('Crossed or locked book rejected')
        buy=sum(q for p,q in bids[:5]);sell=sum(q for p,q in asks[:5]);imbalance=(buy-sell)/(buy+sell);side='BUY' if imbalance>=Decimal('.2') else 'SELL' if imbalance<=Decimal('-.2') else 'NEUTRAL'
        checksum_book=data['kind']=='VENUE_L2_CHECKSUM_BOOK'
        source_zone(out,f,(bids[0][0]+asks[0][0])/2,('Broker observed DOM imbalance ' if broker_book else 'Checksum L2 top-10 / top-5 imbalance ' if checksum_book else 'Venue displayed-depth imbalance ')+str(round(imbalance,3)),data,side)
        out['metrics'].update(imbalance=str(imbalance),venue_only=not broker_book,executed_volume=False)
        if broker_book:
            out['metrics'].update(interpretation_id='BROKER_SCOPED_DISPLAYED_DOM_V1',
                interpretation_name='Broker DOM · displayed-size imbalance',alternative=False,
                genuine_displayed_depth=True,measurement_unit='DISPLAYED_BASE_UNITS',
                native_sequence=False,full_book_complete=False,strict_native_full_book_qualified=False,
                known_aggressors=False,market_wide_volume=False,broker_fill_claim=False,
                clock_basis=data['parameters']['clock_basis'],original_received_at=r['time'],
                unknown_deleted_ids=data['parameters']['unknown_deleted_ids'],imbalance_depth=5,
                source_window_start=data['window_start'],source_window_end=data['window_end'],
                semantic_warning='Genuine observed broker-scoped displayed liquidity, permitted by DOM_BOOK; local receipt clock only. No native event time/sequence, complete venue book, executed-volume or aggressor claim.')
        if checksum_book:out['metrics'].update(native_sequence=False,full_book_complete=False,checksum_verified=True,subscription_depth=10,imbalance_depth=5,clock_basis=data['parameters']['clock_basis'],native_event_at=r['time'],verified_received_at=r['available_at'])
        if data['kind']=='VENUE_NATIVE_CHAIN_BOOK':
            out['metrics'].update(native_sequence=True,full_book_complete=True,sequence_model=data['parameters']['sequence_model'],full_order_count=data['parameters']['full_order_count'],native_event_id=r['event_id'],native_pre_event_id=r['pre_event_id'],checkpoint_verified=True,imbalance_depth=5)
    elif key=='footprint_delta':
        bins=defaultdict(lambda:dict(BUY=Decimal(0),SELL=Decimal(0)))
        for r in rows:bins[r['price']][r['aggressor']]+=Decimal(r['quantity'])
        buy=sum(v['BUY'] for v in bins.values());sell=sum(v['SELL'] for v in bins.values());delta=buy-sell
        strongest=max(bins,key=lambda p:(abs(bins[p]['BUY']-bins[p]['SELL']),Decimal(p)))
        source_zone(out,f,Decimal(strongest),'Executed footprint delta '+str(delta),data,'BUY' if delta>0 else 'SELL' if delta<0 else 'NEUTRAL')
        out['metrics'].update(delta=str(delta),buy_quantity=str(buy),sell_quantity=str(sell),levels=[dict(price=p,buy=str(v['BUY']),sell=str(v['SELL'])) for p,v in sorted(bins.items(),key=lambda t:Decimal(t[0]))[-256:]])
    elif key=='cot_macro':
        r=rows[-1];base,quote=inputs['symbol'][:3],inputs['symbol'][3:];currency=quote if base=='USD' else base
        if r.get('currency')!=currency or r.get('report_type')!='LEGACY_NONCOMMERCIAL' or instant(r['report_as_of'])>instant(r['time']):raise ValueError('Explicit CFTC class/currency/report/publication mapping required')
        long,short,interest=map(lambda k:Decimal(str(r[k])),('long','short','open_interest'))
        if not all(v.is_finite() for v in (long,short,interest)) or min(long,short)<0 or interest<=0 or max(long,short)>interest:raise ValueError('Invalid published contract quantities')
        net=(long-short)/interest*(-1 if base=='USD' else 1)
        source_zone(out,f,Decimal(f.bars[-1]['close']),'Published futures COT context (not spot positions)',data,'BUY' if net>0 else 'SELL' if net<0 else 'NEUTRAL')
        out['metrics'].update(mapped_net_fraction=str(net),report_as_of=r['report_as_of'],actual_release=None if data['parameters'].get('availability_basis')=='FIRST_VERIFIED_HTTP_OBSERVATION' else r['time'],first_verified_available_at=r['time'] if data['parameters'].get('availability_basis')=='FIRST_VERIFIED_HTTP_OBSERVATION' else None,spot_position_claim=False)
    elif key=='calendar_context':
        params=data['parameters'];cutoff=instant(inputs['_evaluation_at'])
        if not all(k in params for k in ('schedule_coverage_start','schedule_coverage_end')) or not instant(params['schedule_coverage_start'])<=cutoff<=instant(params['schedule_coverage_end']):raise ProjectionInputUnavailable('Official calendar schedule coverage missing at cutoff')
        relevant=[]
        for r in rows:
            if r.get('currency') not in (inputs['symbol'][:3],inputs['symbol'][3:]):continue
            if not r.get('title') or r.get('importance') not in {'HIGH','MEDIUM','LOW','UNSPECIFIED'}:raise ValueError('Official event name/importance required')
            delta=(instant(r['scheduled_at'])-cutoff).total_seconds()
            if -1800<delta<=1800:
                source_zone(out,f,Decimal(f.bars[-1]['close']),'Published release risk: '+r['title'][:80],data);relevant.append(r['id'])
        out['metrics'].update(nearby_published_events=relevant,complete_feed_interval_only=True,no_news_guarantee=False,coverage_policy=params.get('coverage_policy','CONFIGURED_PROVIDER_DECLARATION'),importance_unspecified=any(r.get('importance')=='UNSPECIFIED' for r in rows))
    else:raise ValueError('Unknown genuine-data profile')
    out['metrics'].update(source_kind=data['kind'],source_venue=data['venue'],source_unit=data['unit'],input_origin=data['origin'],source_evidence_hash=digest(data),provider_provenance='CONFIGURED_ADAPTER_DECLARATION_NOT_INDEPENDENT_AUTHENTICATION')
    if data['venue']=='KRAKEN_SPOT_FIAT':
        names={'volume_displacement':'Executed-quantity displacement','effort_result':'Executed effort / price result','volume_profile':'Executed volume profile','vwap_bands':'Executed anchored VWAP / bands','footprint_delta':'Executed taker-side footprint','dom_imbalance':'Checksum-verified L2 depth imbalance'}
        out['metrics'].update(interpretation_name='Kraken venue · '+names.get(key,key),external_venue=True,executed_volume=data['kind']!='VENUE_L2_CHECKSUM_BOOK',known_aggressors=data['kind']=='AGGRESSOR_PRINTS',market_wide_volume=False,broker_fill_claim=False,source_window_start=data['window_start'],source_window_end=data['window_end'],semantic_warning='Separately sourced Kraken fiat venue context only; not cTrader fills or consolidated spot FX. Checksum depth is displayed liquidity, not executions or a sequenced full book.')
        if out['metrics'].get('latest_lookback_complete') is False:
            out['metrics']['interpretation_name']+=' [historical coverage only]'
    if data['venue']=='BITSTAMP_SPOT_FIAT':
        out['metrics'].update(interpretation_name='Bitstamp venue · Native-chain full displayed-book imbalance',external_venue=True,executed_volume=False,known_aggressors=False,market_wide_volume=False,broker_fill_claim=False,semantic_warning='Full public displayed orders with native UUID predecessor continuity; not hidden liquidity, executions, cTrader fills or consolidated FX.')
    if data['venue']=='FXOPEN_TICKTRADER_REPORTED_FX_EXECUTIONS':
        names={'volume_displacement':'Reported-execution quantity displacement','effort_result':'Reported executed effort / price result','volume_profile':'Reported executed-volume profile','vwap_bands':'Reported execution-weighted VWAP / bands'}
        out['metrics'].update(interpretation_name='FXOpen reported · '+names.get(key,key),external_venue=True,
            executed_volume=True,known_aggressors=False,market_wide_volume=False,broker_fill_claim=False,
            source_window_start=data['window_start'],source_window_end=data['window_end'],
            semantic_warning='FXOpen public reported NZDUSD FX-contract executions only, not all ECN/client trades, cTrader fills, consolidated FX or documented aggressors. Local row content addresses are not native IDs or sequences.')
        if out['metrics'].get('latest_lookback_complete') is False:
            out['metrics']['interpretation_name']+=' [historical coverage only]'
    return out


def evaluate_live_body(f,inputs):
    from .public_algorithms import blank
    q=inputs.get('quote');now=instant(inputs['_evaluation_at']);out=blank()
    if not q or inputs.get('quote_usable') is not True:raise ProjectionInputUnavailable('Fresh coherent same-source Bid/Ask quote required; no live recovery inferred from OHLC')
    expected=(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'])
    if (q['scope_id'],q['source_epoch'],q['symbol'])!=expected:raise ValueError('Quote source mismatch')
    stamp=max(q.get('bid_at') or q['available_at'],q.get('ask_at') or q['available_at'],key=instant)
    eligible=[b for b in f.bars if instant(b['available_at'])<=instant(q['available_at']) and instant(b['close_time'])<=instant(q['available_at'])]
    if not eligible:raise ProjectionInputUnavailable('No preceding completed body before quote','WARMUP')
    b=eligible[-1];o,c=Decimal(b['open']),Decimal(b['close']);mid=(Decimal(q['bid'])+Decimal(q['ask']))/2
    side='BUY' if c<o<mid else 'SELL' if c>o>mid else None
    if side:out['markers'].append(dict(time=stamp,available_at=stamp,price=str(mid),label='Provisional previous-body quote recovery',side=side,root_ids=[digest(b),digest(q)],provisional=True,quote_basis='MID',previous_body_time=b['open_time']))
    out['metrics'].update(provisional=True,forming_ohlc_reconstructed=False,quote_time=stamp)
    return out
