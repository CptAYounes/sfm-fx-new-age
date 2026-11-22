"""Offline recording-wire proof of native closed-bar ingress, never a broker trade."""
from dataclasses import replace
from decimal import Decimal
from test_connector_boundary import connected
from sfm_fx_new_age.connector.protocol import milliseconds
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest


def ready(connected):
    r,event=connected;c=r.connector;c.start_market_feed()
    event('ProtoOASubscribeSpotsRes',{'ctidTraderAccountId':'123'})
    for identity in c.feed_intents[r.market.scope_id]['jobs'].values():
        job=r.database.get('backfill',identity);job['status']='COMPLETE';r.database.put('backfill',identity,job)
    c._seed_feed()
    for identity,q in list(c.requests.items()):
        if q['name']=='ProtoOASubscribeLiveTrendbarReq':event('ProtoOASubscribeLiveTrendbarRes',{'ctidTraderAccountId':'123'},request_id=identity)
    return r,event


def bar():return {'utcTimestampInMinutes':milliseconds('2026-11-04T00:00:00Z')//60000,'low':'109900','deltaOpen':'100','deltaHigh':'300','deltaClose':'200','volume':'42','period':'D1'}


def test_live_closed_bar_subscriptions_follow_spot_ack_and_history(connected):
    r,event=connected;c=r.connector;c.start_market_feed()
    assert not any(q['name']=='ProtoOASubscribeLiveTrendbarReq' for q in c.requests.values())
    r,event=ready(connected)
    sent=[m for m in c.workers['LIVE'].sent if m.get('name')=='ProtoOASubscribeLiveTrendbarReq']
    assert len(sent)==4 and {m['payload']['period'] for m in sent}=={'W1','D1','H4','H1'}
    c._seed_feed();assert sum(m.get('name')=='ProtoOASubscribeLiveTrendbarReq' for m in c.workers['LIVE'].sent)==4
    assert c.feed_status()['live_bar_subscriptions']['ACTIVE']==4
    assert not r.database.orders()


def test_timestamped_native_trendbar_reaches_same_shared_chart_and_dedupes(connected):
    r,event=ready(connected);payload={'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(r.clock()),'trendbar':[bar()]}
    event('ProtoOASpotEvent',payload)
    data=thaw(r.api(1).query('1.3',DataRequest('chart',timeframe='D1')))
    assert len(data['rows'])==1 and data['rows'][0]['tick_volume']==42
    assert data['rows'][0]['construction']=='NATIVE_OBSERVED' and data['rows'][0]['close']=='1.101'
    event('ProtoOASpotEvent',payload);assert len(r.market.scoped_rows('bar'))==1
    state=r.connector.native[('LIVE','123')];assert state['live_bar_received']==1
    assert not r.connector.errors and not r.database.orders()


def test_native_bar_rejects_wrong_account_future_and_unsubscribed_period(connected):
    r,event=ready(connected)
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(r.clock())+1000,'trendbar':[bar()]})
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(r.clock()),'trendbar':[dict(bar(),period='M1')]})
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'999','symbolId':'1','timestamp':milliseconds(r.clock()),'trendbar':[bar()]})
    assert not r.market.scoped_rows('bar') and not r.database.orders()


def test_native_correction_is_revisioned_without_rewriting_asof(connected):
    r,event=ready(connected);old_clock=r.clock
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(r.clock()),'trendbar':[bar()]})
    r.clock=lambda:'2026-11-05T12:00:01Z'
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(r.clock()),'trendbar':[dict(bar(),deltaClose='210',volume='43')]})
    assert len(r.market.scoped_rows('bar'))==2
    epoch=r.market.authority('EURUSD')['source_epoch']
    assert r.market.bars('EURUSD','D1',old_clock(),epoch)[0].close==Decimal('1.101')
    assert r.market.bars('EURUSD','D1',r.clock(),epoch)[0].revision==2
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(old_clock()),'trendbar':[bar()]})
    assert r.market.bars('EURUSD','D1',r.clock(),epoch)[0].revision==2


def test_live_bar_subscription_failure_stays_explicit_without_blind_retry(connected):
    r,event=connected;c=r.connector;c.start_market_feed();event('ProtoOASubscribeSpotsRes',{'ctidTraderAccountId':'123'})
    for job_id in c.feed_intents[r.market.scope_id]['jobs'].values():
        job=r.database.get('backfill',job_id);job['status']='COMPLETE';r.database.put('backfill',job_id,job)
    c._seed_feed();identity,request=next((i,q) for i,q in c.requests.items() if q['name']=='ProtoOASubscribeLiveTrendbarReq')
    c.handle('LIVE',{'kind':'REQUEST_FAILED','request_id':identity,'error_type':'SYNTHETIC_FAILURE'})
    assert c.feed_status()['live_bar_subscriptions']['FAILED']==1
    before=len(c.workers['LIVE'].sent);c._seed_feed();assert len(c.workers['LIVE'].sent)==before
    assert not r.database.orders()


def test_native_incomplete_bar_is_not_promoted(connected):
    r,event=ready(connected);raw=dict(bar(),utcTimestampInMinutes=milliseconds('2026-11-05T00:00:00Z')//60000)
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(r.clock()),'trendbar':[raw]})
    assert not r.market.scoped_rows('bar')


def test_connector_tick_forming_never_races_native_closed_bar_authority(connected):
    r,event=ready(connected)
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(r.clock()),'trendbar':[dict(bar(),period='H1')]})
    assert len(r.market.scoped_rows('bar'))==1
    for stamp in ('2026-11-05T12:00:00Z','2026-11-05T13:00:00Z','2026-11-05T14:00:00Z'):
        r.clock=lambda stamp=stamp:stamp
        event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','timestamp':milliseconds(stamp),'bid':'110100','ask':'110120'})
    assert len(r.market.scoped_rows('bar'))==1
    assert any(row['maturity']=='FORMING' for row in r.timeline.snapshot('EURUSD'))
