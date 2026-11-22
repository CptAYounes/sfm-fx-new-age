"""Offline chart interaction, causality and session UX regression; no broker sockets."""
import os,csv,io,importlib.util
from pathlib import Path
from datetime import datetime,timedelta,timezone
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import Qt,QPointF,QPoint,QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from sfm_fx_new_age.ui.chart_workspace import CandleCanvas,chart_csv
from sfm_fx_new_age.services.chart_studies import moving_average,ChartStudyService
from sfm_fx_new_age.contracts.domain import PAIRS,FRAMES
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.testing.fixtures import fixture_runtime
from sfm_fx_new_age.app import create_main_window


def rows(n=180):
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    return [dict(symbol='EURUSD',timeframe='H1',open_time=(start+timedelta(hours=i)).isoformat(),close_time=(start+timedelta(hours=i+1)).isoformat(),available_at=(start+timedelta(hours=i+1)).isoformat(),open=str(1.1+i*.0001),high=str(1.102+i*.0001),low=str(1.099+i*.0001),close=str(1.101+i*.0001),tick_volume=i*3,origin='SYNTHETIC_FIXTURE',source_epoch='epoch') for i in range(n)]

@pytest.fixture
def canvas():
    app=QApplication.instance() or QApplication([]);c=CandleCanvas();c.resize(820,420);c.set_data(rows(),'EURUSD fixture',('scope','epoch','EURUSD','H1'));c.show();app.processEvents();c.grab()
    yield app,c
    c.close();app.processEvents()

def move(c,pos):QApplication.sendEvent(c,QMouseEvent(QEvent.MouseMove,QPointF(pos),QPointF(pos),Qt.NoButton,Qt.LeftButton,Qt.NoModifier))


def test_chart_buttons_keyboard_and_price_scale(canvas):
    app,c=canvas;QTest.keyClick(c,Qt.Key_Left);assert c.offset>0 and not c.follow
    QTest.keyClick(c,Qt.Key_End);assert c.offset==0 and c.follow
    old=c.window;QTest.keyClick(c,Qt.Key_Plus);assert c.window<old
    app.processEvents();c.grab();area=c.plot_rect();pos=QPoint(int(area.right()+20),int(area.center().y()))
    QTest.mousePress(c,Qt.LeftButton,pos=pos);move(c,pos+QPoint(0,40));QTest.mouseRelease(c,Qt.LeftButton,pos=pos+QPoint(0,40))
    assert c.price_range and c.price_range[0]<c.price_range[1]
    c.fit();assert c.price_range is None and c.offset==0


def test_new_candles_preserve_historical_anchor_and_latest_follows(canvas):
    _,c=canvas;c.pan(30);anchor=c.visible_bars()[-1]['open_time'];old_offset=c.offset
    c.set_data(rows(183),'EURUSD',c.data_identity)
    assert c.visible_bars()[-1]['open_time']==anchor and c.offset==old_offset+3
    c.latest();c.set_data(rows(184),'EURUSD',c.data_identity)
    assert c.offset==0 and c.visible_bars()[-1]['open_time']==rows(184)[-1]['open_time']


def test_zoom_go_to_and_source_scoped_drawing_memory(canvas):
    app,c=canvas;c.zoom(.8,c.plot_rect().center());assert c.window<80
    assert c.go_to(rows()[45]['open_time']) and c.offset>0
    assert not c.go_to('2020-01-01T00:00:00Z')
    c.horizontal=[1.11];c.price_range=(1.09,1.14);old=(c.window,c.offset)
    identity=c.data_identity;c.set_data(rows(),'GBPUSD',('scope','epoch','GBPUSD','H1'))
    assert not c.horizontal and c.price_range is None
    c.set_data(rows(),'EURUSD',identity);assert (c.window,c.offset)==old and c.horizontal==[1.11]
    c.set_data(rows(),'EURUSD',('scope','different-epoch','EURUSD','H1'));assert not c.horizontal and c.offset==0


def test_ruler_levels_all_styles_volume_and_shared_studies_render(canvas):
    app,c=canvas;captured=[];c.hovered.connect(captured.append)
    p=QPoint(200,140);q=QPoint(320,185)
    c.tool='Ruler';QTest.mousePress(c,Qt.LeftButton,pos=p);move(c,q);QTest.mouseRelease(c,Qt.LeftButton,pos=q)
    assert c.ruler and any('pips' in t and 'bars' in t for t in captured)
    c.tool='Level';QTest.mouseClick(c,Qt.LeftButton,pos=p);assert len(c.horizontal)==1
    c._study_values=ChartStudyService().query(rows(),('fixture',));c.studies={'SMA 20','EMA 50'};c.volume=True
    for style in ('Candles','OHLC','Line'):
        c.style=style;assert not c.grab().isNull()
    QTest.keyClick(c,Qt.Key_Escape);assert c.tool=='Pan' and c.ruler is None


def test_studies_are_shared_trailing_causal_and_defensive_copies():
    values=list(range(1,101));a=moving_average(values,20);b=moving_average(values+[9999],20)
    assert a[:19]==[None]*19 and a[19]==10.5 and a==b[:100]
    assert moving_average(values,50,exponential=True)[:49]==[None]*49
    service=ChartStudyService();one=service.query(rows(),('scope','epoch'));two=service.query(rows(),('scope','epoch'))
    assert service.computations==1 and one==two
    one['SMA 20'][-1]=999;assert service.query(rows(),('scope','epoch'))['SMA 20'][-1]!=999
    r=fixture_runtime()
    try:
        data=thaw(r.api(1).query('1.3',DataRequest('chart',limit=1)))
        assert all(len(v)<=1 for v in data['studies'].values())
    finally:r.close()


def test_forming_is_separate_and_wrong_source_is_not_rendered(canvas):
    _,c=canvas;forming=dict(rows(181)[-1],scope_id='scope',source_epoch='epoch',maturity='FORMING')
    c.set_forming(forming);assert c.forming and len(c.bars)==180 and not c.grab().isNull()
    c.set_forming(dict(forming,source_epoch='other'));assert c.forming is None
    c.set_forming(dict(forming,high='NaN'));assert c.forming is None


def test_csv_retains_exact_observations_without_prices_or_volumes_invented():
    data=rows(2);data[0]['tick_volume']=None
    parsed=list(csv.DictReader(io.StringIO(chart_csv(data))))
    assert parsed[0]['open']==data[0]['open'] and parsed[0]['tick_volume']==''
    assert parsed[1]['tick_volume']==str(data[1]['tick_volume']) and parsed[1]['origin']=='SYNTHETIC_FIXTURE'


def test_chart_toolbar_actions_and_compact_geometry_do_not_issue_orders():
    app=QApplication.instance() or QApplication([]);r=fixture_runtime();w=create_main_window(r);w.resize(960,640);w.show();app.processEvents()
    try:
        p=w.main_tabs.widget(0).widget(0).widget();p.refresh()
        p.style.setCurrentText('Line');assert p.canvas.style=='Line'
        p.study_actions['SMA 20'].setChecked(True);assert 'SMA 20' in p.canvas.studies
        p.volume_action.setChecked(True);assert p.canvas.volume
        p._tool('Ruler');assert p.canvas.tool=='Ruler'
        assert p.connection.isVisible() and 'Connection' in p.connection.text()
        assert w.main_tabs.widget(0).widget(0).verticalScrollBar().maximum()==0
        for button in (p.zoom_in,p.zoom_out,p.latest,p.fit,p.study_button,p.tools_button,p.export_button):
            assert p.rect().contains(button.geometry()) and button.isVisible()
        assert not r.connector.workers and not r.database.orders()
    finally:w.close();r.close();app.processEvents()


def test_closed_market_verifier_never_promotes_stale_open_unknown_or_other_epoch():
    spec=importlib.util.spec_from_file_location('verify',Path(__file__).resolve().parents[1]/'scripts/verify_ctrader_feed.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    quotes={s:{'current_connection_epoch':True,'fresh':False,'future':False} for s in PAIRS};history={s:{f:1 for f in FRAMES} for s in PAIRS};feed={'completed_history_jobs':28,'failed_history_jobs':0};sessions={s:{'market_open':False} for s in PAIRS}
    f=module.acceptance_result
    assert f(quotes,history,feed,sessions)=='PARTIAL_DATA'
    assert f(quotes,history,feed,sessions,allow_market_closed=True)=='PASS_CLOSED_MARKET_SNAPSHOTS_AND_HISTORY'
    for bad in (True,None):
        sessions['EURUSD']['market_open']=bad
        assert f(quotes,history,feed,sessions,allow_market_closed=True)=='PARTIAL_DATA'
    sessions['EURUSD']['market_open']=False;quotes['EURUSD']['current_connection_epoch']=False
    assert f(quotes,history,feed,sessions,allow_market_closed=True)=='PARTIAL_DATA'


def test_real_export_buttons_and_date_dialog_are_exercised(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QFileDialog,QDialog,QDateTimeEdit
    from PySide6.QtCore import QTimer
    app=QApplication.instance() or QApplication([]);r=fixture_runtime();w=create_main_window(r);w.show();app.processEvents()
    try:
        p=w.main_tabs.widget(0).widget(0).widget();p.refresh()
        csv_path=tmp_path/'observed.csv';png_path=tmp_path/'chart.png'
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(str(csv_path),'CSV'))
        p._export_csv();assert len(list(csv.DictReader(io.StringIO(csv_path.read_text()))))==len(p.canvas.bars)
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(str(png_path),'PNG'))
        p._export_image();assert png_path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        def accept():
            dialog=app.activeModalWidget();assert isinstance(dialog,QDialog)
            field=dialog.findChild(QDateTimeEdit);assert field.minimumDateTime()<=field.maximumDateTime();dialog.accept()
        QTimer.singleShot(20,accept);p._go_to()
        p._tool('Ruler');QTest.keyClick(p.canvas,Qt.Key_Escape);assert p.tool_actions['Pan'].isChecked() and p.tools_button.text()=='Tools'
        assert not r.database.orders() and not r.connector.workers
    finally:w.close();r.close();app.processEvents()

