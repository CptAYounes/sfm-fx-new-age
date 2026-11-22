"""Core-side cTrader session supervisor. No sockets or SDK reactor run on the UI thread."""
from __future__ import annotations
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from time import time,monotonic
from uuid import uuid4
import json
import math
from typing import Callable,TYPE_CHECKING
from queue import Full

from sfm_fx_new_age.contracts.domain import AccountContext,Origin,Quote,Bar,BrokerOutcome,OrderState,PAIRS,record,instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.services.continuity import SessionCalendar
from .protocol import symbol_spec,trendbar,timestamp,milliseconds,new_limit_request,execution_state
from .sdk_worker import SdkProcess,READ_REQUESTS,redact
from .oauth import OAuthConfig,OAuthSession,SecretStore
from .symbols import resolve_symbols
from .lanes import eligible_lanes
if TYPE_CHECKING:
    from .analytical_feed import ConnectedAnalyticalFeed


class ConnectorService:
    is_fixture=False
    def __init__(self,runtime,*,worker_factory:Callable[[dict],SdkProcess]=SdkProcess):
        self.r=runtime;self.worker_factory=worker_factory;self.workers={};self.native={};self.requests={}
        self._pending_native={}
        self.state='DISCONNECTED';self.reason='Human configuration and authentication required'
        self.oauth=None;self.oauth_url=None;self.auth_worker=None
        self.permission='SCOPE_VIEW';self.backfill_requests={};self.sequence=0
        self.errors=[];self.closing=False;self.endpoint_failures={}
        self.analytical_feed:ConnectedAnalyticalFeed|None=None
        from .history import NativeHistory
        self.history=NativeHistory(runtime.database,self.request,lambda:runtime.clock())
        self.history.disconnect()
        from .quote_history import NativeQuoteHistory
        self.quote_history=NativeQuoteHistory(self)
        self.quote_history.interrupt()
        self.feed_intents={}
        self.preferences=self.r.database.get('setting','connector_remember') or {'enabled':False,'scope_id':None}
        self.remember_preference_set=bool(self.r.database.get('setting','connector_remember'))
        self._startup_attempted=False;self._resume_scope=None;self._oauth_consumed=False;self._generation=0
        self.session_available=False;self._auto_select_single=False;self._account_lists_seen=set()
        public=self.r.database.get('setting','connector_public_profile')
        if public:
            try:self.oauth=OAuthSession(OAuthConfig(public['client_id'],public['redirect_uri'],public['scope']),SecretStore(Path(public['credential_path'])))
            except (ValueError,KeyError):self.reason='Saved connection settings need review'
            else:
                self.state='CONFIGURED';self.reason='Application configured; sign in with cTrader'
                try:
                    saved=self.oauth.store.load();self.session_available=bool(saved.get('refresh_token'))
                except (OSError,ValueError):pass

    def status(self):
        import importlib.util
        return {'state':self.state,'reason':self.reason,'sdk_installed':importlib.util.find_spec('ctrader_open_api') is not None,
            'endpoints':sorted(self.workers),'authenticated_scopes':sorted(self.r.accounts.sessions),
            'ready_scopes':[v['context'].scope_id for v in self.native.values() if v.get('context') and self.ready_for_issue(v['context'].scope_id)],
            'pending_requests':len(self.requests),'oauth_state':self.oauth.last_status if self.oauth else 'NOT_STARTED',
            'oauth_url':self.oauth_url,'network_started':bool(self.workers),'errors':list(self.errors),
            'configuration':{'client_id':self.oauth.config.client_id,'redirect_uri':self.oauth.config.redirect_uri,
                'credential_path':str(self.oauth.store.path),'scope':self.oauth.config.scope} if self.oauth else None,
            'feed':self.feed_status(),'saved_session':self.session_available,
            'analytical_compute':self.r.analytics.projections.compute_status(),
            'analytical_feed':self.analytical_feed.status() if self.analytical_feed else {'enabled':False,'state':'NOT_ENABLED_IN_THIS_RUNTIME'},
            'endpoint_health':{route:{'state':'AUTHENTICATED' if any(v.get('connected') for (ep,_),v in self.native.items() if ep==route) else 'UNAVAILABLE' if route in self.endpoint_failures else 'CONNECTING' if route in self.workers else 'NOT_STARTED',
                'reason':self.endpoint_failures.get(route,'')} for route in ('DEMO','LIVE')},
            'auto_login':self.preferences['enabled'],'remembered_scope':self.preferences.get('scope_id'),
            'remember_preference_set':self.remember_preference_set}

    def remember(self,enabled):
        if type(enabled) is not bool:raise ValueError('Explicit remember preference required')
        self.remember_preference_set=True
        self.preferences=dict(self.preferences,enabled=enabled)
        self.r.database.put('setting','connector_remember',self.preferences)
        if not enabled:self._resume_scope=None

    def resume_saved_session(self):
        """GUI entrypoint only: no network from headless checks or construction."""
        if self._startup_attempted:return
        self._startup_attempted=True
        if self.r.fixture_mode or not self.preferences['enabled'] or not self.oauth or not self.session_available:return
        self._resume_scope=self.preferences.get('scope_id')
        self.connect()

    def sign_out(self):
        self.remember(False);self.disconnect()
        if self.oauth:
            saved=self.oauth.store.load()
            for key in ('access_token','refresh_token','expires_at'):saved.pop(key,None)
            self.oauth.store.save(saved)
        self.session_available=False;self.state='SIGNED_OUT';self.reason='Saved login removed; application setup retained'

    def start_market_feed(self):
        account=self.r.accounts.current
        if not account or not account.authenticated or account.origin!=Origin.LIVE_OBSERVED:raise ValueError('Select an authenticated cTrader account first')
        state=self.native.get((account.endpoint_class,account.account_id),{})
        if not state.get('connected'):raise ValueError('Selected account session is disconnected')
        self.feed_intents.setdefault(account.scope_id,{'end':self.r.clock(),'epoch':state['epoch'],'jobs':{},'missing':[]})
        state.setdefault('symbol_pins',{}).update({s:sid for sid,s in state['symbols'].items() if s not in state.get('symbol_pins',{})})
        self.activate_selected()
        self._seed_feed()
        self.preferences=dict(self.preferences,scope_id=account.scope_id)
        self.r.database.put('setting','connector_remember',self.preferences)

    def _seed_feed(self):
        account=self.r.accounts.current
        if not account or account.scope_id not in self.feed_intents:return
        intent=self.feed_intents[account.scope_id];state=self.native.get((account.endpoint_class,account.account_id),{})
        if not state.get('connected') or state.get('epoch')!=intent['epoch']:return
        missing=[]
        eligible,_=eligible_lanes(self)
        # Engineering history windows, not analytical thresholds or inferred candles.
        for symbol in PAIRS:
            spec=self.r.market.spec(account.account_id,symbol)
            authority=self.r.market.authority(symbol);calendar=self.r.continuity.calendar(symbol)
            # Persisted specifications/calendars may belong to the prior connection.
            # Account auth alone is not current-epoch native symbol metadata.
            if (symbol not in eligible or not spec or spec.broker_symbol_id not in state['specs']
                or state['symbols'].get(spec.broker_symbol_id)!=symbol
                or not authority or authority['source_epoch']!=intent['epoch']
                or not calendar or calendar.source_ref!='ProtoOASymbol.schedule / '+intent['epoch']):
                missing.append(symbol);continue
            for frame,days in (('W1',730),('D1',180),('H4',60),('H1',14)):
                key=symbol+':'+frame
                if key in intent['jobs']:continue
                start=(instant(intent['end'])-timedelta(days=days)).isoformat().replace('+00:00','Z')
                job=self.r.continuity.request_backfill(symbol,frame,start,intent['end'])
                if job['status']!='COMPLETE':
                    try:self.start_backfill(job)
                    except Full:return
                intent['jobs'][key]=job['id']
        intent['missing']=missing
        self._subscribe_closed_bars(account,state,intent)

    def _subscribe_closed_bars(self,account,state,intent):
        """Spots acknowledgement and bounded bootstrap precede live native bars."""
        if not state.get('spots_active'):return
        subscriptions=state.setdefault('live_bars',{})
        eligible,_=eligible_lanes(self)
        for symbol in eligible:
            for frame in ('W1','D1','H4','H1'):
                job=self.r.database.get('backfill',intent['jobs'].get(symbol+':'+frame,''))
                if not job or job['status']!='COMPLETE':continue
                spec=self.r.market.spec(account.account_id,symbol)
                if not spec:continue
                key=(spec.broker_symbol_id,frame)
                if key in subscriptions:continue # FAILED is explicit; never retry silently.
                try:
                    self.request(account.endpoint_class,'ProtoOASubscribeLiveTrendbarReq',
                        {'ctidTraderAccountId':account.account_id,'symbolId':key[0],'period':frame},
                        context={'live_bar':key,'epoch':state['epoch']})
                except Full:return
                subscriptions[key]='PENDING'

    def _live_bar_reply(self,endpoint,request,status):
        context=(request or {}).get('context') or {};key=context.get('live_bar')
        if not key:return
        aid=str(request['payload']['ctidTraderAccountId']);state=self.native.get((endpoint,aid),{})
        if state.get('epoch')==context.get('epoch'):state.setdefault('live_bars',{})[tuple(key)]=status

    def feed_status(self):
        account=self.r.accounts.current
        intent=self.feed_intents.get(account.scope_id) if account else None
        frames=('W1','D1','H4','H1');required=len(PAIRS)*len(frames)
        if not intent:return {'state':'NOT_STARTED','history_jobs':0,'completed_history_jobs':0,'missing_metadata':[],'failed_history_jobs':0,'received_bars':0,
                              'pending_history_jobs':0,'pending_history_symbols':[],'history_by_pair':{},
                              'required_pairs':list(PAIRS),'required_history_jobs':required,'eligible_pairs':[],
                              'eligible_history_jobs':0,'unavailable_history_jobs':required,'metadata_by_pair':{}}
        eligible,metadata=eligible_lanes(self)
        calendars={s:self.r.continuity.calendar(s) for s in PAIRS}
        for symbol in tuple(eligible):
            cal=calendars[symbol]
            if not cal or cal.source_ref!='ProtoOASymbol.schedule / '+intent['epoch']:
                eligible.pop(symbol);metadata[symbol]='WAITING_CURRENT_CALENDAR'
        missing=[s for s in PAIRS if s not in eligible]
        by_pair={s:{f:'NOT_SCHEDULED' if s in eligible else 'UNAVAILABLE_CURRENT_METADATA' for f in frames} for s in PAIRS}
        pending=[];completed=failed=bars=0
        jobs=[self.r.database.get('backfill',identity) for identity in intent['jobs'].values()]
        for key,job in zip(intent['jobs'],jobs):
            symbol,frame=key.split(':')
            if symbol not in eligible:continue
            status=job['status'] if job and job.get('source_epoch')==intent['epoch'] else 'MISSING_JOB_RECORD'
            by_pair[symbol][frame]=status
            completed+=status=='COMPLETE';failed+=status in {'FAILED','MISSING_JOB_RECORD'}
            bars+=job.get('received_bars',0) if job else 0
            if status in {'QUEUED','PARTIAL','RUNNING'}:pending.append(symbol)
        known=len(eligible)==len(PAIRS)
        market_open=any(calendars[s].is_open(self.r.clock()) for s in eligible) if known else None
        next_opens=[calendars[s].next_open(self.r.clock()) for s in eligible] if known and market_open is False else []
        state='HISTORY_INCOMPLETE' if failed else 'PARTIAL_COVERAGE' if missing and eligible else 'WAITING_METADATA' if missing else ('HISTORY_FETCHED' if bars else 'HISTORY_EMPTY') if completed==required else 'LOADING_HISTORY'
        return {'state':state,'history_jobs':len(jobs),'completed_history_jobs':completed,'missing_metadata':missing,
                'required_pairs':list(PAIRS),'required_history_jobs':required,'eligible_pairs':list(eligible),
                'eligible_history_jobs':len(eligible)*len(frames),'unavailable_history_jobs':len(missing)*len(frames),'metadata_by_pair':metadata,
                'pending_history_jobs':len(pending),'pending_history_symbols':sorted(set(pending)),'history_by_pair':by_pair,
                'source_epoch':intent['epoch'],'failed_history_jobs':failed,'received_bars':bars,
                'market_open':market_open,'next_scheduled_open':min((v for v in next_opens if v),default=None),
                'live_bar_subscriptions':{status:list(self.native.get((account.endpoint_class,account.account_id),{}).get('live_bars',{}).values()).count(status) for status in ('PENDING','ACTIVE','FAILED')},
                'native_live_bars_received':self.native.get((account.endpoint_class,account.account_id),{}).get('live_bar_received',0)}

    def _fail_backfill(self,request,reason):
        identity=(request or {}).get('context',{}).get('job_id') if (request or {}).get('context') else None
        job=self.r.database.get('backfill',identity) if identity else None
        if job and job['status']!='COMPLETE':
            job.update(status='FAILED',detail=reason);self.r.database.put('backfill',identity,job)

    def configure(self,config:OAuthConfig,secret_store:SecretStore):
        if self.auth_worker and self.auth_worker.is_alive():raise ValueError('Authentication is still in progress')
        if self.workers:raise ValueError('Disconnect before changing connector configuration')
        if self.oauth:self.oauth.close()
        self.oauth=OAuthSession(config,secret_store)
        self._generation+=1;self._resume_scope=None;self.session_available=False
        self.r.database.put('setting','connector_public_profile',{'client_id':config.client_id,'redirect_uri':config.redirect_uri,
            'scope':config.scope,'credential_path':str(secret_store.path)})
        self.state='CONFIGURED';self.reason='Human login or saved token required'

    def import_profile(self,path):
        if self.r.database.path==':memory:':raise ValueError('Persistent application state is required')
        if self.workers or (self.auth_worker and self.auth_worker.is_alive()):raise ValueError('Disconnect before changing application setup')
        try:
            body=SecretStore(path).load()
            config=OAuthConfig(body['client_id'],body['redirect_uri'],body.get('scope','trading'))
            if not isinstance(body.get('client_secret'),str) or not body['client_secret']:raise ValueError('Missing application credential')
        except (OSError,ValueError,KeyError,TypeError):
            raise ValueError('Choose a private application JSON with client_id, client_secret and registered loopback redirect_uri (file 0600, folder 0700).') from None
        store=SecretStore(Path(self.r.database.path).parent/'private'/'connector-secrets.json')
        store.save({'client_secret':body['client_secret']});self.configure(config,store)

    def import_session(self,path):
        """Explicit human token handoff, distinct from app-only/foreign-token rejecting import."""
        if self.r.fixture_mode or self.r.database.path==':memory:':raise ValueError('Persistent nonfixture application state required')
        if self.workers or (self.auth_worker and self.auth_worker.is_alive()):raise ValueError('Disconnect before linking a different application session')
        try:
            body=SecretStore(path).load()
            config=OAuthConfig(body['client_id'],body['redirect_uri'],body.get('scope','accounts'))
            for key in ('client_secret','refresh_token'):
                if not isinstance(body.get(key),str) or not body[key] or len(body[key])>8192 or any(c.isspace() for c in body[key]):raise ValueError('Invalid application/session field')
        except (OSError,ValueError,KeyError,TypeError):
            raise ValueError('Private application connection requires client_id, client_secret, refresh_token and registered redirect_uri; file 0600 and folder 0700.') from None
        store=SecretStore(Path(self.r.database.path).parent/'private'/'connector-secrets.json')
        # Expiry is NOT guessed from a portal refresh; authoritative renewal supplies it.
        store.save({'client_secret':body['client_secret'],'refresh_token':body['refresh_token'],'expires_at':0})
        self.configure(config,store);self.session_available=True;self._auto_select_single=True
        self.remember(True);self.connect()

    def begin_oauth(self):
        if not self.oauth:raise ValueError('Configure registered OAuth client and private application credential first')
        if self.auth_worker and self.auth_worker.is_alive():raise ValueError('Previous authentication is finishing; try sign-in again shortly')
        self.oauth_url=self.oauth.begin();self.state='WAITING_FOR_HUMAN'
        self._oauth_consumed=False
        self._auto_select_single=True
        return self.oauth_url

    def connect(self):
        if not self.oauth:raise ValueError('OAuth application is not configured')
        if self.auth_worker and self.auth_worker.is_alive():raise ValueError('Token refresh already in progress')
        # Token HTTP work occurs outside the owning core/UI thread.
        from threading import Thread
        oauth=self.oauth
        oauth.closed=False
        generation=self._generation
        if oauth.last_status=='TOKEN_STORED':self._oauth_consumed=True
        def prepare():
            try:
                saved=oauth.store.load()
                if not saved.get('refresh_token'):raise ValueError('Human OAuth login required')
                if not saved.get('access_token') or float(saved.get('expires_at',0))<=time()+60:
                    oauth.refresh();saved=oauth.store.load()
                if not self.closing:self.r.post(self._start_if_current,saved,generation)
            except Exception as exc:
                if not self.closing:self.r.post(self._failure_if_current,type(exc).__name__,generation)
        self.auth_worker=Thread(target=prepare,daemon=True);self.auth_worker.start()
        self.state='AUTHENTICATING';self.reason='Preparing authenticated SDK sessions'

    def _failure(self,error_type):self.state='AUTHENTICATION_FAILED';self.reason=error_type

    def _failure_if_current(self,error_type,generation):
        if generation==self._generation and not self.closing:
            code=self.oauth.last_error if self.oauth else None
            self.state='CONNECTION_FAILED' if code in {'CONNECTION_FAILED','RATE_LIMITED'} else 'LOGIN_REQUIRED'
            self.reason='cTrader authorization renewal failed ('+(code or error_type)+'). '+('Retry connection explicitly after the connection/rate limit clears.' if self.state=='CONNECTION_FAILED' else 'Link the current application credentials and refreshed token.')
            if code=='MALFORMED_CLIENT_ID':
                self.reason='cTrader rejected the Client ID format. Copy Client ID from the registered application credentials, not the app name/page number or account login.'
                self.remember(False)

    def _start_if_current(self,saved,generation):
        if generation==self._generation and not self.closing:self._start(saved)

    def _start(self,saved):
        if self.closing:return
        assert self.oauth is not None
        self.disconnect(clear_oauth=False)
        self.endpoint_failures.clear()
        self._account_lists_seen.clear()
        for endpoint in ('LIVE','DEMO'):
            worker=self.worker_factory({'endpoint':endpoint,'client_id':self.oauth.config.client_id,
                'client_secret':saved['client_secret'],'access_token':saved['access_token']})
            worker.start();self.workers[endpoint]=worker
        self.state='CONNECTING';self.reason='Endpoint routing only; account class is never eligibility policy'
        self.r.orders.transport=self
        self.token_expires_at=float(saved['expires_at'])
        self.session_available=True

    def request(self,endpoint,name,payload,*,context=None):
        if name not in READ_REQUESTS:raise ValueError('Read operation not allowlisted')
        if len(self.requests)>=128:raise Full('Connector in-flight request budget exhausted')
        identity=str(uuid4())
        queued_at=monotonic()
        self.workers[endpoint].send({'kind':'READ','name':name,'payload':payload,'request_id':identity})
        self.requests[identity]={'name':name,'payload':payload,'context':context,'sent':queued_at,'endpoint':endpoint,
            'awaiting_sdk_admission':bool(getattr(self.workers[endpoint],'reports_sdk_admission',False))}
        return identity

    def poll(self):
        if self.oauth and self.state=='WAITING_FOR_HUMAN':
            if self.oauth.last_status=='TOKEN_EXCHANGE_FAILED' or monotonic()>self.oauth.expires:
                self.oauth.close();self.state='LOGIN_REQUIRED';self.reason='Browser sign-in expired or failed. Sign in again.'
        if self.oauth and self.oauth.last_status=='TOKEN_STORED' and not self._oauth_consumed:
            self._oauth_consumed=True;self.connect()
        for endpoint,worker in tuple(self.workers.items()):
            from collections import deque
            pending=self._pending_native.setdefault(endpoint,deque())
            if not pending:pending.extend(worker.poll())
            deadline=monotonic()+0.025;processed=0
            while pending and (processed==0 or monotonic()<deadline):
                message=pending.popleft();processed+=1
                try:
                    with self.r.database.batch_writes():self.handle(endpoint,message)
                except Exception as exc:
                    self.errors=(self.errors+[{'endpoint':endpoint,'message_type':message.get('name',message.get('kind')),'error_type':type(exc).__name__}])[-100:]
                    self._disconnected(endpoint,'Native frame/continuity failure: '+type(exc).__name__)
            if hasattr(worker,'process') and not worker.process.is_alive():self._disconnected(endpoint,'SDK process stopped')
        if self._resume_scope and self._resume_scope in self.r.accounts.sessions:
            scope=self._resume_scope;self._resume_scope=None
            self.r.accounts.select_known(scope);self.start_market_feed()
        elif self._auto_select_single and self.workers and self._account_lists_seen==set(self.workers):
            if all(state.get('context') and state.get('connected') for state in self.native.values()):
                self._auto_select_single=False
                if len(self.r.accounts.sessions)==1:
                    self.r.accounts.select_known(next(iter(self.r.accounts.sessions)));self.start_market_feed()
        self._seed_feed()
        if self.analytical_feed:self.analytical_feed.poll()
        current=self.r.accounts.current
        if current and current.endpoint_class in self.workers:
            state=self.native.get((current.endpoint_class,current.account_id),{})
            if state.get('context') and monotonic()-state.get('last_money_request',state.get('trader_received_monotonic',monotonic()))>20:
                try:
                    self.request(current.endpoint_class,'ProtoOATraderReq',{'ctidTraderAccountId':current.account_id})
                    state['last_money_request']=monotonic()
                except (Full,OSError):self.reason='Read-only monetary refresh backpressure; old balance remains stale'
            if state.get('context') and monotonic()-state.get('last_reconcile_request',0)>30:
                try:
                    self.request(current.endpoint_class,'ProtoOAReconcileReq',{'ctidTraderAccountId':current.account_id})
                    state['last_reconcile_request']=monotonic()
                except (Full,OSError):self.reason='Reconcile request backpressure; stale reconciliation cannot enable Issue'
        for identity,request in tuple(self.requests.items()):
            # SDK command queuing is not provider response time. Both waits are
            # bounded; this changes no market/evidence TTL or order deadline.
            queued=request.get('awaiting_sdk_admission',False)
            started=request['sent'] if queued else request.get('sdk_accepted_at',request['sent'])
            if monotonic()-started>(120 if queued else 30):
                self.requests.pop(identity,None)
                if self.analytical_feed:self.analytical_feed.depth.fail(request)
                self.quote_history.fail(request,'Native quote history request timeout; incomplete interval not admitted')
                self._live_bar_reply(request.get('endpoint'),request,'FAILED')
                self._fail_backfill(request,'Native history request timeout; explicit reconnect required')
                if request.get('context') and request['context'].get('history_job'):self.history.fail(request['context']['history_job'],'Native request timeout')
                if request.get('order_id'):self.r.orders._apply(request['order_id'],BrokerOutcome(OrderState.UNKNOWN,detail='Native request timeout; reconcile only'))
                self.reason='Request timeout; no blind retry'
        if self.workers and getattr(self,'token_expires_at',float('inf'))<=time()+60:
            self._resume_scope=self.r.accounts.current.scope_id if self.r.accounts.current else None
            self.disconnect(clear_oauth=False)
            self.connect() # refresh/re-authenticate read path; never replay write requests

    def handle(self,endpoint,message):
        if endpoint not in {'LIVE','DEMO'}:raise ValueError('Unknown source endpoint')
        kind=message.get('kind')
        if kind in {'DISCONNECTED','FATAL'}:
            self._disconnected(endpoint,message.get('error_type',kind));return
        if kind=='READ_SDK_ACCEPTED':
            request=self.requests.get(message.get('request_id',''))
            accepted=message.get('accepted_monotonic')
            if (request and request.get('endpoint')==endpoint and request.get('awaiting_sdk_admission')
                and type(accepted) in (int,float) and math.isfinite(accepted)
                and request['sent']<=accepted<=monotonic()):
                request.update(awaiting_sdk_admission=False,sdk_accepted_at=accepted)
            return
        if kind=='CONNECTED':self.state='APPLICATION_AUTH';return
        identity=message.get('request_id','');request=self.requests.pop(identity,None)
        if kind=='REQUEST_FAILED':
            if self.analytical_feed:self.analytical_feed.depth.fail(request)
            self.quote_history.fail(request,'Native quote history request failed')
            self._live_bar_reply(endpoint,request,'FAILED')
            self._fail_backfill(request,'Native history request failed')
            if request and request.get('context') and request['context'].get('history_job'):self.history.fail(request['context']['history_job'],'Native request failed')
            if request and request.get('order_id'):self.r.orders._apply(request['order_id'],BrokerOutcome(OrderState.UNKNOWN,detail='Native operation uncertain'))
            self.reason='Native request failed: '+message.get('error_type','Unknown')
            if request is None and not self.r.accounts.sessions and self.state in {'CONNECTING','APPLICATION_AUTH'}:self.state='APPLICATION_AUTH_FAILED'
            return
        if kind!='MESSAGE':return
        name=message['name'];body=redact(message['payload'])
        if name in {'ProtoOAErrorRes','ProtoErrorRes','ProtoOAOrderErrorEvent'}:
            if self.analytical_feed:self.analytical_feed.depth.fail(request)
            self.quote_history.fail(request,'Native quote history API error')
            # Application/auth errors often have no account id; handle before account lookup.
            raw=body.get('errorCode','UNKNOWN')
            code=str(raw) if isinstance(raw,(str,int)) and len(str(raw))<=80 and all(c.isupper() or c.isdigit() or c=='_' for c in str(raw)) else 'UNKNOWN'
            self.reason='cTrader API error: '+code
            self._live_bar_reply(endpoint,request,'FAILED')
            self.errors=(self.errors+[{'endpoint':endpoint,'message_type':name,'error_code':code}])[-100:]
            self._fail_backfill(request,self.reason)
            if request and request.get('context') and request['context'].get('history_job'):self.history.fail(request['context']['history_job'],self.reason)
            if request and request.get('order_id'):self.r.orders._apply(request['order_id'],BrokerOutcome(OrderState.UNKNOWN,detail=self.reason))
            if code in {'CH_ACCESS_TOKEN_INVALID','OA_AUTH_TOKEN_EXPIRED','OA_AUTH_TOKEN_INVALID','ACCESS_DENIED'}:
                self._disconnected(endpoint,self.reason);self.state='LOGIN_REQUIRED'
            elif not self.r.accounts.sessions and not body.get('ctidTraderAccountId'):
                self.state='APPLICATION_AUTH_FAILED'
            return
        if name in {'ProtoOAAccountsTokenInvalidatedEvent','ProtoOAClientDisconnectEvent'}:
            self.disconnect();self.state='LOGIN_REQUIRED';self.reason='cTrader ended the authorization. Sign in again; no orders are replayed.'
            return
        account_id=str(body.get('ctidTraderAccountId',(request or {}).get('payload',{}).get('ctidTraderAccountId','')))
        if name=='ProtoOAGetAccountListByAccessTokenRes':
            self._account_lists_seen.add(endpoint)
            self.permission=body.get('permissionScope','SCOPE_VIEW')
            for account in body.get('ctidTraderAccount',[]):
                route='LIVE' if account.get('isLive',False) else 'DEMO'
                if route!=endpoint:continue
                aid=str(account['ctidTraderAccountId']);key=(endpoint,aid)
                self.native[key]={'epoch':str(uuid4()),'metadata':account,'symbols':{},'specs':{},'quotes':{},'reconciled':False}
                self.workers[endpoint].send({'kind':'AUTH_ACCOUNT','account_id':aid,'request_id':str(uuid4())})
            return
        key=(endpoint,account_id)
        if key not in self.native:return
        state=self.native[key]
        if self.analytical_feed and name in {'ProtoOADepthEvent','ProtoOASubscribeDepthQuotesRes','ProtoOAUnsubscribeDepthQuotesRes'}:
            try:self.analytical_feed.depth.handle(endpoint,name,body,request)
            except (ValueError,KeyError,TypeError,ArithmeticError):
                self.analytical_feed.depth._withdraw()
                self.analytical_feed.depth.ack=False
                self.analytical_feed.depth.states={s:'INVALID_NATIVE_DEPTH' for s in PAIRS}
            return
        if name=='ProtoOAAccountAuthRes':
            for operation in ('ProtoOATraderReq','ProtoOAAssetListReq','ProtoOASymbolsListReq','ProtoOAReconcileReq'):
                self.request(endpoint,operation,{'ctidTraderAccountId':account_id})
        elif name=='ProtoOATraderRes':
            state['trader']=body['trader'];state['trader_observed_at']=self.r.clock();state['trader_received_monotonic']=monotonic();self._register(endpoint,account_id)
        elif name=='ProtoOAAssetListRes':
            state['assets']={str(a['assetId']):a['name'] for a in body.get('asset',[])}
            self._resolve_symbols(endpoint,account_id)
            self._register(endpoint,account_id)
        elif name=='ProtoOASymbolsListRes':
            state['symbols_ready']=True
            state['light_symbols']=body.get('symbol',[])
            self._resolve_symbols(endpoint,account_id)
            self.activate_selected()
        elif name=='ProtoOASymbolByIdRes':
            for spec in body.get('symbol',[]):
                sid=int(spec['symbolId'])
                if sid not in state['symbols']:continue
                symbol=state['symbols'][sid]
                try:symbol_spec(account_id,symbol,spec,scope_id=state.get('context').scope_id if state.get('context') else 'UNBOUND')
                except (ValueError,KeyError,TypeError,ArithmeticError):
                    state['specs'].pop(sid,None);state.setdefault('symbol_resolution',{})[symbol]='INVALID_NATIVE_SPECIFICATION'
                    if self.r.accounts.current==state.get('context'):self.r.market.withdraw_source(symbol,state['epoch'])
                    continue
                state['specs'][sid]=spec
            self.activate_selected()
        elif name=='ProtoOASubscribeSpotsRes':state['spots_active']=True
        elif name=='ProtoOASubscribeLiveTrendbarRes':self._live_bar_reply(endpoint,request,'ACTIVE')
        elif name=='ProtoOASpotEvent':self._spot(endpoint,account_id,body)
        elif name=='ProtoOAReconcileRes':
            state['reconcile']=body;state['reconciled']=True;state['reconciled_at']=monotonic()
            state['reconcile_version']=state.get('reconcile_version',0)+1
            self._apply_reconcile(endpoint,account_id)
        elif name in {'ProtoOAExecutionEvent','ProtoOAOrderDetailsRes','ProtoOAOrderListRes','ProtoOADealListRes'}:
            self._activity(endpoint,account_id,name,body)
            if request and request.get('context') and request['context'].get('history_job'):
                try:self.history.page(request['context'],body)
                except Exception:
                    self.history.fail(request['context']['history_job'],'Native history page rejected');raise
        elif name=='ProtoOAGetTrendbarsRes' and request and request.get('context'):
            self._backfill_page(endpoint,account_id,request['context'],body)
        elif name=='ProtoOAGetTickDataRes' and request and (request.get('context') or {}).get('native_quote_history'):
            try:self.quote_history.page(request,body)
            except (ValueError,KeyError,TypeError,ArithmeticError):
                self.quote_history.fail(request,'Original quote page validation failed')


    def _resolve_symbols(self,endpoint,account_id):
        state=self.native[(endpoint,account_id)]
        if 'light_symbols' not in state:return
        resolved=resolve_symbols(state['light_symbols'],state.get('assets',{}))
        for sid,symbol in tuple(resolved.symbols.items()):
            pin=state.get('symbol_pins',{}).get(symbol)
            if pin is not None and pin!=sid:
                resolved.symbols.pop(sid);resolved.native_names.pop(sid,None);resolved.assets.pop(sid,None)
                resolved.states[symbol]='NATIVE_ID_CHANGED_RECONNECT_REQUIRED'
        previous=dict(state['symbols'])
        state.update(symbols=resolved.symbols,native_symbol_names=resolved.native_names,
                     symbol_assets=resolved.assets,symbol_resolution=resolved.states)
        # A removed/ambiguous native instrument cannot retain current authority.
        account=self.r.accounts.current
        for sid,symbol in previous.items():
            if resolved.symbols.get(sid)==symbol:continue
            state['specs'].pop(sid,None);state.get('quotes',{}).pop(sid,None)
            if account and state.get('context')==account:
                self.r.market.withdraw_source(symbol,state['epoch'])
        requested=state.setdefault('spec_requested',set())
        requested.intersection_update(resolved.symbols)
        ids=[sid for sid in resolved.symbols if sid not in state['specs'] and sid not in requested]
        if ids:
            self.request(endpoint,'ProtoOASymbolByIdReq',{'ctidTraderAccountId':account_id,'symbolId':ids})
            requested.update(ids)

    def _register(self,endpoint,account_id):
        state=self.native[(endpoint,account_id)];trader=state.get('trader');assets=state.get('assets')
        if not trader or not assets:return
        currency=assets.get(str(trader.get('depositAssetId')))
        if not currency or not trader.get('brokerName'):self.reason='Account currency/broker identity unavailable';return
        context=AccountContext(account_id,endpoint,currency,True,
            self.permission=='SCOPE_TRADE' and trader.get('accessRights','FULL_ACCESS')=='FULL_ACCESS',
            Origin.LIVE_OBSERVED,'LIVE' if endpoint=='LIVE' else 'DEMO',trader['brokerName'])
        state['context']=context
        # An explicit observed exponent, never a guessed cents/FX convention.
        if 'moneyDigits' in trader and 'balance' in trader and state.get('trader_observed_at'):
            digits=int(trader['moneyDigits'])
            if 0<=digits<=18:
                self.r.database.put('account_money_snapshot',context.scope_id,{'scope_id':context.scope_id,
                    'account_currency':currency,'balance':str(Decimal(str(trader['balance']))/(Decimal(10)**digits)),
                    'money_digits':digits,'balance_version':trader.get('balanceVersion'),
                    'source_epoch':state['epoch'],'observed_at':state['trader_observed_at'],'origin':context.origin.value})
        state['connected']=True
        self.endpoint_failures.pop(endpoint,None)
        self.r.accounts.register(context)
        self.state='AUTHENTICATED';self.reason='Select an authenticated account; reconciliation precedes new Issue'
        self.activate_selected()

    def activate_selected(self):
        account=self.r.accounts.current
        if not account:return
        state=self.native.get((account.endpoint_class,account.account_id))
        if not state or not state.get('connected') or state.get('context')!=account:return
        ids=[]
        for sid,raw in state['specs'].items():
            symbol=state['symbols'].get(sid)
            if not symbol:continue
            if not self.r.market.authority(symbol) or self.r.market.authority(symbol)['source_epoch']!=state['epoch']:
                self.r.market.activate_source(symbol,state['epoch'],Origin.LIVE_OBSERVED.value)
            self.r.market.set_spec(symbol_spec(account.account_id,symbol,raw,scope_id=account.scope_id))
            if account.scope_id in self.feed_intents:state.setdefault('symbol_pins',{}).setdefault(symbol,sid)
            self.r.database.put('native_symbol_binding',account.scope_id+':'+symbol,
                dict(scope_id=account.scope_id,source_epoch=state['epoch'],symbol=symbol,
                     native_symbol_id=sid,native_symbol_name=state.get('native_symbol_names',{}).get(sid,symbol),
                     resolution=state.get('symbol_resolution',{}).get(symbol,'EXACT_NATIVE_NAME')))
            assets=state.get('symbol_assets',{}).get(sid);names=state.get('assets',{})
            if assets and all(v in names for v in assets):
                self.r.database.put('symbol_currency',account.scope_id+':'+symbol,{'scope_id':account.scope_id,'symbol':symbol,
                    'base_currency':names[assets[0]],'quote_currency':names[assets[1]],'source_epoch':state['epoch']})
            if raw.get('schedule') and raw.get('scheduleTimeZone'):
                windows=[]
                for window in raw['schedule']:
                    start,end=int(window['startSecond']),int(window['endSecond'])
                    if not (0<=start<=604800 and 0<=end<=604800) or start==end:raise ValueError('Invalid native weekly session interval')
                    if start<end:windows.append((start,end))
                    else:
                        if end:windows.append((0,end))
                        if start<604800:windows.append((start,604800))
                previous=self.r.continuity.calendar(symbol)
                calendar=SessionCalendar(digest([account.scope_id,symbol,state['epoch']]),raw['scheduleTimeZone'],tuple(sorted(windows)),
                    source_ref='ProtoOASymbol.schedule / '+state['epoch'],version=previous.version if previous else 1)
                if previous and calendar!=previous:calendar=replace(calendar,version=previous.version+1)
                self.r.continuity.set_calendar(symbol,calendar)
            ids.append(sid)
        previous=set(state.get('spot_ids',())) if state.get('subscribed_scope')==account.scope_id else set()
        removed=previous-set(ids);added=set(ids)-previous
        if removed:
            self.request(account.endpoint_class,'ProtoOAUnsubscribeSpotsReq',{'ctidTraderAccountId':account.account_id,'symbolId':sorted(removed)})
            for key in tuple(state.get('live_bars',{})):
                if key[0] in removed:
                    self.request(account.endpoint_class,'ProtoOAUnsubscribeLiveTrendbarReq',{'ctidTraderAccountId':account.account_id,'symbolId':key[0],'period':key[1]})
                    state['live_bars'].pop(key)
        if added:
            self.request(account.endpoint_class,'ProtoOASubscribeSpotsReq',{'ctidTraderAccountId':account.account_id,'symbolId':sorted(added),'subscribeToSpotTimestamp':True})
        state['subscribed_scope']=account.scope_id;state['spot_ids']=set(ids)
        self._apply_reconcile(account.endpoint_class,account.account_id)

    def _spot(self,endpoint,aid,body):
        state=self.native[(endpoint,aid)];context=state.get('context')
        if context!=self.r.accounts.current or context is None:return
        sid=int(body['symbolId']);symbol=state['symbols'].get(sid)
        if symbol not in PAIRS or not body.get('timestamp'):return
        authority=self.r.market.authority(symbol)
        if sid not in state['specs'] or not authority or authority['source_epoch']!=state['epoch']:return
        observed=timestamp(body['timestamp']);sides=state['quotes'].setdefault(sid,{})
        if instant(observed)>instant(self.r.clock()):
            self.r.continuity.mark_stream_gap(symbol,state['epoch'],'FUTURE_NATIVE_QUOTE');return
        for raw in body.get('trendbar',[]):self._closed_native_bar(state,context,sid,symbol,observed,raw)
        if 'bid' in body:
            from sfm_fx_new_age.services.timeline import Tick
            # Tick observations draw partial forming candles; native trendbars own
            # complete OHLC/tick-volume. Never race two finalizers for one interval.
            self.r.timeline.ingest(Tick(symbol,Decimal(body['bid'])/100000,observed,self.r.clock(),state['epoch'],context.scope_id,Origin.LIVE_OBSERVED),finalize=False)
        for side in ('bid','ask'):
            if side in body:
                if side in sides and instant(sides[side][1])>instant(observed):continue
                sides[side]=(Decimal(body[side])/100000,observed)
        if 'bid' in sides and 'ask' in sides:
            incoherent=state.setdefault('incoherent_quotes',set())
            if sides['ask'][0]<sides['bid'][0]:
                # Independent native sides can briefly cross. Never clamp/fabricate
                # prices, reuse a known-invalid old quote, or disconnect all symbols.
                if symbol not in incoherent:
                    self.r.market.invalidate_quote(aid,symbol,state['epoch'],observed,'CROSSED_NATIVE_SIDES')
                incoherent.add(symbol)
                return
            quote_time=min((sides[s][1] for s in ('bid','ask')),key=instant)
            self.sequence+=1
            self.r.market.set_quote(Quote(aid,symbol,sides['bid'][0],sides['ask'][0],quote_time,state['epoch'],Origin.LIVE_OBSERVED,context.scope_id,
                bid_at=sides['bid'][1],ask_at=sides['ask'][1],sequence=self.sequence))
            incoherent.discard(symbol)

    def _closed_native_bar(self,state,context,sid,symbol,observed,raw):
        period=raw.get('period');frame={9:'H1',10:'H4',12:'D1',13:'W1'}.get(period,period)
        if frame not in {'W1','D1','H4','H1'} or state.get('live_bars',{}).get((sid,frame)) not in {'PENDING','ACTIVE'}:return
        calendar=self.r.continuity.calendar(symbol);authority=self.r.market.authority(symbol)
        if not authority or authority['source_epoch']!=state['epoch'] or not calendar or calendar.source_ref!='ProtoOASymbol.schedule / '+state['epoch']:return
        try:
            start=timestamp(int(raw['utcTimestampInMinutes'])*60000);close=calendar.next_close(start,frame)
            # An incomplete/current bar cannot become a completed bar just because
            # it came from a native message. Preserve the provider timestamp.
            if instant(close)>instant(observed):return
            bar=trendbar(raw,symbol=symbol,timeframe=frame,source_epoch=state['epoch'],scope_id=context.scope_id,received_at=self.r.clock(),close_time=close)
        except (KeyError,TypeError,ValueError):
            self.r.continuity.mark_stream_gap(symbol,state['epoch'],'INVALID_NATIVE_CLOSED_BAR');return
        identity=(sid,frame,start);seen=state.setdefault('live_bar_seen',{})
        if identity in seen and instant(observed)<=instant(seen[identity]):return
        seen[identity]=observed
        if len(seen)>512:seen.pop(next(iter(seen)))
        previous=next((b for b in self.r.market.bars(symbol,frame,self.r.clock(),state['epoch']) if b.open_time==bar.open_time),None)
        if previous:
            if all(getattr(previous,k)==getattr(bar,k) for k in ('open','high','low','close','tick_volume','construction')):return
            if instant(bar.available_at)<=instant(previous.available_at):return
            bar=replace(bar,revision=previous.revision+1)
        self.r.market.ingest(bar);state['live_bar_received']=state.get('live_bar_received',0)+1

    def _apply_reconcile(self,endpoint,aid):
        state=self.native[(endpoint,aid)];context=state.get('context');body=state.get('reconcile')
        if not body or context!=self.r.accounts.current or context is None or not state.get('symbols_ready'):return
        version=state.get('reconcile_version',0)
        if state.get('applied_reconcile_version')==version:return
        native_orders=body.get('order',[])
        display=[];unmapped=0
        for order in native_orders:
            trade=order.get('tradeData',{});symbol=state['symbols'].get(int(trade.get('symbolId',0)))
            if symbol not in PAIRS:
                unmapped+=1;display.append(dict(order,status='UNMAPPED_NATIVE_INVENTORY',broker_order_id=str(order.get('orderId','UNKNOWN'))));continue
            display.append({'broker_order_id':str(order['orderId']),'symbol':symbol,'scope_id':context.scope_id,'source_epoch':state['epoch'],
                'side':trade.get('tradeSide'),'units':str(Decimal(trade.get('volume',0))/100),'entry_price':str(order.get('limitPrice') or order.get('stopPrice')) if order.get('limitPrice') or order.get('stopPrice') else None,
                'state':order.get('orderStatus','UNKNOWN'),'order_type':order.get('orderType','UNKNOWN'),'origin':Origin.LIVE_OBSERVED.value,'observed_at':self.r.clock()})
        self.r.database.put('broker_pending_snapshot',context.scope_id,{'scope_id':context.scope_id,'source_epoch':state['epoch'],
            'observed_at':self.r.clock(),'complete':True,'orders':native_orders,'display_orders':display,'excluded_native_orders':unmapped})
        self.r.emit('BROKER.ORDER_STATE','BROKER_RECONCILER',{'scope_id':context.scope_id,'source_epoch':state['epoch']},Priority.P1,context.scope_id)
        for order in native_orders:self._native_order(context,order,'ACCEPTED_PENDING')
        rows=[];outside=0
        for p in body.get('position',[]):
            data=p['tradeData'];symbol=state['symbols'].get(int(data['symbolId']))
            if symbol not in PAIRS:outside+=1;continue
            if p.get('positionStatus')!='POSITION_STATUS_OPEN':continue
            rows.append({'position_id':str(p['positionId']),'symbol':symbol,'side':data['tradeSide'],
                'units':str(Decimal(data['volume'])/100),'entry_price':str(p['price'])})
        old=self.r.positions.snapshot()
        observed=self.r.clock()
        self.sequence+=1
        self.r.positions.replace_snapshot(context.scope_id,rows,observed_at=observed,origin=Origin.LIVE_OBSERVED.value,
            complete=outside==0,sequence=self.sequence,excluded_native_positions=outside)
        native_ids={str(o['orderId']) for o in native_orders}
        pending=set()
        for local in self.r.database.orders():
            if local.get('scope_id')!=context.scope_id or local['state'] in {'FILLED','CANCELED','EXPIRED','REJECTED'}:continue
            if local.get('broker_order_id') and local['broker_order_id'] not in native_ids:
                pending.add(local['id'])
                self.request(endpoint,'ProtoOAOrderDetailsReq',{'ctidTraderAccountId':aid,'orderId':local['broker_order_id']})
        state['pending_readback']=pending
        state['applied_reconcile_version']=version
        state['reconciled']=True

    def _native_order(self,context,order,native_state=None):
        state=native_state or {'ORDER_STATUS_ACCEPTED':'ACCEPTED_PENDING','ORDER_STATUS_FILLED':'FILLED',
            'ORDER_STATUS_CANCELLED':'CANCELED','ORDER_STATUS_EXPIRED':'EXPIRED','ORDER_STATUS_REJECTED':'REJECTED'}.get(order.get('orderStatus'),'UNKNOWN')
        if state=='ACCEPTED_PENDING' and int(order.get('executedVolume',0))>0:state='PARTIALLY_FILLED'
        matching=[o for o in self.r.database.orders() if o.get('scope_id')==context.scope_id and
            (o['client_order_id']==order.get('clientOrderId') or o.get('broker_order_id')==str(order.get('orderId')))]
        if len(matching)!=1:return
        local=matching[0];updated=int(order.get('utcLastUpdateTimestamp',0))
        if updated<local.get('native_updated_ms',0):return
        native_id=str(order['orderId'])
        if local['state'] in {'FILLED','CANCELED','EXPIRED','REJECTED'} and state!=local['state']:return
        if state=='UNKNOWN':return
        quantity=Decimal(order.get('executedVolume',0))/100
        if quantity<Decimal(local.get('filled_units','0')):return
        if quantity>Decimal(local['units']):raise ValueError('Native cumulative fill exceeds local order units')
        if state=='FILLED' and quantity!=Decimal(local['units']):raise ValueError('Filled state requires exact cumulative native quantity')
        self.r.orders._apply(local['id'],BrokerOutcome(OrderState(state),native_id,str(order['positionId']) if order.get('positionId') else None,'Native event/readback'))
        self.r.database.update_order(local['id'],{'native_updated_ms':updated,'filled_units':str(quantity)})
        native=self.native.get((context.endpoint_class,context.account_id),{})
        native.get('pending_readback',set()).discard(local['id'])

    def _activity(self,endpoint,aid,name,body):
        state=self.native[(endpoint,aid)];context=state.get('context')
        if not context:return
        identity=digest([endpoint,aid,name,body]);key=context.scope_id+':'+identity
        previous=self.r.database.get('native_activity',key)
        if previous and previous.get('processed'):return
        self.r.database.put('native_activity',key,{'scope_id':context.scope_id,'native_event_id':identity,
            'message_type':name,'payload':body,'observed_at':self.r.clock()})
        if context!=self.r.accounts.current:return
        if isinstance(body.get('order'),dict):self._native_order(context,body['order'],execution_state(body) if name=='ProtoOAExecutionEvent' else None)
        elif isinstance(body.get('order'),list):
            for order in body['order']:self._native_order(context,order)
        if name=='ProtoOAExecutionEvent' and body.get('position'):
            # Authoritative full readback owns completeness; event is never converted from order acceptance.
            self.request(endpoint,'ProtoOAReconcileReq',{'ctidTraderAccountId':aid})
        saved=self.r.database.get('native_activity',key)
        saved['processed']=True;self.r.database.put('native_activity',key,saved)
        self.r.emit('BROKER.ACTIVITY','CT_OPEN_API_CONNECTOR',{'scope_id':context.scope_id,'native_event_id':identity},Priority.P0,context.scope_id)

    def ready_for_issue(self,scope):
        current=self.r.accounts.current
        if not current or current.scope_id!=scope:return False
        state=self.native.get((current.endpoint_class,current.account_id))
        unresolved=any(o.get('scope_id')==scope and o['state'] in {'RESERVED','SUBMITTING','UNKNOWN'} for o in self.r.database.orders())
        return bool(state and state.get('context')==current and state.get('reconciled')
                    and state.get('applied_reconcile_version')==state.get('reconcile_version')
                    and monotonic()-state.get('reconciled_at',0)<=60 and not state.get('pending_readback')
                    and not unresolved and state.get('connected'))

    def submit(self,order):
        context=self.r.accounts.current
        if not context or context.scope_id!=order['scope_id']:raise ValueError('Matching authenticated account required')
        spec=self.r.market.spec(context.account_id,order['symbol'])
        if spec is None:raise ValueError('Native specification required')
        message=new_limit_request(order,spec);identity=str(uuid4())
        self.workers[context.endpoint_class].send({'kind':'NEW_LIMIT','protobuf':message.SerializeToString(),'request_id':identity})
        self.requests[identity]={'order_id':order['id'],'name':'NEW_LIMIT','endpoint':context.endpoint_class,'sent':monotonic()}
        return BrokerOutcome(OrderState.UNKNOWN,detail='Queued native submission; await execution event, never resubmit automatically')

    def reconcile(self,order):
        context=self.r.accounts.current
        if not context or context.scope_id!=order['scope_id']:raise ValueError('Matching account required')
        self.request(context.endpoint_class,'ProtoOAReconcileReq',{'ctidTraderAccountId':context.account_id})
        if order.get('broker_order_id'):self.request(context.endpoint_class,'ProtoOAOrderDetailsReq',{'ctidTraderAccountId':context.account_id,'orderId':order['broker_order_id']})
        return BrokerOutcome(OrderState.UNKNOWN,detail='Authoritative native readback requested; no submission')

    def cancel(self,order):
        context=self.r.accounts.current
        if not context or context.scope_id!=order['scope_id']:raise ValueError('Matching account required')
        identity=str(uuid4());self.workers[context.endpoint_class].send({'kind':'CANCEL_PENDING','account_id':context.account_id,'broker_order_id':order['broker_order_id'],'request_id':identity})
        self.requests[identity]={'order_id':order['id'],'name':'CANCEL_PENDING','endpoint':context.endpoint_class,'sent':monotonic()}
        return BrokerOutcome(OrderState.UNKNOWN,order['broker_order_id'],detail='Native cancellation queued; await readback')

    def start_backfill(self,job):
        account=self.r.accounts.current
        if not account or account.scope_id!=job['scope_id']:raise ValueError('Selected matching backfill account required')
        spec=self.r.market.spec(account.account_id,job['symbol'])
        if not spec:raise ValueError('Native symbol required')
        self.request(account.endpoint_class,'ProtoOAGetTrendbarsReq',{'ctidTraderAccountId':account.account_id,
            'symbolId':spec.broker_symbol_id,'period':job['timeframe'],'fromTimestamp':milliseconds(job['from']),
            'toTimestamp':milliseconds(job.get('cursor') or job['to']),'count':500},context={'job_id':job['id'],'symbol_id':spec.broker_symbol_id})

    def _backfill_page(self,endpoint,aid,context,body):
        job=self.r.database.get('backfill',context['job_id']);state=self.native[(endpoint,aid)]
        if not job or job['scope_id']!=self.r.market.scope_id or job['source_epoch']!=state['epoch']:return
        spec=self.r.market.spec(aid,job['symbol']);authority=self.r.market.authority(job['symbol'])
        if not spec or not authority or authority['source_epoch']!=state['epoch'] or state['symbols'].get(spec.broker_symbol_id)!=job['symbol'] or spec.broker_symbol_id not in state['specs'] or context.get('symbol_id',spec.broker_symbol_id)!=spec.broker_symbol_id:
            self._fail_backfill({'context':context},'Pair metadata withdrawn before history response');return
        calendar=self.r.continuity.calendar(job['symbol'])
        if not calendar:raise ValueError('Broker session/timeframe calendar required before normalizing history')
        normalized=[]
        rows=body.get('trendbar',[])
        for raw in rows:
            start=timestamp(int(raw['utcTimestampInMinutes'])*60000);close=calendar.next_close(start,job['timeframe'])
            if instant(start)<instant(job['from']) or instant(close)>instant(job['to']) or instant(close)>instant(self.r.clock()):continue
            normalized.append(trendbar(raw,symbol=job['symbol'],timeframe=job['timeframe'],source_epoch=job['source_epoch'],scope_id=job['scope_id'],received_at=self.r.clock(),close_time=close))
        earliest=min((int(r['utcTimestampInMinutes'])*60000 for r in rows),default=None)
        # count is measured backwards from toTimestamp: some servers return rows
        # older than fromTimestamp. Reaching our lower bound is exhaustion for
        # this job, not permission to walk the account's entire history.
        reached_start=earliest is not None and earliest<=milliseconds(job['from'])
        complete=reached_start or not rows or (not body['hasMore'] if 'hasMore' in body else len(rows)<500)
        cursor=timestamp(earliest-1) if earliest is not None else None
        if not complete and (instant(cursor)>=instant(job.get('cursor') or job['to']) or job.get('pages',0)>=64):
            self._fail_backfill({'context':context},'Native history cursor/page budget exhausted');return
        self.r.continuity.apply_page(job['id'],normalized,complete=complete,cursor=cursor)
        updated=self.r.database.get('backfill',job['id']);updated['pages']=job.get('pages',0)+1
        self.r.database.put('backfill',job['id'],updated)
        if not complete:self.start_backfill(updated)

    def _disconnected(self,endpoint,reason):
        self.quote_history.interrupt(endpoint)
        self.endpoint_failures[endpoint]=reason
        self.history.disconnect(endpoint)
        for request in self.requests.values():
            if request.get('endpoint')==endpoint:self._fail_backfill(request,'Endpoint disconnected before history completed')
        for (route,aid),state in self.native.items():
            if route!=endpoint:continue
            state['reconciled']=False
            state['connected']=False
            context=state.get('context')
            if context:self.r.accounts.sessions.pop(context.scope_id,None)
            if context and context==self.r.accounts.current:
                for symbol in state['symbols'].values():self.r.continuity.mark_stream_gap(symbol,state['epoch'],reason)
                self.r.accounts.unselect()
        self.state='DEGRADED' if any(v.get('connected') for v in self.native.values()) else 'DISCONNECTED';self.reason=reason
        if self.analytical_feed:self.analytical_feed.poll()

    def disconnect(self,*,clear_oauth=True):
        if self.analytical_feed:self.analytical_feed.disconnect()
        if clear_oauth:self._generation+=1;self._resume_scope=None;self._auto_select_single=False;self._oauth_consumed=True
        self.feed_intents.clear()
        self.history.disconnect()
        self.quote_history.interrupt()
        for worker in self.workers.values():worker.close()
        self.workers.clear();self.requests.clear();self.native.clear();self._pending_native.clear()
        if self.r.orders.transport is self:self.r.orders.transport=None
        if not self.r.fixture_mode:self.r.accounts.disconnect()
        if clear_oauth and self.oauth:self.oauth.close();self.oauth_url=None
        self.state='DISCONNECTED';self.reason='Disconnected; no write requests replayed'

    def close(self):
        self.closing=True
        if self.analytical_feed:self.analytical_feed.close()
        self.disconnect()
