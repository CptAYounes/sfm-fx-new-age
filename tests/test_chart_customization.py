"""Chart/object customization acceptance; labelled synthetic prices, no native sockets."""
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt,QPoint,QPointF,QDateTime,QItemSelectionModel
from PySide6.QtTest import QTest
from test_chart_workstation import canvas,move,rows
from sfm_fx_new_age.ui.chart_objects import DrawingBook
from sfm_fx_new_age.ui.chart_properties import ObjectProperties
from sfm_fx_new_age.ui.chart_preferences import ChartPreferences
from sfm_fx_new_age.ui.chart_object_manager import DrawingManager
from sfm_fx_new_age.contracts.chart_display import validate_display,validate_drawing


def obj(c,kind='Trend',x=180):return c.drawings.add(kind,[c._anchor(QPointF(x,120))] if kind in {'Level','Vertical','Text'} else [c._anchor(QPointF(x,120)),c._anchor(QPointF(x+110,175))])


def test_properties_exact_coordinates_style_apply_cancel_defaults(canvas):
    app,c=canvas;o=obj(c);d=ObjectProperties(c,o['id']);d.show();app.processEvents()
    d.name.setText('My trend');d.width.setValue(3);d.line.setCurrentText('Dash');d.color.set_value('#BC9FFF');d.fields['extend_right'].setChecked(True)
    d.anchor_fields[0][1].setValue(1.1105);d.as_default.setChecked(True)
    assert d.apply();assert o['anchors'][0][1]==1.1105 and o['name']=='My trend' and o['width']==3
    assert c.display['drawing_defaults']['Trend']['color']=='#BC9FFF'
    before=deepcopy(o);d.name.setText('Unsaved');d.reject();assert o==before
    new=c._new_object('Trend',o['anchors']);assert new['width']==3 and not new.get('name')


def test_invalid_fibonacci_edit_is_atomic(canvas):
    _,c=canvas;o=obj(c,'Fibonacci');d=ObjectProperties(c,o['id']);before=deepcopy(o)
    d.fib.setText('0,61.8,61.8');d.name.setText('Invalid');assert not d.apply() and o==before
    d.fib.setText('-27.2,0,38.2,61.8,100,161.8');assert d.apply()
    assert len(c.drawings.fibonacci(o))==6 and c.drawings.fibonacci(o)[-1][0]==1.618;d.close()


def test_locked_properties_cannot_move_and_source_guard(canvas):
    _,c=canvas;o=obj(c);c.drawings.modify(o['id'],locked=True);d=ObjectProperties(c,o['id']);d.show()
    assert not d.anchor_fields[0][1].isEnabled();before=deepcopy(o['anchors']);d.width.setValue(4);assert d.apply() and o['anchors']==before
    c.set_data(rows(),'new',('scope','new','EURUSD','H1'));assert not d.check_source() and not d.isVisible()


def test_multi_selection_duplicate_layer_delete_and_undo(canvas):
    _,c=canvas;a=obj(c,'Level');b=obj(c,'Trend',300);c.drawings._selection=[a['id'],b['id']]
    copy=c.drawings.duplicate();assert len(copy)==2 and len(c.drawings.selection)==2 and all(not x['locked'] for x in copy)
    c.drawings.reorder([a['id']],True);assert c.drawings.items[-1]['id']==a['id'];c.drawings.undo();assert c.drawings.items[-1]['id']!=a['id']
    c.drawings._selection=[x['id'] for x in copy];c.drawings.delete();assert len(c.drawings.items)==2;c.drawings.undo();assert len(c.drawings.items)==4


def test_single_click_no_edit_history_and_escape_restores_group(canvas):
    _,c=canvas;o=obj(c);c.grab();p=c._coordinates(o['anchors'][0]).toPoint();before=deepcopy(o['anchors']);count=len(c.drawings._undo)
    QTest.mouseClick(c,Qt.LeftButton,pos=p);assert len(c.drawings._undo)==count
    QTest.mousePress(c,Qt.LeftButton,pos=p);move(c,p+QPoint(30,15));assert c.drawings.get(o['id'])['anchors']!=before
    QTest.keyClick(c,Qt.Key_Escape);QTest.mouseRelease(c,Qt.LeftButton,pos=p+QPoint(30,15))
    assert c.drawings.get(o['id'])['anchors']==before and len(c.drawings._undo)==count


def test_ctrl_drag_duplicates_in_one_undoable_gesture(canvas):
    _,c=canvas;o=obj(c);c.grab();p=c._coordinates(o['anchors'][0]).toPoint();before=deepcopy(o);count=len(c.drawings._undo)
    QTest.mousePress(c,Qt.LeftButton,Qt.ControlModifier,pos=p);move(c,p+QPoint(35,20));QTest.mouseRelease(c,Qt.LeftButton,pos=p+QPoint(35,20))
    assert len(c.drawings.items)==2 and c.drawings.get(o['id'])==before and len(c.drawings._undo)==count+1
    c.drawings.undo();assert len(c.drawings.items)==1


def test_ctrl_select_group_nudge_skips_locked_objects(canvas):
    _,c=canvas;a=obj(c,'Level');b=obj(c,'Trend',300);c.drawings._selection=[a['id'],b['id']];c.drawings.modify(a['id'],locked=True)
    before=deepcopy(b['anchors']);original=deepcopy(a['anchors']);QTest.keyClick(c,Qt.Key_Up,Qt.AltModifier)
    assert a['anchors']==original and b['anchors'][0][1]==pytest.approx(before[0][1]+.0001)
    c.drawings.undo();assert c.drawings.get(b['id'])['anchors']==before


def test_clipboard_never_crosses_source_identity(canvas):
    _,c=canvas;o=obj(c);QTest.keyClick(c,Qt.Key_C,Qt.ControlModifier);QTest.keyClick(c,Qt.Key_V,Qt.ControlModifier)
    assert len(c.drawings.items)==2 and len({x['id'] for x in c.drawings.items})==2
    c.set_data(rows(),'new',('scope','different','EURUSD','H1'));QTest.keyClick(c,Qt.Key_V,Qt.ControlModifier);assert not c.drawings.items


def test_extra_shapes_text_and_render_preferences(canvas):
    app,c=canvas
    for k in ('Ellipse','Triangle','Rectangle','Fibonacci','Text'):
        o=obj(c,k);c.drawings.modify(o['id'],name=k+' example',width=2,opacity=25,line_style='Dot')
    c.set_display({'background':'#18212F','bull_color':'#73C7FF','bear_color':'#F4C66B','right_margin':8,'price_padding':20,'volume_height':85});c.volume=True
    assert not c.grab().isNull() and c._point(QPointF(c.plot_rect().right()-2,100)) is None
    c.drawings.hidden=True;assert not c.grab().isNull()


def test_snapping_modes_one_shot_and_time_only_pan(canvas):
    _,c=canvas;c.set_display({'snap_mode':'Always','one_shot':True,'pan_mode':'Time only'});c.grab()
    anchor=c._anchor(QPointF(200,155),snap=True);index=c._point(QPointF(200,155))[0]
    assert anchor[1] in {float(c._bounds[1][index][k]) for k in ('open','high','low','close')}
    c.tool='Level';QTest.mouseClick(c,Qt.LeftButton,pos=QPoint(200,155));assert c.tool=='Pan'
    c.drawings.hidden=True;QTest.mousePress(c,Qt.LeftButton,pos=QPoint(250,150));move(c,QPoint(300,175));QTest.mouseRelease(c,Qt.LeftButton,pos=QPoint(300,175));assert c.price_range is None


def test_preferences_apply_cancel_and_reset_are_real_actions(canvas):
    app,c=canvas;d=ChartPreferences(c);d.show();app.processEvents();d.fields['right_margin'].setValue(12);d.fields['show_forming'].setChecked(False);d.fields['snap_mode'].setCurrentText('Off');d.simple['show_ask'].setChecked(True)
    assert d.apply() and c.display['right_margin']==12 and not c.display['show_forming'] and c.show_ask
    d.fields['right_margin'].setValue(19);d.reject();assert c.display['right_margin']==12
    d=ChartPreferences(c);d.reset();assert c.display['right_margin']==12;assert d.apply() and c.display['right_margin']==3;d.close()


def test_manager_filter_bulk_flags_and_properties(canvas):
    app,c=canvas;a=obj(c,'Level');b=obj(c,'Trend');d=DrawingManager(c);d.show();d.table.selectAll();app.processEvents();assert len(d.identities())==2
    d.buttons['lock'].click();assert all(o['locked'] for o in c.drawings.items)
    d.buttons['duplicate'].click();assert len(c.drawings.items)==4
    d.search.setText('Trend');assert d.table.rowCount()==2;d.close()


def test_custom_workspace_roundtrip_and_old_epoch_archive(runtime):
    api=runtime.api(1);ctx=api.inspect(symbol='EURUSD');b=DrawingBook();o=b.add('Ellipse',[('2026-11-05T00:00:00Z',1.1),('2026-11-05T12:00:00Z',1.2)],width=3,opacity=24,name='Round trip')
    api.save_workspace(ctx,{'drawings':b.items,'display':{'right_margin':8,'drawing_defaults':{'Ellipse':{'fill':False,'width':2}}}},0)
    v=api.workspace(ctx);assert v['settings']['drawings'][0]['name']=='Round trip'
    runtime.market.activate_source('EURUSD','NEXT','SYNTHETIC_FIXTURE');new=api.inspect(symbol='EURUSD');v=api.workspace(new)
    assert not v['settings'].get('drawings') and v['settings']['display']['right_margin']==8 and v['archives']


@pytest.mark.parametrize('bad',[{'right_margin':float('nan')},{'one_shot':1},{'candle_width':1000},{'background':'red'},{'snap_mode':'Fake'},{'drawing_defaults':{'order':{}}},{'drawing_defaults':{'Level':{'width':True}}}])
def test_invalid_display_payload_is_rejected_without_state_change(runtime,bad):
    ctx=runtime.api(1).inspect();before=runtime.database.connection.total_changes
    with pytest.raises(ValueError):runtime.api(1).save_workspace(ctx,{'display':bad},0)
    assert runtime.database.connection.total_changes==before


def test_double_click_selected_object_opens_properties_not_fit(canvas):
    _,c=canvas;o=obj(c,'Level');c.grab();observed=[];c.editDrawing.connect(observed.append);before=c.window
    point=c._coordinates(o['anchors'][0]).toPoint();QTest.mouseDClick(c,Qt.LeftButton,pos=point)
    assert observed==[o['id']] and c.window==before


def test_settings_and_property_dialogs_reject_changed_source(canvas):
    _,c=canvas;settings=ChartPreferences(c);settings.show();o=obj(c);properties=ObjectProperties(c,o['id']);properties.show()
    c.set_data(rows(),'different',('scope','other','EURUSD','H1'));assert not settings.apply() and not properties.apply()
    assert not settings.isVisible() and not properties.isVisible()


def test_exact_time_property_uses_fractional_chart_position(canvas):
    _,c=canvas;o=obj(c);first=o['anchors'][0][0];i=c._time_index(first);stamp=c._stamp_index(i+.5)
    x=c._coordinates((stamp,1.1)).x();left=c._coordinates((first,1.1)).x()
    assert x-left==pytest.approx(c._bounds[2]/2)


def test_workspace_never_autosaves_half_finished_object_drag(runtime):
    from sfm_fx_new_age.app import create_main_window
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance() or QApplication([]);w=create_main_window(runtime);w.show();app.processEvents();p=w._active_panel();c=p.canvas
    o=c.drawings.add('Level',[(c.bars[-1]['open_time'],float(c.bars[-1]['close']))]);p._save_workspace();before=p._workspace_version;initial=deepcopy(o['anchors'])
    c.drag=('object',);c.drawings.begin();c.drawings.move(o['id'],[(initial[0][0],initial[0][1]+.01)],remember=False);p._save_workspace()
    assert p._workspace_version==before
    c.drawings.cancel();c.drag=None;p._save_workspace();assert p._workspace_version==before
    w.close();app.processEvents()


def test_extended_settings_and_objects_survive_real_sqlite_restart(tmp_path):
    from sfm_fx_new_age.testing.fixtures import fixture_runtime
    path=tmp_path/'state.sqlite';r=fixture_runtime(path)
    account=r.accounts.current
    assert account is not None
    try:
        api=r.api(1);ctx=api.inspect(symbol='EURUSD');book=DrawingBook();book.add('Text',[('2026-11-05T00:00:00Z',1.1)],text='Persistent human note',font_size=14)
        api.save_workspace(ctx,{'drawings':book.items,'display':{'pan_mode':'Time only','snap_mode':'Off','drawing_defaults':{'Trend':{'width':3,'line_style':'Dash'}}}},0)
    finally:r.close()
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    from sfm_fx_new_age.services.orders import FixtureBroker
    r=ApplicationRuntime(path,clock=lambda:'2026-11-05T12:00:00Z',transport=FixtureBroker())
    r.accounts.select(account)
    try:
        ws=r.api(1).workspace(r.api(1).inspect(symbol='EURUSD'))
        assert ws['settings']['drawings'][0]['text']=='Persistent human note'
        assert ws['settings']['display']['drawing_defaults']['Trend']['width']==3 and ws['version']==1
        assert not r.database.orders() and not r.connector.workers
    finally:r.close()


def test_group_edit_source_change_cancels_before_caching_old_book(canvas):
    _,c=canvas;o=obj(c);identity=c.data_identity;before=deepcopy(o['anchors']);book=c.drawings
    c.drag=('object',);book.begin();book.move(o['id'],[(t,v+.001) for t,v in before],remember=False)
    c.set_data(rows(),'next',('scope','next','EURUSD','H1'));assert book.get(o['id'])['anchors']==before
    c.set_data(rows(),'old',identity);assert c.drawings.get(o['id'])['anchors']==before
