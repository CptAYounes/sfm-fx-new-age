"""Connector-owned observed broker DOM; never a sequenced/full venue book.

One subscription per authenticated binding, bounded ID maps, one coalesced
publication per pair/second, original receive clocks. No new worker or orders.
"""
from collections import deque
from datetime import timedelta
from decimal import Decimal
from time import monotonic
from uuid import uuid4
from queue import Full
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import PAIRS,instant
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.contracts.enums import Priority
from .lanes import lane_matches

PROVIDER='CTRADER_OBSERVED_BROKER_DEPTH_V1'


class ConnectedBrokerDepth:
    def __init__(self,connector,*,excluded=False):
        self.c=connector;self.r=connector.r;self.store=self.r.analytics.supplemental;self.excluded=excluded
        self.binding=None;self.attempted=False;self.ack=False;self.session=None;self.ids={};self.books={};self.received={};self.unknown={};self.dirty=set();self.published={};self.states={};self.audit=deque(maxlen=64);self.events=0;self.publications=0
        self.tokens={};self.acknowledged=set()
    def _withdraw(self):
        self.store.providers.pop(PROVIDER,None);self.store.admissions.pop(PROVIDER,None)
        for symbol in self.books:self.r.emit('ANALYTICS.INPUT','CT_OPEN_API_CONNECTOR',dict(symbol=symbol,source_epoch='BROKER_DEPTH_WITHDRAWN'),Priority.P2,self.r.market.scope_id)
    def disconnect(self):
        if self.binding and self.tokens:
            try:self.c.request(self.binding[0],'ProtoOAUnsubscribeDepthQuotesReq',dict(ctidTraderAccountId=self.binding[1],symbolId=list(self.ids)),context={'broker_depth':'UNSUBSCRIBE','binding':self.binding})
            except (ValueError,OSError,KeyError,Full):pass
        self._withdraw();self.binding=None;self.ack=False;self.attempted=False;self.ids={};self.books={};self.received={};self.unknown={};self.dirty.clear();self.published={};self.states={}
        self.tokens.clear();self.acknowledged.clear()

    def _withdraw_pair(self,symbol):
        if not self.binding:return
        epoch=dict(self.binding[2][1]).get(symbol)
        if epoch:
            members=self.store.admissions.get(PROVIDER,set())
            for row in self.r.database.supplemental_candidates(scope=self.binding[2][0],epoch=epoch,symbol=symbol,origin='LIVE_OBSERVED',providers=self.store.providers,cutoff=self.r.clock()):
                if row['provider_id']==PROVIDER:members.discard(digest(row))
        self.r.emit('ANALYTICS.INPUT','CT_OPEN_API_CONNECTOR',dict(symbol=symbol,source_epoch='BROKER_DEPTH_WITHDRAWN'),Priority.P2,self.r.market.scope_id)

    def _same_session(self,binding):
        return bool(binding and self.binding and binding[:2]==self.binding[:2] and binding[2][0]==self.binding[2][0] and {e for _,e in binding[2][1]}=={e for _,e in self.binding[2][1]})
    def poll(self,identity):
        if self.excluded:return
        account=self.r.accounts.current
        binding=(account.endpoint_class,account.account_id,identity) if account and identity else None
        if binding!=self.binding:
            if self._same_session(binding):
                wanted={self.r.market.spec(account.account_id,s).broker_symbol_id:s for s,_ in identity[1] if lane_matches(self.r,identity,s)}
                removed=[sid for sid in self.ids if wanted.get(sid)!=self.ids[sid]]
                if removed:
                    try:self.c.request(binding[0],'ProtoOAUnsubscribeDepthQuotesReq',dict(ctidTraderAccountId=binding[1],symbolId=removed),context={'broker_depth':'UNSUBSCRIBE','binding':self.binding})
                    except (ValueError,OSError,KeyError,Full):pass
                for sid in removed:
                    symbol=self.ids[sid];self._withdraw_pair(symbol)
                    for table in (self.books,self.received,self.unknown,self.published,self.states):table.pop(symbol,None)
                    self.dirty.discard(symbol);self.acknowledged.discard(symbol);self.tokens.pop(sid,None)
                self.ids=wanted;self.binding=binding
                for symbol in wanted.values():
                    self.books.setdefault(symbol,{});self.unknown.setdefault(symbol,0);self.states.setdefault(symbol,'SUBSCRIBING')
            else:
                self.disconnect();self.binding=binding;self.session=str(uuid4())
        if not binding:return
        if not self.ids:
            pairs=tuple(s for s,_ in identity[1] if lane_matches(self.r,identity,s))
            self.ids={self.r.market.spec(account.account_id,s).broker_symbol_id:s for s in pairs}
            if not self.ids:return
            self.books={s:{} for s in pairs};self.unknown={s:0 for s in pairs};self.states={s:'SUBSCRIBING' for s in pairs}
        pending=[sid for sid in self.ids if sid not in self.tokens]
        if pending:
            token=str(uuid4())
            try:
                self.c.request(account.endpoint_class,'ProtoOASubscribeDepthQuotesReq',dict(ctidTraderAccountId=account.account_id,symbolId=pending),context={'broker_depth':'SUBSCRIBE','binding':binding,'subscription_token':token})
            except Full:
                # Nothing was enqueued. Wait for capacity, not a fake failure or
                # a permanently consumed attempt. Sent/failed reads never retry.
                for sid in pending:self.states[self.ids[sid]]='WAITING_READ_CAPACITY'
            else:
                self.tokens.update({sid:token for sid in pending});self.attempted=True
        self.ack=bool(self.acknowledged) and self.acknowledged==set(self.books)
        for symbol in tuple(self.dirty):
            if symbol not in self.acknowledged:continue
            if monotonic()-self.published.get(symbol,-100)<1:continue
            self.dirty.discard(symbol)
            try:self.publish(symbol)
            except (ValueError,KeyError,ArithmeticError):
                self.states[symbol]='INCOMPLETE_OR_INVALID_OBSERVED_SIDES'
                # Withdraw only this pair's current admissions, never revive old book.
                members=self.store.admissions.get(PROVIDER,set())
                for row in self.r.database.supplemental_candidates(scope=self.r.market.scope_id,epoch=self.r.market.authority(symbol)['source_epoch'],symbol=symbol,origin='LIVE_OBSERVED',providers=self.store.providers,cutoff=self.r.clock()):
                    if row['provider_id']==PROVIDER:members.discard(digest(row))
                self.store.admissions[PROVIDER]=members
    def fail(self,request):
        context=(request or {}).get('context') or {}
        if context.get('broker_depth')!='SUBSCRIBE' or not self._same_session(context.get('binding')):return
        for sid in (request.get('payload') or {}).get('symbolId',[]):
            if sid in self.ids and self.tokens.get(sid)==context.get('subscription_token'):
                symbol=self.ids[sid];self._withdraw_pair(symbol);self.acknowledged.discard(symbol);self.states[symbol]='SUBSCRIPTION_FAILED'
        self.ack=bool(self.acknowledged) and self.acknowledged==set(self.books)
    def handle(self,endpoint,name,body,request):
        if not self.binding or endpoint!=self.binding[0] or str(body.get('ctidTraderAccountId',''))!=self.binding[1]:return
        if name=='ProtoOASubscribeDepthQuotesRes':
            context=(request or {}).get('context') or {}
            if self._same_session(context.get('binding')):
                for sid in (request.get('payload') or {}).get('symbolId',[]):
                    if sid in self.ids and self.tokens.get(sid)==context.get('subscription_token'):
                        self.acknowledged.add(self.ids[sid]);self.states[self.ids[sid]]='WAITING_OBSERVED_SIDES'
                self.ack=bool(self.acknowledged) and self.acknowledged==set(self.books)
            return
        if name!='ProtoOADepthEvent':return
        symbol=self.ids.get(int(body.get('symbolId',-1)))
        if not symbol or not lane_matches(self.r,self.binding[2],symbol):return
        received=self.r.clock();book=self.books[symbol];self.events+=1
        self.audit.append(dict(symbol=symbol,received_at=received,payload=dict(body)))
        if set(body)-{'payloadType','ctidTraderAccountId','symbolId','newQuotes','deletedQuotes'}:raise ValueError('Unknown native depth fields')
        for value in body.get('deletedQuotes',[]):
            identity=str(value)
            if identity not in book:self.unknown[symbol]+=1
            book.pop(identity,None)
        for q in body.get('newQuotes',[]):
            if set(q)-{'id','size','bid','ask'} or not {'id','size'}<=set(q) or ('bid' in q)==('ask' in q):raise ValueError('Exact native depth quote required')
            size=Decimal(str(q['size']));side='bids' if 'bid' in q else 'asks';p=Decimal(str(q['bid' if side=='bids' else 'ask']))
            if min(size,p)<=0 or not size.is_finite() or not p.is_finite() or size!=int(size) or p!=int(p):raise ValueError('Positive integral native depth fields required')
            book[str(q['id'])]=(side,p/100000,size/100)
        if len(book)>5000:book.clear();self.dirty.add(symbol);raise ValueError('Broker depth ID budget')
        self.received[symbol]=received;self.dirty.add(symbol)
    def publish(self,symbol):
        if not self.binding or not lane_matches(self.r,self.binding[2],symbol):raise ValueError('Current pair metadata required')
        assert self.session is not None
        received=self.received[symbol];published_at=self.r.clock();now=instant(published_at);at=instant(received)
        if not .000001<=(now-at).total_seconds()<15:raise ValueError('Observed receipt expired or publication clock not advanced')
        levels={'bids':{},'asks':{}}
        for side,p,q in self.books[symbol].values():levels[side][p]=levels[side].get(p,Decimal(0))+q
        levels={side:[[str(p),str(q)] for p,q in sorted(values.items(),reverse=side=='bids')[:100]] for side,values in levels.items()}
        authority=self.r.market.authority(symbol);assert authority is not None
        evidence=SupplementalEvidence(provider_id=PROVIDER,kind='BROKER_DEPTH',scope_id=authority['scope_id'],source_epoch=authority['source_epoch'],symbol=symbol,origin='LIVE_OBSERVED',
            source_ref='ProtoOADepthEvent observed subscription / '+self.session,venue='CTRADER_BROKER_OBSERVED_DEPTH_NOT_GLOBAL_BOOK',instrument=symbol,price_domain='SPOT_PAIR',unit='DISPLAYED_BASE_UNITS',
            window_start=received,window_end=(at+timedelta(microseconds=1)).isoformat(),available_at=published_at,valid_until=(at+timedelta(seconds=15)).isoformat(),complete=True,
            records=(dict(id=digest([self.session,symbol,received,levels]),time=received,available_at=received,**levels),),
            parameters=dict(clock_basis='LOCAL_RECEIPT_NOT_VENDOR_EVENT_TIME',native_sequence=False,full_book_complete=False,unknown_deleted_ids=self.unknown[symbol],subscription_acknowledged=True))
        validate_wire_shape(evidence)
        if PROVIDER not in self.store.providers:self.store.register_provider(PROVIDER,kinds=['BROKER_DEPTH'],origin='LIVE_OBSERVED')
        # Current membership contains one envelope per pair; corruption/one-sided
        # updates cannot leave a former good snapshot authoritative.
        if PROVIDER not in self.store.admissions:self.store.admissions[PROVIDER]=set()
        previous=self.r.database.supplemental_candidates(scope=authority['scope_id'],epoch=authority['source_epoch'],symbol=symbol,origin='LIVE_OBSERVED',providers={PROVIDER:self.store.providers[PROVIDER]},cutoff=received)
        for row in previous:self.store.admissions[PROVIDER].discard(digest(row))
        self.store.accept(evidence)
        from sfm_fx_new_age.contracts.domain import record
        self.store.admissions[PROVIDER].add(digest(record(evidence)))
        self.states[symbol]='OBSERVED_BROKER_DEPTH';self.published[symbol]=monotonic();self.publications+=1

    def status(self):
        states=dict(self.states)
        for symbol,at in self.received.items():
            if states.get(symbol)=='OBSERVED_BROKER_DEPTH' and (instant(self.r.clock())-instant(at)).total_seconds()>15:states[symbol]='STALE_RECEIPT'
        return dict(pairs=states,subscription_acknowledged=self.ack,acknowledged_pairs=sorted(self.acknowledged),events=self.events,publications=self.publications,native_sequence=False,full_book_complete=False,receipt_freshness_seconds=15,local_audit_events=len(self.audit))
