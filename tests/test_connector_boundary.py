"""SYNTHETIC PROTOCOL TESTS ONLY. No credentials, account contact or external orders."""
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from queue import Empty
from time import monotonic,sleep
import json,os,stat
import pytest

from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.connector.protocol import new_limit_request,symbol_spec,trendbar,milliseconds
from sfm_fx_new_age.connector.sdk_worker import SdkProcess,redact,verified_client
from sfm_fx_new_age.connector.oauth import SecretStore,OAuthConfig,OAuthSession
from sfm_fx_new_age.contracts.domain import Candidate,Origin,OrderState
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW


class RecordingWorker:
    def __init__(self):self.sent=[]
    def send(self,body):self.sent.append(body)
    def poll(self):return []
    def close(self):pass


@pytest.fixture
def connected():
    pytest.importorskip('ctrader_open_api',reason='Optional cTrader SDK protocol acceptance')
    r=ApplicationRuntime(clock=lambda:FIXTURE_NOW);c=r.connector
    r.orders.transport=c
    c.workers={'LIVE':RecordingWorker(),'DEMO':RecordingWorker()}
    def event(name,payload,endpoint='LIVE',request_id=''):
        c.handle(endpoint,{'kind':'MESSAGE','name':name,'payload':payload,'request_id':request_id})
    for endpoint in ('LIVE','DEMO'):
        event('ProtoOAGetAccountListByAccessTokenRes',{'permissionScope':'SCOPE_TRADE','ctidTraderAccount':[
            {'ctidTraderAccountId':'123','isLive':endpoint=='LIVE'}]},endpoint)
        event('ProtoOATraderRes',{'ctidTraderAccountId':'123','trader':{'depositAssetId':'1','brokerName':'SYNTHETIC_PROTOCOL_TEST_NO_NETWORK','accessRights':'FULL_ACCESS'}},endpoint)
        event('ProtoOAAssetListRes',{'ctidTraderAccountId':'123','asset':[{'assetId':'1','name':'USD'}]},endpoint)
        event('ProtoOASymbolsListRes',{'ctidTraderAccountId':'123','symbol':[{'symbolId':'1','symbolName':'EURUSD','enabled':True}]},endpoint)
        event('ProtoOASymbolByIdRes',{'ctidTraderAccountId':'123','symbol':[{'symbolId':'1','digits':5,'pipPosition':4,
            'minVolume':'100000','maxVolume':'100000000','stepVolume':'100000','lotSize':'10000000',
            'scheduleTimeZone':'UTC','schedule':[{'startSecond':0,'endSecond':604800}]}]},endpoint)
    assert r.accounts.current is None
    account=next(a for a in r.accounts.sessions.values() if a.endpoint_class=='LIVE')
    r.accounts.select_known(account.scope_id);c.activate_selected()
    event('ProtoOAReconcileRes',{'ctidTraderAccountId':'123','order':[],'position':[]})
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','bid':'110100','ask':'110120','timestamp':milliseconds(FIXTURE_NOW)})
    yield r,event
    r.close()


def test_discovery_preserves_endpoint_namespaces_and_never_switches_silently(connected):
    r,event=connected
    assert len(r.accounts.sessions)==2
    assert r.accounts.current.endpoint_class=='LIVE'
    assert r.connector.ready_for_issue(r.market.scope_id)
    assert r.market.spec('123','EURUSD').volume_min==1000
    assert r.market.spec('123','EURUSD').units_per_lot==100000
    assert r.market.quote('123','EURUSD').bid==Decimal('1.101')
    assert r.positions.snapshot()['complete'] is True
    assert r.positions.snapshot()['rows']==[]


def test_real_sdk_serialization_and_async_native_state_deduplication(connected):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import LIMIT,GOOD_TILL_DATE
    r,event=connected;account=r.accounts.current;epoch=r.market.authority('EURUSD')['source_epoch']
    r.signals.propose(Candidate('protocol-signal','protocol-setup',1,'EURUSD','BUY',Decimal('1.1'),Decimal('1.09'),
        Decimal('1000'),'2026-11-06T12:00:00Z',FIXTURE_NOW,epoch,Origin.LIVE_OBSERVED,scope_id=account.scope_id))
    result=r.api(4).command('4.1','ISSUE',{'signal_id':'protocol-signal','revision':1,'user_initiated':True,'acknowledge_research':True})
    order=r.database.orders()[0];assert order['state']=='UNKNOWN'
    sent=[m for m in r.connector.workers['LIVE'].sent if m['kind']=='NEW_LIMIT']
    assert len(sent)==1
    proto=ProtoOANewOrderReq();proto.ParseFromString(sent[0]['protobuf'])
    assert proto.orderType==LIMIT and proto.timeInForce==GOOD_TILL_DATE and proto.volume==100000
    assert not proto.HasField('stopLoss') and not proto.HasField('takeProfit')
    native={'orderId':'9001','clientOrderId':order['client_order_id'],'orderStatus':'ORDER_STATUS_ACCEPTED',
            'tradeData':{'symbolId':'1','volume':'100000','tradeSide':'BUY'},'utcLastUpdateTimestamp':'1000','executedVolume':'0'}
    ack={'ctidTraderAccountId':'123','executionType':'ORDER_ACCEPTED','order':native}
    event('ProtoOAExecutionEvent',ack);event('ProtoOAExecutionEvent',ack)
    assert r.database.order(order['id'])['state']=='ACCEPTED_PENDING'
    assert len(r.database.list('native_activity'))==1
    partial=dict(native,executedVolume='40000',utcLastUpdateTimestamp='2000')
    event('ProtoOAExecutionEvent',{'ctidTraderAccountId':'123','executionType':'ORDER_PARTIAL_FILL','order':partial})
    assert r.database.order(order['id'])['filled_units']=='400'
    event('ProtoOAExecutionEvent',ack) # duplicate/stale cannot undo partial fill
    assert r.database.order(order['id'])['state']=='PARTIALLY_FILLED'
    filled=dict(native,orderStatus='ORDER_STATUS_FILLED',executedVolume='100000',utcLastUpdateTimestamp='3000')
    event('ProtoOAExecutionEvent',{'ctidTraderAccountId':'123','executionType':'ORDER_FILLED','order':filled})
    assert r.database.order(order['id'])['state']=='FILLED'
    assert r.positions.snapshot()['rows']==[] # order never manufactures a position
    assert len([m for m in r.connector.workers['LIVE'].sent if m['kind']=='NEW_LIMIT'])==1


def test_disconnect_revokes_issue_and_never_replays_orders(connected):
    r,event=connected
    r.connector.handle('LIVE',{'kind':'DISCONNECTED'})
    assert r.accounts.current is None
    assert r.connector.state=='DEGRADED' # Independent DEMO endpoint remains authenticated.
    assert all(a.endpoint_class=='DEMO' for a in r.accounts.sessions.values())
    assert not [m for w in r.connector.workers.values() for m in w.sent if m['kind']=='NEW_LIMIT']


def test_protobuf_trendbar_price_scale_and_completion(connected):
    r,event=connected
    b=trendbar({'utcTimestampInMinutes':int(milliseconds('2026-11-05T08:00:00Z')/60000),
        'low':110000,'deltaOpen':20,'deltaHigh':40,'deltaClose':30},symbol='EURUSD',timeframe='H4',source_epoch='test',
        scope_id=r.market.scope_id,received_at=FIXTURE_NOW,close_time=FIXTURE_NOW)
    assert b.low==Decimal('1.1') and b.high==Decimal('1.1004')
    assert b.available_at==FIXTURE_NOW


def test_secret_store_is_private_and_rejects_symlinks(tmp_path):
    directory=tmp_path/'private';store=SecretStore(directory/'tokens.json')
    store.save({'client_secret':'SYNTHETIC_ONLY','access_token':'SYNTHETIC_ONLY'})
    assert stat.S_IMODE(store.path.stat().st_mode)==0o600
    assert stat.S_IMODE(directory.stat().st_mode)==0o700
    assert store.load()['client_secret']=='SYNTHETIC_ONLY'
    link=directory/'link.json';link.symlink_to(store.path)
    with pytest.raises((OSError,ValueError)):SecretStore(link).load()
    with pytest.raises(ValueError):SecretStore(link).save({})
    os.chmod(store.path,0o644)
    with pytest.raises(ValueError):store.load()


def test_oauth_callback_state_and_one_time_exchange(tmp_path):
    from urllib.parse import urlencode
    from io import BytesIO
    store=SecretStore(tmp_path/'private'/'tokens.json');store.save({'client_secret':'SYNTHETIC_SECRET'})
    requests=[]
    def request(url,timeout):
        requests.append((url,timeout));return BytesIO(json.dumps({'accessToken':'SYNTHETIC_TOKEN','refreshToken':'SYNTHETIC_REFRESH','expiresIn':600}).encode())
    session=OAuthSession(OAuthConfig('synthetic-client','http://127.0.0.1:49151/callback'),store,request=request)
    session.state='SYNTHETIC_STATE';session.expires=monotonic()+10
    with pytest.raises(ValueError):session.accept_callback('/callback?'+urlencode({'code':'SYNTHETIC_CODE','state':'wrong'}))
    assert requests==[]
    path='/callback?'+urlencode({'code':'SYNTHETIC_CODE','state':'SYNTHETIC_STATE'})
    session.accept_callback(path)
    assert store.load()['access_token']=='SYNTHETIC_TOKEN'
    with pytest.raises(ValueError):session.accept_callback(path)
    session.refresh();assert len(requests)==2
    assert redact({'accessToken':'test','nested':{'clientSecret':'test'},'errorCode':'OK'})=={'nested':{},'errorCode':'OK'}


def test_sdk_process_probe_exercises_actual_spawn_without_network():
    pytest.importorskip('ctrader_open_api',reason='Optional cTrader SDK process probe')
    worker=SdkProcess({},probe=True);worker.start()
    try:
        result=worker.events.get(timeout=15)
        assert result['kind']=='SDK_PROBE',result
        assert result['endpoint']=='NO_NETWORK'
        assert result['pid']!=os.getpid()
    finally:worker.close()


def test_tls_client_is_hostname_verified_without_opening_connection():
    pytest.importorskip('ctrader_open_api',reason='Optional cTrader SDK TLS construction')
    from twisted.internet import reactor
    client=verified_client('live.ctraderapi.com',5035,reactor)
    assert client.tls_hostname=='live.ctraderapi.com'
    assert client.isConnected is False


def test_one_sided_quotes_retain_independent_freshness_without_conflicting(connected):
    r,event=connected
    r.clock=lambda:'2026-11-05T12:00:00.003000Z'
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','bid':'110110','timestamp':milliseconds(FIXTURE_NOW)+1})
    quote=r.market.quote('123','EURUSD')
    assert quote.bid==Decimal('1.1011') and quote.available_at==FIXTURE_NOW
    assert quote.bid_at!=quote.ask_at
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','ask':'110130','timestamp':milliseconds(FIXTURE_NOW)+2})
    quote=r.market.quote('123','EURUSD')
    assert quote.ask==Decimal('1.1013') and milliseconds(quote.available_at)==milliseconds(FIXTURE_NOW)+1


def test_two_complete_reconciliations_at_same_clock_replace_actual_positions(connected):
    r,event=connected
    initial=r.positions.snapshot()['sequence']
    body={'ctidTraderAccountId':'123','order':[],'position':[{'positionId':'88','positionStatus':'POSITION_STATUS_OPEN','tradeData':{'symbolId':'1','tradeSide':'BUY','volume':'100000'},'price':1.1}]}
    event('ProtoOAReconcileRes',body)
    assert r.positions.snapshot()['rows'][0]['position_id']=='88'
    assert r.positions.snapshot()['sequence']>initial
    event('ProtoOAReconcileRes',{'ctidTraderAccountId':'123','order':[],'position':[]})
    assert r.positions.snapshot()['rows']==[]
    r.connector.native[('LIVE','123')]['reconciled_at']=monotonic()-61
    assert not r.connector.ready_for_issue(r.market.scope_id)


def test_invalid_native_frame_does_not_crash_owner_pump_or_retain_authority(connected):
    r,event=connected
    worker=r.connector.workers['LIVE']
    frames=[{'kind':'MESSAGE','name':'ProtoOASpotEvent','payload':{'ctidTraderAccountId':'123','symbolId':'1','bid':'malformed','timestamp':milliseconds(FIXTURE_NOW)}}]
    worker.poll=lambda:frames.copy() if frames else []
    r.pump();frames.clear()
    assert r.accounts.current is None and r.connector.errors[-1]['error_type'] in {'ValueError','InvalidOperation'}
    r.pump()
    assert not [m for w in r.connector.workers.values() for m in w.sent if m['kind']=='NEW_LIMIT']


def test_oauth_loopback_http_callback_is_one_time_and_closes_listener(tmp_path):
    from urllib.request import urlopen
    from urllib.parse import urlparse,parse_qs,urlencode
    from urllib.error import HTTPError
    from io import BytesIO
    import socket
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    calls=[]
    def request(url,timeout):
        calls.append(True)
        return BytesIO(json.dumps({'accessToken':'SYNTHETIC_TOKEN','refreshToken':'SYNTHETIC_REFRESH','expiresIn':600}).encode())
    store=SecretStore(tmp_path/'private'/'tokens.json');store.save({'client_secret':'SYNTHETIC_SECRET'})
    session=OAuthSession(OAuthConfig('synthetic-client',f'http://127.0.0.1:{port}/callback'),store,request=request)
    try:
        authorization=session.begin();state=parse_qs(urlparse(authorization).query)['state'][0]
        path=f'http://127.0.0.1:{port}/callback?'+urlencode({'code':'SYNTHETIC_CODE','state':state})
        with urlopen(path,timeout=3) as response:assert response.status==200
        with pytest.raises(HTTPError):urlopen(path,timeout=3)
        assert calls==[True]
        assert session.last_status=='TOKEN_STORED'
    finally:session.close()
    with socket.socket() as sock:assert sock.connect_ex(('127.0.0.1',port))!=0


def test_tab4_native_history_command_uses_only_read_requests_and_exposes_job(connected):
    from sfm_fx_new_age.contracts.enums import CommandStatus
    from sfm_fx_new_age.contracts.tab_data import DataRequest
    r,event=connected
    result=r.api(4).command('4.8','REFRESH_HISTORY',{'start':'2026-11-05T11:00:00Z','end':FIXTURE_NOW})
    assert result.status is CommandStatus.ACCEPTED
    for name,field,rows in [('ProtoOAOrderListRes','order',[{'orderId':'9009'}]),('ProtoOADealListRes','deal',[{'dealId':'9010'}])]:
        identity=next(key for key,value in r.connector.requests.items() if (value.get('context') or {}).get('history_job'))
        event(name,{'ctidTraderAccountId':'123',field:rows,'hasMore':False},request_id=identity)
    jobs=r.api(4).query('4.8',DataRequest('broker_history_jobs'))['rows']
    assert jobs[0]['state']=='COMPLETE'
    assert len(r.api(4).query('4.8',DataRequest('broker_history'))['rows'])==2
    assert not [m for w in r.connector.workers.values() for m in w.sent if m['kind']=='NEW_LIMIT']


def test_external_pending_orders_remain_native_inventory_not_local_adoption(connected):
    from sfm_fx_new_age.contracts.tab_data import DataRequest
    r,event=connected
    event('ProtoOAReconcileRes',{'ctidTraderAccountId':'123','order':[{'orderId':'9999'}],'position':[]})
    inventory=r.api(4).query('4.3',DataRequest('broker_pending'))
    assert inventory['status']=='LAST_KNOWN' and inventory['rows'][0]['orderId']=='9999'
    assert r.database.orders()==[]


def test_history_error_without_account_field_uses_request_context(connected):
    from sfm_fx_new_age.contracts.enums import CommandStatus
    r,event=connected
    assert r.api(4).command('4.8','REFRESH_HISTORY',{'start':'2026-11-05T11:00:00Z','end':FIXTURE_NOW}).status is CommandStatus.ACCEPTED
    identity=next(key for key,value in r.connector.requests.items() if (value.get('context') or {}).get('history_job'))
    event('ProtoOAErrorRes',{'errorCode':'SYNTHETIC_HISTORY_ERROR'},request_id=identity)
    assert r.database.list('native_history_job')[0]['state']=='REQUEST_FAILED'


def closed_pending_proposal(r,event,endpoint='LIVE'):
    """Recording SDK only: exact native calendar/epoch, no network or real order."""
    account=next(a for a in r.accounts.sessions.values() if a.endpoint_class==endpoint)
    r.accounts.select_known(account.scope_id);r.connector.activate_selected()
    event('ProtoOAReconcileRes',{'ctidTraderAccountId':'123','order':[],'position':[]},endpoint)
    raw=r.connector.native[(endpoint,'123')]['specs'][1]
    event('ProtoOASymbolByIdRes',{'ctidTraderAccountId':'123','symbol':[dict(raw,schedule=[{'startSecond':0,'endSecond':60}])]},endpoint)
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','bid':'110100','ask':'110120','timestamp':milliseconds(FIXTURE_NOW)},endpoint)
    r.clock=r.orders.clock=r.analytics.clock=lambda:'2026-11-05T12:01:00Z'
    epoch=r.market.authority('EURUSD')['source_epoch']
    identity='closed-pending-'+endpoint
    r.signals.propose(Candidate(identity,'SYNTHETIC_PROTOCOL_CLOSED_SESSION',1,'EURUSD','BUY',Decimal('1.1'),Decimal('1.09'),
        Decimal('1000'),'2026-11-06T12:00:00Z',FIXTURE_NOW,epoch,Origin.LIVE_OBSERVED,scope_id=account.scope_id))
    return identity,account,epoch


@pytest.mark.parametrize('endpoint',['LIVE','DEMO'])
@pytest.mark.parametrize('with_snapshot',[True,False])
def test_pending_limit_closed_native_session_does_not_require_live_quote(connected,endpoint,with_snapshot):
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOANewOrderReq
    from sfm_fx_new_age.contracts.enums import CommandStatus
    r,event=connected;identity,account,epoch=closed_pending_proposal(r,event,endpoint)
    if not with_snapshot:
        with r.database.transaction() as conn:conn.execute("DELETE FROM records WHERE kind='quote'")
    before=list(r.connector.workers[endpoint].sent)
    preview=r.orders.preview(identity,1,acknowledge_research=True)
    assert preview['price_validation']==('CLOSED_SESSION_LAST_SNAPSHOT_BROKER_VALIDATES_PENDING' if with_snapshot else 'CLOSED_SESSION_NO_QUOTE_BROKER_VALIDATES_PENDING')
    assert (preview['quote']['available_at']==FIXTURE_NOW) if with_snapshot else preview['quote'] is None
    assert r.database.orders()==[] and r.connector.workers[endpoint].sent==before
    result=r.api(4).command('4.1','ISSUE',{'signal_id':identity,'revision':1,'user_initiated':True,'acknowledge_research':True})
    assert result.status is CommandStatus.ACCEPTED
    order=r.database.orders()[0]
    assert order['state']=='UNKNOWN' # Recording worker is not a fabricated broker ACK.
    assert order['price_validation']==preview['price_validation']
    assert order['reference_quote_at']==(FIXTURE_NOW if with_snapshot else None)
    sent=[m for m in r.connector.workers[endpoint].sent if m['kind']=='NEW_LIMIT'];assert len(sent)==1
    p=ProtoOANewOrderReq();p.ParseFromString(sent[0]['protobuf'])
    assert str(p.ctidTraderAccountId)==account.account_id and p.limitPrice==1.1 and p.volume==100000
    assert r.api(4).command('4.1','ISSUE',{'signal_id':identity,'revision':1,'user_initiated':True,'acknowledge_research':True}).status is CommandStatus.REJECTED
    assert len([m for m in r.connector.workers[endpoint].sent if m['kind']=='NEW_LIMIT'])==1


@pytest.mark.parametrize('case',['open','missing_calendar','old_epoch','unattributed_calendar','future_quote','continuity_gap'])
def test_closed_pending_exception_does_not_relax_other_admission_gates(connected,case):
    from sfm_fx_new_age.contracts.enums import CommandStatus
    r,event=connected;identity,account,epoch=closed_pending_proposal(r,event)
    cal=r.continuity.calendar('EURUSD')
    if case=='missing_calendar':
        with r.database.transaction() as conn:conn.execute("DELETE FROM records WHERE kind='calendar'")
    elif case in {'open','old_epoch','unattributed_calendar'}:
        changes={'weekly_windows':((0,604800),)} if case=='open' else {'source_ref':'ProtoOASymbol.schedule / OTHER-EPOCH' if case=='old_epoch' else 'UNVERIFIED_SCHEDULE'}
        r.continuity.set_calendar('EURUSD',replace(cal,version=cal.version+1,**changes))
    elif case=='future_quote':
        q=r.market.quote('123','EURUSD');stamp='2026-11-05T12:02:00Z'
        r.market.set_quote(replace(q,sequence=q.sequence+1,available_at=stamp,bid_at=stamp,ask_at=stamp))
    else:r.continuity.mark_stream_gap('EURUSD',epoch,'SYNTHETIC_UNRESOLVED_GAP')
    result=r.api(4).command('4.1','ISSUE',{'signal_id':identity,'revision':1,'user_initiated':True,'acknowledge_research':True})
    assert result.status is CommandStatus.REJECTED and not r.database.orders()
    assert not [m for w in r.connector.workers.values() for m in w.sent if m['kind']=='NEW_LIMIT']
