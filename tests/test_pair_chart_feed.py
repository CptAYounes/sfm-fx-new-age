"""Offline UI/feed acceptance. Recording protocol workers never open broker sockets."""
import json
import os
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QPoint,QPointF,Qt
from PySide6.QtGui import QWheelEvent,QMouseEvent
from PySide6.QtCore import QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QLabel,QLineEdit

from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.domain import PAIRS
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.connector.oauth import OAuthConfig,SecretStore
from sfm_fx_new_age.testing.fixtures import fixture_runtime,FIXTURE_NOW
from sfm_fx_new_age.ui.chart_workspace import CandleCanvas,ChartPanel,CHART_LABELS
from test_connector_boundary import connected

@pytest.fixture
def shell():
    app=QApplication.instance() or QApplication([]);r=ApplicationRuntime();w=create_main_window(r);w.resize(960,640);w.show();app.processEvents()
    yield app,r,w
    w.close();r.close();app.processEvents()


def test_header_footer_are_minimal_and_feed_card_is_actionable(shell):
    app,r,w=shell
    assert w.windowTitle()=='SFM FX New Age Engine'
    assert w.findChild(QLabel,'brand').text()==w.windowTitle()
    assert w.statusBar().currentMessage()=='cTrader adapter disconnected'
    assert not any('Forex research ·' in l.text() or 'Shared Tab API' in l.text() for l in w.findChildren(QLabel))
    w.feed_card.button.click();app.processEvents();d=w.feed_dialog
    assert d.isVisible() and not r.connector.workers and r.connector.oauth is None
    assert not d.feed.isEnabled() and not d.login.isEnabled()
    assert not d.accounts.isEnabled()
    assert all('token' not in e.objectName().lower() and e.echoMode()==QLineEdit.Normal for e in d.findChildren(QLineEdit))
    assert d.geometry().width()<=960


def test_active_pairs_expose_all_ten_chart_views_without_changing_42_contract(shell):
    app,r,w=shell
    assert [len(r.api(i).definitions) for i in (1,2,3,4)]==[10,10,13,9]
    assert [w.subtab_picker.itemText(i) for i in range(len(PAIRS))]==list(PAIRS)
    assert [w.chart_tabs.tabText(i) for i in range(10)]==list(CHART_LABELS)
    seen=set()
    for pair_index,pair in enumerate(PAIRS):
        w.subtab_picker.setCurrentIndex(pair_index)
        for index in range(10):
            w.chart_tabs.setCurrentIndex(index);app.processEvents()
            panel=w.main_tabs.widget(0).widget(index).widget()
            assert isinstance(panel,ChartPanel) and pair in panel.heading.text()
            assert not panel.canvas.bars and not panel.fit.isEnabled()
            assert w.main_tabs.widget(0).widget(index).verticalScrollBar().maximum()==0
            seen.add((pair,panel.model.subtab_id))
    assert len(seen)==len(PAIRS)*10 and not r.connector.workers and not r.database.orders()


def test_pair_chart_selection_is_remembered_independently(shell):
    app,r,w=shell
    w.chart_tabs.setCurrentIndex(2);w.subtab_picker.setCurrentIndex(1)
    assert w.chart_tabs.currentIndex()==0
    w.chart_tabs.setCurrentIndex(3);w.subtab_picker.setCurrentIndex(0)
    assert w.chart_tabs.currentIndex()==2
    w.subtab_picker.setCurrentIndex(1)
    assert w.chart_tabs.currentIndex()==3
    w.main_tabs.setCurrentIndex(1);app.processEvents()
    assert not w.chart_tabs.isVisible() and not w.view_toolbar.isVisible()
    w.main_tabs.setCurrentIndex(0);app.processEvents()
    assert w.chart_tabs.isVisible() and w.subtab_picker.currentText()=='GBPUSD'


def test_chart_uses_only_causal_source_scoped_bars_and_clears_on_epoch_switch():
    r=fixture_runtime()
    try:
        api=r.api(1);data=thaw(api.query('1.3',DataRequest('chart',timeframe='D1')))
        assert data['rows'] and data['origin']=='SYNTHETIC_FIXTURE'
        assert all(v['source_epoch']==data['source_epoch'] and v['scope_id']==data['scope_id'] for v in data['rows'])
        historic=thaw(api.query('1.3',DataRequest('chart',timeframe='D1',as_of='2026-11-01T00:00:00Z')))
        assert not historic['rows'] and 'orders' not in historic and 'positions' not in historic
        r.market.activate_source('EURUSD','new-fixture-epoch','SYNTHETIC_FIXTURE')
        assert not thaw(api.query('1.3',DataRequest('chart',timeframe='D1')))['rows']
        api.close()
    finally:r.close()


def test_h1_opt_in_is_available_from_the_chart(shell):
    app,r,w=shell
    w.chart_tabs.setCurrentIndex(4);app.processEvents();p=w.main_tabs.widget(0).widget(4).widget()
    assert p.enable_h1.isVisible() and 'disabled' in p.canvas.empty
    p.enable_h1.click();app.processEvents()
    assert r.consumers.enabled('display.1.5') and not p.enable_h1.isVisible()


def test_chart_canvas_zoom_pan_fit_hover_and_sparse_center(shell):
    app,_,_=shell;c=CandleCanvas();c.resize(780,360);c.show()
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    rows=[dict(open_time=(start+timedelta(hours=i)).isoformat(),open='1.1000',high='1.1020',low='1.0990',close='1.1010') for i in range(100)]
    c.set_data(rows,'SYNTHETIC FIXTURE · EURUSD',('fixture','epoch'));app.processEvents();assert not c.grab().isNull()
    pos=c.plot_rect().center()
    QApplication.sendEvent(c,QMouseEvent(QEvent.MouseMove,pos,pos,Qt.NoButton,Qt.NoButton,Qt.NoModifier));assert c.mouse is not None
    before=c.window
    wheel=QWheelEvent(QPointF(200,120),QPointF(200,120),QPoint(),QPoint(0,120),Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
    QApplication.sendEvent(c,wheel);assert c.window<before
    QTest.mousePress(c,Qt.LeftButton,pos=QPoint(200,120))
    QApplication.sendEvent(c,QMouseEvent(QEvent.MouseMove,QPointF(300,120),QPointF(300,120),Qt.NoButton,Qt.LeftButton,Qt.NoModifier))
    QTest.mouseRelease(c,Qt.LeftButton,pos=QPoint(300,120));assert c.offset>0
    c.fit();assert c.offset==0
    c.set_data(rows[:1],'SYNTHETIC FIXTURE',('fixture','sparse'));app.processEvents();c.grab()
    area,_,step,_,_,offset=c._bounds
    assert abs(offset+step*.5-area.center().x())<1
    c.close()


def test_start_feed_requires_selected_authenticated_account(shell):
    _,r,_=shell
    result=r.api(2).command('2.3','START_MARKET_FEED',{})
    assert result.status.value=='REJECTED' and 'authenticated' in result.message
    assert not r.connector.workers and not r.database.orders()


def test_feed_start_only_sends_read_subscriptions_and_bounded_history(connected):
    r,event=connected;c=r.connector;account=r.accounts.current
    for worker in c.workers.values():worker.sent.clear()
    r.api(2).command('2.3','START_MARKET_FEED',{})
    sent=[m for worker in c.workers.values() for m in worker.sent]
    assert len([m for m in sent if m.get('name')=='ProtoOAGetTrendbarsReq'])==4
    assert {m['payload']['period'] for m in sent if m.get('name')=='ProtoOAGetTrendbarsReq'}=={'W1','D1','H4','H1'}
    assert all(m['kind']=='READ' for m in sent) and not r.database.orders()
    before=len(sent);r.api(2).command('2.3','START_MARKET_FEED',{})
    assert sum(len(w.sent) for w in c.workers.values())==before
    status=c.feed_status();assert status['history_jobs']==4 and len(status['missing_metadata'])==len(PAIRS)-1
    assert set(c.feed_intents)=={account.scope_id}
    r.api(2).command('2.3','DISCONNECT_FEED',{})
    assert not c.workers and not c.feed_intents and r.accounts.current is None


def test_feed_dialog_account_selection_supports_live_and_demo_without_orders(connected):
    app=QApplication.instance() or QApplication([]);r,_=connected;w=create_main_window(r);w.show();w.open_feed();d=w.feed_dialog;app.processEvents()
    try:
        assert d.accounts.count()==3 and not d.feed.isEnabled()
        for index in range(1,d.accounts.count()):
            d.accounts.setCurrentIndex(index);d.feed.click();app.processEvents()
            assert r.accounts.current.scope_id==d.accounts.currentData()
            assert r.connector.feed_status()['history_jobs']==4
        assert {r['context'].account_type for r in r.connector.native.values()}=={'LIVE','DEMO'}
        assert not r.database.orders()
    finally:w.close();app.processEvents()


def test_native_history_response_reaches_source_bound_chart(connected):
    r,event=connected;c=r.connector;c.start_market_feed()
    request_id,request=next((i,q) for i,q in c.requests.items() if q['name']=='ProtoOAGetTrendbarsReq' and q['payload']['period']=='D1')
    opened=datetime(2026,11,4,tzinfo=timezone.utc)
    event('ProtoOAGetTrendbarsRes',{'ctidTraderAccountId':'123','trendbar':[{'utcTimestampInMinutes':int(opened.timestamp()/60),'low':'109900','deltaOpen':'100','deltaHigh':'300','deltaClose':'200','volume':'42'}]},request_id=request_id)
    data=thaw(r.api(1).query('1.3',DataRequest('chart',timeframe='D1')))
    assert len(data['rows'])==1 and data['origin']=='LIVE_OBSERVED'
    assert data['rows'][0]['close']=='1.101' and data['scope_id']==r.accounts.current.scope_id
    assert not r.database.orders()


def test_public_connection_profile_survives_restart_without_authentication(tmp_path):
    db=tmp_path/'state.sqlite';private=tmp_path/'private';private.mkdir(mode=0o700)
    store=SecretStore(private/'credential.json');store.save({'client_secret':'SYNTHETIC_TEST_NOT_A_REAL_SECRET'})
    r=ApplicationRuntime(db);r.connector.configure(OAuthConfig('SYNTHETIC_TEST_CLIENT','http://127.0.0.1:8765/callback','accounts'),store);r.close()
    r=ApplicationRuntime(db)
    try:
        status=r.connector.status()
        assert status['configuration']['client_id']=='SYNTHETIC_TEST_CLIENT'
        assert status['state']=='CONFIGURED' and not status['network_started'] and r.accounts.current is None
        assert 'SYNTHETIC_TEST_NOT_A_REAL_SECRET' not in json.dumps(r.database.list('setting'))
    finally:r.close()


def test_missing_credential_file_is_actionable_without_exposing_material(tmp_path):
    r=ApplicationRuntime(tmp_path/'state.sqlite')
    try:
        result=r.api(4).command('4.5','HUMAN_OAUTH_LOGIN',{'client_id':'SYNTHETIC_TEST_CLIENT','redirect_uri':'http://127.0.0.1:8765/callback','credential_path':str(tmp_path/'missing.json'),'scope':'accounts'})
        assert result.status.value=='REJECTED' and 'private credential JSON file' in result.message
        assert r.connector.oauth is None and not r.connector.workers
    finally:r.close()


@pytest.mark.parametrize('failure',['request','timeout'])
def test_feed_history_failure_is_explicit_and_not_blindly_retried(connected,failure):
    r,_=connected;c=r.connector;c.start_market_feed()
    identity,request=next((i,q) for i,q in c.requests.items() if q['name']=='ProtoOAGetTrendbarsReq')
    before=sum(m.get('name')=='ProtoOAGetTrendbarsReq' for w in c.workers.values() for m in w.sent)
    if failure=='request':c.handle('LIVE',{'kind':'REQUEST_FAILED','request_id':identity,'error_type':'SYNTHETIC_TEST_FAILURE'})
    else:request['sent']-=35;c.poll()
    status=c.feed_status()
    assert status['state']=='HISTORY_INCOMPLETE' and status['failed_history_jobs']==1
    assert r.database.get('backfill',request['context']['job_id'])['status']=='FAILED'
    c.start_market_feed();assert sum(m.get('name')=='ProtoOAGetTrendbarsReq' for w in c.workers.values() for m in w.sent)==before
    assert not r.database.orders()


def test_reopening_browser_login_does_not_overwrite_remember_preference(shell,tmp_path,monkeypatch):
    app,r,w=shell
    r.connector.configure(OAuthConfig('SYNTHETIC_CLIENT','http://127.0.0.1:8765/callback','trading'),SecretStore(tmp_path/'private.json'))
    monkeypatch.setattr(r.connector,'begin_oauth',lambda:None) # Never start a browser/listener from this settings test.
    w.open_feed();d=w.feed_dialog;assert d is not None
    assert not d.setup.isVisible() and not d.findChildren(QLineEdit)
    d.remember.setChecked(False);d.refresh();assert not d.remember.isChecked()
    d.close();assert not d.timer.isActive()
    w.open_feed();assert d.isVisible() and d.timer.isActive() and not r.connector.workers


def test_chart_canvas_rejects_malformed_candles_without_substituting_data(shell):
    app,_,_=shell;c=CandleCanvas();c.resize(600,300)
    valid=dict(open_time='2026-01-01T00:00:00Z',open='1.1',high='1.2',low='1.0',close='1.15')
    c.set_data([{},dict(valid,high='NaN'),dict(valid,low='-1'),dict(valid,high='1.01'),dict(valid,open_time='not-a-timestamp')],
        'SYNTHETIC FIXTURE',('test','bad'),empty='No source data')
    assert c.bars==[] and not c.grab().isNull()
    c.close()
