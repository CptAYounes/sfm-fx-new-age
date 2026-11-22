"""Bounded TLS cTrader FIX Price/QUOTE capture. No Trade session or order writer.

Connection values must come from actual private FIX Price credentials; OAuth and
cTID credentials are never guessed, converted or reused. This is an opt-in closed
capture, not a background price service or automatic current-source promotion.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone,timedelta
from time import monotonic
from decimal import Decimal
from uuid import uuid4
import json,hashlib,socket,ssl,sqlite3
from typing import Any
from .oauth import SecretStore
from .fix_protocol import Decoder,QuoteBook,FixError,encode_quote,one,groups,stamp,text
from .official_context import write_new
from sfm_fx_new_age.contracts.domain import PAIRS,instant
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape

FIX_FIELDS={'schema_version','host','tls_port','sender_comp_id','target_comp_id','username','password','scope_id'}

def load_price_credentials(path):
    body=SecretStore(Path(path)).load()
    if set(body)!=FIX_FIELDS or type(body['schema_version']) is not int or body['schema_version']!=1:raise ValueError('Exact private FIX Price configuration required')
    for field in ('host','sender_comp_id','target_comp_id','username','password','scope_id'):text(body[field])
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for c in body['host']) or body['host'].startswith(('.', '-')) or body['host'].endswith(('.', '-')):raise ValueError('Explicit TLS broker hostname required')
    if type(body['tls_port']) is not int or not 1<=body['tls_port']<=65535 or not body['username'].isdecimal():raise ValueError('Explicit Price TLS port and numeric username required')
    if body['target_comp_id'].upper()!='CSERVER':raise ValueError('cTrader target identity required')
    return body


def original_bindings(database,scope):
    p=Path(database).resolve(strict=True);c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
    try:
        c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
        def get(kind,identity):
            row=c.execute('SELECT body FROM records WHERE kind=? AND id=?',(kind,identity)).fetchone()
            return json.loads(row[0]) if row else None
        remember=get('setting','connector_remember');meta=get('account_metadata',scope)
        if not remember or not remember.get('enabled') or remember.get('scope_id')!=scope or not meta:raise ValueError('FIX must declare the actually remembered source scope')
        rows={}
        for symbol in PAIRS:
            candidates=[json.loads(body) for body, in c.execute("SELECT body FROM records WHERE kind='authority' AND json_extract(body,'$.scope_id')=? AND json_extract(body,'$.symbol')=?",(scope,symbol))]
            specs=[json.loads(body) for body, in c.execute("SELECT body FROM records WHERE kind='spec' AND json_extract(body,'$.scope_id')=? AND json_extract(body,'$.symbol')=?",(scope,symbol))]
            if len(candidates)!=1 or len(specs)!=1 or candidates[0]['origin']!='LIVE_OBSERVED':raise ValueError('Unique original authority/specification required')
            rows[symbol]=dict(authority=candidates[0],spec=specs[0])
        return rows
    finally:c.close()


class PriceSession:
    def __init__(self,config,stream):
        self.config=config;self.stream=stream;self.incoming=1;self.outgoing=1;self.decoder=Decoder();self.logged_in=False;self.sent_counts={};self.received_counts={};self.messages=0;self.last_send=monotonic()
    def send(self,kind,fields=()):
        wire=encode_quote(kind,self.outgoing,self.config['sender_comp_id'],self.config['target_comp_id'],fields)
        self.stream.sendall(wire);self.last_send=monotonic();self.outgoing+=1;self.sent_counts[kind]=self.sent_counts.get(kind,0)+1
    def receive(self):
        chunk=self.stream.recv(65536)
        if not chunk:raise FixError('FIX peer closed stream')
        frames=self.decoder.feed(chunk);results=[]
        for raw,fields in frames:
            if any(k in {553,554,95,96} for k,v in fields):raise FixError('Unexpected secret/raw field in server frame; never recorded')
            seq=one(fields,34)
            if not seq.isdecimal() or int(seq)!=self.incoming:raise FixError('FIX native session gap/duplicate; reconnect with full snapshots required')
            if one(fields,49)!=self.config['target_comp_id'] or one(fields,56)!=self.config['sender_comp_id'] or one(fields,50)!='QUOTE' or one(fields,57)!='QUOTE':raise FixError('FIX Price routing identity mismatch')
            if one(fields,43,'N')!='N':raise FixError('Possible duplicate replay cannot refresh book')
            native=stamp(one(fields,52));kind=one(fields,35)
            if kind not in {'A','0','1','5','3','j','Y','y','W','X'}:raise FixError('Unrequested FIX traffic/reset; invalidate rather than patch gaps')
            if not self.logged_in:
                if kind!='A' or one(fields,98)!='0' or one(fields,108)!='30':raise FixError('Expected original FIX logon acknowledgement')
                self.logged_in=True
            elif kind=='A':raise FixError('Unexpected repeated FIX logon')
            self.incoming+=1;self.messages+=1
            if self.messages>5000:raise FixError('FIX message budget exhausted')
            self.received_counts[kind]=self.received_counts.get(kind,0)+1
            if kind in {'5','3','j','Y'}:raise FixError('FIX peer logout/reject; private text not recorded')
            if kind=='1':self.send('0',[(112,one(fields,112))])
            results.append((raw,fields,native))
        return results


def snapshot_envelope(symbol,levels,sequence,native,received,binding,session_identity) -> dict[str,Any]:
    t=instant(native);available=instant(received)
    if not 0<=(available-t).total_seconds()<=5 or available<=t:raise FixError('Original FIX book is future-dated or older than five seconds')
    tick=Decimal(str(binding['spec']['tick_size']))
    if tick<=0 or any(Decimal(p)%tick for side in ('bids','asks') for p,q in levels[side]):raise FixError('FIX/native symbol price grid mismatch')
    # Session MsgSeqNum identifies native transport continuity, not a correction
    # of this publication interval. Each newly captured interval starts at one;
    # the original native sequence remains unchanged in its observation and ID.
    body:dict[str,Any]=dict(provider_id='CTRADER_FIX_QUOTE_FULL_BOOK_V1',kind='VENUE_BOOK',scope_id=binding['authority']['scope_id'],source_epoch=binding['authority']['source_epoch'],symbol=symbol,origin='LIVE_OBSERVED',source_ref='Original TLS FIX Price W-initialized contiguous session '+session_identity+'; CLOSED_CAPTURE_NOT_A_CURRENT_PUBLISHER',venue='CTRADER_BROKER_QUOTED_LIQUIDITY_NOT_GLOBAL_EXECUTIONS',instrument=symbol,price_domain='SPOT_PAIR',unit='DISPLAYED_BASE_UNITS',window_start=(t-timedelta(microseconds=1)).isoformat().replace('+00:00','Z'),window_end=(t+timedelta(microseconds=1)).isoformat().replace('+00:00','Z'),available_at=received,valid_until=(t+timedelta(seconds=5)).isoformat().replace('+00:00','Z'),complete=True,records=[dict(id=session_identity+':'+str(sequence)+':'+symbol,time=native,available_at=received,sequence=sequence,**levels)],parameters={},revision=1)
    validate_wire_shape(SupplementalEvidence(**dict(body,records=tuple(body['records']))))
    return body


def capture_fix_price(source_database,credentials_path,output_directory,*,capture_seconds=12) -> dict[str,Any]:
    out=Path(output_directory)
    if not out.is_absolute() or out.resolve()!=out or out.exists() or not 3<=capture_seconds<=30:raise ValueError('New absolute nonsymlink FIX output and bounded capture required')
    out.mkdir(mode=0o700,parents=True)
    proof:dict[str,Any]=dict(result='FIX_NOT_CONNECTED',logged_in=False,credentials_present=False,network_started=False,full_book_symbols=[],market_frames=0,broker_mutations=0,execution_print_feed=False,aggressor_feed=False,dom_operationally_qualified=False,synthetic_market_observations=0,background_jobs_left=0,private_logon_bytes_recorded=False,stream_closed=True)
    sock=None;session=None;book=None;frames=[];latest={};start=monotonic();socket_opened=False;market_bytes=0
    try:
        path=Path(credentials_path)
        if not path.exists():proof['result']='FIX_PRICE_CREDENTIALS_MISSING';return proof
        config=load_price_credentials(path);proof['credentials_present']=True;bindings=original_bindings(source_database,config['scope_id'])
        proof['network_started']=True;plain=socket.create_connection((config['host'],config['tls_port']),timeout=10);socket_opened=True
        try:sock=ssl.create_default_context().wrap_socket(plain,server_hostname=config['host'])
        except Exception:plain.close();raise
        sock.settimeout(.5);proof['stream_closed']=False;proof['tls_verified']=True;session=PriceSession(config,sock);session.send('A',[(98,'0'),(108,'30'),(141,'Y'),(553,config['username']),(554,config['password'])]);session_id=str(uuid4());list_id='list-'+str(uuid4());request_id='book-'+str(uuid4());ids={};subscribed=False;last_receive=monotonic();last_send=monotonic();capture_started=None
        while monotonic()-start<min(90,capture_seconds+40):
            try:messages=session.receive()
            except socket.timeout:
                if monotonic()-last_receive>45:raise FixError('FIX peer heartbeat timeout')
                if monotonic()-session.last_send>=25:session.send('0')
                continue
            last_receive=monotonic()
            for raw,fields,native in messages:
                kind=one(fields,35);received=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
                if kind=='A':proof['logged_in']=True;session.send('x',[(320,list_id),(559,'0')])
                if kind=='y':
                    if one(fields,320)!=list_id or one(fields,560)!='0':raise FixError('Security list response is not the actual request')
                    for row in groups(fields,146,55,{55,1007,1008}):
                        symbol=row.get(1007)
                        if symbol not in PAIRS:continue
                        digits=row.get(1008)
                        if digits is None or not digits.isdecimal() or int(digits)>5 or Decimal(bindings[symbol]['spec']['tick_size'])!=Decimal(10)**-int(digits):raise FixError('FIX security list/native tick mismatch')
                        if row[55] in ids or symbol in ids.values() or not row[55].isdecimal():raise FixError('Ambiguous native FIX instrument identity')
                        ids[row[55]]=symbol
                    if len(ids)==len(PAIRS) and not subscribed:
                        book=QuoteBook(ids);payload=[(262,request_id),(263,'1'),(264,'0'),(265,'1'),(267,'2'),(269,'0'),(269,'1'),(146,str(len(ids)))]+[(55,k) for k in ids]
                        session.send('V',payload);subscribed=True;capture_started=monotonic()
                if kind in {'W','X'}:
                    if not book or not subscribed:raise FixError('Unrequested book traffic')
                    # MDReqID is required on native W/X. Absence cannot prove
                    # this subscription's identity by defaulting to our request.
                    if one(fields,262)!=request_id:raise FixError('Book request identity mismatch')
                    changed=book.apply(fields)
                    market_bytes+=len(raw)
                    if len(frames)>=2000 or market_bytes>8000000:raise FixError('FIX original capture storage budget')
                    frames.append(dict(native_sending_time=native,received_at=received,sequence=int(one(fields,34)),wire_hex=raw.hex(),origin='LIVE_ORIGINAL_TLS_FIX_QUOTE'))
                    for symbol in changed:
                        levels=book.levels(symbol)
                        if levels is None:latest.pop(symbol,None);continue
                        try:latest[symbol]=snapshot_envelope(symbol,levels,int(one(fields,34)),native,received,bindings[symbol],session_id)
                        except FixError:latest.pop(symbol,None)
                if monotonic()-session.last_send>=25:session.send('0')
            if capture_started is not None and monotonic()-capture_started>=capture_seconds:break
        if not subscribed:raise FixError('FIX authentication/security-list deadline')
        if book is None or set(PAIRS)-book.initialized:raise FixError('Full W snapshots not received for all requested native symbols')
        final_time=datetime.now(timezone.utc)
        latest={symbol:body for symbol,body in latest.items() if final_time<=instant(body['valid_until'])}
        session.send('V',[(262,request_id),(263,'2'),(264,'0'),(265,'1'),(267,'2'),(269,'0'),(269,'1'),(146,str(len(ids)))]+[(55,k) for k in ids]);session.send('5')
        for symbol,body in latest.items():write_new(out/(symbol+'-book.json'),(json.dumps(body,indent=2)+'\n').encode())
        entries=[dict(file=s+'-book.json',sha256=hashlib.sha256((out/(s+'-book.json')).read_bytes()).hexdigest()) for s in latest]
        if entries:
            write_new(out/'manifest.json',(json.dumps(dict(schema_version=1,entries=entries),indent=2)+'\n').encode());write_new(out/'sources.json',(json.dumps(dict(schema_version=1,providers=[dict(provider_id='CTRADER_FIX_QUOTE_FULL_BOOK_V1',origin='LIVE_OBSERVED',kinds=['VENUE_BOOK'],manifest_path=str(out/'manifest.json'))]),indent=2)+'\n').encode())
        proof.update(result='FIX_ORIGINAL_FULL_BOOK_CAPTURED_CLOSED_EPOCH',full_book_symbols=sorted(book.initialized),published_snapshot_symbols=sorted(latest),dom_operationally_qualified=False,full_snapshot_and_contiguous_session_proved=True,current_publisher=False)
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
        if book:book.invalidate()
        latest.clear();proof.update(result='FIX_CAPTURE_REFUSED_OR_FAILED',error_type=type(exc).__name__,dom_operationally_qualified=False)
    finally:
        if sock:sock.close()
        proof.update(stream_closed=True,market_frames=len(frames),sent_message_type_counts=session.sent_counts if session else {},received_message_type_counts=session.received_counts if session else {},elapsed_seconds=round(monotonic()-start,3),socket_opened=socket_opened)
        if frames:write_new(out/'original-fix-market-frames.json',(json.dumps(frames,indent=2)+'\n').encode())
        write_new(out/'fix-receipt.json',(json.dumps(proof,indent=2)+'\n').encode())
    return proof
