"""Core-only ingress of trusted-connector optional evidence; no networking.

Tabs and research plugins receive frozen snapshots, never an ingestion handle.
Provider registration is ephemeral startup configuration, not persisted authority.
"""
import json
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence,KINDS
from sfm_fx_new_age.contracts.domain import record,instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.storage.database import StateConflict

class SupplementalEvidenceStore:
    def __init__(self,db,market,clock,emit):
        self.db,self.market,self.clock,self.emit=db,market,clock,emit
        self.providers={};self.admissions={};self._admission_index={}
    def register_provider(self,provider_id,*,kinds,origin):
        from sfm_fx_new_age.contracts.domain import Origin
        if not provider_id or provider_id in self.providers or not kinds or not set(kinds)<=KINDS:raise ValueError('Unique explicit core source provider required')
        self.providers[provider_id]=(frozenset(kinds),Origin(origin).value)
        self._admission_index[provider_id]={}
    def accept(self,evidence):
        return self.accept_many((evidence,))
    def accept_many(self,evidences):
        """Validate and commit a bounded batch atomically, then publish notifications."""
        values=tuple(evidences)
        if not 0<len(values)<=32:raise ValueError('Bounded nonempty optional evidence batch required')
        changes=[];size=0
        with self.db.transaction() as conn:
            for evidence in values:
                prepared=self._prepare(evidence)
                if prepared is None:continue
                key,body=prepared;size+=len(json.dumps(body,allow_nan=False))
                if size>12000000:raise ValueError('Optional evidence batch budget exceeded')
                self.db.write(conn,'supplemental_evidence',key,body);changes.append((key,body))
        # Ephemeral housekeeping metadata only. Persisted latest-selection,
        # expiry and membership checks in snapshot() remain authoritative.
        for evidence in values:
            body=record(evidence);provider=body['provider_id']
            group=(body['scope_id'],body['source_epoch'],body['symbol'],body['kind'])
            rank=(instant(body['available_at']),body['revision'])
            index=self._admission_index.setdefault(provider,{})
            if index is None:continue
            old=index.get(group)
            if old is None or rank>old[0]:index[group]=(rank,{})
            if rank==index[group][0]:index[group][1][digest(body)]=instant(body['valid_until'])
            if len(index)>256 or len(index[group][1])>64:self._admission_index[provider]=None
        for key,body in changes:
            self.emit('ANALYTICS.INPUT','STRATEGY_RECIPE_HOST',dict(symbol=body['symbol'],scope_id=body['scope_id'],source_epoch=body['source_epoch'],kind=body['kind'],evidence_hash=digest(body)),Priority.P2,body['scope_id'])
        return len(changes)

    def live_admission_members(self,provider,binding,now):
        """Intersect-only pruning; no database payload reread or restoration."""
        index=self._admission_index.get(provider)
        if index is None:return None
        at=instant(now);lanes=dict(binding[1]);retained=set()
        for group,(rank,members) in list(index.items()):
            scope,epoch,symbol,kind=group
            if scope!=binding[0] or lanes.get(symbol)!=epoch:
                del index[group];continue
            # A backwards clock requires the original as-of database query.
            if at<rank[0]:return None
            retained.update(h for h,until in members.items() if at<=until)
        return retained
    def _prepare(self,evidence):
        if type(evidence) is not SupplementalEvidence:raise ValueError('Typed optional source evidence required')
        provider=self.providers.get(evidence.provider_id);authority=self.market.authority(evidence.symbol)
        if not provider or evidence.kind not in provider[0] or evidence.origin!=provider[1]:raise ValueError('No configured matching source adapter')
        if not authority or (evidence.scope_id,evidence.source_epoch,evidence.origin)!=(self.market.scope_id,authority['source_epoch'],authority['origin']):raise ValueError('Optional evidence scope / epoch / origin mismatch')
        if instant(evidence.available_at)>instant(self.clock()):raise ValueError('Future source evidence rejected')
        body=record(evidence)
        if len(json.dumps(body,allow_nan=False))>6000000:raise ValueError('Optional source payload budget exceeded')
        key=digest([evidence.scope_id,evidence.source_epoch,evidence.symbol,evidence.kind,evidence.provider_id,evidence.window_start,evidence.window_end,evidence.revision])
        existing=self.db.get('supplemental_evidence',key)
        if existing and existing!=body:raise StateConflict('Optional evidence revisions are immutable')
        if existing:return None
        old=self.db.supplemental_revision(evidence)
        if old:
            if evidence.revision<=old['revision'] or instant(evidence.available_at)<=instant(old['available_at']):raise StateConflict('Optional correction must advance revision and availability')
        elif evidence.revision!=1:raise StateConflict('First optional revision must be one')
        return key,body
    def snapshot(self,symbol,cutoff):
        authority=self.market.authority(symbol)
        if not authority:return {}
        latest={};at=instant(cutoff)
        candidates=self.db.supplemental_candidates(scope=self.market.scope_id,epoch=authority['source_epoch'],
            symbol=symbol,origin=authority['origin'],providers=self.providers,cutoff=cutoff)
        for row in candidates:
            provider=self.providers.get(row['provider_id'])
            if not provider or row['kind'] not in provider[0] or row['origin']!=provider[1]:continue

            if (row['scope_id'],row['source_epoch'],row['symbol'],row['origin'])!=(self.market.scope_id,authority['source_epoch'],symbol,authority['origin']):continue
            if instant(row['available_at'])>at:continue
            key=(row['kind'],row['provider_id']);old=latest.get(key)
            rank=lambda r:(instant(r['available_at']),r['revision'],digest(r))
            if old is None or rank(row)>rank(old):latest[key]=row
        result={}
        for kind in sorted(KINDS):
            # Select the latest admitted revision BEFORE expiry: never resurrect
            # a superseded older publication after its correction expires.
            values=[r for (k,_),r in latest.items() if k==kind and at<=instant(r['valid_until'])
                and (self.admissions.get(r['provider_id']) is None or digest(r) in self.admissions[r['provider_id']])]
            if len(values)==1:result[kind]=values[0]
        return result
