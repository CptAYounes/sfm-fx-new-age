"""Explicit human OAuth and private token persistence. No secret enters the core journal."""
from __future__ import annotations
from dataclasses import dataclass,field
from pathlib import Path
from urllib.parse import urlparse,parse_qs,urlencode
from urllib.request import urlopen,Request
from urllib.error import HTTPError,URLError
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from threading import Thread,RLock
from time import monotonic,time
import json,os,secrets,stat,re

AUTH_URL='https://id.ctrader.com/my/settings/openapi/grantingaccess/'
TOKEN_URL='https://openapi.ctrader.com/apps/token'


def token_http_request(url,timeout):
    """Official token API: code exchange GET, refresh POST; never log its URL."""
    grant=parse_qs(urlparse(url).query).get('grant_type',[])
    return urlopen(Request(url,method='POST' if grant==['refresh_token'] else 'GET',
        headers={'Accept':'application/json','Content-Type':'application/json'}),timeout=timeout)


def token_error_code(body):
    if isinstance(body,dict) and body.get('description')=='Malformed client_id parameter':return 'MALFORMED_CLIENT_ID'
    value=body.get('errorCode',body.get('error_code')) if isinstance(body,dict) else None
    return value if value in {'ACCESS_DENIED','INVALID_CLIENT','INVALID_GRANT','INVALID_REQUEST','INVALID_TOKEN','TOKEN_EXPIRED','TOO_MANY_REQUESTS'} else None


class SecretStore:
    """User-owned 0700 directory and 0600 atomic plaintext file; not an encrypted vault."""
    def __init__(self,path:Path):self.path=Path(path)

    def _check_parent(self,create=False):
        parent=self.path.parent
        if create:parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        if parent.is_symlink() or not parent.is_dir():raise ValueError('Private regular secret directory required')
        info=parent.stat()
        if info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o077:raise ValueError('Secret directory must be user-owned mode 0700')

    def load(self)->dict:
        self._check_parent()
        fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            info=os.fstat(fd)
            if info.st_size>65536:raise ValueError('Private credential file exceeds the size limit')
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:
                raise ValueError('Secret file must be user-owned regular mode 0600')
            with os.fdopen(fd,'r') as handle:fd=-1;body=json.load(handle)
        finally:
            if fd>=0:os.close(fd)
        if type(body) is not dict:raise ValueError('Secret record must be an object')
        return body

    def save(self,body:dict):
        self._check_parent(create=True)
        if self.path.is_symlink():raise ValueError('Secret symlink rejected')
        if self.path.exists():self.load() # refuse an unsafe existing target
        temp=self.path.with_name('.token-'+secrets.token_hex(12))
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'w') as handle:
                json.dump(body,handle);handle.flush();os.fsync(handle.fileno())
            os.replace(temp,self.path)
            parent=os.open(self.path.parent,os.O_DIRECTORY)
            try:os.fsync(parent)
            finally:os.close(parent)
        finally:temp.unlink(missing_ok=True)


@dataclass(frozen=True)
class OAuthConfig:
    client_id:str
    redirect_uri:str
    scope:str='trading'

    def __post_init__(self):
        url=urlparse(self.redirect_uri)
        if not isinstance(self.client_id,str) or not self.client_id or len(self.client_id)>256 or self.scope not in {'accounts','trading'} or url.query or url.fragment or url.username or url.password:
            raise ValueError('Registered application ID, redirect and OAuth scope required')
        if not (self.loopback or (url.scheme=='https' and url.hostname=='openapi.ctrader.com' and url.port in (None,443) and re.fullmatch(r'/apps/[1-9][0-9]*/playground',url.path))):
            raise ValueError('Registered loopback callback or official cTrader Playground redirect required')

    @property
    def loopback(self):
        url=urlparse(self.redirect_uri)
        return url.scheme=='http' and url.hostname=='127.0.0.1' and bool(url.port) and url.path=='/callback'


class OAuthSession:
    def __init__(self,config:OAuthConfig,store:SecretStore,*,request=token_http_request):
        self.config,self.store,self.request=config,store,request
        self.state=None;self.expires=0;self.server=None;self.thread=None;self.last_status='IDLE'
        self._state_lock=RLock();self._exchange_lock=RLock();self.closed=False;self._generation=0
        self.last_error=None;self.last_http_status=None

    def begin(self):
        if not self.config.loopback:raise ValueError('This application uses the cTrader Sandbox redirect. Link its refreshed token once, or register a local /callback redirect for browser sign-in.')
        self.close()
        self.closed=False
        self.state=secrets.token_urlsafe(32);self.expires=monotonic()+300
        session=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,format,*args):pass # callback URL contains a one-time secret
            def do_GET(self):
                try:
                    session.accept_callback(self.path)
                    status,text=200,b'Authorization received. Return to SFM FX New Age.'
                except Exception:
                    status,text=400,b'Authorization refused. Restart login in SFM FX New Age.'
                self.send_response(status);self.send_header('Content-Type','text/plain');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(text)
        port=urlparse(self.config.redirect_uri).port
        assert port is not None
        self.server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
        self.server.daemon_threads=True
        self.server.timeout=0.2
        self.thread=Thread(target=self.server.serve_forever,kwargs={'poll_interval':0.2},daemon=True)
        self.thread.start();self.last_status='WAITING_FOR_HUMAN'
        return AUTH_URL+'?'+urlencode({'client_id':self.config.client_id,'redirect_uri':self.config.redirect_uri,
                                     'scope':self.config.scope,'state':self.state,'product':'web'})

    def accept_callback(self,path):
        url=urlparse(path);params=parse_qs(url.query)
        if url.path!='/callback' or set(params)!={'code','state'} or any(len(v)!=1 for v in params.values()):raise ValueError('Invalid OAuth callback')
        with self._state_lock:
            if self.closed or not self.state or monotonic()>self.expires or not secrets.compare_digest(params['state'][0],self.state):raise ValueError('OAuth state/expiry mismatch')
            self.state=None # consume once, even if exchange fails
            generation=self._generation
        self._exchange({'grant_type':'authorization_code','code':params['code'][0],'redirect_uri':self.config.redirect_uri},generation)
        with self._state_lock:
            if not self.closed and generation==self._generation:self.last_status='TOKEN_STORED'

    def _exchange(self,fields,generation=None):
        with self._state_lock:
            if generation is None:generation=self._generation
        with self._exchange_lock:
            self._exchange_locked(fields,generation)

    def _exchange_locked(self,fields,generation):
        with self._state_lock:
            if self.closed or generation!=self._generation:raise ValueError('OAuth exchange belongs to a closed login attempt')
        saved=self.store.load()
        if not saved.get('client_secret'):raise ValueError('Application credential is not configured')
        params=fields|{'client_id':self.config.client_id,'client_secret':saved['client_secret']}
        self.last_error=None;self.last_http_status=None
        try:
            with self.request(TOKEN_URL+'?'+urlencode(params),timeout=15) as response:body=json.load(response)
            self.last_error=token_error_code(body)
            if not body.get('accessToken') or not body.get('refreshToken') or int(body.get('expiresIn',0))<=0:raise ValueError('Token response refused')
            saved.update(access_token=body['accessToken'],refresh_token=body['refreshToken'],expires_at=time()+int(body['expiresIn']))
            with self._state_lock:
                if self.closed or generation!=self._generation:raise ValueError('OAuth session was closed')
                self.store.save(saved)
        except Exception as exc:
            with self._state_lock:
                if generation==self._generation:
                    self.last_status='TOKEN_EXCHANGE_FAILED'
                    if isinstance(exc,HTTPError):
                        self.last_http_status=exc.code
                        try:self.last_error=token_error_code(json.load(exc))
                        except Exception:pass
                        self.last_error=self.last_error or ('RATE_LIMITED' if exc.code==429 else 'HTTP_'+str(exc.code))
                    elif isinstance(exc,(URLError,TimeoutError,OSError)):self.last_error='CONNECTION_FAILED'
                    self.last_error=self.last_error or 'TOKEN_EXCHANGE_FAILED'
            raise ValueError('OAuth token exchange failed; no credential details logged') from None

    def refresh(self):
        saved=self.store.load()
        if not saved.get('refresh_token'):raise ValueError('Human OAuth login required')
        self._exchange({'grant_type':'refresh_token','refresh_token':saved['refresh_token']})
        return True

    def close(self):
        with self._state_lock:self.closed=True;self.state=None;self._generation+=1
        if self.server:
            self.server.shutdown();self.server.server_close()
            if self.thread:self.thread.join(timeout=2)
        self.server=None;self.thread=None;self.state=None
