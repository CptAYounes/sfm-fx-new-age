"""Local interaction refinement. Synthetic prices only; no SDK or broker calls."""
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt,QPoint,QPointF
from PySide6.QtTest import QTest
from test_chart_workstation import canvas,rows,move
from sfm_fx_new_age.ui.chart_properties import ObjectProperties
from sfm_fx_new_age.ui.chart_preferences import ChartPreferences
from sfm_fx_new_age.contracts.chart_display import DISPLAY_DEFAULTS


def test_future_plot_drawing_does_not_fabricate_candle(canvas):
    _,c=canvas;c.set_display({'right_margin':12});c.grab();area=c.plot_rect();pos=QPoint(int(area.right()-12),int(area.center().y()))
    assert c._point(QPointF(pos)) is None
    c.tool='Level';QTest.mouseClick(c,Qt.LeftButton,pos=pos)
    assert len(c.drawings.items)==1 and c.drawings.items[0]['anchors'][0][0]>c.bars[-1]['open_time']
    assert c._point(QPointF(pos)) is None and len(c.bars)==180
    c.tool='Pan';c.grab();before=deepcopy(c.drawings.items[0]['anchors'])
    QTest.mousePress(c,Qt.LeftButton,pos=pos);move(c,pos+QPoint(-20,15));QTest.mouseRelease(c,Qt.LeftButton,pos=pos+QPoint(-20,15))
    assert c.drawings.items[0]['anchors']!=before


def test_single_weekly_future_geometry_uses_week_not_hour(canvas):
    _,c=canvas;c.set_data(rows(1),'EURUSD W1',('scope','epoch','EURUSD','W1'));c.grab()
    stamp=c._stamp_index(1)
    from sfm_fx_new_age.contracts.domain import instant
    assert (instant(stamp)-instant(c.bars[0]['open_time'])).total_seconds()==604800
    assert c._time_index(stamp)==pytest.approx(1)


def test_settings_reset_includes_simple_controls_and_wheel(canvas):
    _,c=canvas;c.grid=False;c.crosshair=False;c.volume=True;c.show_bid=True;c.show_ask=True;c.wheel_mode='Scroll'
    d=ChartPreferences(c);d.reset();assert d.apply()
    assert c.grid and c.crosshair and not c.volume and not c.show_bid and not c.show_ask and c.wheel_mode=='Zoom'
    d.close()


def test_properties_noop_preserves_exact_timestamp_and_undo(canvas):
    _,c=canvas;stamp=c.bars[25]['open_time'];o=c.drawings.add('Trend',[(stamp,1.1100123456),(c.bars[40]['open_time'],1.12)])
    before=deepcopy(o);undos=len(c.drawings._undo);d=ObjectProperties(c,o['id']);assert d.apply()
    assert o==before and len(c.drawings._undo)==undos
    d.close()


def test_properties_reject_concurrent_same_source_edit(canvas):
    _,c=canvas;o=c.drawings.add('Level',[(c.bars[25]['open_time'],1.11)]);d=ObjectProperties(c,o['id'])
    c.drawings.modify(o['id'],name='Another editor');before=deepcopy(o);d.name.setText('Stale edit')
    assert not d.apply() and o==before and 'changed' in d.error.text().lower();d.close()


def test_filled_shape_interior_hit_and_marquee_selection(canvas):
    _,c=canvas;area=c.plot_rect();a=c._anchor(QPointF(180,100));b=c._anchor(QPointF(330,190))
    o=c.drawings.add('Rectangle',[a,b]);c.grab();assert c._hit_drawing(QPointF(245,145))[0]['id']==o['id']
    c.tool='Select';QTest.mousePress(c,Qt.LeftButton,pos=QPoint(150,80));move(c,QPoint(360,215));QTest.mouseRelease(c,Qt.LeftButton,pos=QPoint(360,215))
    assert c.drawings.selection==[o['id']]


def test_rectangle_edge_resize_is_one_undo(canvas):
    _,c=canvas;o=c.drawings.add('Rectangle',[c._anchor(QPointF(180,100)),c._anchor(QPointF(330,190))]);c.grab()
    rect=c._shape(o)[3];start=rect.topRight().toPoint();before=deepcopy(o['anchors']);n=len(c.drawings._undo)
    QTest.mousePress(c,Qt.LeftButton,pos=start);move(c,start+QPoint(25,-15));QTest.mouseRelease(c,Qt.LeftButton,pos=start+QPoint(25,-15))
    assert o['anchors']!=before and len(c.drawings._undo)==n+1
    c.drawings.undo();assert c.drawings.get(o['id'])['anchors']==before


def test_shift_disables_snap_for_drawing_not_ruler(canvas):
    _,c=canvas;c.set_display({'snap_mode':'Always'});c.grab();c.tool='Level';pos=QPoint(220,140);free=c._anchor(QPointF(pos),snap=False)
    QTest.mouseClick(c,Qt.LeftButton,Qt.ShiftModifier,pos=pos)
    assert c.drawings.items[-1]['anchors'][0][1]==free[1]


def test_new_display_flags_are_validated_and_persisted(runtime):
    api=runtime.api(1);ctx=api.inspect(symbol='EURUSD');display={'grid_horizontal':False,'grid_vertical':True,'show_drawings':False,'bull_filled':False,'bear_filled':True,'line_width':2.5,'dot_radius':3.5,'nudge_pips':.5,'hit_distance':10,'crosshair_style':'Dot'}
    api.save_workspace(ctx,{'display':display},0)
    assert api.workspace(ctx)['settings']['display']==display
    before=runtime.database.connection.total_changes
    with pytest.raises(ValueError):api.save_workspace(ctx,{'display':{'hit_distance':1000}},1)
    assert runtime.database.connection.total_changes==before


def test_display_updates_invalidate_geometry_without_losing_objects(canvas):
    _,c=canvas;o=c.drawings.add('Text',[(c.bars[60]['open_time'],1.11)],text='A note')
    c.set_display({'grid_horizontal':False,'bull_filled':False,'line_width':2.5,'dot_radius':3.5,'show_drawings':False})
    assert c._hit_drawing(QPointF(200,140)) is None and not c.grab().isNull() and c.drawings.get(o['id'])


def test_defaults_editor_stages_multiple_tools_without_creating_objects(canvas):
    from sfm_fx_new_age.ui.chart_properties import DrawingDefaults
    _,c=canvas;d=DrawingDefaults(c);d.width.setValue(3);d.color.set_value('#BC9FFF');d.snap.setCurrentText('Off')
    d.kind.setCurrentText('Fibonacci');d.fib.setText('0,50,100,161.8');assert d.apply()
    assert not c.drawings.items and not c.drawings._undo
    a=c._new_object('Level',[(c.bars[20]['open_time'],1.11)])
    assert a['width']==3 and a['snap']=='Off' and a['color']=='#BC9FFF'
    assert c.display['drawing_defaults']['Fibonacci']['fib_levels']==[0,.5,1,1.618];d.close()


def test_default_reset_and_cancel_leave_existing_objects_unchanged(canvas):
    from sfm_fx_new_age.ui.chart_properties import DrawingDefaults
    _,c=canvas;o=c.drawings.add('Level',[(c.bars[20]['open_time'],1.11)],width=4);before=deepcopy(o)
    d=DrawingDefaults(c);d.width.setValue(5);d.reject();assert not c.display['drawing_defaults'] and o==before
    d=DrawingDefaults(c);d.width.setValue(6);d.reset();assert d.apply();assert o==before
    assert c.display['drawing_defaults']['Level']['width']==1.4;d.close()


def test_invalid_defaults_prevent_tool_switch_and_partial_apply(canvas):
    from sfm_fx_new_age.ui.chart_properties import DrawingDefaults
    _,c=canvas;d=DrawingDefaults(c);d.kind.setCurrentText('Fibonacci');d.fib.setText('0,50,50');before=deepcopy(c.display)
    d.kind.setCurrentText('Text');assert d.kind.currentText()=='Fibonacci'
    assert not d.apply() and c.display==before and not c.drawings.items;d.close()


def test_defaults_editor_rejects_source_and_concurrent_changes(canvas):
    from sfm_fx_new_age.ui.chart_properties import DrawingDefaults
    _,c=canvas;d=DrawingDefaults(c);c.set_display({'drawing_defaults':{'Trend':{'width':4}}});assert not d.apply()
    assert c.display['drawing_defaults']=={'Trend':{'width':4}}
    c.set_data(rows(),'other',('other','epoch','EURUSD','H1'));assert not d.apply();d.close()


def test_bulk_style_only_checked_fields_one_undo(canvas):
    from sfm_fx_new_age.ui.chart_properties import BulkAppearance
    _,c=canvas;a=c.drawings.add('Level',[(c.bars[20]['open_time'],1.11)],name='First',width=2)
    b=c.drawings.add('Text',[(c.bars[40]['open_time'],1.12)],name='Second',color='#BC9FFF',text='Keep note');c.drawings.modify(b['id'],locked=True,hidden=True)
    before=deepcopy(c.drawings.items);n=len(c.drawings._undo);d=BulkAppearance(c,[a['id'],b['id']]);assert not d.apply()
    d.enabled['width'].setChecked(True);d.fields['width'].setValue(4);assert d.apply()
    assert len(c.drawings._undo)==n+1 and all(o['width']==4 for o in c.drawings.items)
    assert a['name']=='First' and b['text']=='Keep note' and b['locked'] and b['hidden'] and b['color']=='#BC9FFF'
    assert [o['anchors'] for o in c.drawings.items]==[o['anchors'] for o in before]
    c.drawings.undo();assert c.drawings.items==before;d.close()


def test_bulk_style_rejects_conflicting_and_new_source_edits(canvas):
    from sfm_fx_new_age.ui.chart_properties import BulkAppearance
    _,c=canvas;o=c.drawings.add('Level',[(c.bars[20]['open_time'],1.11)]);d=BulkAppearance(c,[o['id']]);d.enabled['width'].setChecked(True)
    c.drawings.modify(o['id'],name='Updated');before=deepcopy(o);assert not d.apply() and o==before
    c.set_data(rows(),'other',('scope','new','EURUSD','H1'));assert not d.apply() and not c.drawings.items;d.close()


def test_object_snap_override_and_shift_draft_match_preview(canvas):
    _,c=canvas;c.set_display({'snap_mode':'Always','drawing_defaults':{'Trend':{'snap':'Off'}}});c.grab();c.tool='Trend'
    p=QPoint(200,150);q=QPoint(330,190);a=c._anchor(QPointF(p));b=c._anchor(QPointF(q))
    QTest.mousePress(c,Qt.LeftButton,pos=p);move(c,q);assert c._draft['anchors']==[a,b]
    QTest.mouseRelease(c,Qt.LeftButton,pos=q);assert c.drawings.items[0]['anchors']==[a,b]


def test_fractional_style_and_sub_millisecond_anchor_noop(canvas):
    _,c=canvas;o=c.drawings.add('Level',[('2026-01-01T12:00:00.123456Z',1.11001234567)],width=1.23456,opacity=12.5,font_size=12.4)
    before=deepcopy(o);n=len(c.drawings._undo);d=ObjectProperties(c,o['id']);assert d.apply() and o==before and len(c.drawings._undo)==n;d.close()


def test_text_hit_region_tracks_multiline_font_geometry(canvas):
    _,c=canvas;o=c.drawings.add('Text',[c._anchor(QPointF(200,150))],text='A note\nwith a much longer second line',font_size=20)
    rect=c._text_rect(o);p=QPointF(rect.right()-10,rect.bottom()-4);assert c._hit_drawing(p)[0]['id']==o['id']


def test_nudge_steps_and_global_drawing_visibility(canvas):
    _,c=canvas;o=c.drawings.add('Level',[(c.bars[20]['open_time'],1.11)]);c.set_display({'nudge_pips':.5,'nudge_bars':3});c.nudge_objects(1,1)
    assert o['anchors'][0][0]==c.bars[23]['open_time'] and o['anchors'][0][1]==pytest.approx(1.11005)
    QTest.keyClick(c,Qt.Key_H,Qt.ControlModifier);assert not c.display['show_drawings'];c.grab();assert c._hit_drawing(QPointF(200,150)) is None
    QTest.keyClick(c,Qt.Key_H,Qt.ControlModifier);assert c.display['show_drawings']


def test_cut_undo_redo_and_enter_property_signal(canvas):
    _,c=canvas;o=c.drawings.add('Level',[(c.bars[20]['open_time'],1.11)]);calls=[];c.editDrawing.connect(calls.append)
    QTest.keyClick(c,Qt.Key_Return);assert calls==[o['id']]
    QTest.keyClick(c,Qt.Key_X,Qt.ControlModifier);assert not c.drawings.items and c._clipboard
    QTest.keyClick(c,Qt.Key_Z,Qt.ControlModifier);assert len(c.drawings.items)==1
    QTest.keyClick(c,Qt.Key_Z,Qt.ControlModifier|Qt.ShiftModifier);assert not c.drawings.items


def test_three_color_presets_staged_not_immediate(canvas):
    _,c=canvas;d=ChartPreferences(c);original=deepcopy(c.display);d.theme.setCurrentText('Light chart');assert c.display==original
    assert d.apply() and c.display['background']=='#F5F7FB'
    d.theme.setCurrentText('High contrast');assert d.apply() and c.display['foreground']=='#FFFFFF'
    d.theme.setCurrentText('SFM navy');assert d.apply() and c.display['background']==DISPLAY_DEFAULTS['background'];d.close()


def test_draw_settings_and_styles_persist_in_one_workspace(runtime):
    from sfm_fx_new_age.ui.chart_objects import DrawingBook
    api=runtime.api(1);ctx=api.inspect(symbol='EURUSD');book=DrawingBook();book.add('Fibonacci',[('2026-11-01T00:00:00Z',1.1),('2026-11-02T00:00:00Z',1.2)],fib_levels=[0,.5,1,1.618],line_style='Dash',show_prices=False,snap='Off')
    settings={'drawings':book.items,'display':deepcopy(DISPLAY_DEFAULTS)};api.save_workspace(ctx,settings,0)
    from sfm_fx_new_age.contracts.models import thaw
    import json
    assert thaw(api.workspace(ctx)['settings'])==json.loads(json.dumps(settings))


@pytest.mark.parametrize('bad',[{'hit_distance':0},{'grid_horizontal':1},{'nudge_bars':1.5},{'crosshair_style':'Fake'},{'drawing_defaults':{'Trend':{'snap':'Fake'}}}])
def test_extended_setting_validation_has_zero_partial_writes(runtime,bad):
    api=runtime.api(1);ctx=api.inspect(symbol='EURUSD');before=runtime.database.connection.total_changes
    with pytest.raises(ValueError):api.save_workspace(ctx,{'display':bad},0)
    assert runtime.database.connection.total_changes==before


@pytest.mark.parametrize('kind',['properties','defaults','bulk','settings','manager'])
def test_source_dialogs_are_chart_owned_and_stop_polling_after_close(canvas,kind):
    from sfm_fx_new_age.ui.chart_properties import DrawingDefaults,BulkAppearance
    from sfm_fx_new_age.ui.chart_object_manager import DrawingManager
    _,c=canvas;o=c.drawings.add('Level',[(c.bars[20]['open_time'],1.11)])
    factories={'properties':lambda:ObjectProperties(c,o['id']),'defaults':lambda:DrawingDefaults(c),'bulk':lambda:BulkAppearance(c,[o['id']]),'settings':lambda:ChartPreferences(c),'manager':lambda:DrawingManager(c)}
    d=factories[kind]();assert d.parent() is c and d.timer.isActive();d.reject();assert not d.timer.isActive()


def test_objects_button_and_keyboard_open_real_manager_after_workflow_setup(runtime):
    from sfm_fx_new_age.app import create_main_window
    from sfm_fx_new_age.ui.chart_object_manager import DrawingManager
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    app=QApplication.instance() or QApplication([]);w=create_main_window(runtime);w.show();app.processEvents();p=w._active_panel();seen=[]
    def close_manager():
        d=app.activeModalWidget()
        if isinstance(d,DrawingManager):seen.append(d.objectName());d.reject()
    for action in (p.objects.click,p.canvas.manageDrawings.emit):
        QTimer.singleShot(0,close_manager);action();app.processEvents()
    assert seen==['chartDrawingManager','chartDrawingManager']
    assert not runtime.database.orders() and not runtime.connector.workers;w.close();app.processEvents()
