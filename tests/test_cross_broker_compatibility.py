"""NONMARKET metadata and lifecycle controls; no provider/broker qualification."""
from copy import deepcopy
from dataclasses import replace
import pytest
from test_connector_boundary import connected
from test_feed_bootstrap_isolation import full_feed, history_states
from sfm_fx_new_age.contracts.domain import PAIRS
from sfm_fx_new_age.services.market import market_key


def test_noncanonical_native_name_is_mapped_by_authoritative_assets(connected):
    r,event=connected;c=r.connector;a=r.accounts.current
    raw=deepcopy(c.native[(a.endpoint_class,a.account_id)]['specs'][1]);raw['symbolId']='77'
    event('ProtoOAAssetListRes',dict(ctidTraderAccountId=a.account_id,asset=[dict(assetId='1',name='USD'),dict(assetId='2',name='EUR')]))
    event('ProtoOASymbolsListRes',dict(ctidTraderAccountId=a.account_id,symbol=[dict(symbolId='77',symbolName='EUR/USD.raw',enabled=True,baseAssetId='2',quoteAssetId='1')]))
    state=c.native[(a.endpoint_class,a.account_id)]
    assert state['symbols']=={77:'EURUSD'}
    assert state['native_symbol_names'][77]=='EUR/USD.raw'
    event('ProtoOASymbolByIdRes',dict(ctidTraderAccountId=a.account_id,symbol=[raw]))
    assert r.market.spec(a.account_id,'EURUSD').broker_symbol_id==77


def test_partial_metadata_keeps_five_analytical_lanes(connected):
    r,c,_=full_feed(connected,include={'BROKER_DEPTH','INTRABAR_PRICES'})
    with r.database.transaction() as conn:conn.execute("DELETE FROM records WHERE kind='authority' AND id=?",(market_key(r.market.scope_id,'AUDUSD'),))
    history_states(r,c)
    feed=c.analytical_feed;feed.poll()
    assert feed.binding is not None
    assert set(dict(feed.binding[1]))==set(PAIRS)-{'AUDUSD'}
    assert set(feed.depth.ids.values())==set(PAIRS)-{'AUDUSD'}
    assert set(feed.jobs)==set(PAIRS)-{'AUDUSD'}
    assert not r.database.orders()


@pytest.mark.parametrize('symbol',PAIRS)
@pytest.mark.parametrize('missing',['authority','spec','native_spec'])
def test_each_missing_lane_isolated_with_fixed_coverage_denominator(connected,symbol,missing):
    r,c,_=full_feed(connected,include={'BROKER_DEPTH','INTRABAR_PRICES'})
    a=r.accounts.current;state=c.native[(a.endpoint_class,a.account_id)]
    if missing=='native_spec':state['specs'].pop(r.market.spec(a.account_id,symbol).broker_symbol_id)
    else:
        kind='authority' if missing=='authority' else 'spec'
        key=market_key(a.scope_id,symbol) if kind=='authority' else market_key(a.scope_id,a.account_id,symbol)
        with r.database.transaction() as conn:conn.execute('DELETE FROM records WHERE kind=? AND id=?',(kind,key))
    history_states(r,c);f=c.analytical_feed;f.poll()
    expected=set(PAIRS)-{symbol}
    assert set(dict(f.binding[1]))==expected
    assert set(f.depth.ids.values())==expected and set(f.jobs)==expected
    status=c.feed_status()
    assert status['state']=='PARTIAL_COVERAGE'
    assert status['required_history_jobs']==24 and status['eligible_history_jobs']==20
    assert status['unavailable_history_jobs']==4 and status['completed_history_jobs']==20
    assert status['missing_metadata']==[symbol]
    assert set(status['history_by_pair'][symbol].values())=={'UNAVAILABLE_CURRENT_METADATA'}
    assert not r.database.orders()


@pytest.mark.parametrize('name',['EURUSD','EUR/USD','EURUSD.a','FX.raw.77'])
def test_pure_mapping_preserves_native_identity(name):
    from sfm_fx_new_age.connector.symbols import resolve_symbols
    result=resolve_symbols([dict(symbolId='77',symbolName=name,enabled=True,baseAssetId='2',quoteAssetId='1')],{'1':'USD','2':'EUR'})
    assert result.symbols=={77:'EURUSD'} and result.native_names=={77:name}
    assert result.assets[77]==('2','1')


@pytest.mark.parametrize('change',[
    {'enabled':False},{'enabled':'true'},{'symbolId':'077'},{'symbolId':True},
    {'baseAssetId':'MISSING'},{'quoteAssetId':None},{'isFuture':True},
    {'expirationTimestamp':'1893456000000'},{'instrumentType':'FUTURE'},
    {'symbolName':'EURUSD\n'},{'baseAssetId':'1','quoteAssetId':'2'},
])
def test_pure_mapping_rejects_malformed_disabled_or_mismatched_contract(change):
    from sfm_fx_new_age.connector.symbols import resolve_symbols
    row=dict(symbolId='77',symbolName='EURUSD',enabled=True,baseAssetId='2',quoteAssetId='1');row.update(change)
    result=resolve_symbols([row],{'1':'USD','2':'EUR'})
    assert not result.symbols and not result.native_names


@pytest.mark.parametrize('same_id',[False,True])
def test_ambiguous_variants_never_choose_exact_name_or_row_order(same_id):
    from sfm_fx_new_age.connector.symbols import resolve_symbols
    first=dict(symbolId='77',symbolName='EURUSD',enabled=True,baseAssetId='2',quoteAssetId='1')
    other=dict(first,symbolId='77' if same_id else '78',symbolName='EURUSD.raw')
    for rows in ([first,other],[other,first]):
        result=resolve_symbols(rows,{'1':'USD','2':'EUR'})
        assert not result.symbols
        assert result.states['EURUSD']==('DUPLICATE_NATIVE_ID' if same_id else 'AMBIGUOUS_NATIVE_CONTRACT')


def test_noncanonical_name_without_asset_identity_is_not_guessed():
    from sfm_fx_new_age.connector.symbols import resolve_symbols
    assert not resolve_symbols([dict(symbolId=7,symbolName='EURUSD.a')],{}).symbols


def test_late_asset_metadata_resolves_without_duplicate_detail_requests(connected):
    r,event=connected;c=r.connector;a=r.accounts.current
    raw=deepcopy(c.native[(a.endpoint_class,a.account_id)]['specs'][1]);raw['symbolId']=77
    event('ProtoOASymbolsListRes',dict(ctidTraderAccountId=a.account_id,symbol=[dict(symbolId=77,symbolName='EURUSD.a',baseAssetId=2,quoteAssetId=1)]))
    state=c.native[(a.endpoint_class,a.account_id)];assert not state['symbols']
    event('ProtoOAAssetListRes',dict(ctidTraderAccountId=a.account_id,asset=[dict(assetId=1,name='USD'),dict(assetId=2,name='EUR')]))
    assert state['symbols']=={77:'EURUSD'}
    before=len([q for q in c.requests.values() if q['name']=='ProtoOASymbolByIdReq'])
    event('ProtoOAAssetListRes',dict(ctidTraderAccountId=a.account_id,asset=[dict(assetId=1,name='USD'),dict(assetId=2,name='EUR')]))
    assert len([q for q in c.requests.values() if q['name']=='ProtoOASymbolByIdReq'])==before
    event('ProtoOASymbolByIdRes',dict(ctidTraderAccountId=a.account_id,symbol=[raw]))
    assert r.database.get('native_symbol_binding',a.scope_id+':EURUSD')['native_symbol_name']=='EURUSD.a'


def test_withdraw_one_pair_keeps_healthy_tpo_and_depth_subscription(connected):
    r,c,event=full_feed(connected,include={'BROKER_DEPTH','INTRABAR_PRICES'})
    history_states(r,c);f=c.analytical_feed;f.poll();a=r.accounts.current
    request_id=next(k for k,q in c.requests.items() if (q.get('context') or {}).get('broker_depth')=='SUBSCRIBE')
    event('ProtoOASubscribeDepthQuotesRes',dict(ctidTraderAccountId=a.account_id),request_id=request_id)
    jobs=dict(f.jobs);token=f.depth.tokens[1];session=f.depth.session
    r.market.withdraw_source('AUDUSD',dict(f.binding[1])['AUDUSD']);f.poll()
    assert f.jobs=={s:j for s,j in jobs.items() if s!='AUDUSD'}
    assert r.database.get('native_quote_history_job',jobs['AUDUSD'])['state']=='REQUEST_FAILED'
    assert f.depth.session==session and f.depth.tokens[1]==token
    assert f.depth.acknowledged==set(PAIRS)-{'AUDUSD'}
    assert 'AUDUSD' not in f.depth.books
    assert f.reported_fx.binding is None
    event('ProtoOADepthEvent',dict(ctidTraderAccountId=a.account_id,symbolId=1,newQuotes=[dict(id='SYNTHETIC_B',size=100000,bid=110100),dict(id='SYNTHETIC_A',size=200000,ask=110120)]))
    r.clock=lambda:'2026-11-05T12:00:00.001000Z';r.analytics.supplemental.clock=r.clock
    f.poll()
    assert 'BROKER_DEPTH' in r.analytics.supplemental.snapshot('EURUSD',r.clock())
    c.activate_selected();f.poll()
    assert set(f.jobs)==set(PAIRS) and f.jobs['EURUSD']==jobs['EURUSD']
    assert f.depth.tokens[1]==token and f.depth.session==session


def test_removed_pair_old_depth_ack_does_not_qualify_readded_subscription(connected):
    r,c,event=full_feed(connected,include={'BROKER_DEPTH'})
    f=c.analytical_feed;f.poll();a=r.accounts.current
    old=next(k for k,q in c.requests.items() if (q.get('context') or {}).get('broker_depth')=='SUBSCRIBE')
    r.market.withdraw_source('AUDUSD',dict(f.binding[1])['AUDUSD']);f.poll()
    c.activate_selected();f.poll()
    new=next(k for k,q in c.requests.items() if k!=old and (q.get('context') or {}).get('broker_depth')=='SUBSCRIBE')
    event('ProtoOASubscribeDepthQuotesRes',dict(ctidTraderAccountId=a.account_id),request_id=old)
    assert 'AUDUSD' not in f.depth.acknowledged and 'EURUSD' in f.depth.acknowledged
    event('ProtoOASubscribeDepthQuotesRes',dict(ctidTraderAccountId=a.account_id),request_id=new)
    assert f.depth.acknowledged==set(PAIRS)


@pytest.mark.parametrize('which',['scope','epoch','origin','native_spec','intent_epoch'])
def test_late_or_foreign_lane_binding_is_refused(connected,which):
    from sfm_fx_new_age.connector.lanes import lane_matches
    r,c,_=full_feed(connected);f=c.analytical_feed;f.poll();a=r.accounts.current;b=f.binding
    state=c.native[(a.endpoint_class,a.account_id)]
    authority=r.market.authority('EURUSD')
    if which=='native_spec':state['specs'].pop(1)
    elif which=='intent_epoch':c.feed_intents[a.scope_id]['epoch']='OLD'
    else:
        authority[{'scope':'scope_id','epoch':'source_epoch','origin':'origin'}[which]]='WRONG'
        r.database.put('authority',market_key(a.scope_id,'EURUSD'),authority)
    assert not lane_matches(r,b,'EURUSD')
    with pytest.raises(ValueError):f.venue._accept('EURUSD',{},(),r.clock(),'AGGRESSOR_PRINTS',r.clock(),r.clock(),'nonmarket')
    with pytest.raises(ValueError):f.native_book._admit('EURUSD',{})


def test_native_id_cannot_silently_rebind_history_inside_an_active_epoch(connected):
    r,c,event=full_feed(connected);a=r.accounts.current
    event('ProtoOASymbolsListRes',dict(ctidTraderAccountId=a.account_id,symbol=[dict(symbolId=77,symbolName='EURUSD')]))
    state=c.native[(a.endpoint_class,a.account_id)]
    assert state['symbol_resolution']['EURUSD']=='NATIVE_ID_CHANGED_RECONNECT_REQUIRED'
    assert not r.market.authority('EURUSD')
    assert 77 not in state['symbols']


class ControlledThread:
    """Scheduling double only. Never executes target or synthesizes feed output."""
    def __init__(self,*,target,args=(),**kwargs):self.target=target;self.args=args;self.alive=False
    def start(self):self.alive=True
    def is_alive(self):return self.alive
    def join(self,timeout=None):self.alive=False


def test_child_workers_receive_only_eligible_supported_pairs(connected,monkeypatch,tmp_path):
    import sfm_fx_new_age.connector.kraken_public as kraken
    import sfm_fx_new_age.connector.bitstamp_feed as bitstamp
    r,c,_=full_feed(connected);f=c.analytical_feed
    # Persistent-state scheduling control; all network thread targets are inert.
    r.database.path=str(tmp_path/'NONMARKET.sqlite')
    monkeypatch.setattr(kraken,'Thread',ControlledThread);monkeypatch.setattr(bitstamp,'Thread',ControlledThread)
    r.market.withdraw_source('GBPUSD',r.market.authority('GBPUSD')['source_epoch']);f.poll()
    assert set(dict(f.venue.worker.args[0][1]))==set(PAIRS)-{'GBPUSD'}
    assert set(dict(f.native_book.worker.args[0][1]))=={'EURUSD'}
    assert f.reported_fx.binding is None and f.reported_fx.worker is None
    before=f.venue.worker
    r.market.withdraw_source('AUDUSD',r.market.authority('AUDUSD')['source_epoch']);f.poll()
    assert f.venue.worker is not before and not before.alive
    assert set(dict(f.venue.binding[1]))==set(PAIRS)-{'GBPUSD','AUDUSD'}
    assert f.reported_fx.binding is None
    current=f.venue.worker
    f.disconnect();assert not current.alive
    assert not r.database.orders()


def test_weekly_recovery_does_not_wait_for_unrelated_hours_or_lookback(connected,monkeypatch,tmp_path):
    import sfm_fx_new_age.connector.kraken_weekly as module
    from sfm_fx_new_age.connector.lanes import project_binding
    from sfm_fx_new_age.contracts.domain import Bar,Origin
    from decimal import Decimal
    from datetime import datetime,timedelta,timezone
    r,c,_=full_feed(connected);f=c.analytical_feed;binding=project_binding(f._identity(),{'EURUSD','GBPUSD'})
    r.database.path=str(tmp_path/'NONMARKET.sqlite');monkeypatch.setattr(module,'Thread',ControlledThread)
    venue=f.venue;weekly=venue.weekly;venue.pairs={'EURUSD':{},'GBPUSD':{}}
    weekly.binding=binding;weekly.hour_inputs['EURUSD']=('NONMARKET_HOUR_CONTROL',)
    # Use actual immutable Bar objects; no market-admission call.
    end=datetime(2026,11,2,tzinfo=timezone.utc)
    bars=tuple(Bar('EURUSD','W1',(end-timedelta(weeks=i+1)).isoformat(),(end-timedelta(weeks=i)).isoformat(),(end-timedelta(weeks=i)).isoformat(),Decimal('1'),Decimal('1.1'),Decimal('.9'),Decimal('1'), 'NONMARKET',Origin.SYNTHETIC_FIXTURE) for i in range(21))
    monkeypatch.setattr(r.market,'bars',lambda symbol,*args:bars if symbol=='EURUSD' else ())
    weekly.poll(binding)
    assert weekly.worker and set(weekly.worker.args[1])=={'EURUSD'}
    worker=weekly.worker;weekly.disconnect();assert not worker.alive


def test_official_context_validator_keeps_strict_default_and_allows_explicit_subset(connected):
    from sfm_fx_new_age.connector.official_context import validate_binding
    r,c,_=full_feed(connected);a=r.accounts.current
    source=dict(scope_id=a.scope_id,authorities={'EURUSD':r.market.authority('EURUSD')})
    with pytest.raises(ValueError):validate_binding(source)
    assert validate_binding(source,require_all=False)==source
    with pytest.raises(ValueError):validate_binding(dict(scope_id=a.scope_id,authorities={}),require_all=False)


def test_partial_coverage_is_visible_without_reducing_requested_denominator(connected):
    from PySide6.QtWidgets import QApplication
    from sfm_fx_new_age.ui.feed_connection import FeedDialog
    app=QApplication.instance() or QApplication([])
    r,c,_=full_feed(connected);a=r.accounts.current
    r.market.withdraw_source('AUDUSD',r.market.authority('AUDUSD')['source_epoch'])
    history_states(r,c)
    dialog=FeedDialog(r.api(2),r.api(4))
    try:
        dialog.refresh()
        assert '20/24 required jobs complete' in dialog.status.text()
        assert 'eligible pairs 5/6' in dialog.status.text()
        assert 'unavailable: AUDUSD' in dialog.status.text()
    finally:dialog.close();dialog.deleteLater();app.processEvents()


def test_late_history_page_after_metadata_withdrawal_is_not_admitted(connected):
    r,c,_=full_feed(connected);a=r.accounts.current
    request=next(q for q in c.requests.values() if q['name']=='ProtoOAGetTrendbarsReq' and r.database.get('backfill',q['context']['job_id'])['symbol']=='AUDUSD')
    job=r.database.get('backfill',request['context']['job_id'])
    r.market.withdraw_source('AUDUSD',r.market.authority('AUDUSD')['source_epoch'])
    c._backfill_page(a.endpoint_class,a.account_id,request['context'],dict(trendbar=[],hasMore=False))
    assert r.database.get('backfill',job['id'])['status']=='FAILED'
    assert not r.market.authority('AUDUSD')
