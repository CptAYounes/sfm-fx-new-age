"""Real SDK framing with a virtual clock; no network, credentials or broker writes."""
from types import SimpleNamespace
import pytest


def make_protocol():
    pytest.importorskip('ctrader_open_api')
    from twisted.internet.task import Clock
    from sfm_fx_new_age.connector.sdk_worker import paced_protocol
    from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
    clock=Clock();protocol_type=paced_protocol(clock=clock);protocol=protocol_type();wire=[]
    protocol.factory=SimpleNamespace(numberOfMessagesToSendPerSecond=1,connected=lambda _:None,disconnected=lambda _:None)
    protocol.sendString=lambda data:wire.append(ProtoMessage.FromString(data))
    return clock,protocol_type,protocol,wire


def test_history_frames_are_spaced_below_the_rolling_window_limit():
    clock,_,protocol,wire=make_protocol()
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAGetTrendbarsReq
    from ctrader_open_api.messages.OpenApiModelMessages_pb2 import H1
    times=[]
    original=protocol.sendString
    def record(data):
        original(data)
        if wire[-1].payloadType==ProtoOAGetTrendbarsReq().payloadType:times.append(clock.seconds())
    protocol.sendString=record;protocol.connectionMade()
    try:
        for i in range(28):protocol.send(ProtoOAGetTrendbarsReq(ctidTraderAccountId=123,symbolId=1,period=H1,fromTimestamp=1,toTimestamp=2),clientMsgId=str(i))
        assert not times
        for _ in range(120):clock.advance(.25)
        assert len(times)==28
        assert all(b-a>=.349 for a,b in zip(times,times[1:]))
        assert max(sum(start<=t<start+1 for t in times) for start in times)<=3
    finally:protocol.connectionLost(None)


def test_each_connection_has_its_own_queue_and_discards_unsent_frames_on_loss():
    clock,protocol_type,protocol,_=make_protocol();other=protocol_type()
    from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOATraderReq
    protocol.connectionMade()
    protocol.send(ProtoOATraderReq(ctidTraderAccountId=123),clientMsgId='SYNTHETIC_READ')
    assert len(protocol._send_queue)==1 and len(other._send_queue)==0
    protocol.connectionLost(None)
    assert not protocol._send_queue and not protocol._send_task.running
    assert not protocol._heartbeat_task.running


def test_heartbeat_runs_while_idle_and_stops_with_the_connection():
    clock,_,protocol,wire=make_protocol()
    from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoHeartbeatEvent
    protocol.connectionMade()
    initial=sum(frame.payloadType==ProtoHeartbeatEvent().payloadType for frame in wire)
    clock.advance(10)
    assert sum(frame.payloadType==ProtoHeartbeatEvent().payloadType for frame in wire)>initial
    protocol.connectionLost(None);count=len(wire);clock.advance(30)
    assert len(wire)==count
