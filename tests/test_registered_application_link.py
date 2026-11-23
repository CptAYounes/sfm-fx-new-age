"""Synthetic-only acceptance for existing registered Sandbox application linking."""
import os,json,socket,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import pytest
from PySide6.QtWidgets import QApplication,QLineEdit,QDialog
from sfm_fx_new_age.connector.oauth import OAuthConfig,OAuthSession,SecretStore,AUTH_URL
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.ui.session_link import ApplicationLinkDialog,link_through_api
from sfm_fx_new_age.ui.feed_connection import FeedDialog
from test_tools_and_saved_login import OfflineWorker,finish_auth
from test_connector_boundary import connected


def test_authorization_uses_documented_ctrader_id_endpoint(tmp_path):
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    session=OAuthSession(OAuthConfig('SYNTHETIC_CLIENT',f'http://127.0.0.1:{port}/callback','accounts'),SecretStore(tmp_path/'unused'/'app.json'))
    try:
        url=urlparse(session.begin());query=parse_qs(url.query)
        assert url.hostname=='id.ctrader.com' and url.path=='/my/settings/openapi/grantingaccess/'
        assert query['product']==['web'] and query['scope']==['accounts'] and query['state']
    finally:session.close()


def test_sandbox_redirect_is_usable_for_refresh_but_never_fakes_local_callback(tmp_path):
    config=OAuthConfig('SYNTHETIC_CLIENT','https://openapi.ctrader.com/apps/3414/playground','accounts')
    session=OAuthSession(config,SecretStore(tmp_path/'unused'/'app.json'))
    assert not config.loopback
    with pytest.raises(ValueError,match='Sandbox'):session.begin()
    assert session.server is None and session.state is None


@pytest.mark.parametrize('url',['https://evil.example/apps/3414/playground','https://openapi.ctrader.com.evil.example/apps/3414/playground','https://openapi.ctrader.com/apps/3414/playground?code=token','https://user:pass@openapi.ctrader.com/apps/3414/playground','http://openapi.ctrader.com/apps/3414/playground','http://127.0.0.1:8765/wrong'])
def test_sandbox_redirect_remains_exact_and_bounded(url):
    with pytest.raises(ValueError):OAuthConfig('SYNTHETIC_CLIENT',url)


def body():return {'client_id':'SYNTHETIC_CLIENT','client_secret':'SYNTHETIC_APP_SECRET','refresh_token':'SYNTHETIC_PORTAL_REFRESH','redirect_uri':'https://openapi.ctrader.com/apps/3414/playground','scope':'accounts'}


def test_explicit_portal_session_link_refreshes_once_and_keeps_secrets_out_of_journal(tmp_path):
    source=SecretStore(tmp_path/'handoff'/'portal.json');source.save(body());r=ApplicationRuntime(tmp_path/'state.sqlite');r.connector.worker_factory=OfflineWorker
    # configure creates the OAuth owner; inject an offline-only HTTP opener at construction.
    import sfm_fx_new_age.connector.service as service
    original=service.OAuthSession;calls=[]
    def request(url,timeout):
        calls.append(url);return BytesIO(json.dumps({'accessToken':'SYNTHETIC_OBSERVED_ACCESS','refreshToken':'SYNTHETIC_ROTATED_REFRESH','expiresIn':600}).encode())
    service.OAuthSession=lambda config,store:original(config,store,request=request)
    try:
        result=r.api(2).command('2.3','IMPORT_CTRADER_SESSION',{'path':str(source.path)});assert result.status.value=='ACCEPTED'
        finish_auth(r);saved=r.connector.oauth.store.load()
        assert len(calls)==1 and parse_qs(urlparse(calls[0]).query)['grant_type']==['refresh_token']
        assert saved['refresh_token']=='SYNTHETIC_ROTATED_REFRESH' and saved['expires_at']>time.time()
        assert r.connector.session_available and r.connector.preferences['enabled']
        assert set(r.connector.workers)=={'LIVE','DEMO'} and r.accounts.current is None
        assert not r.database.orders()
        dbtext=json.dumps(r.database.list('setting'))
        assert all(value not in dbtext for key,value in body().items() if key in {'client_secret','refresh_token'})
        assert 'SYNTHETIC_OBSERVED_ACCESS' not in dbtext
    finally:service.OAuthSession=original;r.close()


def test_portal_handoff_dialog_masks_credentials_and_clears_on_save_cancel():
    app=QApplication.instance() or QApplication([]);received=[]
    dialog=ApplicationLinkDialog(redirect_uri=body()['redirect_uri'],submit=lambda b:received.append(b))
    try:
        dialog.save.click();assert not received and dialog.feedback.text()
        for name,field in dialog.fields.items():
            if name!='redirect_uri':field.setText(body()[name])
        assert dialog.fields['client_secret'].echoMode()==QLineEdit.Password
        assert dialog.fields['refresh_token'].echoMode()==QLineEdit.Password
        dialog.save.click();assert received==[body()] and dialog.result()==QDialog.Accepted
        assert all(not f.text() for f in dialog.fields.values())
        dialog=ApplicationLinkDialog(redirect_uri=body()['redirect_uri'],submit=lambda b:received.append(b))
        dialog.fields['client_secret'].setText('SYNTHETIC_CANCELLED_SECRET');dialog.reject()
        assert all(not f.text() for f in dialog.fields.values())
    finally:dialog.close()


def test_private_handoff_transient_file_is_removed_and_command_contains_no_secrets(tmp_path,monkeypatch):
    calls=[];monkeypatch.setenv('TMPDIR',str(tmp_path))
    class Api:
        def command(self,view,name,payload):
            assert view=='2.3' and name=='IMPORT_CTRADER_SESSION' and set(payload)=={'path'}
            store=SecretStore(Path(payload['path']));assert store.load()==body();calls.append(store.path)
            class Result:status=type('Status',(),{'value':'ACCEPTED'})();message='Linked'
            return Result()
    assert link_through_api(Api(),body())=='Linked' and calls and not calls[0].exists()


@pytest.mark.parametrize('code,expected',[('CH_ACCESS_TOKEN_INVALID','LOGIN_REQUIRED'),('CANT_ROUTE_REQUEST','APPLICATION_AUTH_FAILED'),('INVALID_CLIENT','APPLICATION_AUTH_FAILED')])
def test_preaccount_broker_errors_are_visible_instead_of_silently_ignored(code,expected):
    r=ApplicationRuntime()
    try:
        r.connector.state='APPLICATION_AUTH'
        r.connector.handle('LIVE',{'kind':'MESSAGE','name':'ProtoOAErrorRes','payload':{'errorCode':code,'description':'SYNTHETIC_PRIVATE_DETAIL_NOT_LOGGED'}})
        status=r.connector.status()
        assert status['state']==expected and code in status['reason']
        assert status['errors'][-1]['error_code']==code
        assert 'SYNTHETIC_PRIVATE_DETAIL_NOT_LOGGED' not in json.dumps(status)
        assert not r.database.orders()
    finally:r.close()


def test_new_native_epoch_versions_calendar_and_reconnect_is_idempotent(connected):
    r,event=connected;c=r.connector;a=r.accounts.current;state=c.native[('LIVE','123')]
    old=r.continuity.calendar('EURUSD');state['epoch']='SYNTHETIC_RECONNECTED_EPOCH';state.pop('subscribed_scope',None)
    c.activate_selected();new=r.continuity.calendar('EURUSD')
    assert new.version==old.version+1 and new.calendar_id!=old.calendar_id
    c.activate_selected();assert r.continuity.calendar('EURUSD')==new
    assert not r.database.orders()


def test_native_week_wrapping_session_is_split_without_inventing_hours(connected):
    r,event=connected;c=r.connector;raw=c.native[('LIVE','123')]['specs'][1]
    raw['schedule']=[{'startSecond':500000,'endSecond':100000}];c.activate_selected()
    assert r.continuity.calendar('EURUSD').weekly_windows==((0,100000),(500000,604800))


def test_fixture_cannot_import_portal_session(runtime,tmp_path):
    source=SecretStore(tmp_path/'handoff'/'portal.json');source.save(body())
    result=runtime.api(2).command('2.3','IMPORT_CTRADER_SESSION',{'path':str(source.path)})
    assert result.status.value=='REJECTED' and not runtime.connector.workers


def test_refresh_http_uses_documented_method_without_echoing_request(monkeypatch):
    import sfm_fx_new_age.connector.oauth as oauth
    calls=[]
    class Opener:
        def open(self,request,timeout):calls.append((request.method,request.full_url,timeout))
    monkeypatch.setattr(oauth,'build_opener',lambda *handlers:Opener())
    oauth.token_http_request(oauth.TOKEN_URL+'?grant_type=refresh_token&refresh_token=SYNTHETIC',15)
    oauth.token_http_request(oauth.TOKEN_URL+'?grant_type=authorization_code&code=SYNTHETIC',15)
    assert [c[0] for c in calls]==['POST','GET']


@pytest.mark.parametrize('description,expected',[('Malformed client_id parameter','MALFORMED_CLIENT_ID'),('SYNTHETIC_SECRET_DO_NOT_ECHO','INVALID_REQUEST')])
def test_provider_error_description_is_classified_not_exported(tmp_path,description,expected):
    store=SecretStore(tmp_path/'private'/'login.json');store.save({'client_secret':'SYNTHETIC_APP_SECRET','refresh_token':'SYNTHETIC_REFRESH'})
    session=OAuthSession(OAuthConfig('SYNTHETIC_CLIENT','https://openapi.ctrader.com/apps/3414/playground'),store,
        request=lambda url,timeout:BytesIO(json.dumps({'errorCode':'INVALID_REQUEST','description':description}).encode()))
    with pytest.raises(ValueError) as error:session.refresh()
    assert session.last_error==expected and description not in str(error.value)
    assert 'access_token' not in store.load()


def test_malformed_client_id_disables_startup_retry_and_stays_user_actionable(tmp_path):
    r=ApplicationRuntime(tmp_path/'state.sqlite');store=SecretStore(tmp_path/'private'/'login.json');store.save({'client_secret':'SYNTHETIC_APP_SECRET','refresh_token':'SYNTHETIC_REFRESH'})
    try:
        r.connector.configure(OAuthConfig('SYNTHETIC_CLIENT','https://openapi.ctrader.com/apps/3414/playground'),store);r.connector.remember(True)
        r.connector.oauth.last_error='MALFORMED_CLIENT_ID';r.connector._failure_if_current('ValueError',r.connector._generation)
        assert r.connector.state=='LOGIN_REQUIRED' and not r.connector.preferences['enabled']
        assert 'Client ID' in r.connector.reason and 'SYNTHETIC' not in r.connector.reason
        assert not r.connector.workers and not r.database.orders()
    finally:r.close()


def test_feed_acceptance_refuses_unconfigured_state_without_network(tmp_path):
    import subprocess,sys
    root=Path(__file__).resolve().parents[1];receipt=tmp_path/'receipt.json'
    process=subprocess.run([sys.executable,str(root/'scripts/verify_ctrader_feed.py'),'--state-dir',str(tmp_path/'state'),'--timeout','10','--receipt',str(receipt)],cwd=root,capture_output=True,text=True,timeout=15)
    assert process.returncode==2
    summary=json.loads(receipt.read_text())
    assert summary['result']=='FAILED' and summary['error_type']=='ValueError' and not summary.get('read_request_counts')
    assert not summary['broker_writes_permitted']
