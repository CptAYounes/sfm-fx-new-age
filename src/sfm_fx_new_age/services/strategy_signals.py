"""Owner-only strategy signal materialization and fresh, explicit human binding.

Pure policy code sees immutable market observations only. Projection workers do
not acquire database, GUI, connector, units or broker command authority.
"""
import json
from decimal import Decimal as D
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import Candidate,Origin,FRAMES,instant
from sfm_fx_new_age.contracts.strategy_signals import POLICIES,GATE_NAMES,validate_observation
from sfm_fx_new_age.contracts.public_strategies import METHODS,BY_KEY
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.storage.database import StateConflict
from .strategy_signal_policy import build_observation


class StrategySignalService:
    def __init__(self, runtime):
        self.r=runtime
        self.errors=[];self.active={}

    @staticmethod
    def lane(scope,epoch,symbol,frame,key): return digest([scope,epoch,symbol,frame,key])

    def observe(self, projection, inputs, deps):
        key=projection['strategy_id']
        if key not in POLICIES:return  # Custom extension is not one of the 83 policies.
        r=self.r;frame=projection['timeframe']
        lane=self.lane(projection['scope_id'],projection['source_epoch'],projection['symbol'],frame,key)
        slot=(projection['symbol'],frame,key)
        context=digest([projection['fingerprint'],inputs.get('_signal_input_hash'),POLICIES[key].profile_hash])
        previous=r.database.get('strategy_signal_current',lane)
        if previous and previous.get('context_fingerprint')==context:
            self.active[slot]=previous
            return
        raw=build_observation(key,projection,dict(inputs,frame=frame),deps)
        raw['context_fingerprint']=context
        if raw['opportunity_id']:raw['opportunity_id']='strategy:'+digest([raw['opportunity_id'],context])
        # Decimal remains exact text, never binary-price rounding at persistence.
        raw=json.loads(json.dumps(raw,default=str,allow_nan=False))
        validate_observation(raw)
        lane=self.lane(raw['scope_id'],raw['source_epoch'],raw['symbol'],frame,key)
        immutable=digest([lane,context])
        stored=r.database.get('strategy_signal_observation',immutable)
        if stored is not None and stored!=raw:raise StateConflict('Immutable strategy signal collision')
        if stored is None:r.database.put('strategy_signal_observation',immutable,raw)
        if raw['opportunity_id']:
            old=r.database.get('strategy_opportunity',raw['opportunity_id'])
            if old is not None and old!=raw:raise StateConflict('Immutable strategy opportunity collision')
            if old is None:r.database.put('strategy_opportunity',raw['opportunity_id'],raw)
        r.database.put('strategy_signal_current',lane,raw)
        self.active[slot]=raw
        # One bounded revision notification is emitted by the projection owner,
        # rather than 332 events with duplicated metrics for every pair scan.

    def eligibility(self, raw):
        r=self.r;now=r.clock();symbol=raw['symbol'];method=BY_KEY[raw['strategy_id']]
        account=r.accounts.current;authority=r.market.authority(symbol)
        spec=r.market.spec(account.account_id,symbol) if account else None
        quote=r.market.quote(account.account_id,symbol) if account else None
        enabled=r.analytics.projections.enabled(method)
        pointer=r.database.get('projection_current',r.analytics.projections.key(raw['scope_id'],raw['source_epoch'],symbol,raw['timeframe'],method.key))
        snapshot=r.analytics.snapshot(symbol) or {}
        expected=(raw['scope_id'],raw['source_epoch'],raw['origin'])
        active=bool(account and account.authenticated and account.origin is not Origin.HISTORICAL_REPLAY
            and authority and (account.scope_id,authority['source_epoch'],account.origin.value)==expected)
        current=bool(pointer and pointer['fingerprint']==raw['projection_fingerprint']
            and pointer['profile_hash']==raw['profile_hash'] and symbol not in r._analytics_dirty)
        pool=r.analytics.projections.pool
        if pool and (pool.pending((symbol,raw['timeframe'])) or pool.failed):current=False
        gates:dict[str,bool]=dict.fromkeys(GATE_NAMES,False)
        gates.update(AUTHENTICATED_SELECTED_SOURCE=active,
            CURRENT_ENABLED_METHOD=bool(enabled and raw['policy_hash']==POLICIES[method.key].profile_hash and r.consumers.enabled('analysis.scanner') and r.consumers.enabled('analysis.pair.'+symbol)),
            CURRENT_PROJECTION=current,
            TRIGGER_UNEXPIRED=bool(raw.get('expires_at') and instant(raw['available_at'])<=instant(now)<instant(raw['expires_at'])),
            RESOLVED_SOURCE_CONTINUITY=not bool(r.database.get('stream_gap',json.dumps([raw['scope_id'],symbol,raw['source_epoch']]))),
            GENUINE_REQUIRED_INPUTS=raw['projection_classification']!='EXPLICIT_ACTIVITY_ALTERNATIVE_NOT_GENUINE_EXECUTION_FLOW',
            CURRENT_PARAMETER_PROFILE=snapshot.get('profile_hash')==raw['profile_hash'])
        if not raw.get('opportunity_id'):return gates
        entry,stop=D(raw['entry']),D(raw['stop']);buy=raw['side']=='BUY'
        if spec:
            gates['VALID_NATIVE_GRID_GEOMETRY']=bool(spec.scope_id==raw['scope_id'] and spec.origin.value==raw['origin']
                and entry>0 and stop>0 and entry%spec.tick_size==0 and stop%spec.tick_size==0 and (stop<entry if buy else stop>entry))
        if quote:
            times=(quote.bid_at or quote.available_at,quote.ask_at or quote.available_at)
            maximum=(r.database.get('parameter','feed.quote_max_age_seconds') or {}).get('value',30)
            fresh=bool((quote.scope_id,quote.source_epoch,quote.origin.value)==expected and quote.bid<quote.ask
                and all(0<=(instant(now)-instant(t)).total_seconds()<=float(maximum) for t in times))
            spread=quote.ask-quote.bid
            gates['FRESH_TWO_SIDED_QUOTE']=fresh
            gates['SPREAD_WITHIN_THREE_NATIVE_PIPS']=bool(spec and 0<=spread<=3*spec.pip_size)
            gates['PENDING_LIMIT_SIDE']=bool(entry<quote.ask if buy else entry>quote.bid)
            gates['INTACT_INVALIDATION']=bool(quote.bid>stop if buy else quote.ask<stop)
            if raw['strategy_id']=='previous_body_live':
                # A provisional quote recovery must still be true NOW, not only
                # at the original marker's younger side timestamp.
                mid=(quote.bid+quote.ask)/2
                gates['CURRENT_PROJECTION'] &= mid>entry if buy else mid<entry
            target=D(raw['target']) if raw.get('target') else None
            gates['OBSERVED_UNREACHED_TARGET']=bool(target and (target>max(entry,quote.ask) if buy else target<min(entry,quote.bid)))
            if target:
                gates['REWARD_AFTER_OBSERVED_SPREAD']=bool(fresh and spread>=0 and
                    (abs(target-entry)-spread)/(abs(entry-stop)+spread)>=1)
        if r.database.get('strategy_signal_revoked',digest([raw['setup_id'],raw['strategy_id']])):
            gates['INTACT_INVALIDATION']=False
        return gates

    def quote_changed(self,symbol):
        """Once an observed stop/objective is crossed, recovery cannot revive it."""
        r=self.r;account=r.accounts.current
        quote=r.market.quote(account.account_id,symbol) if account else None
        if not quote:return
        for lane,raw in tuple(self.active.items()):
            if raw['symbol']!=symbol or not raw.get('opportunity_id'):continue
            if (raw['scope_id'],raw['source_epoch'])!=(quote.scope_id,quote.source_epoch):continue
            if instant(r.clock())>=instant(raw['expires_at']):self.active.pop(lane,None);continue
            if instant(quote.available_at)<instant(raw['available_at']):continue
            buy=raw['side']=='BUY';target=D(raw['target']) if raw.get('target') else None
            invalid=quote.bid<=D(raw['stop']) if buy else quote.ask>=D(raw['stop'])
            reached=bool(target and (quote.bid>=target if buy else quote.ask<=target))
            if invalid or reached:
                key=digest([raw['setup_id'],raw['strategy_id']])
                if not r.database.get('strategy_signal_revoked',key):
                    r.database.put('strategy_signal_revoked',key,dict(reason='OBSERVED_INVALIDATION' if invalid else 'OBSERVED_OBJECTIVE_REACHED',
                        quote_at=quote.available_at,source_epoch=quote.source_epoch,scope_id=quote.scope_id))

    def read(self,symbol,frame=None):
        r=self.r;scope=r.market.scope_id;authority=r.market.authority(symbol);epoch=authority['source_epoch'] if authority else None
        frames=(frame,) if frame else FRAMES
        enabled=r.analytics.projections.enabled_states()
        keys={(m.key,f):self.lane(scope,epoch,symbol,f,m.key) for m in METHODS for f in frames}
        stored=r.database.get_many('strategy_signal_current',list(keys.values()))
        output=[]
        for f in frames:
            for m in METHODS:
                p=POLICIES[m.key];raw=stored.get(keys[(m.key,f)])
                row=dict(strategy_id=m.key,name=m.name,recipe_id=m.recipe_id,recipe_version=m.version,
                    policy_id=p.policy_id,policy=p.description,policy_hash=p.profile_hash,
                    scope_id=scope,source_epoch=epoch,symbol=symbol,timeframe=f,origin=authority['origin'] if authority else 'NO_SOURCE',
                    enabled=enabled.get(m.key,False),state='OFF' if m.key in enabled else 'UNAVAILABLE',
                    reason='Enable this method in Tab 3 to evaluate its research signal pipeline.' if m.key in enabled else 'Public method is not installed in this custom analytical runtime.',
                    opportunity_id=None,side=None,entry=None,stop=None,target=None,blockers=[],gates={})
                if enabled.get(m.key,False):
                    if raw:
                        row.update(raw,enabled=True)
                        # Read-time withdrawal is no-write and cannot restore live
                        # authority from a persisted observation after restart.
                        if raw.get('opportunity_id'):
                            gates=self.eligibility(raw);blockers=[k for k,v in gates.items() if v is not True]
                            state='BLOCKED' if blockers else 'SIGNAL'
                            if not gates['TRIGGER_UNEXPIRED']:state='EXPIRED'
                            elif any(not gates[k] for k in ('AUTHENTICATED_SELECTED_SOURCE','CURRENT_PROJECTION','CURRENT_PARAMETER_PROFILE','FRESH_TWO_SIDED_QUOTE')):state='STALE'
                            elif not gates['INTACT_INVALIDATION']:state='INVALIDATED'
                            bound=r.signals.get(self.signal_id(raw))
                            row.update(bound_signal_id=bound['signal_id'] if bound else None,bound_revision=bound['revision'] if bound else 0,bound_state=bound['state'] if bound else None)
                            if bound and bound.get('market_candidate_id')==raw['opportunity_id'] and not blockers:state='BOUND' if bound['state']=='QUEUED' else bound['state']
                            row.update(gates=gates,blockers=blockers,state=state)
                            row['reason']='Research signal; review explicit units before binding. Issue is separate.' if not blockers else 'Research trigger present; blocked: '+', '.join(blockers)
                            if state=='BOUND':row['reason']='Bound local proposal is in the Issue queue. No broker request has been sent.'
                        elif symbol in r._analytics_dirty:row.update(state='WAITING',reason='Waiting for current owner evaluation')
                    else:row.update(state='WAITING',reason='Waiting for current source / projection evaluation')
                output.append(row)
        return output

    def current(self,identity,revision):
        r=self.r;raw=r.database.get('strategy_opportunity',identity)
        if not raw or raw['revision']!=revision:raise ValueError('Current strategy opportunity revision required')
        authority=r.market.authority(raw['symbol'])
        if not authority or (r.market.scope_id,authority['source_epoch'])!=(raw['scope_id'],raw['source_epoch']):raise ValueError('Strategy signal source is no longer current')
        lane=self.lane(raw['scope_id'],raw['source_epoch'],raw['symbol'],raw['timeframe'],raw['strategy_id'])
        if r.database.get('strategy_signal_current',lane)!=raw:raise ValueError('Strategy signal superseded by a new source observation')
        gates=self.eligibility(raw);failed=[k for k,v in gates.items() if v is not True]
        if failed:raise ValueError('Strategy signal blocked: '+', '.join(failed))
        return raw

    @staticmethod
    def signal_id(raw):
        return digest([raw['scope_id'],raw['source_epoch'],raw['setup_id'],raw['strategy_id']])

    def bind(self,*,candidate_id,candidate_revision,variant_id,units,expected_version,user_initiated):
        if user_initiated is not True:raise ValueError('Explicit human selection required')
        if variant_id!='native-stop':raise ValueError('Explicit native-stop research variant required')
        r=self.r;raw=self.current(candidate_id,candidate_revision)
        # Stable per-method setup prevents a quote/observation revision from
        # creating an independent order. Existing reservation remains in core.
        identity=self.signal_id(raw)
        previous=r.signals.get(identity)
        if (previous or {}).get('revision',0)!=expected_version:raise StateConflict('Bound signal version conflict')
        spec=r.market.spec(r.accounts.current.account_id,raw['symbol'])
        if spec is None:raise ValueError('Native symbol contract required')
        spec.validate_order(D(raw['entry']),D(units))
        candidate=Candidate(identity,raw['setup_id'],expected_version+1,raw['symbol'],raw['side'],D(raw['entry']),D(raw['stop']),D(units),
            raw['expires_at'],raw['available_at'],raw['source_epoch'],Origin(raw['origin']),scope_id=raw['scope_id'],
            market_candidate_id=candidate_id,market_candidate_revision=candidate_revision,source_candidate_hash=digest(raw),variant_id=variant_id)
        return r.signals.propose(candidate)

    def validate(self,signal):
        raw=self.current(signal['market_candidate_id'],signal['market_candidate_revision'])
        if (digest(raw)!=signal['source_candidate_hash'] or raw['setup_id']!=signal['setup_id'] or raw['symbol']!=signal['symbol']
            or raw['side']!=signal['side'] or D(raw['entry'])!=D(signal['entry_price']) or D(raw['stop'])!=D(signal['invalidation_price'])
            or raw['expires_at']!=signal['expires_at'] or signal['variant_id']!='native-stop'):
            raise ValueError('Bound strategy signal lineage or geometry changed')
