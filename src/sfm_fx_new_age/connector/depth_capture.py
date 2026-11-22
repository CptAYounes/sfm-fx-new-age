"""Opt-in native broker-depth evidence capture, not a sequenced-venue publisher.

The protocol has no native sequence, event clock or full-snapshot marker. Receive
ordinals are transport bookkeeping only. Never convert this capture to VENUE_BOOK
or admit it to DOM strategy computation under an invented completeness claim.
"""
from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from time import monotonic,sleep
import hashlib,json,sqlite3
from typing import Any
from .original_capture import ReadOnlyCaptureSdk
from .official_context import now,write_new
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.storage.database import Database
from sfm_fx_new_age.contracts.domain import PAIRS


def decode_observed_levels(events):
    """Reconstruct only observed IDs; no assurance about the initial/full book."""
    book={};unknown_deletes=0
    for event in events:
        body=event['payload']
        if set(body)-{'payloadType','ctidTraderAccountId','symbolId','newQuotes','deletedQuotes'}:raise ValueError('Unknown depth field')
        for identity in body.get('deletedQuotes',[]):
            key=str(identity)
            if key not in book:unknown_deletes+=1
            book.pop(key,None)
        for quote in body.get('newQuotes',[]):
            if set(quote)-{'id','size','bid','ask'} or not {'id','size'}<=set(quote) or ('bid' in quote)==('ask' in quote):raise ValueError('Exact native depth quote required')
            identity=str(quote['id']);size=Decimal(str(quote['size']));side='bid' if 'bid' in quote else 'ask';raw_price=Decimal(str(quote[side]))
            if not identity.isdecimal() or not size.is_finite() or size<=0 or size!=size.to_integral_value() or not raw_price.is_finite() or raw_price<=0 or raw_price!=raw_price.to_integral_value():raise ValueError('Native positive integral depth fields required')
            book[identity]=dict(side=side,price=str(raw_price/Decimal(100000)),displayed_base_units=str(size/Decimal(100)))
            if len(book)>5000:raise ValueError('Observed depth ID budget exhausted')
    aggregated={'bid':{},'ask':{}}
    for q in book.values():
        p=Decimal(q['price']);side=aggregated[q['side']];side[p]=side.get(p,Decimal(0))+Decimal(q['displayed_base_units'])
    levels={side:[[str(p),str(q)] for p,q in sorted(values.items(),reverse=side=='bid')] for side,values in aggregated.items()}
    coherent=bool(levels['bid'] and levels['ask'] and Decimal(levels['bid'][0][0])<Decimal(levels['ask'][0][0]))
    return dict(observed_levels=levels,coherent_observed_sides=coherent,unknown_deleted_ids=unknown_deletes,full_book_complete=False,native_sequence_available=False,sequence_gap_detection_available=False)


def acquire_original_depth(source_database,output_directory,*,capture_seconds=12,timeout_seconds=120):
    source=Path(source_database).resolve(strict=True);out=Path(output_directory)
    if not out.is_absolute() or out.resolve()!=out or not 3<=capture_seconds<=30 or not 30<=timeout_seconds<=180:raise ValueError('New absolute nonsymlink output and bounded interval required')
    out.mkdir(mode=0o700,parents=True,exist_ok=False)
    c=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    try:
        c.execute('PRAGMA query_only=ON');c.execute('BEGIN');settings=c.execute("SELECT kind,id,body FROM records WHERE kind='setting' AND id IN ('connector_public_profile','connector_remember')").fetchall()
    finally:c.close()
    values={identity:json.loads(body) for _,identity,body in settings};remembered=values.get('connector_remember',{})
    if not remembered.get('enabled') or not remembered.get('scope_id') or not values.get('connector_public_profile'):raise ValueError('Remembered original source required')
    db=Database(out/'state.sqlite3')
    try:
        with db.transaction() as c:c.executemany('INSERT INTO records VALUES(?,?,?)',settings)
    finally:db.close()
    r=ApplicationRuntime(out/'state.sqlite3');workers=[];events={s:[] for s in PAIRS};acks=[];unsubscribed=[];errors=[];binding={};started=monotonic()
    proof:dict[str,Any]={}
    def factory(config):
        worker=ReadOnlyCaptureSdk(config);workers.append(worker);return worker
    r.connector.worker_factory=factory
    def deny(*args,**kwargs):raise PermissionError('Depth capture has no broker mutation authority')
    r.connector.submit=deny;r.connector.cancel=deny
    original_handle=r.connector.handle
    def handle(endpoint,message):
        request=r.connector.requests.get(message.get('request_id',''));original_handle(endpoint,message)
        if message.get('kind')!='MESSAGE' or not binding or endpoint!=binding['endpoint']:return
        body=message.get('payload',{});name=message.get('name')
        if str(body.get('ctidTraderAccountId',''))!=binding['account_id']:return
        if name in {'ProtoOASubscribeDepthQuotesRes','ProtoOAUnsubscribeDepthQuotesRes'} and request and (request.get('context') or {}).get('original_depth'):
            target=acks if name=='ProtoOASubscribeDepthQuotesRes' else unsubscribed;target.append(dict(received_at=now(),payload=body));return
        if name=='ProtoOADepthEvent':
            symbol=binding['symbol_ids'].get(str(body.get('symbolId')))
            if symbol is None:return
            rows=events[symbol]
            if len(rows)>=1024 or len(json.dumps(body))>256000:raise ValueError('Native depth capture budget exhausted')
            rows.append(dict(receive_ordinal=len(rows)+1,received_at=now(),payload=body))
    r.connector.handle=handle
    def poll():
        r.connector.poll();r.pump()
        if r.connector.errors:raise ValueError('Connector rejected native frame')
        if r.connector.state in {'LOGIN_REQUIRED','CONNECTION_FAILED','APPLICATION_AUTH_FAILED'}:raise ValueError('Original source unavailable')
    try:
        r.connector.resume_saved_session()
        while monotonic()-started<timeout_seconds:
            poll();account=r.accounts.current
            if account and account.authenticated and account.scope_id==remembered['scope_id'] and all(r.market.spec(account.account_id,s) for s in PAIRS):break
            sleep(.05)
        else:raise TimeoutError('Native depth source metadata deadline')
        account=r.accounts.current
        assert account is not None
        ids={}
        for symbol in PAIRS:
            spec=r.market.spec(account.account_id,symbol)
            if spec is None:raise ValueError('Original symbol metadata disappeared')
            ids[str(spec.broker_symbol_id)]=symbol
        binding.update(account_id=account.account_id,endpoint=account.endpoint_class,symbol_ids=ids)
        authority={s:r.market.authority(s) for s in PAIRS}
        payload=dict(ctidTraderAccountId=account.account_id,symbolId=[int(s) for s in ids]);r.connector.request(account.endpoint_class,'ProtoOASubscribeDepthQuotesReq',payload,context={'original_depth':True})
        while not acks and monotonic()-started<timeout_seconds:poll();sleep(.04)
        if not acks:raise TimeoutError('Native depth subscription acknowledgement absent')
        subscribed_at=monotonic()
        while monotonic()-subscribed_at<capture_seconds and monotonic()-started<timeout_seconds:
            poll()
            if not r.accounts.current or r.accounts.current.scope_id!=account.scope_id or any(r.market.authority(s)!=authority[s] for s in PAIRS):raise ValueError('Source changed during native depth capture')
            sleep(.04)
        r.connector.request(account.endpoint_class,'ProtoOAUnsubscribeDepthQuotesReq',payload,context={'original_depth':True});stop=monotonic()+5
        while not unsubscribed and monotonic()<stop:poll();sleep(.04)
        if not unsubscribed:raise TimeoutError('Native unsubscribe acknowledgement absent')
        if not all(events.values()):raise ValueError('No original depth observations for one or more requested pairs')
        rows={s:decode_observed_levels(v) for s,v in events.items()}
        raw=dict(scope='ORIGINAL_BROKER_DEPTH_CHANGES_NOT_PROVED_FULL_SEQUENCED_BOOK',source_scope_sha256=hashlib.sha256(account.scope_id.encode()).hexdigest(),authority=authority,subscription_acks=acks,unsubscribe_acks=unsubscribed,events=events)
        data=(json.dumps(raw,indent=2)+'\n').encode();write_new(out/'raw-depth.json',data)
        proof=dict(result='ORIGINAL_DEPTH_CAPTURED_NOT_ADMITTED_AS_VENUE_BOOK',raw_sha256=hashlib.sha256(data).hexdigest(),symbols={s:dict(events=len(events[s]),**rows[s]) for s in PAIRS},source_scope_sha256=raw['source_scope_sha256'],source_database_modified=False,native_sequence_available=False,native_event_clock_available=False,full_snapshot_marker_available=False,dom_strategy_admitted=False,synthetic_observations=0,executed_volume_claim=False,receive_ordinals_are_not_native_sequences=True)
    except Exception as exc:
        errors.append(type(exc).__name__);proof=dict(result='DEPTH_CAPTURE_INCOMPLETE',error_types=errors,dom_strategy_admitted=False,synthetic_observations=0)
        data=(json.dumps(dict(subscription_acks=acks,unsubscribe_acks=unsubscribed,events=events),indent=2)+'\n').encode();write_new(out/'partial-raw-depth.json',data)
    finally:
        auth=r.connector.auth_worker;r.close()
        if auth and auth.is_alive():auth.join(timeout=35)
        proof.update(sdk_processes_stopped=all(not w.process.is_alive() for w in workers),auth_thread_stopped=not(auth and auth.is_alive()),runtime_closed=r.closed,denied_broker_mutations=sum(w.denied_writes for w in workers),read_request_counts={name:sum(w.read_counts.get(name,0) for w in workers) for name in sorted({n for w in workers for n in w.read_counts})},elapsed_seconds=round(monotonic()-started,3),delegated_agents_started=0)
        write_new(out/'depth-receipt.json',(json.dumps(proof,indent=2)+'\n').encode())
    if not proof['sdk_processes_stopped'] or not proof['auth_thread_stopped']:raise RuntimeError('Depth capture did not stop owned workers')
    return proof
