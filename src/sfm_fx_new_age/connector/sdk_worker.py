"""Isolated SDK reactor process. Only this module's explicit start path can contact cTrader."""
from __future__ import annotations
from multiprocessing import get_context
from queue import Empty,Full
from uuid import uuid4
from time import monotonic
from typing import Any

READ_REQUESTS=frozenset({'ProtoOATraderReq','ProtoOAAssetListReq','ProtoOASymbolsListReq','ProtoOASymbolByIdReq',
 'ProtoOASubscribeSpotsReq','ProtoOAUnsubscribeSpotsReq','ProtoOAGetTrendbarsReq','ProtoOAReconcileReq',
 'ProtoOAOrderListReq','ProtoOADealListReq','ProtoOAExpectedMarginReq','ProtoOAOrderDetailsReq',
 'ProtoOASubscribeLiveTrendbarReq','ProtoOAUnsubscribeLiveTrendbarReq','ProtoOAGetTickDataReq',
 'ProtoOASubscribeDepthQuotesReq','ProtoOAUnsubscribeDepthQuotesReq'})


def redact(value: Any) -> Any:
    if type(value) is dict:return {k:redact(v) for k,v in value.items() if k not in {'accessToken','refreshToken','clientSecret','access_token','refresh_token','client_secret','code'}}
    if type(value) is list:return [redact(v) for v in value]
    return value


def paced_protocol(*,clock=None):
    """Real SDK framing without one-second bursts or cross-connection queue replay.

    A conservative single frame every 350 ms leaves margin below cTrader's
    historical-request limit. Independent heartbeats keep a busy connection alive.
    ``clock`` is injected only by socket-free virtual-clock acceptance tests.
    """
    from collections import deque
    from ctrader_open_api import TcpProtocol
    from twisted.internet import task
    class PacedTcpProtocol(TcpProtocol):
        def __init__(self):
            self._send_queue=deque();self._lastSendMessageTime=None;self._next_frame_at=0
            self._send_task=task.LoopingCall(self._sendStrings)
            self._heartbeat_task=task.LoopingCall(self.heartbeat)
            if clock is not None:
                self._send_task.clock=clock;self._heartbeat_task.clock=clock

        def _sendStrings(self):
            now=clock.seconds() if clock is not None else monotonic()
            if self._send_queue and now+1e-9<self._next_frame_at:return
            before=len(self._send_queue)
            super()._sendStrings()
            if len(self._send_queue)<before:self._next_frame_at=now+.35

        def connectionMade(self):
            # The official SDK initializes framing/factory callbacks here. Replace
            # only its one-second batching timer, not serialization or response IDs.
            super().connectionMade()
            self._send_task.stop();self._send_task.start(.35,now=False)
            self._heartbeat_task.start(10,now=False)

        def connectionLost(self,reason):
            if self._heartbeat_task.running:self._heartbeat_task.stop()
            super().connectionLost(reason)
            self._send_queue.clear() # Never carry uncertain unsent writes into a reconnect.
    return PacedTcpProtocol


def verified_client(host, port, reactor):
    """SDK Client methods with explicit hostname-verifying TLS and paced framing."""
    # Fail closed when the supported hostname verifier is unavailable rather
    # than accepting Twisted's reduced-assurance optional-dependency fallback.
    from service_identity.pyopenssl import verify_hostname
    from ctrader_open_api import Client, TcpProtocol
    from twisted.application.internet import ClientService
    from twisted.internet.endpoints import SSL4ClientEndpoint
    from twisted.internet.ssl import optionsForClientTLS
    from ctrader_open_api.factory import Factory
    class VerifiedClient(Client):
        def __init__(self):
            self._runningReactor = reactor
            # SDK _sendStrings uses this as its per-tick batch size; our timer is 350 ms.
            self.numberOfMessagesToSendPerSecond = 1
            self.tls_hostname = host
            endpoint = SSL4ClientEndpoint(reactor, host, port, optionsForClientTLS(host))
            factory = Factory.forProtocol(paced_protocol(), client=self)
            ClientService.__init__(self, endpoint, factory)
            self._events = {}; self._responseDeferreds = {}; self.isConnected = False
    return VerifiedClient()


def sdk_worker_main(configuration:dict,commands,events,probe=False):
    try:
        from ctrader_open_api import Client,EndPoints,TcpProtocol,Protobuf
        from ctrader_open_api.messages import OpenApiMessages_pb2 as M,OpenApiModelMessages_pb2 as D
        from google.protobuf.json_format import MessageToDict,ParseDict
        from twisted.internet import reactor,task
        import os
        if probe:
            events.put({'kind':'SDK_PROBE','pid':os.getpid(),'reactor':'ISOLATED','endpoint':'NO_NETWORK',
                        'limit_enum':D.LIMIT},timeout=2)
            return
        endpoint=configuration['endpoint']
        if endpoint not in {'LIVE','DEMO'}:raise ValueError('Unknown protocol endpoint')
        host=EndPoints.PROTOBUF_LIVE_HOST if endpoint=='LIVE' else EndPoints.PROTOBUF_DEMO_HOST
        client=verified_client(host,EndPoints.PROTOBUF_PORT,reactor)
        pending=set();stopping=[False]
        def output(body):
            try:events.put(redact(body)|{'endpoint':endpoint},timeout=2)
            except Full:
                stopping[0]=True
                client.stopService()
                if reactor.running:reactor.stop()
        def failed(failure,request_id):
            pending.discard(request_id)
            output({'kind':'REQUEST_FAILED','request_id':request_id,'error_type':failure.type.__name__})
            return None
        def send(message,request_id=None,*,report_read_admission=False):
            identity=request_id or str(uuid4());pending.add(identity)
            accepted_at=monotonic()
            deferred=client.send(message,clientMsgId=identity,responseTimeoutInSeconds=20)
            deferred.addCallbacks(lambda message:pending.discard(identity),lambda failure:failed(failure,identity))
            if report_read_admission:
                # SDK acceptance, NOT a wire-send or vendor-acknowledgement claim.
                # No credentials, request payloads or market timestamps in notices.
                output({'kind':'READ_SDK_ACCEPTED','request_id':identity,'accepted_monotonic':accepted_at})
        def connected(_):
            output({'kind':'CONNECTED'})
            send(M.ProtoOAApplicationAuthReq(clientId=configuration['client_id'],clientSecret=configuration['client_secret']))
        def disconnected(*_):
            pending.clear();output({'kind':'DISCONNECTED'})
        def received(_,message):
            payload=Protobuf.extract(message);name=payload.DESCRIPTOR.name
            body=MessageToDict(payload,preserving_proto_field_name=False)
            output({'kind':'MESSAGE','name':name,'payload':body,'request_id':message.clientMsgId or ''})
            if name=='ProtoOAApplicationAuthRes':send(M.ProtoOAGetAccountListByAccessTokenReq(accessToken=configuration['access_token']))
        def poll():
            if stopping[0]:return
            if len(pending)>=16:return
            try:item=commands.get_nowait()
            except Empty:return
            if item['kind']=='STOP':
                stopping[0]=True;client.stopService();reactor.stop();return
            if not client.isConnected:
                output({'kind':'REQUEST_FAILED','request_id':item['request_id'],'error_type':'Disconnected'});return
            try:
                if item['kind']=='AUTH_ACCOUNT':
                    message=M.ProtoOAAccountAuthReq(ctidTraderAccountId=int(item['account_id']),accessToken=configuration['access_token'])
                elif item['kind']=='READ' and item['name'] in READ_REQUESTS:
                    message=ParseDict(item['payload'],getattr(M,item['name'])())
                elif item['kind']=='NEW_LIMIT':
                    message=M.ProtoOANewOrderReq();message.ParseFromString(item['protobuf'])
                    if message.orderType!=D.LIMIT or message.HasField('stopLoss') or message.HasField('takeProfit') or not message.clientOrderId:
                        raise ValueError('Native order route denied')
                elif item['kind']=='CANCEL_PENDING':
                    message=M.ProtoOACancelOrderReq(ctidTraderAccountId=int(item['account_id']),orderId=int(item['broker_order_id']))
                else:raise ValueError('SDK operation not allowlisted')
                if not message.IsInitialized():raise ValueError('Incomplete protocol request')
                send(message,item['request_id'],report_read_admission=item['kind']=='READ')
            except Exception as exc:output({'kind':'REQUEST_FAILED','request_id':item.get('request_id',''),'error_type':type(exc).__name__})
        client.setConnectedCallback(connected);client.setDisconnectedCallback(disconnected);client.setMessageReceivedCallback(received)
        task.LoopingCall(poll).start(0.05)
        client.startService();reactor.run(installSignalHandlers=False)
    except Exception as exc:
        events.put({'kind':'FATAL','error_type':type(exc).__name__},timeout=2)


class SdkProcess:
    """Spawn, don't fork the Qt application; process lifetime is bounded by the application."""
    reports_sdk_admission=True
    def __init__(self,configuration:dict,*,probe=False):
        context=get_context('spawn')
        self.commands=context.Queue(maxsize=256);self.events=context.Queue(maxsize=4096)
        self.process=context.Process(target=sdk_worker_main,args=(configuration,self.commands,self.events,probe),daemon=True)
        self.started=False

    def start(self):self.process.start();self.started=True
    def send(self,body:dict):
        if not self.started or not self.process.is_alive():raise ValueError('SDK process is not running')
        self.commands.put_nowait(body)
    def poll(self,limit=128):
        rows=[]
        for _ in range(limit):
            try:rows.append(self.events.get_nowait())
            except Empty:break
        return rows
    def close(self):
        if self.started and self.process.is_alive():
            try:self.commands.put_nowait({'kind':'STOP'})
            except Full:pass
            self.process.join(timeout=3)
            if self.process.is_alive():self.process.terminate();self.process.join(timeout=2)
        self.commands.close();self.events.close()
