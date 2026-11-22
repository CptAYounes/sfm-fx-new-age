"""Bounded original cTrader health/capability audit; never grants trade authority."""
from pathlib import Path
from decimal import Decimal
from typing import Any
import json,sqlite3
from sfm_fx_new_age.contracts.domain import PAIRS,FRAMES,instant
from .depth_capture import acquire_original_depth
from .official_context import write_new,now


def native_quote_health(quote,cutoff) -> dict[str,Any]:
    if quote is None:return dict(original_quote_received=False,coherent_bid_ask=False,coherent_fresh_bid_ask=False,oldest_side_age_seconds=None,zero_spread=False)
    stamps=[quote.get(k) or quote['available_at'] for k in ('bid_at','ask_at')]
    ages=[(instant(cutoff)-instant(t)).total_seconds() for t in stamps]
    coherent=Decimal(quote['bid'])<=Decimal(quote['ask'])
    return dict(original_quote_received=True,coherent_bid_ask=coherent,coherent_fresh_bid_ask=coherent and min(ages)>=0 and max(ages)<=30,oldest_side_age_seconds=round(max(ages),3),zero_spread=Decimal(quote['bid'])==Decimal(quote['ask']))


def protocol_capabilities() -> dict[str,Any]:
    from ctrader_open_api.messages import OpenApiMessages_pb2 as M,OpenApiModelMessages_pb2 as D
    def fields(name):
        owner=M if hasattr(M,name) else D
        return [f.name for f in getattr(owner,name).DESCRIPTOR.fields]
    names=('ProtoOASpotEvent','ProtoOATrendbar','ProtoOATickData','ProtoOADepthEvent','ProtoOADepthQuote','ProtoOADealListReq','ProtoOADealListRes')
    result={name:fields(name) for name in names}
    return dict(descriptor_fields=result,trendbar_volume_unit='TICK_COUNT_NOT_EXECUTED_QUANTITY',historical_ticks='BID_OR_ASK_PRICE_AND_TIME_NOT_TRADE_PRINTS',depth_size_unit='DISPLAYED_BASE_UNITS_RAW_DIV_100',depth_clock='LOCAL_RECEIPT_ONLY_NOT_NATIVE_EVENT_TIME',depth_sequence='NONE_NOT_LOCAL_RECEIVE_ORDINAL',depth_snapshot_completeness='NOT_ATTESTED_BY_PROTOCOL',account_deals='ACCOUNT_SPECIFIC_NOT_ALL_MARKET_EXECUTIONS',execution_print_feed_available=False,aggressor_print_feed_available=False,strict_sequenced_full_book_available=False)


def audit_native_feed(source_database,output_directory) -> dict[str,Any]:
    out=Path(output_directory)
    if not out.is_absolute() or out.resolve()!=out or out.exists():raise ValueError('New absolute nonsymlink native audit output required')
    capture=acquire_original_depth(source_database,out/'capture',capture_seconds=12)
    result=dict(result='NATIVE_FEED_AUDIT_INCOMPLETE',capabilities=protocol_capabilities(),capture_result=capture['result'],synthetic_market_observations=0,broker_mutations=0,source_database_modified=False,background_jobs_left=0,sdk_processes_stopped=capture['sdk_processes_stopped'],auth_thread_stopped=capture['auth_thread_stopped'])
    if capture['result']=='ORIGINAL_DEPTH_CAPTURED_NOT_ADMITTED_AS_VENUE_BOOK':
        raw=json.loads((out/'capture/raw-depth.json').read_bytes());database=out/'capture/state.sqlite3'
        if Path(str(database)+'-wal').exists() and Path(str(database)+'-wal').stat().st_size:raise ValueError('Native audit requires a closed source snapshot')
        last_depth=max(e['received_at'] for events in raw['events'].values() for e in events)
        c=sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)
        try:
            c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
            quotes=[json.loads(body) for body, in c.execute("SELECT body FROM records WHERE kind='quote'")]
            bars=[json.loads(body) for body, in c.execute("SELECT body FROM records WHERE kind='bar'")]
        finally:c.close()
        cutoff=now();lanes={}
        for symbol in PAIRS:
            authority=raw['authority'][symbol];q=[v for v in quotes if v['symbol']==symbol and v['source_epoch']==authority['source_epoch'] and v['origin']=='LIVE_OBSERVED']
            quote=q[0] if len(q)==1 else None
            original=[v for v in bars if v['symbol']==symbol and v['source_epoch']==authority['source_epoch'] and v['origin']=='LIVE_OBSERVED']
            depth=capture['symbols'][symbol]
            lanes[symbol]=dict(**native_quote_health(quote,cutoff),history_bars={frame:sum(b['timeframe']==frame for b in original) for frame in FRAMES},native_tick_volume_bars=sum(type(b.get('tick_volume')) is int for b in original),depth_events=depth['events'],coherent_observed_depth=depth['coherent_observed_sides'],unknown_deleted_ids=depth['unknown_deleted_ids'],complete_book=False,executed_volume=False,aggressors=False)
        healthy=all(v['coherent_fresh_bid_ask'] and v['depth_events']>0 for v in lanes.values())
        result.update(result='CTRADER_NATIVE_FEED_AUDITED',quote_depth_transport='HEALTHY_DURING_BOUNDED_CAPTURE' if healthy else 'PARTIAL',observed_at=cutoff,last_depth_received_at=last_depth,freshness_measurement_clock='ACTUAL_LOCAL_WALL_CLOCK_AFTER_CAPTURE_NOT_VENDOR_EVENT_TIME',lanes=lanes,depth_events=sum(v['depth_events'] for v in lanes.values()),all_28_history_lanes_received=all(all(v['history_bars'].values()) for v in lanes.values()),strict_dom_admitted=False,no_global_execution_feed_claim=True)
    write_new(out/'feed-audit.json',(json.dumps(result,indent=2)+'\n').encode())
    return result
