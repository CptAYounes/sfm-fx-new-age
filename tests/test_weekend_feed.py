"""Weekend snapshots retain provider time and must not revoke a new source epoch."""
from dataclasses import replace
from sfm_fx_new_age.connector.protocol import milliseconds
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from test_connector_boundary import connected


def test_older_weekend_snapshot_from_new_connection_is_not_out_of_order(connected):
    r,event=connected;c=r.connector;account=r.accounts.current
    q=r.market.quote(account.account_id,'EURUSD');state=c.native[(account.endpoint_class,account.account_id)]
    state['epoch']='SYNTHETIC_WEEKEND_RECONNECT';state['quotes']={};c.activate_selected()
    r.clock=lambda:'2026-11-07T19:00:00Z'
    event('ProtoOASpotEvent',{'ctidTraderAccountId':account.account_id,'symbolId':'1','bid':'110090','ask':'110110','timestamp':milliseconds('2026-11-05T11:59:00Z')})
    current=r.market.quote(account.account_id,'EURUSD')
    assert current.source_epoch==state['epoch'] and current.available_at=='2026-11-05T11:59:00Z'
    assert current.available_at<q.available_at and r.accounts.current==account
    assert thaw(r.api(1).query('1.1',DataRequest('watchlist')))['rows'][0]['state']=='STALE'
    assert not r.database.orders()


def test_same_epoch_older_price_remains_rejected(connected):
    import pytest
    r,_=connected;q=r.market.quote('123','EURUSD')
    with pytest.raises(ValueError,match='Out-of-order'):
        r.market.set_quote(replace(q,available_at='2026-11-05T11:59:00Z',bid_at='2026-11-05T11:59:00Z',ask_at='2026-11-05T11:59:00Z'))


def test_native_lower_history_bound_exhausts_even_if_provider_returns_full_page(connected):
    r,event=connected;c=r.connector;c.start_market_feed()
    key,request=next((k,v) for k,v in c.requests.items() if v.get('payload',{}).get('period')=='H1')
    raw={'utcTimestampInMinutes':milliseconds('2026-01-01T00:00:00Z')//60000,'low':'110000','deltaOpen':'0','deltaHigh':'20','deltaClose':'10'}
    before=sum(len(w.sent) for w in c.workers.values())
    event('ProtoOAGetTrendbarsRes',{'ctidTraderAccountId':'123','trendbar':[raw]*500,'hasMore':True},request_id=key)
    job=r.database.get('backfill',request['context']['job_id'])
    assert job['status']=='COMPLETE' and job['received_bars']==0 and job['pages']==1
    assert sum(len(w.sent) for w in c.workers.values())==before


def test_weekend_calendar_and_chart_health_do_not_claim_fresh_quotes(connected):
    from sfm_fx_new_age.services.continuity import SessionCalendar
    r,_=connected;epoch=r.market.authority('EURUSD')['source_epoch'];r.clock=lambda:'2026-11-07T19:00:00Z'
    cal=SessionCalendar('test','America/New_York',((61260,493020),),source_ref='ProtoOASymbol.schedule / '+epoch,version=2)
    r.continuity.set_calendar('EURUSD',cal)
    assert not cal.is_open(r.clock()) and cal.next_open(r.clock())=='2026-11-08T22:01:00Z'
    health=thaw(r.api(1).query('1.3',DataRequest('chart')))['health']
    assert health['authenticated'] and health['market_open'] is False
    assert health['next_open']=='2026-11-08T22:01:00Z'
    assert thaw(r.api(1).query('1.1',DataRequest('watchlist')))['rows'][0]['state']=='STALE'
    assert 'health' not in thaw(r.api(1).query('1.3',DataRequest('chart',as_of='2026-11-05T00:00:00Z')))

