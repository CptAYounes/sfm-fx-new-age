"""Opt-in local read-only source adapter; no code loading, network or account selection.

The publisher's provenance remains a configuration declaration, not independent
vendor authentication. Paths/record text are never included in status/error logs.
"""
from __future__ import annotations
from dataclasses import fields
from pathlib import Path
import hashlib,json,os,re,stat,time
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence,KINDS
from sfm_fx_new_age.contracts.domain import Origin,PAIRS,instant
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.contracts.domain import record
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape

MAX_FILE=6000000
MAX_BATCH=12000000


def read_bytes(path,budget):
    path=Path(path)
    if not path.is_absolute() or path.resolve()!=path:raise ValueError('Absolute nonsymlink input required')
    fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_mode&0o022 or before.st_size>budget:raise ValueError('Bounded private regular input required')
        if before.st_uid not in {os.getuid(),0}:raise ValueError('Input owner rejected')
        with os.fdopen(os.dup(fd),'rb') as stream:data=stream.read(budget+1)
        after=os.fstat(fd)
        if len(data)>budget or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('Input changed while reading')
        return data
    finally:os.close(fd)


def parse_json(raw):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate JSON field')
            result[k]=v
        return result
    def nonfinite(_):raise ValueError('Nonfinite JSON value')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)


def load_config(path,*,allow_fixture=False):
    config=parse_json(read_bytes(Path(path),64000))
    if not isinstance(config,dict) or set(config)!={'schema_version','providers'} or type(config['schema_version']) is not int or config['schema_version']!=1:raise ValueError('Exact source configuration schema required')
    providers=config['providers']
    if not isinstance(providers,list) or not 0<len(providers)<=16:raise ValueError('One to sixteen explicit source providers required')
    ids=set();paths=set()
    for p in providers:
        if not isinstance(p,dict) or set(p)!={'provider_id','origin','kinds','manifest_path'}:raise ValueError('Exact source provider fields required')
        if not isinstance(p['provider_id'],str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',p['provider_id']) or p['provider_id'] in ids:raise ValueError('Unique bounded provider identity required')
        ids.add(p['provider_id']);origin=Origin(p['origin'])
        if origin==Origin.SYNTHETIC_FIXTURE and not allow_fixture:raise ValueError('Fixture source requires explicit fixture session')
        if not isinstance(p['kinds'],list) or not p['kinds'] or any(not isinstance(k,str) for k in p['kinds']) or len(set(p['kinds']))!=len(p['kinds']) or not set(p['kinds'])<=KINDS:raise ValueError('Exact unique supported source kinds required')
        path=Path(p['manifest_path'])
        if not path.is_absolute() or path.resolve()!=path or path.suffix!='.json' or str(path) in paths:raise ValueError('Unique absolute nonsymlink manifest path required')
        paths.add(str(path))
    return config


class SupplementalFileIngress:
    def __init__(self,store,config_path=None,*,allow_fixture=False,monotonic=time.monotonic):
        self.store,self.monotonic=store,monotonic;self.next_poll=0;self.rows={};self.configured=False
        self.providers=load_config(config_path,allow_fixture=allow_fixture)['providers'] if config_path is not None else []
        if any(p['provider_id'] in store.providers for p in self.providers):raise ValueError('Source provider is already owned')
        self.configured=bool(self.providers)
        for p in self.providers:self.rows[p['provider_id']]=dict(provider_id=p['provider_id'],origin=p['origin'],kinds=p['kinds'],state='WAITING_SCOPE',admitted=0,manifest_sha256=None)
    def _withdraw(self,provider_id):
        self.store.admissions.pop(provider_id,None)
        if self.store.providers.pop(provider_id,None) is not None:
            for symbol in PAIRS:
                self.store.emit('ANALYTICS.INPUT','STRATEGY_RECIPE_HOST',dict(symbol=symbol,scope_id=self.store.market.scope_id,source_epoch='OPTIONAL_INPUT_WITHDRAWN',kind='LOCAL_SOURCE_STATUS'),Priority.P2,self.store.market.scope_id)
    def poll(self,*,force=False):
        now=self.monotonic()
        if not force and now<self.next_poll:return
        self.next_poll=now+2
        for p in self.providers:
            row=self.rows[p['provider_id']]
            before=dict(row)
            try:
                if self.store.market.scope_id=='UNBOUND':
                    self._withdraw(p['provider_id']);row.update(state='WAITING_SCOPE',admitted=0)
                else:self._poll_provider(p,row)
            except FileNotFoundError:
                self._withdraw(p['provider_id']);row.update(state='WAITING_INPUT',admitted=0)
            except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError,ArithmeticError,RecursionError):
                self._withdraw(p['provider_id']);row.update(state='REJECTED',admitted=0)
            if row!=before:
                for symbol in PAIRS:
                    self.store.emit('ANALYTICS.INPUT','STRATEGY_RECIPE_HOST',dict(symbol=symbol,scope_id=self.store.market.scope_id,source_epoch='OPTIONAL_FILE_STATUS',kind='LOCAL_SOURCE_STATUS'),Priority.P2,self.store.market.scope_id)
    def _poll_provider(self,p,row):
        path=Path(p['manifest_path']);raw=read_bytes(path,64000);manifest=parse_json(raw)
        if not isinstance(manifest,dict) or set(manifest)!={'schema_version','entries'} or type(manifest['schema_version']) is not int or manifest['schema_version']!=1:raise ValueError('Exact source manifest schema required')
        entries=manifest['entries']
        if not isinstance(entries,list) or not 0<len(entries)<=32:raise ValueError('Bounded nonempty source manifest required')
        values=[];used=set();bytes_used=0
        for e in entries:
            if not isinstance(e,dict) or set(e)!={'file','sha256'} or not isinstance(e['file'],str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.json',e['file']) or e['file'] in used:raise ValueError('Unique plain JSON filename required')
            if not isinstance(e['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',e['sha256']):raise ValueError('Exact lowercase SHA-256 required')
            used.add(e['file']);data=read_bytes(path.parent/e['file'],MAX_FILE);bytes_used+=len(data)
            if bytes_used>MAX_BATCH or hashlib.sha256(data).hexdigest()!=e['sha256']:raise ValueError('Source payload checksum or budget mismatch')
            body=parse_json(data)
            required={f.name for f in fields(SupplementalEvidence) if f.name not in {'revision','schema_version'}}
            if not isinstance(body,dict) or not required<=set(body)<=required|{'revision','schema_version'} or not isinstance(body.get('records'),list) or not isinstance(body.get('parameters'),dict):raise ValueError('Exact source envelope fields required')
            if 'schema_version' in body and type(body['schema_version']) is not int:raise ValueError('Integer input schema version required')
            body['records']=tuple(body['records']);evidence=SupplementalEvidence(**body)
            validate_wire_shape(evidence)
            if evidence.provider_id!=p['provider_id'] or evidence.origin!=p['origin'] or evidence.kind not in p['kinds']:raise ValueError('Input provider capability mismatch')
            values.append(evidence)
        # Fail closed on a publisher race; never admit a mixed-manifest batch.
        if read_bytes(path,64000)!=raw:raise ValueError('Source manifest changed during read')
        authority=self.store.market
        matching=lambda e:(e.scope_id,e.source_epoch,e.origin)==(authority.scope_id,(authority.authority(e.symbol) or {}).get('source_epoch'),(authority.authority(e.symbol) or {}).get('origin'))
        if not all(matching(e) for e in values):
            self._withdraw(p['provider_id']);row.update(state='WAITING_SCOPE',admitted=0);return
        for e in values:
            previous=self.store.db.supplemental_revision(e)
            if previous and e.revision<previous['revision']:raise ValueError('Published source correction cannot roll back')
        restored=p['provider_id'] not in self.store.providers
        old_admissions=self.store.admissions.get(p['provider_id'])
        allowed=frozenset(digest(record(e)) for e in values)
        if restored:self.store.register_provider(p['provider_id'],kinds=p['kinds'],origin=p['origin'])
        try:added=self.store.accept_many(values)
        except Exception:
            self._withdraw(p['provider_id']);raise
        self.store.admissions[p['provider_id']]=allowed
        if restored or old_admissions!=allowed:
            for symbol in PAIRS:
                self.store.emit('ANALYTICS.INPUT','STRATEGY_RECIPE_HOST',dict(symbol=symbol,scope_id=authority.scope_id,source_epoch='OPTIONAL_INPUT_PUBLICATION',kind='LOCAL_SOURCE_STATUS'),Priority.P2,authority.scope_id)
        # This input is a file declared by the configured publisher, not a vendor-login proof.
        active=sum(instant(e.available_at)<=instant(self.store.clock())<=instant(e.valid_until) for e in values)
        row.update(state='ADMITTED' if active else 'EXPIRED',admitted=len(values),active_envelopes=active,last_added=added,manifest_sha256=hashlib.sha256(raw).hexdigest())
    def status(self):
        return dict(configured=self.configured,read_only_files=True,network_enabled=False,provenance='CONFIGURED_FILE_PUBLISHER_DECLARATION_NOT_VENDOR_AUTHENTICATION',providers=[dict(v,kinds=list(v['kinds'])) for v in self.rows.values()])
