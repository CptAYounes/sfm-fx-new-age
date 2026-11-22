"""Recording-only native/read contracts for cross-workspace integration."""
import pytest
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW
from test_connector_boundary import connected


def test_native_pending_inventory_normalization_does_not_adopt_or_send(connected):
    r,event=connected
    event('ProtoOAReconcileRes',{'ctidTraderAccountId':'123','order':[{'orderId':'native-1','orderType':'LIMIT','orderStatus':'ORDER_STATUS_ACCEPTED','limitPrice':1.1,
         'tradeData':{'symbolId':'1','tradeSide':'BUY','volume':'100000'}}],'position':[]})
    inventory=r.api(4).query('4.3',DataRequest('broker_pending'))['rows'][0]
    assert inventory['broker_order_id']=='native-1' and inventory['symbol']=='EURUSD' and inventory['units']=='1000'
    chart=r.api(1).query('1.10',DataRequest('chart'))
    assert chart['broker_pending'][0]['broker_order_id']=='native-1' and not chart['orders']
    assert not r.database.orders()
    assert not any(m['kind'] in {'NEW_LIMIT','CANCEL_PENDING'} for worker in r.connector.workers.values() for m in worker.sent)


def test_older_history_uses_single_existing_connector_and_is_deduplicated(connected):
    r,_=connected;context=r.api(1).inspect(symbol='EURUSD',timeframe='W1')
    job=r.api(1).request_older_history(context,30)
    assert job['status']=='QUEUED' and job['source_epoch']==context['source_epoch']
    before=sum(len(w.sent) for w in r.connector.workers.values())
    assert r.api(1).request_older_history(context,30)['id']==job['id']
    assert sum(len(w.sent) for w in r.connector.workers.values())==before
    r.connector.native[('LIVE','123')]['specs'].clear()
    with pytest.raises(ValueError,match='metadata required'):r.api(1).request_older_history(context,90)
    assert sum(len(w.sent) for w in r.connector.workers.values())==before


def test_historical_chart_withholds_current_broker_and_signal_state(runtime):
    data=runtime.api(1).query('1.10',DataRequest('chart',as_of=FIXTURE_NOW))
    assert all(key not in data for key in ('orders','positions','signals','broker_pending'))


def test_replay_and_readonly_tools_cannot_overwrite_market_notes(runtime):
    context=runtime.api(1).inspect(symbol='EURUSD',timeframe='D1')
    with pytest.raises(ValueError):runtime.api(3).save_workspace(context,{'drawings':[]},0)
    runtime.api(1).create_inspection_replay(context,'test-run')
    replay=runtime.api(1).inspect(symbol='EURUSD',timeframe='D1',run_id='test-run')
    with pytest.raises(ValueError):runtime.api(1).save_workspace(replay,{'drawings':[]},0)
    with pytest.raises(ValueError):runtime.api(1).navigate('calculator',replay)
    with pytest.raises(ValueError):runtime.api(1).request_older_history(replay,30)


def test_human_notes_are_unified_and_never_market_evidence(runtime):
    payload={'annotation_id':'legacy-local-note','timeframe':'D1','points':[{'time':FIXTURE_NOW,'price':'1.1'}],'text':'Human observation only','expected_version':0}
    result=runtime.api(1).command('1.3','DRAW_ANNOTATION',payload)
    assert result.status.value=='ACCEPTED'
    rows=runtime.api(1).query('1.3',DataRequest('annotations'))['rows']
    assert rows[0]['text']=='Human observation only' and rows[0]['source_epoch']==runtime.market.authority('EURUSD')['source_epoch']
    assert not runtime.database.list('annotation') and not runtime.research.query('level',scope=runtime.market.scope_id,epoch=rows[0]['source_epoch'],symbol='EURUSD',as_of=FIXTURE_NOW)
    assert runtime.api(1).command('1.3','DRAW_ANNOTATION',payload).status.value=='REJECTED'


def test_invalid_workspace_payloads_are_rejected_without_write(runtime):
    api=runtime.api(1);context=api.inspect(symbol='EURUSD');before=runtime.database.connection.total_changes
    for payload in ({'style':'NOT_A_CHART'},{'window':True},{'volume':'true'},{'drawings':[{'id':'x'}]},{'execute':True}):
        with pytest.raises(ValueError):api.save_workspace(context,payload,0)
    assert runtime.database.connection.total_changes==before and not runtime.database.orders()


def test_destination_permissions_refuse_navigation_before_any_write(runtime):
    runtime.positions.replace_snapshot(runtime.market.scope_id,[{'position_id':'broker-context','symbol':'EURUSD','side':'BUY','units':'1000','entry_price':'1.1'}],observed_at=FIXTURE_NOW,origin='SYNTHETIC_FIXTURE',complete=True)
    api=runtime.api(1);context=api.inspect(symbol='EURUSD',object_kind='position',object_id='broker-context');before=runtime.database.connection.total_changes
    for target in ('3.5','calculator','2.1'):
        with pytest.raises(ValueError):api.navigate(target,context)
    assert runtime.database.connection.total_changes==before
