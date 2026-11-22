"""Axis/ruler display-only acceptance; explicitly synthetic OHLC and local settings."""
from copy import deepcopy
import math
import pytest
from PySide6.QtCore import Qt,QPoint,QPointF
from PySide6.QtTest import QTest
from test_chart_workstation import canvas,move,rows
from sfm_fx_new_age.contracts.chart_display import validate_display
from sfm_fx_new_age.ui.chart_preferences import ChartPreferences


def test_price_ticks_are_round_ordered_unique_and_inside_range():
    from sfm_fx_new_age.ui.chart_axis import price_ticks
    for low,high,height,digits in [(1.10113,1.11987,220,5),(148.712,151.931,400,3),(1.1,1.10003,140,5)]:
        ticks=price_ticks(low,high,height,22,digits)
        assert ticks and ticks==sorted(set(ticks)) and all(low<=v<=high for v in ticks)
        assert len({f'{v:.{digits}f}' for v in ticks})==len(ticks)
        assert all(round(v,digits)==pytest.approx(v,abs=10**(-digits-2)) for v in ticks)
    assert price_ticks(2,1,200,20,5)==[]


def test_axes_have_real_gutters_and_collision_free_adaptive_labels(canvas):
    _,c=canvas
    for width,height in [(480,240),(820,420)]:
        c.resize(width,height);c.set_display({'axis_font_size':16});c.grab()
        area=c.plot_rect();assert area.width()>width/2 and area.height()>60
        assert c.price_axis_rect().left()==area.right() and c.time_axis_rect().top()>area.bottom()-1
        labels=c.time_axis_labels();assert labels
        assert all(c.time_axis_rect().contains(v['rect']) for v in labels)
        assert all(a['rect'].right()+5<=b['rect'].left() for a,b in zip(labels,labels[1:]))
        assert all(v['stamp'] in {r['open_time'] for r in c.visible_bars()} for v in labels)
        assert all(c.price_axis_rect().contains(v['rect']) for v in c.price_axis_labels())


@pytest.mark.parametrize('tool,axis',[('Time ruler','time'),('Price ruler','price')])
def test_dedicated_ruler_actual_axis_gesture_does_not_rescale_or_draw(canvas,tool,axis):
    app,c=canvas;c.tool=tool;c.grab();area,rr,step,low,high,start=c._bounds
    if axis=='time':
        a=QPoint(round(start+5.5*step),round(c.time_axis_rect().center().y()));b=QPoint(round(start+18.5*step),a.y())
    else:
        a=QPoint(round(c.price_axis_rect().center().x()),round(area.top()+area.height()*.25));b=QPoint(a.x(),round(area.top()+area.height()*.7))
    before=(c.window,c.offset,c.price_range,deepcopy(c.drawings.items))
    QTest.mousePress(c,Qt.LeftButton,pos=a);move(c,b);QTest.mouseRelease(c,Qt.LeftButton,pos=b);c.grab()
    assert c.ruler and c.ruler_mode==axis
    d=c.ruler_readout();assert d and d['mode']==axis
    if axis=='time':assert d['bars']==13 and d['hours']==13 and c.ruler[0][1]==c.ruler[1][1]
    else:assert d['pips']<0 and d['bars']==0 and c.ruler[0][0]==c.ruler[1][0]
    assert (c.window,c.offset,c.price_range,c.drawings.items)==before
    assert 'observed' in d['text'].lower() if axis=='time' else 'pips' in d['text']
    assert c.ruler_card_rect() and c.rect().contains(c.ruler_card_rect().toAlignedRect())
    QTest.keyClick(c,Qt.Key_Escape);assert c.ruler is None and c.tool=='Pan'


def test_time_measure_uses_elapsed_wall_time_including_gaps(canvas):
    _,c=canvas;data=rows(3);data[2]['open_time']='2026-01-05T02:00:00+00:00';data[2]['close_time']='2026-01-05T03:00:00+00:00'
    c.set_data(data,'EURUSD synthetic gap',c.data_identity);c.grab();c.ruler_mode='time';c.ruler=((data[0]['open_time'],1.1),(data[2]['open_time'],1.1))
    d=c.ruler_readout();assert d['bars']==2 and d['hours']==98
    assert 'gaps included' in d['text']


def test_ruler_cannot_invent_future_candles_or_survive_source_switch(canvas):
    _,c=canvas;c.tool='Time ruler';c.grab();area=c.plot_rect();future=QPoint(round(area.right()-1),round(c.time_axis_rect().center().y()))
    QTest.mouseClick(c,Qt.LeftButton,pos=future);assert c.ruler is None
    c.tool='Ruler';a=QPoint(180,110);b=QPoint(290,170)
    QTest.mousePress(c,Qt.LeftButton,pos=a);move(c,b);QTest.mouseRelease(c,Qt.LeftButton,pos=b);assert c.ruler
    c.set_data(rows(),'next',('scope','next','EURUSD','H1'));assert c.ruler is None


def test_axis_shift_measure_preserves_default_pan_tool(canvas):
    _,c=canvas;c.grab();rect=c.price_axis_rect();a=rect.center().toPoint();b=a+QPoint(0,30)
    QTest.mousePress(c,Qt.LeftButton,Qt.ShiftModifier,pos=a);move(c,b);QTest.mouseRelease(c,Qt.LeftButton,pos=b)
    assert c.ruler and c.ruler_mode=='price' and c.tool=='Pan' and c.price_range is None


def test_axis_ruler_preferences_apply_cancel_and_new_display_validation(canvas):
    app,c=canvas;d=ChartPreferences(c);d.show();app.processEvents()
    assert any(d.tabs.tabText(i)=='Axes / rulers' for i in range(d.tabs.count()))
    d.fields['axis_font_size'].setValue(14);d.fields['price_tick_spacing'].setValue(64);d.fields['time_label_format'].setCurrentText('ISO date + time')
    d.fields['ruler_color'].set_value('#73C7FF');d.fields['show_axis_highlight'].setChecked(False)
    assert d.apply() and c.display['price_tick_spacing']==64 and c.display['ruler_color']=='#73C7FF'
    d.fields['price_tick_spacing'].setValue(80);d.reject();assert c.display['price_tick_spacing']==64
    for bad in [{'price_tick_spacing':0},{'time_tick_spacing':999},{'axis_minor_ticks':1},{'time_label_format':'local'},{'ruler_color':'red'}]:
        with pytest.raises(ValueError):validate_display(bad)


def test_ruler_reverse_and_zero_bar_price_measure_are_valid(canvas):
    _,c=canvas;stamp=c.bars[-1]['open_time'];c.ruler=((stamp,1.1),(stamp,1.101));c.ruler_mode='price';d=c.ruler_readout()
    assert d['bars']==0 and d['hours']==0 and d['pips']==pytest.approx(10)
    c.ruler=tuple(reversed(c.ruler));assert c.ruler_readout()['pips']==pytest.approx(-10)
    c.set_data([dict(rows(1)[0],symbol='USDJPY',open='150',high='151',low='149',close='150.5')],'USDJPY',('scope','epoch','USDJPY','H1'))
    c.ruler=((c.bars[0]['open_time'],150),(c.bars[0]['open_time'],150.1));c.ruler_mode='price'
    assert c.ruler_readout()['pips']==pytest.approx(10)


def test_new_axis_settings_persist_without_ruler_or_market_mutation(runtime):
    api=runtime.api(1);context=api.inspect(symbol='EURUSD',timeframe='D1')
    values={'axis_minor_ticks':False,'axis_panel':False,'price_tick_spacing':64,'time_tick_spacing':155,'ruler_color':'#73C7FF','show_ruler_card':False,'time_label_format':'Date only'}
    api.save_workspace(context,{'display':values},0)
    assert dict(api.workspace(context)['settings']['display'])==values
    assert not runtime.database.orders() and not runtime.connector.workers


@pytest.mark.parametrize('corner',['Top left','Top right','Bottom left','Bottom right'])
def test_measurement_readout_corner_and_endpoint_badges_keep_exact_anchors(canvas,corner):
    _,c=canvas;c.ruler_mode='time';r=c.visible_bars();c.ruler=((r[5]['open_time'],1.1),(r[6]['open_time'],1.1))
    c.set_display({'ruler_position':corner});c.grab();rect=c.ruler_card_rect();area=c.plot_rect()
    assert area.contains(rect)
    assert abs((rect.right() if corner.endswith('right') else rect.left())-(area.right()-8 if corner.endswith('right') else area.left()+8))<1
    labels=c.time_ruler_labels();assert len(labels)==2
    assert all(c.time_axis_rect().contains(v['rect']) for v in labels) and not labels[0]['rect'].intersects(labels[1]['rect'])
    assert labels[0]['x']<labels[1]['x'] and [v['first'][:2] for v in labels]==['T1','T2']
    c.ruler=tuple(reversed(c.ruler));assert [v['first'][:2] for v in c.time_ruler_labels()]==['T2','T1']


def test_time_ruler_never_creates_a_price_scenario_and_axis_menu_opens_correct_settings(runtime):
    from sfm_fx_new_age.app import create_main_window
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    app=QApplication.instance() or QApplication([]);w=create_main_window(runtime);w.resize(960,640);w.show();app.processEvents();p=w._active_panel();c=p.canvas
    try:
        stamp=c.bars[-1]['open_time'];c.ruler_mode='time';c.ruler=((stamp,1.1),(stamp,1.1))
        assert p.inspection_context()['scenario'] is None
        c.ruler_mode='price';c.ruler=((stamp,1.1),(stamp,1.11));assert p.inspection_context()['scenario']['entry']=='1.1'
        observed=[]
        def dismiss():
            dialog=app.activeModalWidget();observed.append(dialog.tabs.tabText(dialog.tabs.currentIndex()));dialog.reject()
        QTimer.singleShot(20,dismiss);c.axisSettingsRequested.emit();assert observed==['Axes / rulers']
        assert not runtime.database.orders() and not runtime.connector.workers
    finally:w.close();app.processEvents()


def test_measurement_refuses_nonpositive_panned_price_and_empty_chart(canvas):
    _,c=canvas;c.price_range=(-2,-1);c.grab();assert not c._begin_ruler(c.plot_rect().center(),'price') and not c.ruler
    c.set_data([],'No data',('scope','other','EURUSD','H1'));c.grab();assert not c._begin_ruler(c.price_axis_rect().center(),'price')
