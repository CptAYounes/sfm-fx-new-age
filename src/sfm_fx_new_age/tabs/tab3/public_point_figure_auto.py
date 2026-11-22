"""Causal automatic close-only P&F research profile, no fabricated intrabar path.

The public close-only/ATR/3-box and five-column horizontal-count components are
combined in an explicit engineering profile. ATR20 is frozen on the first 21
own-frame bars, rather than reboxing old columns whenever volatility changes.
This is not the discretionary tick-count interpretation or profitability proof.
"""
from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR
from typing import Any
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable

PROFILE='PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1'
SOURCES=(
 'https://chartschool.stockcharts.com/table-of-contents/chart-analysis/point-and-figure-charts/point-and-figure-basics/introduction-to-point-and-figure-charts',
 'https://chartschool.stockcharts.com/table-of-contents/chart-analysis/point-and-figure-charts/p-and-f-price-objectives/p-and-f-price-objectives-horizontal-counts')


def automatic_point_figure(f,inputs):
    from .public_algorithms import blank,marker,zone
    out=blank();bars=f.bars;tick=Decimal(str((inputs.get('spec') or {}).get('tick_size') or '0'))
    if not tick.is_finite() or tick<=0:raise ProjectionInputUnavailable('Native tick grid required for automatic P&F')
    if len(bars)<21:raise ProjectionInputUnavailable('21 original completed own-frame bars required for frozen ATR20 seed','WARMUP')
    expected=(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],inputs['frame'],inputs['authority']['origin'])
    previous=None
    for b in bars:
        if (b['scope_id'],b['source_epoch'],b['symbol'],b['timeframe'],b['origin'])!=expected:raise ValueError('P&F source/frame identity mismatch')
        if instant(b['close_time'])>instant(inputs['_evaluation_at']) or instant(b['available_at'])>instant(inputs['_evaluation_at']):raise ValueError('Future P&F bar')
        if previous is not None and instant(b['open_time'])<previous:raise ValueError('Overlapping P&F bars')
        previous=instant(b['close_time'])
    tr=[max(Decimal(bars[i]['high'])-Decimal(bars[i]['low']),abs(Decimal(bars[i]['high'])-Decimal(bars[i-1]['close'])),abs(Decimal(bars[i]['low'])-Decimal(bars[i-1]['close']))) for i in range(1,21)]
    atr=sum(tr,Decimal(0))/20
    box=max(tick,(atr/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
    floor=lambda p:int((p/box).to_integral_value(rounding=ROUND_FLOOR))
    ceil=lambda p:int((p/box).to_integral_value(rounding=ROUND_CEILING))
    columns:list[dict[str,Any]]=[];active:dict[str,Any]|None=None;events:list[dict[str,Any]]=[]
    seed=Decimal(bars[20]['close']);fired=set();known=max((b['available_at'] for b in bars[:21]),key=instant)
    seed_hash=digest([PROFILE,tick,bars[:21]])
    for i in range(21,len(bars)):
        b=bars[i];p=Decimal(b['close']);down=ceil(p);up=floor(p);known=max(known,b['available_at'],key=instant)
        # Retire objectives only from observations strictly after confirmation.
        for e in events:
            if e['state']!='ACTIVE':continue
            reached=Decimal(b['high'])>=e['target'] if e['side']=='BUY' else Decimal(b['low'])<=e['target']
            invalid=p<e['boundary'] if e['side']=='BUY' else p>e['boundary']
            if reached or invalid:e.update(state='REACHED_AND_INVALIDATED_SAME_BAR_NO_PATH_CLAIM' if reached and invalid else 'REACHED' if reached else 'INVALIDATED',retired_at=b['close_time'])
        if active is None:
            if up>=floor(seed)+1:active=dict(direction='X',low=floor(seed),high=up,start=bars[20]['close_time'],end=b['close_time'])
            elif down<=ceil(seed)-1:active=dict(direction='O',low=down,high=ceil(seed),start=bars[20]['close_time'],end=b['close_time'])
            else:continue
        elif active['direction']=='X':
            if up>active['high']:active.update(high=up,end=b['close_time'])
            elif down<=active['high']-3:
                columns.append(dict(active));active=dict(direction='O',low=down,high=active['high']-1,start=b['close_time'],end=b['close_time'])
        else:
            if down<active['low']:active.update(low=down,end=b['close_time'])
            elif up>=active['low']+3:
                columns.append(dict(active));active=dict(direction='X',low=active['low']+1,high=up,start=b['close_time'],end=b['close_time'])
        if len(columns)<4 or len(columns) in fired:continue
        a,b1,c,d=columns[-4:];side=None
        if active['direction']=='X' and a['direction']==c['direction']=='X' and a['high']==c['high'] and active['high']>a['high']:side='BUY'
        elif active['direction']=='O' and a['direction']==c['direction']=='O' and a['low']==c['low'] and active['low']<a['low']:side='SELL'
        if side is None:continue
        fired.add(len(columns));pattern=[a,b1,c,d,active]
        low=Decimal(min(v['low'] for v in pattern))*box;high=Decimal(max(v['high'] for v in pattern))*box
        extent=box*3*5;target=low+extent if side=='BUY' else high-extent
        if target<=0:continue
        consumed=Decimal(b['high'])>=target if side=='BUY' else Decimal(b['low'])<=target
        e=dict(side=side,target=target,boundary=low if side=='BUY' else high,available_at=known,confirmed_at=b['close_time'],count_start=a['start'],count_end=b['close_time'],count_line=str(Decimal(a['high'] if side=='BUY' else a['low'])*box),count_columns=5,extension=str(extent),state='ALREADY_OBSERVED_BY_CONFIRMATION' if consumed else 'ACTIVE')
        events.append(e)
        marker(out,f,i,'P&F close-only triple '+('top breakout' if side=='BUY' else 'bottom breakdown'),side,available=known,roots=(seed_hash,digest(b)))
    for e in [v for v in events if v['state']=='ACTIVE'][-16:]:
        zone(out,f,len(bars)-1,float(e['target']),float(e['target']),'P&F auto close-only 5-column objective',e['side'],available=e['available_at'],roots=(seed_hash,digest({k:str(v) for k,v in e.items()})))
        out['zones'][-1].update(confirmed_at=e['confirmed_at'],count_start=e['count_start'],count_end=e['count_end'],box_size=str(box),count_columns=5)
    out['metrics'].update(profile=PROFILE,price_method='ORIGINAL_COMPLETED_CLOSE_ONLY',source_frame=inputs['frame'],atr_period=20,seed_at=bars[20]['close_time'],seed_atr=str(atr),box_size=str(box),reversal_boxes=3,box_frozen=True,native_tick_size=str(tick),completed_columns=len(columns),developing_column_excluded_from_completed_count=True,pattern_width_includes_breakout_column=True,columns=[dict(v,complete=True) for v in columns[-63:]]+([dict(active,complete=False)] if active else []),pattern_count=len(events),active_objectives=sum(v['state']=='ACTIVE' for v in events),events=[{k:str(v) if isinstance(v,Decimal) else v for k,v in e.items()} for e in events[-32:]],settings_authority='VERSIONED_AUTOMATIC_RESEARCH_PROFILE_AUTHORIZED_BY_TASK_NOT_MANUAL_OPERATOR_CHOICES',intrabar_sequence_inferred=False,execution_volume_used=False,sources=list(SOURCES),finite_window_reconstruction=True,no_setup_reason='No confirmed five-column triple breakout with an unconsumed objective' if not out['zones'] else '')
    out['metrics'].update(input_origin=inputs['authority']['origin'],source_kind='NATIVE_COMPLETED_BARS',source_unit='OBSERVED_COMPLETED_PRICE',source_evidence_hash=digest([PROFILE,bars,tick]))
    out['markers']=out['markers'][-32:]
    return out
