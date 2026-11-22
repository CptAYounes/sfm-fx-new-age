"""Independent document roster and causal public-model behavior, labelled fixtures."""
import json,math
from pathlib import Path
from importlib.resources import files
from datetime import timedelta
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
import pytest
from sfm_fx_new_age.contracts.public_strategies import METHODS,BY_KEY
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from sfm_fx_new_age.contracts.domain import Bar,Origin,FRAMES,PAIRS,record,instant,Quote
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.services.scanner import confirmed_swings
from sfm_fx_new_age.tabs.tab3.order_blocks import detect_structure,PROFILE
from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
from sfm_fx_new_age.tabs.tab3.public_features import Features
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,stamp,fixture_runtime
from test_public_strategies import bars,seed,enable,chart,EPOCH

SCOPE=json.loads(files('sfm_fx_new_age.contracts.data').joinpath('public_document_requirements.json').read_text())
INITIAL=set(SCOPE['retained_initial_catalogue_ids'])
NEW=set(SCOPE['required_method_ids'])-INITIAL


def ob_shape():
    return [(1.1,1.101,1.099,1.1)]*15+[(1.1,1.105,1.099,1.101),(1.1,1.1015,1.099,1.1),(1.1,1.101,1.099,1.1),(1.1,1.101,1.0985,1.099),(1.099,1.109,1.099,1.108)]


def sweep_shape():
    return ob_shape()[:18]+[(1.1,1.101,1.095,1.098),(1.098,1.101,1.098,1.1),(1.1,1.101,1.097,1.099),(1.099,1.102,1.094,1.1),(1.1,1.112,1.1,1.111),(1.11,1.112,1.1,1.111)]


def breakout_shape():return ob_shape()+[(1.108,1.113,1.107,1.111),(1.109,1.113,1.104,1.112)]


def fvg_shape():
    shape=ob_shape()[:19]+[(1.099,1.1045,1.099,1.104),(1.105,1.12,1.105,1.119),(1.11,1.12,1.103,1.119)]
    shape[4]=(1.1,1.14,1.099,1.1) # Genuine earlier unconsumed opposing objective.
    return shape


def trend_shape():
    shape=ob_shape()+[(1.108,1.112,1.1005,1.11)]
    shape[4]=(1.1,1.14,1.099,1.1)
    return shape


def breaker_shape():
    return ob_shape()+[(1.108,1.1085,1.104,1.107),(1.107,1.108,1.103,1.106),(1.106,1.111,1.105,1.107),(1.107,1.108,1.095,1.096),(1.098,1.1005,1.094,1.0955)]


def mitigation_shape():
    return [(1.1,1.101,1.099,1.1)]*15+[(1.11,1.12,1.1,1.115),(1.115,1.116,1.105,1.11),(1.11,1.114,1.1,1.105),(1.105,1.106,1.09,1.095),(1.095,1.108,1.095,1.105),(1.105,1.11,1.102,1.108),(1.108,1.115,1.105,1.113),(1.108,1.11,1.1,1.105),(1.105,1.109,1.101,1.106),(1.106,1.107,1.08,1.082),(1.09,1.107,1.08,1.085)]


def inducement_shape():
    return ob_shape()+[(1.108,1.112,1.106,1.11),(1.11,1.111,1.105,1.108),(1.108,1.110,1.103,1.107),(1.107,1.111,1.106,1.109),(1.109,1.112,1.107,1.11),(1.11,1.112,1.102,1.108),(1.107,1.111,1.100,1.109)]


def compression_shape():
    return [(1.1,1.15,1.05,1.1)]*30+[(1.1,1.105,1.095,1.1)]*10+[(1.1,1.161,1.099,1.16),(1.16,1.17,1.155,1.166),(1.12,1.133,1.104,1.13)]


def break_confirmation_shape():
    return [(1.1,1.105,1.095,1.1)]*30+[(1.1,1.13,1.099,1.129),(1.129,1.14,1.125,1.132),(1.12,1.133,1.104,1.13),(1.13,1.14,1.129,1.137)]


def wyckoff_shape():
    return [(1.1,1.12 if i%4==0 else 1.115,1.08 if i%4==2 else 1.085,1.1) for i in range(21)]+[(1.09,1.101,1.075,1.095),(1.095,1.105,1.081,1.1),(1.1,1.112,1.09,1.11),(1.11,1.151,1.109,1.15),(1.15,1.155,1.14,1.145),(1.13,1.151,1.119,1.14),(1.14,1.16,1.13,1.157)]


def waypoint(prices):
    sign=1 if prices[1]>prices[0] else -1;values=[prices[0]+sign*.02,prices[0]+sign*.01];previous=values[-1]
    for target in prices:
        values.extend(previous+(target-previous)*j/5 for j in range(1,6));previous=target
    tail=-1 if prices[-1]>prices[-2] else 1;values.extend(previous+tail*.01*j for j in range(1,5))
    return [(v,v+.00001,v-.00001,v) for v in values]


def mirror(shape):return [(3-o,3-l,3-h,3-c) for o,h,l,c in shape]


def native_deps(mapping):
    swings={fr:confirmed_swings(rows) for fr,rows in mapping.items()}
    events={fr:detect_structure(rows,swings[fr],PROFILE['parameters']) for fr,rows in mapping.items()}
    return {'SWING_MAP':{'state':'READY','output':swings},'SMC_STRUCTURE':{'state':'READY','output':events}}


def context(rows,*,supports=None):
    frame=rows[0]['timeframe'];mapping={frame:rows,**(supports or {})};deps=native_deps(mapping)
    return dict(frame=frame,bars=mapping,spec={'tick_size':'.00001','pip_size':'.0001'},scope_id=rows[0]['scope_id'],symbol='EURUSD',
                authority=dict(source_epoch=EPOCH,origin='SYNTHETIC_FIXTURE'),_evaluation_at=FIXTURE_NOW,quote=None,quote_usable=False,optional_evidence={}),deps


def calculate(key,shape,*,supports=None,frame='H4',end=FIXTURE_NOW):
    rows=bars(shape,frame=frame,end=end);inputs,deps=context(rows,supports=supports)
    return evaluate(key,Features(rows,deps['SWING_MAP']['output'][frame]),inputs,deps),rows,inputs,deps


def ancestor(rows,shape=None):
    end=rows[0]['open_time']
    return {fr:bars(shape or ob_shape(),frame=fr,end=end) for fr in ('D1','W1')}


def test_independent_document_denominator_is_complete_not_registry_derived():
    assert len(SCOPE['requirements'])==91 and len(SCOPE['expected_catalogue_ids'])==83
    assert set(BY_KEY)==set(SCOPE['expected_catalogue_ids'])
    assert len(SCOPE['retained_initial_catalogue_ids'])==32
    assert set(SCOPE['required_method_ids'])=={m for r in SCOPE['requirements'] for m in r['method_ids']}
    assert len({r['requirement_id'] for r in SCOPE['requirements']})==91
    assert not SCOPE['unresolved_identities']
    assert {r['requirement_id'] for r in SCOPE['requirements'] if r['requirement_id'].startswith('M')}=={f'M{i:02}' for i in range(1,44)}
    assert {r['requirement_id'] for r in SCOPE['requirements'] if r['requirement_id'].startswith('R0')}=={f'R0{i}' for i in range(1,9)}
    assert all(r['method_ids'] or r['kind'] in {'SUPPORT_OR_LOCAL_MANAGEMENT_NOT_ENTRY','AUTHORING_PRIMITIVE_NOT_STRATEGY'} for r in SCOPE['requirements'])
    missing=set(SCOPE['expected_catalogue_ids'])-set(list(BY_KEY)[:-1]);assert missing


@pytest.mark.parametrize('key,shape',[
 ('mss',sweep_shape()),('sweep_reversal',sweep_shape()),('pool_rejection',sweep_shape()),('sweep_context',sweep_shape()),
 ('pool_breakout',breakout_shape()),('compression_retest',compression_shape()),('break_confirmation',break_confirmation_shape()),
 ('breaker',breaker_shape()),('mitigation_block',mitigation_shape()),('inducement',inducement_shape()),
 ('liquidity_void',[(1.1,1.101,1.099,1.1)]*15+[(1.1,1.111,1.099,1.11),(1.11,1.121,1.109,1.12),(1.12,1.131,1.119,1.13),(1.125,1.134,1.115,1.132)]),
 ('previous_body',[(1.1,1.102,1.09,1.095),(1.098,1.106,1.097,1.105)]),
 ('range_rotation',[(1.1,1.12 if i%4==0 else 1.115,1.08 if i%4==2 else 1.085,1.1) for i in range(60)]+[(1.08,1.086,1.079,1.085),(1.085,1.091,1.083,1.089)]),
 ('wyckoff_spring_test',wyckoff_shape()),('wyckoff_break_retest',wyckoff_shape()),
 ])
def test_named_price_model_positive_mirror_and_no_retrospective_retest(key,shape):
    result,rows,inputs,deps=calculate(key,shape)
    assert result['markers'],(key,result,confirmed_swings(rows))
    inverse_key='wyckoff_utad_test' if key=='wyckoff_spring_test' else key
    inverse,_,_,_=calculate(inverse_key,mirror(shape));assert inverse['markers'],inverse_key
    sides={m['side'] for m in result['markers']};assert {'SELL' if s=='BUY' else 'BUY' for s in sides}=={m['side'] for m in inverse['markers']}
    for event in result['markers']:
        assert event['root_ids'];assert instant(event['time'])<=instant(event['available_at'])
        if 'stages' in event:
            clocks=[instant(s['time']) for s in event['stages']];assert clocks==sorted(clocks)
            assert clocks[-1]==instant(event['time'])
    if key not in {'mss','sweep_context','previous_body','liquidity_void'}:
        short=calculate(key,shape[:-1],end=rows[-2]['close_time'])[0]
        # If earlier valid episodes exist they remain, but the removed last-bar episode cannot.
        assert not any(m['time']==rows[-1]['close_time'] for m in short['markers'])


def test_utad_phase_and_range_hypotheses_are_explicit_not_volume_truth():
    out,_,_,_=calculate('wyckoff_utad_test',mirror(wyckoff_shape()));assert out['markers']
    phase,rows,_,_=calculate('wyckoff_phase',wyckoff_shape())
    assert phase['metrics']['phase']=='E' and phase['metrics']['volume_confirmed'] is False
    assert {'B','C','D','E'}<={m['label'].split()[1] for m in phase['markers']}


@pytest.mark.parametrize('key,shape',[('trend_ob',trend_shape()),('trend_fvg',fvg_shape()),('smc_zone_retest',trend_shape())])
def test_real_shared_structure_and_distinct_zone_origin_for_pullbacks(key,shape):
    rows=bars(shape);supports=ancestor(rows)
    out,rows,inputs,deps=calculate(key,shape,supports=supports)
    assert deps['SMC_STRUCTURE']['output']['H4'] and deps['SMC_STRUCTURE']['output']['D1']
    assert out['markers'],(key,out)
    assert all(('OB' if key!='trend_fvg' else 'FVG') in m['label'] for m in out['markers'])
    if key.startswith('trend_'):
        bad=deepcopy(deps);bad['SMC_STRUCTURE']['output']['D1']=[]
        assert not evaluate(key,Features(rows,confirmed_swings(rows)),inputs,bad)['markers']
        with pytest.raises(ProjectionInputUnavailable):calculate(key,shape)


@pytest.mark.parametrize('key,shape',[('previous_day_sweep',sweep_shape()),('previous_day_breakout',breakout_shape())])
def test_daily_models_freeze_prior_available_day_not_future_day(key,shape):
    rows=bars(shape);day=bars([(1.1,1.105,1.095,1.1)],frame='D1',end=rows[0]['open_time'])
    out,_,_,_=calculate(key,shape,supports={'D1':day});assert out['markers'],out
    later=bars([(1.5,1.6,1.4,1.5)],frame='D1',end=FIXTURE_NOW)
    with_future,_,_,_=calculate(key,shape,supports={'D1':day+later})
    assert out['markers']==with_future['markers']
    with pytest.raises(ProjectionInputUnavailable):calculate(key,shape)


def test_previous_body_retest_is_not_engulfing_and_requires_htf_overlap():
    shape=[(1.1,1.102,1.09,1.095),(1.098,1.107,1.097,1.106),(1.104,1.109,1.099,1.108)]
    rows=bars(shape);day=bars([(1.097,1.099,1.096,1.098)],frame='D1',end=rows[0]['open_time'])
    out,_,_,_=calculate('previous_body_retest',shape,supports={'D1':day});assert out['markers']
    assert not calculate('engulfing',shape)[0]['markers']


@pytest.mark.parametrize('key',['session_asia','session_london','session_new_york','killzones'])
def test_named_complete_sessions_and_timezone_metadata(key):
    rows=bars(n=120,frame='H1');own=bars(n=20)
    inputs,deps=context(own,supports={'H1':rows});out=evaluate(key,Features(own,confirmed_swings(own)),inputs,deps)
    assert out['zones'] and out['metrics']['source_timeframe']=='H1'
    assert all(z['session_timezone'] and z['observed_h1_bars']>0 and z['root_ids'] for z in out['zones'])


def test_session_dst_and_incomplete_support_rejection():
    from sfm_fx_new_age.tabs.tab3.public_sessions import completed_windows,SESSION_WINDOWS
    winter=bars(n=24,frame='H1',end='2026-11-05T00:00:00Z');summer=bars(n=24,frame='H1',end='2026-07-02T00:00:00Z')
    w,_=completed_windows(winter,SESSION_WINDOWS['session_london']);s,_=completed_windows(summer,SESSION_WINDOWS['session_london'])
    assert instant(w[0]['open_time']).hour==8 and instant(s[0]['open_time']).hour==7
    broken=[r for r in winter if instant(r['open_time']).hour!=10];found,missing=completed_windows(broken,SESSION_WINDOWS['session_london']);assert not found and missing==1
    shifted=[dict(r,open_time=stamp(instant(r['open_time'])+timedelta(minutes=15)),close_time=stamp(instant(r['close_time'])+timedelta(minutes=15)),available_at=stamp(instant(r['available_at'])+timedelta(minutes=15))) for r in winter]
    assert not completed_windows(shifted,SESSION_WINDOWS['session_london'])[0]


@pytest.mark.parametrize('key,shape',[('session_sweep',sweep_shape()),('session_breakout',breakout_shape())])
def test_session_models_use_completed_h1_ranges_then_ordered_responses(key,shape):
    shape=list(shape)
    for i in range(6):shape[i]=(1.1,1.105,1.095,1.1)
    rows=bars(shape,frame='H1',end=stamp(instant('2026-11-04T00:00:00Z')+timedelta(hours=len(shape))))
    inputs,deps=context(rows);out=evaluate(key,Features(rows,confirmed_swings(rows)),inputs,deps)
    assert out['markers'],(key,out)
    assert all(m['source_timeframe']=='H1' for m in out['markers'])


def test_elliott_alternatives_and_harmonic_prz_need_later_response():
    shape=waypoint([1.3,1.2,1.25,1.15]);out,_,_,_=calculate('elliott_alternatives',shape)
    assert out['metrics']['competing_counts'] and out['zones']
    assert not calculate('harmonic_prz',shape)[0]['markers']
    shape+=[(1.155,1.20,1.149,1.19),(1.19,1.275,1.18,1.27)]
    out,_,_,_=calculate('harmonic_prz',shape);assert out['markers'],out
    assert all([s['stage'] for s in m['stages']]==['PIVOTS_AND_PRZ_KNOWN','LATER_ZONE_RESPONSE','INDEPENDENT_STRUCTURE_BREAK'] for m in out['markers'])


def test_macro_waves_cannot_create_setup_without_linked_structure():
    shape=waypoint([1.3,1.2,1.25,1.15]);shape+=[(1.19,1.195,1.18,1.185),(1.185,1.28,1.185,1.275),(1.26,1.28,1.19,1.27)]
    rows=bars(shape);supports=ancestor(rows);supports['W1']=bars([(1.5,2.1,1.1,1.5)]*20,frame='W1',end=rows[0]['open_time'])
    out,_,_,_=calculate('macro_elliott',shape,supports=supports);assert out['markers'],out
    no_link,_,_,_=calculate('macro_elliott',shape[:-3],supports=supports);assert not no_link['markers']


@pytest.mark.parametrize('key',['displacement','liquidity_pools','candle_pressure','regime_context','trend_persistence','atr_trail','rolling_extremes','round_numbers'])
def test_other_public_context_algorithms_have_nonempty_bounded_outputs(key):
    if key=='displacement':shape=ob_shape()
    elif key=='trend_persistence':shape=[1.1+(.001 if i>=30 else 0)*(i-29) for i in range(80)]
    elif key=='candle_pressure':shape=[(1.101,1.102,1.099,1.1)]*20+[(1.1,1.102,1.099,1.101)]*20
    else:shape=None
    rows=bars(shape) if shape is not None else bars()
    inputs,deps=context(rows,supports={'W1':bars(n=120,frame='W1')})
    out=evaluate(key,Features(rows,confirmed_swings(rows)),inputs,deps)
    assert any(out[k] for k in ('markers','zones','series')),(key,out)
    assert len(out['markers'])<=32 and len(out['zones'])<=16


@pytest.mark.parametrize('key',sorted(NEW))
def test_every_new_method_no_unhandled_dispatch_and_missing_inputs_are_not_no_setup(key):
    rows=bars();inputs,deps=context(rows,supports={fr:bars(frame=fr) for fr in ('W1','D1','H1')})
    try:out=evaluate(key,Features(rows,confirmed_swings(rows)),inputs,deps)
    except ProjectionInputUnavailable as exc:
        assert BY_KEY[key].data_kind or key in {'session_asia','session_london','session_new_york','session_sweep','session_breakout','killzones'}
        assert exc.reason and exc.state in {'DATA_UNAVAILABLE','WARMUP'}
    else:assert set(out)=={'markers','zones','series','metrics'}


@pytest.mark.parametrize('key',['sweep_reversal','pool_rejection','mss','compression_retest','break_confirmation','breaker','mitigation_block','inducement','range_rotation','wyckoff_spring_test','wyckoff_utad_test','wyckoff_break_retest','harmonic_prz'])
def test_flat_market_does_not_invent_composed_entries(key):
    assert not calculate(key,[(1.1,1.101,1.099,1.1)]*100)[0]['markers']


@pytest.mark.parametrize('key',sorted(NEW-{m.key for m in METHODS if m.data_kind}))
def test_document_family_causal_prefix_and_known_at_emission(key):
    # All bars keep their original timestamps when shortened; future support is
    # filtered at the same core availability boundary as the production scanner.
    rows=bars(n=240);supports={fr:bars(frame=fr) for fr in ('W1','D1','H1')}
    inputs,deps=context(rows,supports=supports);full=evaluate(key,Features(rows,confirmed_swings(rows)),inputs,deps)
    for count in (max(BY_KEY[key].warmup,60),180,239):
        prefix=rows[:count];cutoff=prefix[-1]['available_at']
        available={fr:[b for b in bs if instant(b['available_at'])<=instant(cutoff)] for fr,bs in supports.items()}
        scoped,dependency=context(prefix,supports=available);scoped['_evaluation_at']=cutoff
        try:part=evaluate(key,Features(prefix,confirmed_swings(prefix)),scoped,dependency)
        except ProjectionInputUnavailable:continue
        for marker in part['markers']:
            assert instant(marker['time'])<=instant(marker['available_at'])<=instant(cutoff)
            assert all(instant(s['time'])<=instant(cutoff) for s in marker.get('stages',()))
        for group in ('zones','markers'):
            assert all(instant(r['available_at'])<=instant(cutoff) for r in part[group])
        for line in part['series']:
            assert all(instant(p['time'])<=instant(p['available_at'])<=instant(cutoff) for p in line['points'])
        past=[m for m in full['markers'] if instant(m['available_at'])<=instant(cutoff)]
        assert all(m in part['markers'] for m in past),(key,count,past,part)


@pytest.mark.parametrize('prices,label',[
 ([1.3,1.2,1.25,1.15],'AB=CD'),
 ([1.0,1.1,1.0382,1.0832,1.0214],'Gartley'),
 ([1.0,1.1,1.051,1.0755,1.0114],'Bat'),
 ([1.1,1.2,1.1214,1.17,1.073],'Butterfly')])
def test_each_document_harmonic_prz_family_and_far_edge_invalidation(prices,label):
    shape=waypoint(prices);d=prices[-1]
    shape+=[(d+.0002,d+.03,d-.00001,d+.02),(d+.02,max(prices)+.06,d+.01,max(prices)+.05)]
    out,_,_,_=calculate('harmonic_prz',shape)
    assert any(m['label'].startswith(label+' PRZ') for m in out['markers']),(label,out)
    inverse=calculate('harmonic_prz',mirror(shape))[0]
    assert any(m['label'].startswith(label+' PRZ') and m['side']=='SELL' for m in inverse['markers'])
    failed=waypoint(prices)+[(d,d+.001,d-.02,d-.015)]+shape[-2:]
    out,_,_,_=calculate('harmonic_prz',failed)
    assert not any(m['label'].startswith(label+' PRZ') for m in out['markers'])


def test_range_rotation_does_not_project_an_already_traded_midpoint():
    shape=[(1.1,1.12 if i%4==0 else 1.115,1.08 if i%4==2 else 1.085,1.1) for i in range(60)]+[(1.08,1.101,1.079,1.085),(1.085,1.106,1.083,1.105)]
    assert not calculate('range_rotation',shape)[0]['markers']
