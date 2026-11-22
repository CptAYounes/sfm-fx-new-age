#!/usr/bin/env python3
"""Bounded, real cTrader read-only acceptance. Never accepts secrets on argv/stdout.

Uses an explicitly supplied private handoff file, or the already configured saved
session. A recording/denying worker fence rejects every broker write operation.
"""
from __future__ import annotations
import argparse,json,time,sys
from pathlib import Path
from collections import Counter
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.connector.sdk_worker import SdkProcess,READ_REQUESTS
from sfm_fx_new_age.contracts.domain import PAIRS,FRAMES,instant

class ReadOnlySdkProcess(SdkProcess):
    audit=Counter()
    def send(self,body):
        if body['kind']=='AUTH_ACCOUNT':self.audit['AUTH_ACCOUNT']+=1
        elif body['kind']=='READ' and body.get('name') in READ_REQUESTS:self.audit[body['name']]+=1
        else:
            self.audit['DENIED_WRITE']+=1;raise ValueError('Read-only feed verification forbids writes')
        return super().send(body)


def acceptance_result(quotes,history,feed,sessions,*,allow_market_closed=False):
    history_ok=len(history)==len(PAIRS) and all(set(frames)==set(FRAMES) and all(n>0 for n in frames.values()) for frames in history.values())
    history_ok=history_ok and feed.get('completed_history_jobs')==28 and not feed.get('failed_history_jobs')
    snapshots_ok=len(quotes)==len(PAIRS) and all(q['current_connection_epoch'] and not q.get('future',False) for q in quotes.values())
    if history_ok and snapshots_ok:
        if all(q['fresh'] for q in quotes.values()):return 'PASS_QUOTES_AND_HISTORY'
        if allow_market_closed and len(sessions)==len(PAIRS) and all(s.get('market_open') is False for s in sessions.values()):
            return 'PASS_CLOSED_MARKET_SNAPSHOTS_AND_HISTORY'
    return 'PARTIAL_DATA'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir',type=Path,required=True)
    parser.add_argument('--session-file',type=Path)
    parser.add_argument('--account-scope')
    parser.add_argument('--timeout',type=int,default=120)
    parser.add_argument('--allow-market-closed',action='store_true',help='Accept timestamp-preserved current-connection snapshots and history only when every current native symbol schedule is closed; never claim fresh ticks')
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    if not 10<=args.timeout<=180:parser.error('Timeout must be 10–180 seconds')
    if args.receipt.exists():parser.error('Refusing to overwrite an existing acceptance receipt')
    runtime=ApplicationRuntime(args.state_dir/'state.sqlite3');connector=runtime.connector
    connector.worker_factory=ReadOnlySdkProcess;start=runtime.clock();started=time.monotonic();selected=False
    summary={'started_at':start,'real_external_acceptance':True,'broker_writes_permitted':False,'result':'NOT_CONNECTED'}
    try:
        if args.session_file:connector.import_session(args.session_file)
        elif connector.oauth and connector.session_available:
            connector._resume_scope=connector.preferences.get('scope_id');connector._auto_select_single=True;connector.connect()
        else:raise ValueError('No private application session is configured')
        while time.monotonic()-started<args.timeout:
            runtime.pump()
            if args.account_scope and not selected and args.account_scope in runtime.accounts.sessions:
                runtime.accounts.select_known(args.account_scope);connector.start_market_feed();selected=True
            account=runtime.accounts.current;feed=connector.feed_status()
            if connector.state in {'LOGIN_REQUIRED','APPLICATION_AUTH_FAILED'}:break
            if account:
                quotes=[runtime.market.quote(account.account_id,s) for s in PAIRS]
                fresh=sum(q is not None and 0<=(instant(runtime.clock())-instant(q.available_at)).total_seconds()<=30 for q in quotes)
                closed=all((cal:=runtime.continuity.calendar(s)) is not None and cal.source_ref=='ProtoOASymbol.schedule / '+feed.get('source_epoch','') and not cal.is_open(runtime.clock()) for s in PAIRS)
                snapshots=all(q and q.source_epoch==feed.get('source_epoch') for q in quotes)
                if feed['completed_history_jobs']==28 and feed['received_bars']>0 and (fresh==len(PAIRS) or args.allow_market_closed and closed and snapshots):break
                if feed['failed_history_jobs']:break
            elif connector._account_lists_seen==set(connector.workers) and len(runtime.accounts.sessions)>1 and not args.account_scope:break
            time.sleep(.05)
        runtime.pump();account=runtime.accounts.current
        summary.update(ended_at=runtime.clock(),connector_state=connector.state,reason=connector.reason,
            authenticated_account_count=len(runtime.accounts.sessions),selected_account=bool(account),feed=connector.feed_status(),errors=connector.errors,
            read_request_counts=dict(ReadOnlySdkProcess.audit),local_order_count=len(runtime.database.orders()))
        if account:
            summary['endpoint']=account.endpoint_class;summary['broker']=account.broker_id
            summary['account_tail']=account.account_id[-4:];summary['quotes']={};summary['history']={};summary['sessions']={}
            for symbol in PAIRS:
                quote=runtime.market.quote(account.account_id,symbol);authority=runtime.market.authority(symbol)
                if quote:
                    age=(instant(runtime.clock())-instant(quote.available_at)).total_seconds()
                    summary['quotes'][symbol]={'observed_at':quote.available_at,'bid_at':quote.bid_at,'ask_at':quote.ask_at,'fresh':0<=age<=30,'future':age<0,'current_connection_epoch':bool(authority and authority['source_epoch']==quote.source_epoch),'bid':str(quote.bid),'ask':str(quote.ask)}
                cal=runtime.continuity.calendar(symbol)
                valid=cal is not None and authority is not None and cal.source_ref=='ProtoOASymbol.schedule / '+authority['source_epoch']
                summary['sessions'][symbol]={'market_open':cal.is_open(runtime.clock()) if valid else None,'next_scheduled_open':cal.next_open(runtime.clock()) if valid and not cal.is_open(runtime.clock()) else None}
                summary['history'][symbol]={frame:len(runtime.market.bars(symbol,frame,runtime.clock(),authority['source_epoch'])) if authority else 0 for frame in FRAMES}
            summary['result']=acceptance_result(summary['quotes'],summary['history'],summary['feed'],summary['sessions'],allow_market_closed=args.allow_market_closed)
            if connector.errors:summary['result']='PARTIAL_DATA'
        elif len(runtime.accounts.sessions)>1:
            summary['result']='HUMAN_ACCOUNT_SELECTION_REQUIRED'
            summary['account_choices']=[{'broker':a.broker_id,'endpoint':a.endpoint_class,'tail':a.account_id[-4:],'scope_id':a.scope_id} for a in runtime.accounts.sessions.values()]
        assert ReadOnlySdkProcess.audit['DENIED_WRITE']==0
    except Exception as exc:
        summary.update(result='FAILED',error_type=type(exc).__name__)
        # Exception messages/tracebacks could include secrets; only known connector state is exported.
    finally:
        runtime.close()
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        args.receipt.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');args.receipt.chmod(0o600)
    # Verify the exact newly written receipt and durable observation counts before reporting.
    observed=json.loads(args.receipt.read_text());assert observed==summary
    print(json.dumps(summary,indent=2,sort_keys=True))
    return 0 if summary['result'] in {'PASS_QUOTES_AND_HISTORY','PASS_CLOSED_MARKET_SNAPSHOTS_AND_HISTORY'} else 2

if __name__=='__main__':raise SystemExit(main())
