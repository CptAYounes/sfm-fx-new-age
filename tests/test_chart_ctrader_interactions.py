"""Official-chart-inspired gestures. All supplied prices are explicit offline fixtures."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import Qt,QPoint,QPointF,QEvent
from PySide6.QtGui import QMouseEvent,QWheelEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from test_chart_workstation import rows,canvas,move


def test_middle_crosshair_and_chart_hotkeys_stay_local(canvas):
    app,c=canvas
    QTest.mouseClick(c,Qt.MiddleButton,pos=QPoint(100,100));assert not c.crosshair
    QTest.keyClick(c,Qt.Key_G,Qt.ControlModifier);assert not c.grid
    QTest.keyClick(c,Qt.Key_B,Qt.ControlModifier);assert c.show_bid
    QTest.keyClick(c,Qt.Key_4,Qt.AltModifier);assert c.style=='Dot'
    QTest.keyClick(c,Qt.Key_PageUp);assert c.offset>0 and not c.follow
    QTest.keyClick(c,Qt.Key_End);assert c.offset==0


def test_axis_zoom_and_scroll_wheel_config(canvas):
    app,c=canvas;before=c.window;c.wheel_mode='Scroll'
    wheel=lambda mods:QWheelEvent(QPointF(200,100),QPointF(200,100),QPoint(),QPoint(0,120),Qt.NoButton,mods,Qt.NoScrollPhase,False)
    QApplication.sendEvent(c,wheel(Qt.NoModifier));assert c.window==before and c.offset>0
    QApplication.sendEvent(c,wheel(Qt.ControlModifier));assert c.window<before
    c.grab();p=QPoint(200,c.height()-12);old=c.window
    QTest.mousePress(c,Qt.LeftButton,pos=p);move(c,p+QPoint(60,0));QTest.mouseRelease(c,Qt.LeftButton,pos=p+QPoint(60,0));assert c.window!=old


def test_pointer_zoom_preserves_candle_under_pointer(canvas):
    app,c=canvas;c.pan(20);c.grab();pos=QPointF(270,130)
    before=c._bounds[1][c._point(pos)[0]]['open_time']
    c.zoom(.8,pos);c.grab();after=c._bounds[1][c._point(pos)[0]]['open_time']
    assert before==after


def test_chart_drag_can_pan_price_and_historical_time(canvas):
    app,c=canvas;p=QPoint(200,130);q=p+QPoint(80,40)
    QTest.mousePress(c,Qt.LeftButton,pos=p);move(c,q);QTest.mouseRelease(c,Qt.LeftButton,pos=q)
    assert c.offset>0 and c.price_range
    old=c.price_range;c.latest();assert c.price_range==old


def test_source_bound_drawing_geometry_edit_undo_and_redo(canvas):
    app,c=canvas;c.tool='Trend';a=QPoint(200,110);b=QPoint(340,175)
    QTest.mousePress(c,Qt.LeftButton,pos=a);move(c,b);QTest.mouseRelease(c,Qt.LeftButton,pos=b)
    assert len(c.drawings.items)==1
    drawing=c.drawings.items[0];assert drawing['kind']=='Trend' and len(drawing['anchors'])==2
    assert all(isinstance(x[0],str) and isinstance(x[1],float) for x in drawing['anchors'])
    c.drawings.undo();assert not c.drawings.items
    c.drawings.redo();assert len(c.drawings.items)==1
    c.drawings.selected=c.drawings.items[0]['id'];QTest.keyClick(c,Qt.Key_Delete);assert not c.drawings.items
    QTest.keyClick(c,Qt.Key_Z,Qt.ControlModifier);assert len(c.drawings.items)==1
    old=c.data_identity;c.set_data(rows(),'other',('scope','new','EURUSD','H1'));assert not c.drawings.items and not c.drawings.can_undo
    c.set_data(rows(),'old',old);assert len(c.drawings.items)==1


def test_local_drawing_lock_hide_and_fibonacci_price_levels(canvas):
    app,c=canvas
    obj=c.drawings.add('Fibonacci',[('2026-01-05T06:00:00+00:00',1.1),('2026-01-05T12:00:00+00:00',1.2)])
    assert c.drawings.fibonacci(obj)[0]==(0.0,1.2)
    assert c.drawings.fibonacci(obj)[-1]==(1.0,1.1)
    c.drawings.modify(obj['id'],locked=True);assert c.drawings.items[0]['locked']
    assert not c.drawings.move(obj['id'],[('2026-01-05T06:00:00+00:00',1.3),('2026-01-05T12:00:00+00:00',1.4)])
    c.drawings.modify(obj['id'],hidden=True);assert c.drawings.items[0]['hidden']
    assert not c.grab().isNull()


def test_bid_ask_overlays_are_source_bound_and_not_confused_with_close(canvas):
    app,c=canvas;c.show_bid=c.show_ask=True
    q=dict(scope_id='scope',source_epoch='epoch',symbol='EURUSD',bid='1.12',ask='1.1202',state='STALE',observed_at='2026-01-01T00:00:00Z')
    c.set_quotes(q);assert [r['label'] for r in c.quote_lines()]==['Bid · snapshot','Ask · snapshot']
    c.set_quotes(dict(q,source_epoch='wrong'));assert not c.quote_lines()
    c.set_quotes(dict(q,ask='1.1'));assert not c.quote_lines()


def test_context_menu_and_tool_options_never_expose_broker_actions(canvas):
    _,c=canvas;menu=c.build_context_menu();texts=[]
    def walk(m):
        for a in m.actions():
            texts.append(a.text())
            if a.menu():walk(a.menu())
    walk(menu)
    assert any('drawings' in t.lower() for t in texts) and 'Dot' in texts
    assert not any(any(x in t.lower() for x in ('new order','buy stop','sell limit','quicktrade')) for t in texts)


def test_empty_right_margin_does_not_lie_about_ohlc(canvas):
    app,c=canvas;c.grab();area,rr,step,lo,hi,start=c._bounds
    assert c._point(QPointF(area.right()-1,area.center().y())) is None


def test_price_badge_collisions_keep_real_anchor_and_order():
    from sfm_fx_new_age.ui.chart_axis import price_badges
    entries=[(90,1.1,'blue','C'),(90,1.1,'yellow','B'),(89,1.1002,'green','A')]
    badges=price_badges(entries,30,115,5)
    assert len(badges)==2 and [b['label'] for b in badges]==['A','C/B']
    assert [b['actual_y'] for b in badges]==[89,90]
    assert badges[0]['label_y']+18<badges[1]['label_y'] and all(30<=b['label_y']<=97 for b in badges)
    assert price_badges(entries,30,31,5)==[]


def test_selected_handle_drag_is_one_undoable_edit_and_locked_objects_stay_put(canvas):
    app,c=canvas;c.tool='Pan';c.grab()
    a=c._anchor(QPointF(200,130));b=c._anchor(QPointF(340,170));obj=c.drawings.add('Trend',[a,b]);before=list(obj['anchors']);c.grab()
    start=c._coordinates(a).toPoint();end=start+QPoint(30,25)
    QTest.mousePress(c,Qt.LeftButton,pos=start);move(c,end);QTest.mouseRelease(c,Qt.LeftButton,pos=end)
    assert c.drawings.items[0]['anchors']!=before
    c.drawings.undo();assert c.drawings.items[0]['anchors']==before
    identity=c.drawings.items[0]['id'];c.drawings.modify(identity,locked=True);c.grab()
    QTest.mousePress(c,Qt.LeftButton,pos=start);move(c,end);QTest.mouseRelease(c,Qt.LeftButton,pos=end)
    assert c.drawings.items[0]['anchors']==before


def test_drawing_manager_buttons_and_source_change_guard(canvas):
    from sfm_fx_new_age.ui.chart_object_manager import DrawingManager
    app,c=canvas;c.drawings.add('Level',[(c.bars[-1]['open_time'],1.12)])
    d=DrawingManager(c);d.show();d.table.selectRow(0);app.processEvents()
    QTest.mouseClick(d.buttons['lock'],Qt.LeftButton);assert c.drawings.items[0]['locked']
    QTest.mouseClick(d.buttons['hide'],Qt.LeftButton);assert c.drawings.items[0]['hidden']
    QTest.mouseClick(d.buttons['delete'],Qt.LeftButton);assert not c.drawings.items
    QTest.mouseClick(d.buttons['undo'],Qt.LeftButton);assert len(c.drawings.items)==1
    c.set_data(rows(),'other',('scope','other','EURUSD','H1'));d.check_source();assert not d.isVisible()


def test_shell_period_hotkeys_reuse_fixed_views_and_context_options_stay_synced():
    from sfm_fx_new_age.testing.fixtures import fixture_runtime
    from sfm_fx_new_age.app import create_main_window
    app=QApplication.instance() or QApplication([]);r=fixture_runtime();w=create_main_window(r);w.resize(960,640);w.show();app.processEvents()
    try:
        w.chart_tabs.setCurrentIndex(2);p=w.main_tabs.widget(0).widget(2).widget()
        QTest.keyClick(p.canvas,Qt.Key_Down);app.processEvents();assert w.chart_tabs.currentIndex()==3
        p=w.main_tabs.widget(0).widget(3).widget();QTest.keyClick(p.canvas,Qt.Key_4,Qt.AltModifier);assert p.style.currentText()=='Dot'
        QTest.mouseClick(p.canvas,Qt.MiddleButton,pos=QPoint(150,100));assert not p.crosshair_action.isChecked()
        QTest.keyClick(p.canvas,Qt.Key_B,Qt.ControlModifier);assert p.bid_action.isChecked()
        assert all(p.rect().contains(b.geometry()) for b in (p.objects,p.tools_button,p.export_button))
        assert [len(r.api(i).definitions) for i in (1,2,3,4)]==[10,10,13,9]
        assert not r.database.orders() and not r.connector.workers
    finally:w.close();r.close();app.processEvents()
