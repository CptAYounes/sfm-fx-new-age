"""Reconnect metadata races use synthetic protocol frames only, never sockets."""
from test_connector_boundary import connected


def test_reconnect_does_not_schedule_history_from_previous_epoch_metadata(connected):
    r,event=connected;c=r.connector;account=r.accounts.current
    state=c.native[(account.endpoint_class,account.account_id)]
    old_epoch=state['epoch'];raw=state['specs'][1]
    state['epoch']='SYNTHETIC_RECONNECTED_EPOCH';state['specs']={}
    assert r.market.authority('EURUSD')['source_epoch']==old_epoch
    for worker in c.workers.values():worker.sent.clear()
    c.start_market_feed()
    assert not [m for w in c.workers.values() for m in w.sent if m.get('name')=='ProtoOAGetTrendbarsReq']
    assert 'EURUSD' in c.feed_status()['missing_metadata']
    event('ProtoOASymbolByIdRes',{'ctidTraderAccountId':account.account_id,'symbol':[raw]})
    c.poll()
    sent=[m for w in c.workers.values() for m in w.sent if m.get('name')=='ProtoOAGetTrendbarsReq']
    assert len(sent)==4
    for message in sent:
        request=c.requests[message['request_id']]
        job=r.database.get('backfill',request['context']['job_id'])
        assert job['source_epoch']==state['epoch'] and job['scope_id']==account.scope_id
    assert c.feed_status()['history_jobs']==4
    assert not r.database.orders()
