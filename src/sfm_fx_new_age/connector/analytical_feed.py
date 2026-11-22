"""Runtime-owned producers for data the connected program actually supports.

Construction is inert. Only an authenticated explicitly started native feed can
schedule reads. The core thread owns admission; the single bounded HTTP worker
owns only official GETs and is joined at shutdown. No prices are invented and
there is no execution tape or strict book capability hidden behind these inputs.
"""
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from uuid import uuid4
import json
from sfm_fx_new_age.contracts.domain import PAIRS, instant
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import record
from .official_context import acquire_official_context
from .lanes import eligible_lanes,lane_matches,prune_admissions

TPO='CTRADER_CONNECTED_BID_TPO_V1'
COT='CONNECTED_CFTC_CONTEXT_V1'
CALENDAR='CONNECTED_FED_CONTEXT_V1'
OWNED={TPO:'INTRABAR_PRICES',COT:'CFTC_REPORT',CALENDAR:'OFFICIAL_CALENDAR'}


class ConnectedAnalyticalFeed:
    def __init__(self,connector,*,excluded_kinds=()):
        self.connector=connector;self.r=connector.r;self.store=self.r.analytics.supplemental
        self.excluded=frozenset(excluded_kinds);self.binding=None;self.jobs={};self.attempted={};self.tpo={}
        self.context_state='WAITING_CONNECTION';self.context_error=None;self.next_context=0
        self.worker:Thread|None=None;self.results=Queue(maxsize=1);self.closed=False;self.context_acquisitions=0
        self.last_context_directory=None;self.admitted={k:0 for k in OWNED}
        from .broker_depth import ConnectedBrokerDepth
        self.depth=ConnectedBrokerDepth(connector,excluded='BROKER_DEPTH' in self.excluded)
        from .kraken_public import ConnectedKrakenFeed
        self.venue=ConnectedKrakenFeed(connector,excluded_kinds=self.excluded)
        from .bitstamp_feed import ConnectedBitstampBook
        self.native_book=ConnectedBitstampBook(connector,excluded=bool({'VENUE_BOOK','VENUE_NATIVE_CHAIN_BOOK'} & self.excluded))
        from .fxopen_feed import ConnectedFXOpenReported
        self.reported_fx=ConnectedFXOpenReported(connector,excluded_kinds=self.excluded)

    def _withdraw(self):
        changed=False
        for provider in OWNED:
            self.store.admissions.pop(provider,None)
            changed=self.store.providers.pop(provider,None) is not None or changed
            self.admitted[provider]=0
        if changed:
            for symbol in PAIRS:self.r.emit('ANALYTICS.INPUT','CT_OPEN_API_CONNECTOR',dict(symbol=symbol,scope_id=self.r.market.scope_id,source_epoch='CONNECTED_INPUT_WITHDRAWN',kind='CONNECTED_SOURCE_STATUS'),Priority.P2,self.r.market.scope_id)

    def disconnect(self):
        self.depth.disconnect()
        self.venue.disconnect()
        self.native_book.disconnect()
        self.reported_fx.disconnect()
        for identity in self.jobs.values():
            self.connector.quote_history.fail({'context':{'native_quote_history':identity}},'Analytical binding withdrawn')
        self._withdraw();self.binding=None;self.jobs.clear();self.attempted.clear();self.tpo.clear()
        self.context_state='WAITING_CONNECTION';self.next_context=0

    def _identity(self):
        account=self.r.accounts.current
        if not account or not account.authenticated or account.origin.value!='LIVE_OBSERVED':return None
        state=self.connector.native.get((account.endpoint_class,account.account_id),{})
        if not state.get('connected') or account.scope_id not in self.connector.feed_intents:return None
        eligible,_=eligible_lanes(self.connector)
        if not eligible:return None
        return account.scope_id,tuple(eligible.items()),tuple((s,self.r.market.spec(account.account_id,s).broker_symbol_id) for s in eligible)

    def _rebind_lanes(self,identity):
        """Keep healthy TPO/context work when only another lane changes."""
        if not self.binding or not identity or self.binding[0]!=identity[0] or {e for _,e in self.binding[1]}!={e for _,e in identity[1]}:
            self.disconnect();self.binding=identity;return
        old=dict(self.binding[1]);new=dict(identity[1])
        old_ids=dict(self.binding[2]);new_ids=dict(identity[2])
        changed={s for s in old if old.get(s)!=new.get(s) or old_ids.get(s)!=new_ids.get(s)}
        for symbol in changed:
            job=self.jobs.pop(symbol,None)
            if job:self.connector.quote_history.fail({'context':{'native_quote_history':job}},'Pair metadata withdrawn')
            self.attempted.pop(symbol,None);self.tpo.pop(symbol,None)
            for provider in OWNED:
                members=self.store.admissions.get(provider,set())
                for row in self.r.database.supplemental_candidates(scope=self.binding[0],epoch=old[symbol],symbol=symbol,origin='LIVE_OBSERVED',providers=self.store.providers,cutoff=self.r.clock()):
                    if row['provider_id']==provider:
                        from sfm_fx_new_age.contracts.analytics import digest
                        members.discard(digest(row))
            self.r.emit('ANALYTICS.INPUT','CT_OPEN_API_CONNECTOR',dict(symbol=symbol,source_epoch='PAIR_METADATA_WITHDRAWN'),Priority.P2,identity[0])
        self.binding=identity;self.next_context=0

    def _admit(self,provider,evidences):
        if self.binding is None or OWNED[provider] in self.excluded:return
        values=tuple(e for e in evidences if lane_matches(self.r,self.binding,e.symbol) and e.scope_id==self.binding[0] and e.source_epoch==dict(self.binding[1])[e.symbol])
        if not values:return
        added=False
        if provider not in self.store.providers:
            self.store.register_provider(provider,kinds=[OWNED[provider]],origin='LIVE_OBSERVED');added=True
        try:self.store.accept_many(values)
        except Exception:
            if added:self.store.providers.pop(provider,None)
            raise
        self.store.admissions.setdefault(provider,set()).update(digest(record(e)) for e in values)
        prune_admissions(self.r,self.store,provider,self.binding)
        self.admitted[provider]+=len(values)

    def _tpo_poll(self):
        if self.binding is None or 'INTRABAR_PRICES' in self.excluded:return
        for symbol,identity in tuple(self.jobs.items()):
            job=self.r.database.get('native_quote_history_job',identity)
            if job is None or job['state']=='RUNNING':continue
            self.jobs.pop(symbol)
            if job['state']!='COMPLETE':self.tpo[symbol]=job['state'];continue
            try:
                evidence=self.connector.quote_history.tpo_evidence(identity,provider_id=TPO,available_at=self.r.clock())
                self._admit(TPO,[evidence]);self.tpo[symbol]='ADMITTED'
            except (ValueError,KeyError,TypeError,ArithmeticError):self.tpo[symbol]='NO_COMPLETE_OBSERVED_INTERVAL'
        # Request each closed interval once per connection; failures stay explicit.
        # Candle history is not TPO evidence. Defer only a pair's actual
        # bootstrap work for read backpressure, never wait for global success.
        pending=set(self.connector.feed_status()['pending_history_symbols'])
        end=instant(self.r.clock()).replace(minute=0,second=0,microsecond=0)
        end_text=end.isoformat().replace('+00:00','Z');start=(end-timedelta(hours=1)).isoformat().replace('+00:00','Z')
        for symbol in dict(self.binding[1]):
            if symbol in pending or symbol in self.jobs or self.attempted.get(symbol)==end_text:continue
            # Keep in-flight read backpressure and native quote-job budgets bounded.
            if len(self.connector.requests)>=100:return
            self.attempted[symbol]=end_text
            try:self.jobs[symbol]=self.connector.quote_history.start(symbol,start,end_text);self.tpo[symbol]='LOADING'
            except (ValueError,KeyError):self.tpo[symbol]='REQUEST_REFUSED'

    def _start_context(self):
        if {'CFTC_REPORT','OFFICIAL_CALENDAR'}<=self.excluded:
            self.context_state='EXTERNAL_CONFIGURATION';return
        if self.worker is not None or monotonic()<self.next_context:return
        # Persistent runtime required. Never turn an in-memory test into networking.
        if self.r.database.path==':memory:':self.context_state='NO_PERSISTENT_STATE';return
        binding=self.binding
        if binding is None:return
        authorities={s:self.r.market.authority(s) for s in dict(binding[1])}
        if any(value is None for value in authorities.values()):return
        source=dict(scope_id=binding[0],authorities={s:dict(value) for s,value in authorities.items() if value is not None})
        directory=Path(self.r.database.path).parent/'native-context'/str(uuid4())
        directory.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.context_state='FETCHING_OFFICIAL_HTTPS';self.context_error=None
        def acquire():
            try:
                receipt=acquire_official_context(source,directory)
                self.results.put((binding,directory,receipt,None))
            except Exception as exc:self.results.put((binding,directory,None,type(exc).__name__))
        self.worker=Thread(target=acquire,name='SFM-official-context',daemon=False);self.worker.start()

    def _finish_context(self):
        if self.worker is None or self.worker.is_alive():return
        self.worker.join();self.worker=None
        try:binding,directory,receipt,error=self.results.get_nowait()
        except Empty:return
        if not binding or not self.binding or binding[0]!=self.binding[0] or {e for _,e in binding[1]}!={e for _,e in self.binding[1]}:return
        if error:
            self.context_state='OFFICIAL_SOURCE_UNAVAILABLE';self.context_error=error;self.next_context=monotonic()+900;return
        try:
            config=json.loads(Path(receipt['configuration']).read_bytes())
            batches={COT:[],CALENDAR:[]}
            for provider in config['providers']:
                manifest=Path(provider['manifest_path'])
                for entry in json.loads(manifest.read_bytes())['entries']:
                    import hashlib
                    raw=(manifest.parent/entry['file']).read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Official publication hash changed')
                    body=json.loads(raw);body['records']=tuple(body['records'])
                    evidence=SupplementalEvidence(**body);validate_wire_shape(evidence)
                    owner=COT if evidence.kind=='CFTC_REPORT' else CALENDAR
                    batches[owner].append(replace(evidence,provider_id=owner))
            # Store validates complete scope/epoch and all wire values on owner thread.
            for owner,values in batches.items():self._admit(owner,values)
            self.context_state='ADMITTED';self.context_acquisitions+=1;self.last_context_directory=str(directory);self.next_context=monotonic()+6*3600
        except (OSError,ValueError,KeyError,TypeError,ArithmeticError):
            self.context_state='OFFICIAL_ADMISSION_REFUSED';self.context_error='VALIDATION_FAILURE';self.next_context=monotonic()+900

    def poll(self):
        if self.closed:return
        identity=self._identity()
        if identity!=self.binding:
            self._rebind_lanes(identity)
        self._finish_context()
        # An acknowledged broker-depth subscription has its own evidence and
        # lifecycle. Candle-history success is not a depth prerequisite.
        self.depth.poll(identity)
        self.venue.poll(identity)
        self.native_book.poll(identity)
        self.reported_fx.poll(identity)
        if identity is None:return
        self._tpo_poll();self._start_context()

    def status(self):
        venue=self.venue.status();admitted=venue['admitted_pairs']
        return dict(enabled=True,owner='CT_OPEN_API_CONNECTOR',state='CONNECTED' if self.binding else 'WAITING_CONNECTION',
            eligible_pairs=list(dict(self.binding[1])) if self.binding else [],metadata_by_pair=eligible_lanes(self.connector)[1],required_pairs=list(PAIRS),
            tpo=dict(self.tpo),official_context=self.context_state,official_error_type=self.context_error,
            admitted_envelopes=dict(self.admitted),official_acquisitions=self.context_acquisitions,
            official_worker_alive=bool(self.worker and self.worker.is_alive()),
            broker_depth=self.depth.status(),activity_alternatives=self.r.analytics.activity_alternatives,
            public_venue=venue,public_native_book=self.native_book.status(),public_reported_fx=self.reported_fx.status(),
            excluded_external_kinds=sorted(self.excluded),executed_quantity_feed=bool(admitted['TRADED_PRINTS'] or admitted['EXECUTED_BAR_QUANTITIES'] or self.reported_fx.status()['qualified_pairs']),aggressor_feed=bool(admitted['AGGRESSOR_PRINTS']),strict_full_book_feed=bool(self.native_book.status()['fresh_pairs']),
            capability_note='Native tick volume is quote count; Open API depth is displayed liquidity, not an execution tape or natively sequenced full book.')

    def close(self):
        self.closed=True;self.disconnect()
        self.venue.close()
        self.native_book.close()
        self.reported_fx.close()
        if self.worker is not None:
            self.worker.join(timeout=50)
            if self.worker.is_alive():raise RuntimeError('Official context worker did not stop')
            self.worker=None
        while True:
            try:self.results.get_nowait()
            except Empty:break
