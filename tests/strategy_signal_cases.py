"""Labelled SYNTHETIC source scenarios; no fake connected-source receipts."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal as D
from sfm_fx_new_age.contracts.domain import Bar,Origin,record,instant
from sfm_fx_new_age.contracts.public_strategies import BY_KEY
from sfm_fx_new_age.contracts.strategy_signals import POLICIES
from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
from sfm_fx_new_age.tabs.tab3.public_features import Features
from sfm_fx_new_age.services.scanner import confirmed_swings
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,stamp
from test_public_strategies import bars,EPOCH
from test_document_public_strategies import (ob_shape,sweep_shape,breakout_shape,fvg_shape,trend_shape,breaker_shape,
    mitigation_shape,inducement_shape,compression_shape,break_confirmation_shape,wyckoff_shape,waypoint,mirror,context,ancestor)
from test_public_genuine_inputs import optional_case

SHAPES={
 'mss':sweep_shape(),'sweep_reversal':sweep_shape(),'pool_rejection':sweep_shape(),'sweep_context':sweep_shape(),
 'pool_breakout':breakout_shape(),'compression_retest':compression_shape(),'break_confirmation':break_confirmation_shape(),
 'breaker':breaker_shape(),'mitigation_block':mitigation_shape(),'inducement':inducement_shape(),
 'liquidity_void':[(1.1,1.101,1.099,1.1)]*15+[(1.1,1.111,1.099,1.11),(1.11,1.121,1.109,1.12),(1.12,1.131,1.119,1.13),(1.125,1.134,1.115,1.132)],
 'previous_body':[(1.1,1.102,1.09,1.095),(1.098,1.106,1.097,1.105)],
 'range_rotation':[(1.1,1.12 if i%4==0 else 1.115,1.08 if i%4==2 else 1.085,1.1) for i in range(60)]+[(1.08,1.086,1.079,1.085),(1.085,1.091,1.083,1.089)],
 'wyckoff_spring_test':wyckoff_shape(),'wyckoff_break_retest':wyckoff_shape(),'wyckoff_phase':wyckoff_shape(),
 'wyckoff_utad_test':mirror(wyckoff_shape()),'wyckoff':wyckoff_shape(),
 'trend_ob':trend_shape(),'trend_fvg':fvg_shape(),'smc_zone_retest':trend_shape(),
 'previous_day_sweep':sweep_shape(),'previous_day_breakout':breakout_shape(),
 'compression':[(1.1,1.15,1.05,1.1)]+compression_shape(),'displacement':ob_shape(),'order_block':ob_shape(),
 'pullback_ob':trend_shape(),'structure':ob_shape(),
 'engulfing':[(1.1,1.101,1.09,1.095),(1.094,1.103,1.093,1.102)],
 'pinbar':[(1.1,1.102,1.08,1.101)],
 'inside_break':[(1.1,1.12,1.08,1.11),(1.11,1.115,1.09,1.10),(1.10,1.13,1.10,1.125)],
 'pullback_fvg':[(1.1,1.11,1.09,1.1),(1.1,1.14,1.099,1.13),(1.13,1.15,1.12,1.14),(1.13,1.14,1.115,1.135)],
 'liquidity':ob_shape()[:-1]+[(1.099,1.106,1.099,1.104)],
 'previous_body_retest':[(1.1,1.102,1.09,1.095),(1.098,1.107,1.097,1.106),(1.104,1.109,1.099,1.108)],
 'trend_persistence':[1.1+(.001 if i>=30 else 0)*(i-29) for i in range(80)],
 'candle_pressure':[(1.101,1.102,1.099,1.1)]*20+[(1.1,1.102,1.099,1.101)]*20,
 'harmonic_prz':waypoint([1.3,1.2,1.25,1.15])+[(1.155,1.20,1.149,1.19),(1.19,1.275,1.18,1.27)],
 'macro_elliott':waypoint([1.3,1.2,1.25,1.15])+[(1.19,1.195,1.18,1.185),(1.185,1.28,1.185,1.275),(1.26,1.28,1.19,1.27)],
 'elliott_impulse':waypoint([1,1.1,1.05,1.25,1.15,1.3]),'elliott_abc':waypoint([1.3,1.2,1.25,1.15]),
 'abcd':waypoint([1.3,1.2,1.25,1.15]),'gartley':waypoint([1.0,1.1,1.0382,1.0832,1.0214]),
 'bat':waypoint([1.0,1.1,1.051,1.0755,1.0114]),'butterfly':waypoint([1.1,1.2,1.1214,1.17,1.073]),
}


# Distinct valid price paths for reward-qualified test scenarios. No policy
# output is mocked and no observed-market input is edited by these fixtures.
SHAPES['sweep_context'][21]=(1.098,1.102,1.094,1.1)
SHAPES['wyckoff'][22]=(1.089,1.105,1.081,1.1)
for key in ('wyckoff_spring_test','wyckoff_utad_test'):
    scenario=wyckoff_shape();scenario[22]=(1.089,1.105,1.081,1.1);scenario[23]=(1.083,1.112,1.082,1.106)
    SHAPES[key]=mirror(scenario) if key=='wyckoff_utad_test' else scenario
SHAPES['macro_elliott'][-1]=(1.195,1.28,1.19,1.27)
SHAPES['harmonic_prz'][-1]=(1.16,1.275,1.159,1.26)


def append_bar(rows,values):
    frame=rows[-1]['timeframe'];duration={'W1':timedelta(weeks=1),'D1':timedelta(days=1),'H4':timedelta(hours=4),'H1':timedelta(hours=1)}[frame]
    opened=rows[-1]['close_time'];closed=stamp(instant(opened)+duration)
    o,h,l,c=map(D,map(str,values))
    return rows+[record(Bar('EURUSD',frame,opened,closed,closed,o,h,l,c,EPOCH,Origin.SYNTHETIC_FIXTURE))]


def case(key):
    policy=POLICIES[key];shape=deepcopy(SHAPES.get(key));supports={};data=None
    if shape is not None and len(shape)<BY_KEY[key].warmup:
        shape=[(1.1,1.101,1.099,1.1)]*(BY_KEY[key].warmup-len(shape)+5)+shape
    own=bars(shape) if shape is not None else bars(n=240)
    if key in {'trend_ob','trend_fvg','smc_zone_retest','macro_elliott'}:supports=ancestor(own)
    if key=='macro_elliott':supports['W1']=bars([(1.5,2.1,1.1,1.5)]*20,frame='W1',end=own[0]['open_time'])
    if key in {'previous_day_sweep','previous_day_breakout'}:supports={'D1':bars([(1.1,1.105,1.095,1.1)],frame='D1',end=own[0]['open_time'])}
    if key=='previous_body_retest':supports={'D1':bars([(1.097,1.099,1.096,1.098)],frame='D1',end=own[0]['open_time'])}
    if key in {'session_sweep','session_breakout'}:
        shape=deepcopy(sweep_shape() if key=='session_sweep' else breakout_shape())
        for i in range(6):shape[i]=(1.1,1.105,1.095,1.1)
        own=bars(shape,frame='H1',end=stamp(instant('2026-11-04T00:00:00Z')+timedelta(hours=len(shape))))
    if key in {'volume_displacement','effort_result','cause_effect','profile_tpo','volume_profile','vwap_bands','dom_imbalance','footprint_delta','cot_macro','calendar_context'}:
        own,_,_,data=optional_case(key)
        data=deepcopy(data);data['valid_until']=stamp(instant(FIXTURE_NOW)+timedelta(days=3))
        if key in {'cause_effect','cot_macro','calendar_context'}:
            own=bars([(1.1,1.11,1.08,1.09)]*90)
            own=append_bar(own,(1.09,1.12,1.085,1.115))
        elif key in {'dom_imbalance','footprint_delta'}:
            own=bars([(1.1,1.101,1.099,1.1)]*88+[(1.1,1.11,1.08,1.09),(1.09,1.12,1.085,1.115)])
    if key=='previous_body_live':own=bars([(1.1,1.102,1.09,1.095)]*30)
    if key=='regime_context':
        own=bars([(1.3-i*.001,1.301-i*.001,1.298-i*.001,1.299-i*.001) for i in range(100)])
        last=own[-1];o=D(last['open']);own=append_bar(own,(o-D('.001'),o+D('.003'),o-D('.002'),o+D('.002')))
    if policy.trigger in {'PRIOR_LEVEL_RESPONSE','WAVE_RESPONSE','TRAIL_CROSS'}:
        if key=='fvg':own=bars([(1.1,1.101,1.099,1.1)]*25+[(1.1,1.11,1.09,1.1),(1.1,1.14,1.099,1.13),(1.13,1.15,1.12,1.14)])
        if key=='elliott_alternatives':own=bars(waypoint([1.3,1.2,1.25,1.15]))
        if key in {'session_asia','session_london','session_new_york','killzones'}:
            own=bars([1.1]*240);supports['H1']=bars(n=120,frame='H1')
        if key=='rolling_extremes':supports['W1']=bars(n=120,frame='W1',end=own[0]['open_time'])
        if key in {'previous_extremes','open_midpoint'}:supports.update({fr:bars(n=20,frame=fr,end=own[0]['open_time']) for fr in ('D1','W1')})
        inputs,deps=context(own,supports=supports)
        if data:inputs['optional_evidence']={data['kind']:data}
        out=evaluate(key,Features(own,confirmed_swings(own)),inputs,deps)
        if policy.trigger=='TRAIL_CROSS':
            boundary=D(next(s for s in out['series'] if 'short' in s['label'].lower())['points'][-1]['price']);old=D(own[-1]['close'])
            own=append_bar(own,(old,boundary+D('.01'),min(old,boundary)-D('.001'),boundary+D('.005')))
        else:
            candidates=[z for z in out['zones'] if z['state'] in {'CONFIRMED','TOUCHED'}]
            assert candidates,(key,'No prior source geometry',out)
            z=candidates[-1];lo,hi=D(z['low']),D(z['high']);delta=max(D('.0001'),(hi-lo)/10)
            if z['side']=='SELL':values=(lo+delta,hi+delta,lo-3*delta,lo-2*delta)
            else:values=(hi-delta,hi+3*delta,min(lo,hi-delta)-delta,hi+2*delta)
            own=append_bar(own,values)
    # Choose an actual emitted event's causal prefix, not a hand-authored signal.
    if policy.trigger=='LATEST_DIRECTIONAL_EVENT':
        inputs,deps=context(own,supports=supports)
        if data:inputs['optional_evidence']={data['kind']:data}
        out=evaluate(key,Features(own,confirmed_swings(own)),inputs,deps)
        directional=[m for m in out['markers'] if m['side'] in {'BUY','SELL'}]
        assert directional,(key,'Actual method has no positive scenario')
        marker=max(directional,key=lambda m:instant(m['available_at']))
        own=[b for b in own if instant(b['available_at'])<=instant(marker['available_at'])]
    return own,supports,data,own[-1]['available_at']


def with_observed_target(own,supports):
    """Additional labelled historical weekly pivot, not a generated objective."""
    supports=deepcopy(supports)
    weekly=supports.get('W1') or bars([1.1]*20,frame='W1',end=own[0]['open_time'])
    prelude=bars([(1.2,1.21,1.19,1.2)]*2+[(1.2,3.0,.1,1.2)]+[(1.2,1.21,1.19,1.2)]*2,
                 frame='W1',end=weekly[0]['open_time'])
    supports['W1']=prelude+weekly
    return supports
