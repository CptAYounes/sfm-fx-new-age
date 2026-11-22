"""Synthetic-only tool/remembered-login acceptance. No external cTrader requests."""
import os,json,stat,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from decimal import Decimal
from io import BytesIO
from threading import Event,Thread
import pytest
from PySide6.QtCore import QCoreApplication,QEvent,QPoint
from PySide6.QtWidgets import QApplication,QLineEdit
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.connector.oauth import OAuthConfig,SecretStore
from sfm_fx_new_age.services.tool_calculator import calculate,convert_pnl,PAIRS
from sfm_fx_new_age.tabs.tab2.workspace import ToolsWorkspace,ToolDefinition
from sfm_fx_new_age.tabs.tab2.calculator import CalculatorWidget
from sfm_fx_new_age.ui.feed_connection import FeedDialog
from test_connector_boundary import connected


def app():return QApplication.instance() or QApplication([])
def drain():app().processEvents();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app().processEvents()


@pytest.mark.parametrize('pair,side,entry,exit,lots,pnl,pips',[
 ('EURUSD','BUY','1.1','1.101','.10','10','10'),('EURUSD','SELL','1.1','1.101','.10','-10','-10'),
 ('USDJPY','BUY','150','150.1','.10','1000','10'),('EURGBP','SELL','.86','.859','.01','1','10')])
def test_deb_calculator_decimal_parity(pair,side,entry,exit,lots,pnl,pips):
    value=calculate(pair,side,entry,exit,lots)
    assert value['pnl']==Decimal(pnl) and value['pips']==Decimal(pips)
    assert convert_pnl(value['pnl'],value['quote'],'Quote currency','')==value['pnl']
    assert convert_pnl(value['pnl'],value['quote'],'CAD','1.2')==Decimal(pnl)*Decimal('1.2')


@pytest.mark.parametrize('bad',['0','.001','1.01','NaN','Infinity','garbage'])
def test_calculator_rejects_invalid_lots(bad):
    with pytest.raises(ValueError):calculate('EURUSD','BUY','1.1','1.2',bad)


def test_calculator_pair_memory_and_manual_conversion():
    app();tool=CalculatorWidget()
    try:
        assert tool.pair.count()==len(PAIRS)
        tool.inputs['entry'].setText('1.10');tool.inputs['exit'].setText('1.101')
        assert tool.result.text()=='+10.00 USD'
        tool.pair.setCurrentText('USDJPY');assert not tool.inputs['entry'].text()
        tool.inputs['entry'].setText('150');tool.inputs['exit'].setText('150.1')
        assert tool.result.text()=='+1,000.00 JPY'
        tool.pair.setCurrentText('EURUSD');assert tool.inputs['entry'].text()=='1.10'
        tool.account.setCurrentText('CAD');assert tool.result.text()=='—'
        tool.rate.setText('1.4');assert tool.result.text()=='+14.00 CAD'
        tool.reset();assert tool.result.text()=='—'
    finally:tool.close()


def test_tools_open_close_reopen_and_multiple_registered_widgets_stay_in_container():
    app();definitions=(ToolDefinition('first','First calculator',CalculatorWidget),ToolDefinition('second','Second calculator',CalculatorWidget))
    workspace=ToolsWorkspace(definitions=definitions);workspace.resize(900,650);workspace.show();drain()
    try:
        a=workspace.open_tool('first');b=workspace.open_tool('second');drain()
        assert workspace.open_tool('first') is a and len(workspace.area.subWindowList())==2
        assert all(frame.mdiArea() is workspace.area for frame in (a,b))
        workspace.arrange();drain()
        assert a.parentWidget() is workspace.area.viewport() and not a.isWindow()
        a.close();drain();assert 'first' not in workspace.windows
        reopened=workspace.open_tool('first');assert reopened is not a
        workspace.close_tools();drain();assert not workspace.area.subWindowList() and not workspace.windows
        assert workspace.empty.isVisible()
        with pytest.raises(ValueError):workspace.open_tool('unregistered')
    finally:workspace.dispose();workspace.close();drain()


def test_tools_keep_state_across_main_tab_changes_without_execution(runtime):
    app();window=create_main_window(runtime);window.resize(960,640);window.show();drain()
    try:
        window.main_tabs.setCurrentIndex(1);frame=window.tools.open_tool('forex-calculator');drain()
        tool=frame.widget().widget();tool.inputs['entry'].setText('1.1');tool.inputs['exit'].setText('1.101')
        assert tool.result.text()=='+10.00 USD'
        drain()
        assert frame.widget().verticalScrollBar().maximum()==0
        assert frame.geometry().bottom()<=window.tools.area.viewport().height()
        assert window.tools.area.background().color().name()=='#0b1220'
        window.main_tabs.setCurrentIndex(0);window.main_tabs.setCurrentIndex(1);drain()
        assert window.tools.windows['forex-calculator'] is frame and tool.result.text()=='+10.00 USD'
        assert not window.view_toolbar.isVisible() and not window.chart_tabs.isVisible()
        assert not runtime.orders.transport.submissions and not runtime.database.orders()
        assert len(runtime.api(2).definitions)==10 and len(runtime.api(2).snapshot('2.2').data['rows'])==44
    finally:window.close();drain()


class OfflineWorker:
    def __init__(self,config):self.config=config;self.sent=[];self.started=False;self.closed=False
    def start(self):self.started=True
    def send(self,body):self.sent.append(body)
    def poll(self):return []
    def close(self):self.closed=True


def seed_login(directory,*,expired=False,remember=True):
    r=ApplicationRuntime(directory/'state.sqlite');store=SecretStore(directory/'private'/'login.json')
    store.save({'client_secret':'SYNTHETIC_APP_ONLY','access_token':'SYNTHETIC_ACCESS_ONLY','refresh_token':'SYNTHETIC_REFRESH_ONLY','expires_at':time.time()+(-100 if expired else 3600)})
    r.connector.configure(OAuthConfig('SYNTHETIC_CLIENT','http://127.0.0.1:49151/callback'),store)
    r.connector.remember(remember);r.close();return store


def finish_auth(r):
    assert r.connector.auth_worker;r.connector.auth_worker.join(timeout=5)
    assert not r.connector.auth_worker.is_alive();r.pump()


@pytest.mark.parametrize('remember',[False,True])
def test_restart_requires_saved_consent_and_does_not_restore_auth_from_metadata(tmp_path,remember):
    store=seed_login(tmp_path,remember=remember);r=ApplicationRuntime(tmp_path/'state.sqlite');r.connector.worker_factory=OfflineWorker
    try:
        assert r.accounts.current is None and not r.connector.workers
        r.connector.resume_saved_session()
        if remember:
            finish_auth(r);assert set(r.connector.workers)=={'LIVE','DEMO'}
            assert all(w.started for w in r.connector.workers.values())
        else:assert not r.connector.auth_worker and not r.connector.workers
        r.connector.resume_saved_session() # idempotent, never spawn a duplicate
        assert r.accounts.current is None and not r.database.orders()
        assert 'SYNTHETIC_ACCESS_ONLY' not in json.dumps(r.database.list('setting'))
        assert stat.S_IMODE(store.path.stat().st_mode)==0o600
    finally:r.close()


def test_expired_token_refresh_rotation_is_saved_without_browser(tmp_path):
    store=seed_login(tmp_path,expired=True);r=ApplicationRuntime(tmp_path/'state.sqlite');r.connector.worker_factory=OfflineWorker;calls=[]
    def request(url,timeout):
        calls.append(True);return BytesIO(json.dumps({'accessToken':'SYNTHETIC_ROTATED_ACCESS','refreshToken':'SYNTHETIC_ROTATED_REFRESH','expiresIn':600}).encode())
    r.connector.oauth.request=request
    try:
        r.connector.resume_saved_session();finish_auth(r)
        assert len(calls)==1 and store.load()['refresh_token']=='SYNTHETIC_ROTATED_REFRESH'
        assert r.connector.workers and not r.database.orders()
        assert not r.connector.oauth.server
    finally:r.close()


def test_failed_saved_refresh_requires_sign_in_no_blind_retry(tmp_path):
    seed_login(tmp_path,expired=True);r=ApplicationRuntime(tmp_path/'state.sqlite');calls=[]
    def request(url,timeout):calls.append(True);raise OSError('SYNTHETIC_FAILURE')
    r.connector.oauth.request=request;r.connector.worker_factory=OfflineWorker
    try:
        r.connector.resume_saved_session();finish_auth(r)
        assert r.connector.state=='CONNECTION_FAILED' and not r.connector.workers
        for _ in range(3):r.pump();r.connector.resume_saved_session()
        assert len(calls)==1 and not r.database.orders()
    finally:r.close()


def test_sign_out_deletes_tokens_keeps_app_and_cancels_late_start(tmp_path):
    store=seed_login(tmp_path);r=ApplicationRuntime(tmp_path/'state.sqlite');r.connector.worker_factory=OfflineWorker
    try:
        generation=r.connector._generation;saved=store.load()
        result=r.api(4).command('4.5','SIGN_OUT_CTRADER');assert result.status.value=='ACCEPTED'
        r.connector._start_if_current(saved,generation)
        assert r.connector.state=='SIGNED_OUT' and not r.connector.workers and not r.connector.preferences['enabled']
        assert store.load()=={'client_secret':'SYNTHETIC_APP_ONLY'}
        assert not r.database.orders()
    finally:r.close()
    r=ApplicationRuntime(tmp_path/'state.sqlite')
    try:r.connector.resume_saved_session();assert not r.connector.workers and not r.connector.session_available
    finally:r.close()


def test_logout_during_token_exchange_cannot_restore_credentials(tmp_path):
    store=seed_login(tmp_path,expired=True);r=ApplicationRuntime(tmp_path/'state.sqlite');entered=Event();release=Event()
    def request(url,timeout):
        entered.set();assert release.wait(4);return BytesIO(json.dumps({'accessToken':'SYNTHETIC_LATE_ACCESS','refreshToken':'SYNTHETIC_LATE_REFRESH','expiresIn':600}).encode())
    r.connector.oauth.request=request;r.connector.worker_factory=OfflineWorker
    try:
        r.connector.resume_saved_session();assert entered.wait(3);r.connector.sign_out();release.set();finish_auth(r)
        assert store.load()=={'client_secret':'SYNTHETIC_APP_ONLY'} and not r.connector.workers
        assert r.connector.state=='SIGNED_OUT'
    finally:release.set();r.close()


def test_oauth_callback_is_consumed_without_open_dialog(tmp_path):
    store=seed_login(tmp_path);r=ApplicationRuntime(tmp_path/'state.sqlite');r.connector.worker_factory=OfflineWorker
    try:
        r.connector.oauth.last_status='TOKEN_STORED';r.connector.poll();finish_auth(r)
        workers=dict(r.connector.workers)
        for _ in range(3):r.connector.poll()
        assert r.connector.workers==workers and not r.database.orders()
    finally:r.close()


def test_exact_saved_account_feed_resume_does_not_choose_other_scope(connected):
    r,event=connected;c=r.connector;live=r.accounts.current.scope_id
    r.accounts.unselect();c._resume_scope='UNKNOWN_SCOPE';c.poll();assert r.accounts.current is None
    c._resume_scope=live;c.poll()
    assert r.accounts.current.scope_id==live and live in c.feed_intents
    assert c.feed_status()['history_jobs']==4 and not r.database.orders()
    assert not any(m['kind'] in {'NEW_LIMIT','CANCEL'} for w in c.workers.values() for m in w.sent)


def test_first_login_multiple_accounts_never_auto_selects(connected):
    r,event=connected;r.accounts.unselect();c=r.connector;c._auto_select_single=True;c.poll()
    assert r.accounts.current is None and not c.feed_intents


def test_profile_import_is_private_and_never_trusts_imported_account_tokens(tmp_path):
    appfile=SecretStore(tmp_path/'source-private'/'app.json')
    appfile.save({'client_id':'SYNTHETIC_CLIENT','client_secret':'SYNTHETIC_APP_ONLY','redirect_uri':'http://127.0.0.1:49151/callback','access_token':'SYNTHETIC_FOREIGN_ACCOUNT_TOKEN'})
    r=ApplicationRuntime(tmp_path/'state.sqlite')
    try:
        result=r.api(2).command('2.3','IMPORT_CTRADER_PROFILE',{'path':str(appfile.path)})
        assert result.status.value=='ACCEPTED'
        assert r.connector.oauth.store.load()=={'client_secret':'SYNTHETIC_APP_ONLY'}
        assert not r.connector.workers and not r.connector.session_available
        assert 'SYNTHETIC_APP_ONLY' not in json.dumps(r.database.list('setting'))
        appfile.path.chmod(0o644)
        result=r.api(2).command('2.3','IMPORT_CTRADER_PROFILE',{'path':str(appfile.path)})
        assert result.status.value=='REJECTED' and '0600' in result.message
        assert 'SYNTHETIC_APP_ONLY' not in result.message
    finally:r.close()


def test_login_dialog_is_browser_first_without_credentials_form(tmp_path,monkeypatch):
    app();seed_login(tmp_path,remember=False);r=ApplicationRuntime(tmp_path/'state.sqlite');r.connector.worker_factory=OfflineWorker
    dialog=FeedDialog(r.api(2),r.api(4));dialog.show();drain()
    try:
        assert not dialog.findChildren(QLineEdit) and not dialog.setup.isVisible()
        dialog.remember.setChecked(True);dialog.login.click();finish_auth(r)
        assert r.connector.preferences['enabled'] and r.connector.workers and not r.database.orders()
        dialog.sign_out.click();assert not r.connector.session_available and not r.connector.workers
    finally:dialog.close();r.close();drain()


def test_tool_close_releases_only_its_own_scoped_subscriptions(runtime):
    app();from sfm_fx_new_age.tabs.base import TabPlugin
    from PySide6.QtWidgets import QLabel
    seen=[];apis=[]
    def factory(api,parent):
        apis.append(api);api.subscribe_snapshots('2.1',seen.append);return QLabel('Read-only tool',parent)
    workspace=ToolsWorkspace(definitions=(ToolDefinition('scoped','Scoped',factory),),api_factory=lambda:runtime.api(2))
    baseline=runtime.router.metrics()['subscriber_count'];frame=workspace.open_tool('scoped')
    assert runtime.router.metrics()['subscriber_count']>baseline
    frame.close();drain()
    assert apis[0]._closed and runtime.router.metrics()['subscriber_count']==baseline
    assert not runtime.closed
    workspace.close();drain()


def test_top_card_starts_browser_and_callback_continues_after_dialog_closed(tmp_path,monkeypatch):
    import socket
    from urllib.parse import urlparse,parse_qs,urlencode
    from PySide6.QtGui import QDesktopServices
    app();r=ApplicationRuntime(tmp_path/'state.sqlite');store=SecretStore(tmp_path/'private'/'login.json');store.save({'client_secret':'SYNTHETIC_APP_ONLY'})
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    r.connector.configure(OAuthConfig('SYNTHETIC_CLIENT',f'http://127.0.0.1:{port}/callback'),store);r.connector.worker_factory=OfflineWorker
    r.connector.oauth.request=lambda url,timeout:BytesIO(json.dumps({'accessToken':'SYNTHETIC_CALLBACK_ACCESS','refreshToken':'SYNTHETIC_CALLBACK_REFRESH','expiresIn':600}).encode())
    opened=[];monkeypatch.setattr(QDesktopServices,'openUrl',lambda url:opened.append(url.toString()) or True)
    window=create_main_window(r);window.show();drain()
    try:
        window.feed_card.button.click();drain();assert len(opened)==1
        state=parse_qs(urlparse(opened[0]).query)['state'][0];assert urlparse(opened[0]).hostname=='id.ctrader.com'
        window.feed_dialog.close();r.connector.oauth.accept_callback('/callback?'+urlencode({'code':'SYNTHETIC_CODE','state':state}))
        r.connector.poll();finish_auth(r)
        assert r.connector.workers and store.load().get('refresh_token')=='SYNTHETIC_CALLBACK_REFRESH'
        assert not r.database.orders()
    finally:window.close();r.close();drain()


@pytest.mark.parametrize('failure',['expired','exchange'])
def test_browser_failure_reenables_login(tmp_path,failure):
    seed_login(tmp_path);r=ApplicationRuntime(tmp_path/'state.sqlite')
    try:
        r.connector.state='WAITING_FOR_HUMAN';r.connector.oauth.last_status='TOKEN_EXCHANGE_FAILED' if failure=='exchange' else 'WAITING_FOR_HUMAN'
        r.connector.oauth.expires=time.monotonic()-1 if failure=='expired' else time.monotonic()+10
        r.connector.poll();assert r.connector.state=='LOGIN_REQUIRED' and not r.connector.workers
    finally:r.close()


def test_single_account_first_login_waits_for_both_endpoint_inventories(connected):
    r,event=connected;c=r.connector;r.accounts.unselect()
    demo=next(a for a in r.accounts.sessions.values() if a.endpoint_class=='DEMO')
    r.accounts.sessions.pop(demo.scope_id);c.native.pop(('DEMO','123'));c._account_lists_seen={'LIVE'};c._auto_select_single=True
    c.poll();assert r.accounts.current is None
    c._account_lists_seen.add('DEMO');c.poll()
    assert r.accounts.current.endpoint_class=='LIVE' and c.feed_status()['history_jobs']==4
    assert not r.database.orders()


def test_authorization_revoked_drops_account_without_order_replay(connected):
    r,event=connected;event('ProtoOAAccountsTokenInvalidatedEvent',{})
    assert r.accounts.current is None and not r.connector.workers and r.connector.state=='LOGIN_REQUIRED'
    assert not r.database.orders()


def test_tool_registration_is_lane_scoped_and_duplicate_safe():
    from sfm_fx_new_age.tabs.base import TabPlugin
    factory=lambda *args:None
    with pytest.raises(ValueError):TabPlugin(1).register_tool('one','One',factory)
    plugin=TabPlugin(2);plugin.register_tool('one','One',factory)
    with pytest.raises(ValueError):plugin.register_tool('one','One',factory)


def test_old_exchange_cannot_overwrite_reopened_login_generation(tmp_path):
    from sfm_fx_new_age.connector.oauth import OAuthSession
    store=SecretStore(tmp_path/'private'/'login.json');store.save({'client_secret':'SYNTHETIC_APP_ONLY'})
    entered=Event();release=Event();errors=[]
    def request(url,timeout):
        entered.set();assert release.wait(3);return BytesIO(json.dumps({'accessToken':'SYNTHETIC_OLD_ACCESS','refreshToken':'SYNTHETIC_OLD_REFRESH','expiresIn':600}).encode())
    session=OAuthSession(OAuthConfig('SYNTHETIC_CLIENT','http://127.0.0.1:49151/callback'),store,request=request)
    def exchange():
        try:session._exchange({'grant_type':'authorization_code','code':'SYNTHETIC_OLD_CODE'})
        except ValueError:errors.append(True)
    thread=Thread(target=exchange);thread.start()
    try:
        assert entered.wait(2);session.close();session.closed=False;session.last_status='WAITING_FOR_HUMAN';release.set();thread.join(timeout=4)
        assert errors==[True] and store.load()=={'client_secret':'SYNTHETIC_APP_ONLY'}
        assert session.last_status=='WAITING_FOR_HUMAN'
    finally:release.set();thread.join(timeout=4);session.close()
