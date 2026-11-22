"""Native money uses exact exponent plus native asset identity, not guessed USD."""
from test_connector_boundary import connected
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW


def test_native_money_scaling_currency_metadata_and_observation_time(connected):
    r,event=connected;a=r.accounts.current
    event('ProtoOATraderRes',{'ctidTraderAccountId':'123','trader':{'depositAssetId':'1','brokerName':'SYNTHETIC_PROTOCOL_TEST_NO_NETWORK',
        'moneyDigits':8,'balance':'1000012345678','balanceVersion':'9','accessRights':'FULL_ACCESS'}})
    row=r.database.get('account_money_snapshot',a.scope_id)
    assert row['balance']=='10000.12345678' and row['money_digits']==8 and row['observed_at']==FIXTURE_NOW
    assert row['origin']=='LIVE_OBSERVED' and row['source_epoch']==r.market.authority('EURUSD')['source_epoch']
    event('ProtoOAAssetListRes',{'ctidTraderAccountId':'123','asset':[{'assetId':'1','name':'USD'},{'assetId':'2','name':'EUR'}]})
    event('ProtoOASymbolsListRes',{'ctidTraderAccountId':'123','symbol':[{'symbolId':'1','symbolName':'EURUSD','enabled':True,'baseAssetId':'2','quoteAssetId':'1'}]})
    r.connector.activate_selected()
    currency=r.market.scoped_rows('symbol_currency')[0]
    assert currency['base_currency']=='EUR' and currency['quote_currency']=='USD'
    assert r.money.context()['native_money_current']
    r.clock=lambda:'2026-11-05T12:02:00Z';r.connector.activate_selected()
    assert r.database.get('account_money_snapshot',a.scope_id)['observed_at']==FIXTURE_NOW
    assert not r.money.context()['native_money_current']
    assert all(x['kind']=='READ' or x['kind']=='AUTH_ACCOUNT' for w in r.connector.workers.values() for x in w.sent)


def test_native_money_periodic_refresh_is_read_only_rate_limited_and_not_synthetic(connected,monkeypatch):
    r,event=connected;a=r.accounts.current;c=r.connector;state=c.native[(a.endpoint_class,a.account_id)]
    import sfm_fx_new_age.connector.service as service
    now=service.monotonic();state['trader_received_monotonic']=now-21
    monkeypatch.setattr(service,'monotonic',lambda:now)
    worker=c.workers[a.endpoint_class];before=len(worker.sent);c.poll();sent=worker.sent[before:]
    assert any(x.get('name')=='ProtoOATraderReq' and x['kind']=='READ' for x in sent)
    count=len(worker.sent);c.poll();assert len(worker.sent)==count
    assert r.database.get('account_money_snapshot',a.scope_id) is None
