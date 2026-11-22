"""Public algorithm conformance and real switch→source→chart integration."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import math,json
from datetime import timedelta
from decimal import Decimal as D
from dataclasses import replace
import pytest
from sfm_fx_new_age.contracts.domain import Bar,FRAMES,PAIRS,Origin,record,instant
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.public_strategies import METHODS,BY_KEY
from sfm_fx_new_age.testing.fixtures import fixture_runtime,FIXTURE_NOW,stamp
from sfm_fx_new_age.services.scanner import confirmed_swings
from sfm_fx_new_age.tabs.tab3.public_features import Features,sma,ema,cross
from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate,impulse_matches,abc_matches,harmonic_matches

EPOCH='LABELLED-PUBLIC-STRATEGY-TEST-V1'


def bars(values=None,*,n=240,frame='H4',symbol='EURUSD',end=FIXTURE_NOW):
    if values is None:values=[1.15+.03*math.sin(i/8)+.006*math.sin(i/2.1) for i in range(n)]
    duration={'W1':timedelta(weeks=1),'D1':timedelta(days=1),'H4':timedelta(hours=4),'H1':timedelta(hours=1)}[frame];out=[]
    for i,v in enumerate(values):
        closed=instant(end)-duration*(len(values)-i-1)
        if isinstance(v,(tuple,list)):o,h,l,c=map(D,map(str,v))
        else:
            c=D(str(v));o=c-D('.0001')
            h=max(o,c)+D('.0004');l=min(o,c)-D('.0004')
        out.append(record(Bar(symbol,frame,stamp(closed-duration),stamp(closed),stamp(closed),o,h,l,c,EPOCH,Origin.SYNTHETIC_FIXTURE)))
    return out


def run(key,rows,*,others=None,deps=None):
    f=Features(rows,confirmed_swings(rows));inputs={'frame':rows[-1]['timeframe'] if rows else 'H4','bars':others or {'H4':rows},'spec':{'tick_size':'.00001'}}
    return evaluate(key,f,inputs,deps or {})


def seed(path=':memory:',*,frame='H4',symbol='EURUSD',rows=None):
    r=fixture_runtime(path);r.market.activate_source(symbol,EPOCH,Origin.SYNTHETIC_FIXTURE.value)
    for row in rows or bars(frame=frame,symbol=symbol):r.market.ingest(Bar(**row))
    r.pump();return r


def enable(r,key,on=True):
    m=BY_KEY[key];result=r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=on));assert result.status.value=='ACCEPTED',result
    r.pump()


def chart(r,frame='H4',symbol='EURUSD',as_of=None):return thaw(r.api(1).query('1.4',DataRequest('chart',timeframe=frame,symbol=symbol,as_of=as_of,limit=5000)))


def test_roster_public_identity_not_brand_prefix():
    from importlib.resources import files
    scope=json.loads(files('sfm_fx_new_age.contracts.data').joinpath('public_document_requirements.json').read_text())
    assert len(METHODS)==83 and set(BY_KEY)==set(scope['expected_catalogue_ids'])
    assert len(scope['retained_initial_catalogue_ids'])==32
    assert BY_KEY['order_block'].recipe_id=='sfm.order_block.research.v1'
    assert all(m.sources and m.rules and m.warmup>0 for m in METHODS)
    assert not any(w in m.key for m in METHODS for w in ('treasury','redistribution','sltotp','nullification'))


def test_numeric_sma_ema_rsi_adx_and_no_flat_false_cross():
    values=list(map(float,range(1,71)))
    assert sma(values,20)[19]==10.5
    expected=sum(values[:20])/20
    for v in values[20:]:expected+=(v-expected)*2/21
    assert ema(values,20)[-1]==pytest.approx(expected)
    f=Features(bars(values=[1+i*.001 for i in range(70)]),())
    assert f.get('rsi')[-1]==100
    pos,neg,adx=f.get('adx');assert pos[-1]>0 and neg[-1]==0 and adx[-1]==pytest.approx(100)
    down=Features(bars(values=[2-i*.001 for i in range(70)]),());assert down.get('rsi')[-1]==0
    flat=bars(values=[1.15]*100)
    for key in ('sma_cross','ema_cross','macd','rsi','stochastic','adx','momentum','donchian','bollinger','ichimoku'):
        assert run(key,flat)['markers']==[],key


@pytest.mark.parametrize('key',['sma_cross','ema_cross','macd','rsi','stochastic','adx','bollinger','donchian','momentum','ichimoku'])
def test_real_indicators_on_oscillating_input_and_prefix_causality(key):
    rows=bars();out=run(key,rows)
    assert out['markers'],key
    assert {m['side'] for m in out['markers']}=={'BUY','SELL'}
    short=run(key,rows[:120]);short_times={m['time'] for m in short['markers']}
    from sfm_fx_new_age.tabs.tab3.public_algorithms import indicator_method
    # Compare full causal events before the deliberately bounded 32-marker display cap.
    full=indicator_method(key,Features(rows,confirmed_swings(rows)),{}, {})
    assert short_times<={m['time'] for m in full['markers'] if instant(m['time'])<=instant(rows[119]['close_time'])},key
    if key in {'macd','rsi','stochastic','adx','momentum'}:assert not out['series']


def test_donchian_excludes_current_bar_and_ichimoku_uses_displaced_past_cloud():
    rows=bars(values=[1.1]*80+[1.2]);f=Features(rows,())
    up,lo=f.get('donchian');assert up[-1]==pytest.approx(1.1004)
    assert run('donchian',rows)['markers'][-1]['side']=='BUY'
    ten,base,sa,sb=f.get('ichimoku')
    assert sa[-1]==pytest.approx((ten[-27]+base[-27])/2)
    support=f.bars[-78:-26];assert sb[-1]==pytest.approx((max(float(b['high']) for b in support)+min(float(b['low']) for b in support))/2)


@pytest.mark.parametrize('key,values,label',[
 ('engulfing',[(1.1,1.101,1.09,1.095),(1.094,1.103,1.093,1.102)],'Bull'),
 ('pinbar',[(1.1,1.102,1.08,1.101)],'Hammer'),
 ('inside_break',[(1.1,1.12,1.08,1.11),(1.11,1.115,1.09,1.10),(1.10,1.13,1.10,1.125)],'Inside')])
def test_candle_positive_and_mirrored_negative(key,values,label):
    out=run(key,bars(values));assert out['markers'] and label in out['markers'][-1]['label']
    inverse=[(2.4-o,2.4-l,2.4-h,2.4-c) for o,h,l,c in values]
    other=run(key,bars(inverse));assert other['markers'][-1]['side']!=out['markers'][-1]['side']


def test_structure_sweep_gap_and_mitigation_have_real_source_geometry():
    from test_order_block_workflow import pattern
    rows=[record(b) for b in pattern()]
    assert run('structure',rows)['markers'][-1]['side']=='BUY'
    changed=[dict(b) for b in rows];changed[-1]['high']='1.106';changed[-1]['close']='1.104'
    assert run('liquidity',changed)['markers'][-1]['side']=='SELL'
    g=bars([(1.1,1.11,1.09,1.1),(1.1,1.14,1.099,1.13),(1.13,1.15,1.12,1.14)])
    zone=run('fvg',g)['zones'][0];assert float(zone['low'])==1.11 and float(zone['high'])==1.12 and zone['state']=='CONFIRMED'
    now=instant(g[-1]['close_time'])+timedelta(hours=4)
    touched=record(Bar('EURUSD','H4',g[-1]['close_time'],stamp(now),stamp(now),D('1.13'),D('1.14'),D('1.115'),D('1.135'),EPOCH,Origin.SYNTHETIC_FIXTURE))
    g.append(touched);assert run('fvg',g)['zones'][0]['state']=='TOUCHED'
    assert run('pullback_fvg',g)['markers'][-1]['side']=='BUY'
    g[-1]=dict(touched,low='1.10',close='1.105')
    assert run('fvg',g)['zones'][0]['state']=='INVALIDATED'
    assert not run('pullback_fvg',g)['markers']


def test_order_block_pullback_uses_timestamped_existing_structure_not_replacement_producer():
    from test_order_block_workflow import seeded,enable as ob_enable,pattern
    r=seeded();ob_enable(r)
    try:
        deps=r.analytics.snapshot('EURUSD')['outputs'];rows=[record(b) for b in pattern()]
        now=instant(rows[-1]['close_time'])+timedelta(hours=4)
        rows.append(record(Bar('EURUSD','H4',rows[-1]['close_time'],stamp(now),stamp(now),D('1.10'),D('1.108'),D('1.099'),D('1.107'),rows[-1]['source_epoch'],Origin.SYNTHETIC_FIXTURE)))
        out=run('pullback_ob',rows,deps={'SMC_STRUCTURE':{'output':deps['SMC_STRUCTURE']}})
        assert out['markers'][-1]['side']=='BUY'
    finally:r.close()


def test_wyckoff_spring_utad_and_secondary_test_are_price_hypotheses():
    base=[(1.10,1.12 if i%4==0 else 1.115,1.08 if i%4==2 else 1.085,1.1) for i in range(20)]
    spring=(1.09,1.101,1.075,1.095);test=(1.095,1.105,1.081,1.10)
    out=run('wyckoff',bars(base+[spring,test]));assert any('Spring' in m['label'] for m in out['markers']);assert any('TEST' in m['label'] for m in out['markers'])
    inv=[(2.4-o,2.4-l,2.4-h,2.4-c) for o,h,l,c in base+[spring,test]]
    assert any('UTAD' in m['label'] for m in run('wyckoff',bars(inv))['markers'])
    assert not run('wyckoff',bars(values=[1.1]*25))['markers']


def points(prices):return [dict(price=str(p),kind='LOW' if i%2==0 else 'HIGH') for i,p in enumerate(prices)]


@pytest.mark.parametrize('prices,name',[
 ([1.3,1.2,1.25,1.15],'AB=CD'),
 ([1.0,1.1,1.0382,1.0832,1.0214],'Gartley'),
 ([1.0,1.1,1.05,1.08,1.0114],'Bat'),
 ([1.1,1.2,1.1214,1.17,1.073],'Butterfly')])
def test_harmonic_ratios_and_rejection(prices,name):
    assert harmonic_matches(points(prices))==name
    assert harmonic_matches(points([2.5-p for p in prices]))==name
    bad=list(prices);bad[-1]=bad[-2];assert harmonic_matches(points(bad)) is None


def test_elliott_hard_rules_reject_wave2_wave3_and_overlap():
    assert impulse_matches(points([1,1.1,1.05,1.25,1.15,1.3]))
    for p in ([1,1.1,.99,1.25,1.15,1.3],[1,1.1,1.05,1.11,1.105,1.3],[1,1.1,1.05,1.25,1.09,1.3]):assert not impulse_matches(points(p))
    assert abc_matches(points([1.3,1.2,1.25,1.15]))
    assert not abc_matches(points([1.3,1.2,1.35,1.15]))


@pytest.mark.parametrize('key,prices,label',[
 ('elliott_impulse',[1,1.1,1.05,1.25,1.15,1.3],'Impulse hypothesis'),
 ('elliott_abc',[1.3,1.2,1.25,1.15],'ABC hypothesis'),
 ('abcd',[1.3,1.2,1.25,1.15],'AB=CD'),
 ('gartley',[1.0,1.1,1.0382,1.0832,1.0214],'Gartley'),
 ('bat',[1.0,1.1,1.051,1.08,1.0114],'Bat'),
 ('butterfly',[1.1,1.2,1.1214,1.17,1.073],'Butterfly')])
def test_pattern_detectors_use_actual_confirmed_pivots_and_confirmation_availability(key,prices,label):
    def waypoint(prices):
        sign=1 if prices[1]>prices[0] else -1
        values=[prices[0]+sign*.02,prices[0]+sign*.01]
        previous=values[-1]
        for target in prices:
            values.extend(previous+(target-previous)*j/5 for j in range(1,6));previous=target
        tail=-1 if prices[-1]>prices[-2] else 1
        values.extend(previous+tail*.01*j for j in range(1,5))
        return bars([(v,v+.00001,v-.00001,v) for v in values])
    result=run(key,waypoint(prices));assert any(m['label']==label for m in result['markers'])
    assert any(instant(m['available_at'])>instant(m['time']) for m in result['markers'])


@pytest.mark.parametrize('key',['support_resistance','fibonacci','ote','previous_extremes','open_midpoint'])
def test_level_methods_use_observed_prices_and_causal_roots(key):
    rows=bars();out=run(key,rows,others={'H4':rows,'D1':rows,'W1':rows})
    assert out['zones'] and all(z['root_ids'] and 0<float(z['low'])<=float(z['high']) for z in out['zones'])
    if key=='ote':assert len(out['zones'])==2
    if key=='fibonacci':assert len(out['zones'])==4


def test_compression_has_strict_closed_breakout_not_just_small_range():
    wide=[(1.1,1.15,1.05,1.1)]*30;narrow=[(1.1,1.105,1.095,1.1)]*10
    assert not run('compression',bars(wide+narrow))['markers']
    out=run('compression',bars(wide+narrow+[(1.1,1.12,1.099,1.119)]));assert out['markers'][-1]['side']=='BUY'


@pytest.mark.parametrize('m',METHODS,ids=lambda m:m.key)
def test_each_method_has_independent_effective_switch_and_scoped_chart_output(m):
    r=seed()
    try:
        assert not chart(r)['strategy_layers'];enable(r,m.key)
        layers=chart(r)['strategy_layers'];assert {x['strategy_id'] for x in layers}=={m.key}
        body=layers[0]
        expected={'DATA_UNAVAILABLE'} if m.data_kind and m.key!='cause_effect' or m.input_frames and m.key!='rolling_extremes' else {'WARMUP'} if m.key=='rolling_extremes' else {'READY','NO_SETUP'}
        assert body['state'] in expected,(m.key,body['state'],body['reason'])
        assert (body['scope_id'],body['source_epoch'],body['symbol'],body['timeframe'])==(r.market.scope_id,EPOCH,'EURUSD','H4')
        assert body['classification']=='UNCALIBRATED_PROJECTION_ONLY'
        assert r.analytics.projections.runs.get(m.key,0)>0
        before=dict(r.analytics.projections.runs);r.analytics.refresh('EURUSD');assert r.analytics.projections.runs==before
        enable(r,m.key,False);assert not chart(r)['strategy_layers']
        assert not chart(r,as_of=FIXTURE_NOW)['strategy_layers'] # Display filters apply to inspected charts too.
        assert r.analytics.projections.read('EURUSD','H4',as_of=FIXTURE_NOW) # Immutable audit revisions remain.
        enable(r,m.key);assert chart(r)['strategy_layers']==layers
        assert not r.orders.transport.submissions and not r.orders.transport.cancellations
    finally:r.close()


def test_all_methods_share_one_feature_factory_per_frame_and_reject_stale_source():
    r=seed()
    try:
        for m in METHODS:r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True))
        before=r.analytics.projections.feature_builds;r.pump();assert r.analytics.projections.feature_builds-before<=28
        rows=chart(r)['strategy_layers'];assert {v['strategy_id'] for v in rows}==set(BY_KEY) and not any(v['state']=='ERROR' for v in rows)
        r.market.activate_source('EURUSD','EMPTY-PUBLIC-SUCCESSOR','SYNTHETIC_FIXTURE')
        assert not chart(r)['strategy_layers'];r.pump();assert all(v['state']=='WARMUP' for v in chart(r)['strategy_layers'])
        assert all(not v['series'] and not v['markers'] and not v['zones'] for v in chart(r)['strategy_layers'])
    finally:r.close()


def test_restart_restores_switches_without_authentication_or_history_reseeding(tmp_path):
    path=tmp_path/'state.sqlite3';r=seed(path);account=r.accounts.current;enable(r,'sma_cross');before=chart(r)['strategy_layers'];r.close()
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    r=ApplicationRuntime(path,clock=lambda:FIXTURE_NOW)
    try:
        assert r.accounts.current is None and not r.connector.workers and not chart(r)['strategy_layers']
        assert r.database.get('recipe_state',BY_KEY['sma_cross'].recipe_id)['enabled']
        r.accounts.select(account);assert not chart(r)['strategy_layers'] # Pending current source/input revalidation.
        r.pump();assert chart(r)['strategy_layers']==before
    finally:r.close()


def test_real_catalogue_widgets_and_canvas_render_geometry():
    from PySide6.QtWidgets import QApplication
    from sfm_fx_new_age.app import create_main_window
    app=QApplication.instance() or QApplication([]);r=seed();w=create_main_window(r);w.show();w.core_timer.stop();w.poll_timer.stop()
    def drain():
        for _ in range(3):r.pump();app.processEvents()
    try:
        r.api(3).navigate('3.1',r.api(3).inspect(symbol='EURUSD',timeframe='H4'));drain();p=w._active_panel()
        assert set(p.checkboxes)==set(BY_KEY) and p.table.rowCount()==83
        p.checkboxes['sma_cross'].click();drain();assert chart(r)['strategy_layers']
        p.chart_button.click();drain();c=w._active_panel().canvas;c.grab();assert c.strategy_layers and c.public_strategy_geometry()
        c.data_identity=('OTHER','EPOCH','EURUSD','H4');assert not c.public_strategy_geometry()
    finally:w.close();r.close();app.processEvents()
