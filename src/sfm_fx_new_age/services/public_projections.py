"""Core-owned source-scoped, cached projection execution and immutable snapshots."""
from __future__ import annotations

import json,math
from typing import Any,Callable
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import FRAMES,instant,record
from sfm_fx_new_age.contracts.models import freeze,thaw
from datetime import timedelta
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable,optional_projection_source


class PublicProjectionService:
    def __init__(self,db,market,consumers,clock):
        self.db,self.market,self.consumers,self.clock=db,market,consumers,clock
        self.methods={};self.runs={};self.feature_builds=0
        self.pool=None;self.capacity=None;self.generations={};self.pending_methods={};self.discarded_compute=0
        self.signal_sink:Callable|None=None  # Core owner callback; never crosses process boundary.
    def register(self,definition,handler,feature_factory):
        if definition.key in self.methods:raise ValueError('Projection owner already registered')
        self.methods[definition.key]=(definition,handler,feature_factory)
    def enabled(self,method):
        state=self.db.get('recipe_state',method.recipe_id) or {}
        return state.get('enabled') is True and state.get('version')==method.version
    def enabled_states(self):
        states=self.db.get_many('recipe_state',[m.recipe_id for m,_,_ in self.methods.values()])
        return {m.key:(states.get(m.recipe_id,{}).get('enabled') is True
                       and states.get(m.recipe_id,{}).get('version')==m.version)
                for m,_,_ in self.methods.values()}
    @staticmethod
    def key(scope,epoch,symbol,frame,method):return digest([scope,epoch,symbol,frame,method])
    @staticmethod
    def input_context(definition,inputs):
        now=instant(inputs['_evaluation_at']);kind=definition.data_kind
        if kind=='LIVE_QUOTE':
            q=inputs.get('quote');extra={'quote':q,'usable':inputs.get('quote_usable'),'quote_max_age_seconds':inputs.get('quote_max_age_seconds',30)}
            until=min(instant(q.get(k) or q['available_at']) for k in ('bid_at','ask_at'))+timedelta(seconds=float(extra['quote_max_age_seconds'])) if q else None
        elif kind:
            source=optional_projection_source(definition.key,kind,inputs.get('optional_evidence',{}),inputs.get('frame'));extra={'source':source};until=instant(source['valid_until']) if source else None
            from sfm_fx_new_age.tabs.tab3.public_activity_alternatives import ACTIVITY_NAMES,alternative_kind
            if definition.key in ACTIVITY_NAMES and inputs.get('activity_alternatives') is True:
                extra['activity_alternatives']=True
                if source is None:
                    source=inputs.get('optional_evidence',{}).get(alternative_kind(definition.key))
                    extra['alternative_source']=source
                    until=instant(source['valid_until']) if source else None
            if definition.key=='cause_effect' and source is None:
                extra['automatic_profile']='PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1'
            if source and until is not None and source['kind'] in {'VENUE_BOOK','VENUE_L2_CHECKSUM_BOOK','VENUE_NATIVE_CHAIN_BOOK'}:
                field='available_at' if source['kind']=='VENUE_L2_CHECKSUM_BOOK' else 'time'
                until=min(until,instant(source['records'][-1][field])+timedelta(seconds=5))
            if source and until is not None and source['kind']=='BROKER_DEPTH':
                until=min(until,instant(source['records'][-1]['time'])+timedelta(seconds=15))
            if source and kind=='OFFICIAL_CALENDAR':
                boundaries=[instant(source['parameters']['schedule_coverage_end'])] if 'schedule_coverage_end' in source['parameters'] else []
                boundaries.extend(instant(r['scheduled_at'])+timedelta(seconds=d) for r in source['records'] for d in (-1800,1800) if instant(r['scheduled_at'])+timedelta(seconds=d)>now)
                if boundaries and until is not None:until=min([until,*boundaries])
            if until is not None:extra['within_validity']=now<=until
        else:return {},None
        if until is not None:extra['valid_until']=until.isoformat().replace('+00:00','Z')
        return extra,extra.get('valid_until')
    def refresh(self,inputs,results):
        if not self.consumers.enabled('analysis.scanner'):return
        enabled=self.enabled_states()
        selected=[entry for entry in self.methods.values() if enabled[entry[0].key]]
        if not selected:return
        keys={(m.key,frame):self.key(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol'],frame,m.key)
              for m,_,_ in selected for frame in FRAMES}
        current=self.db.get_many('projection_current',list(keys.values()))
        features={};parallel_frames={frame:[] for frame in FRAMES}
        immutable_inputs={}
        deps={k:{'state':v.state,'output':v.output} for k,v in results.items() if k in {'SWING_MAP','SMC_STRUCTURE','ORDER_BLOCK'}}
        immutable_deps=freeze(deps)
        # Hash each immutable source frame once, not once per strategy. The full
        # supporting frame and the bounded own-frame slice remain separate inputs.
        # This preserves exact cache invalidation without serializing identical
        # native price rows hundreds of times during one pair refresh.
        frame_rows={frame:list(inputs['bars'][frame])[-2048:] for frame in FRAMES}
        own_hashes={frame:digest(frame_rows[frame]) for frame in FRAMES}
        support_hashes={frame:digest(inputs['bars'][frame]) for frame in FRAMES}
        signal_inputs=dict(inputs,_signal_input_hash=digest(support_hashes))
        frame_deps={frame:{k:dict(v,output=(v['output'] or {}).get(frame,()) if k=='SWING_MAP' else v['output'])
                           for k,v in deps.items()} for frame in FRAMES}
        for definition,handler,factory in selected:
            contexts={}
            for frame in FRAMES:
                context_frame='W1' if frame=='W1' and definition.key in {'volume_displacement','effort_result'} and inputs.get('optional_evidence',{}).get('EXECUTED_WEEK_QUANTITIES') else ''
                if context_frame not in contexts:
                    extra,until=self.input_context(definition,dict(inputs,frame=context_frame))
                    contexts[context_frame]=(digest(extra),until)
                extra_hash,valid_until=contexts[context_frame]
                rows=frame_rows[frame]
                relevant=frame_deps[frame]
                # Level metadata methods explicitly depend on D1/W1, all other methods on their own frame.
                frames=definition.input_frames or (('D1','W1') if definition.key in {'previous_extremes','open_midpoint'} else ())
                support_deps={key:relevant.get(key) for key in definition.required_nodes}
                fingerprint=digest([inputs['scope_id'],inputs['authority'],inputs['symbol'],frame,own_hashes[frame],{f:support_hashes[f] for f in frames},support_deps,inputs['profile_hash'],definition,extra_hash])
                key=keys[(definition.key,frame)]
                old=current.get(key)
                if old and old['fingerprint']==fingerprint:
                    if self.signal_sink:self.signal_sink(old,dict(signal_inputs,frame=frame),deps)
                    continue

                body:dict[str,Any]=dict(strategy_id=definition.key,recipe_id=definition.recipe_id,version=definition.version,name=definition.name,
                    scope_id=inputs['scope_id'],source_epoch=inputs['authority']['source_epoch'],symbol=inputs['symbol'],timeframe=frame,
                    origin=inputs['authority']['origin'],method_version=definition.method_version,profile_hash=inputs['profile_hash'],definition_hash=definition.profile_hash,
                    fingerprint=fingerprint,available_at=inputs['_evaluation_at'],classification='UNCALIBRATED_PROJECTION_ONLY',state='WARMUP',
                    bars_used=len(rows),warmup=definition.warmup,series=[],zones=[],markers=[],metrics={},reason='More closed bars required')
                if valid_until is not None:
                    body['valid_until']=valid_until
                    if definition.data_kind=='OFFICIAL_CALENDAR':body['valid_until_exclusive']=True
                unavailable=[key for key in definition.required_nodes if key not in results or results[key].state not in {'READY','DEGRADED'}]
                if len(rows)>=definition.warmup and unavailable:
                    body.update(state='UNAVAILABLE',reason='Required analytical owner not ready: '+', '.join(unavailable))
                elif len(rows)>=definition.warmup:
                    if self.pool and self._builtin(self.methods[definition.key]):
                        parallel_frames[frame].append(body)
                        continue
                    try:
                        feature_key=(frame,factory)
                        if feature_key not in features:
                            features[feature_key]=factory(rows,relevant.get('SWING_MAP',{}).get('output') or ());self.feature_builds+=1
                        # Pure profile handlers share one deeply immutable input
                        # per frame; repeatedly freezing the same original tick
                        # history for every profile needlessly blocks feed/UI work.
                        if frame not in immutable_inputs:immutable_inputs[frame]=freeze(dict(inputs,frame=frame))
                        output=handler(features[feature_key],immutable_inputs[frame],immutable_deps)
                        if not isinstance(output,dict) or set(output)!={'series','zones','markers','metrics'}:
                            raise ValueError('Only bounded analytical geometry fields permitted')
                        body.update(output);self._validate(body,inputs['_evaluation_at'])
                        if body['metrics'].get('alternative'):
                            body['name']=body['metrics']['interpretation_name']
                            body['classification']='EXPLICIT_ACTIVITY_ALTERNATIVE_NOT_GENUINE_EXECUTION_FLOW'
                        elif body['metrics'].get('genuine_displayed_depth'):
                            body['name']=body['metrics']['interpretation_name']
                            body['classification']='BROKER_SCOPED_DISPLAYED_DEPTH_NOT_EXECUTED_VOLUME'
                        has_output=any(body[k] for k in ('series','zones','markers'))
                        if definition.key=='order_block':
                            node=results.get('ORDER_BLOCK');ready=node and node.state=='READY'
                            found=bool(ready and node.output and node.output.get('frames',{}).get(frame))
                            body['state']='READY' if found else 'NO_SETUP' if ready else 'WARMUP';body['reason']='Typed ORDER_BLOCK levels use the existing causal projection owner' if ready else 'Waiting for structure / displacement prerequisites'
                        else:body.update(state='READY' if has_output else 'NO_SETUP',reason='' if has_output else 'Evaluated; no qualifying closed-bar pattern')
                    except ProjectionInputUnavailable as exc:
                        body.update(state=exc.state,reason=exc.reason,series=[],zones=[],markers=[],metrics={})
                    except (ValueError,KeyError,TypeError,ArithmeticError) as exc:
                        body.update(state='ERROR',reason=type(exc).__name__,series=[],zones=[],markers=[],metrics={})
                    self.runs[definition.key]=self.runs.get(definition.key,0)+1
                # Snapshots commit before the mutable current pointer; prior revisions stay available.
                revision_key=digest([key,fingerprint]);stored=self.db.get('strategy_projection',revision_key)
                if stored:
                    # Returning to identical inputs reuses the recorded revision, not a new observation time.
                    body['available_at']=stored['available_at']
                    if stored!=body:raise ValueError('Immutable public projection collision')
                if not stored:self.db.put('strategy_projection',revision_key,body)
                self.db.put('projection_current',key,body)
                if self.signal_sink:self.signal_sink(body,dict(signal_inputs,frame=frame),deps)
        if self.pool:
            nodes={k:{'state':r.state,'output':r.output} for k,r in results.items()}
            for frame,entries in parallel_frames.items():
                lane=(inputs['symbol'],frame)
                if not entries:
                    self.pool.cancel(lane);self.pending_methods.pop(lane,None);continue
                self.pending_methods[lane]={b['strategy_id'] for b in entries}
                job=dict(entries=entries,inputs=dict(signal_inputs,frame=frame),deps=deps,results=nodes,
                    token=digest([[b['fingerprint'] for b in entries],self.generations.get(inputs['symbol'],0)]))
                if len(json.dumps(job,allow_nan=False))>24*1024*1024:raise ValueError('Projection snapshot exceeds process-transfer budget')
                self.pool.offer(lane,job)

    def configure_compute(self,requested):
        from .compute_pool import host_capacity,ProjectionPool
        self.capacity=host_capacity(requested)
        if self.capacity['worker_limit']>1:self.pool=ProjectionPool(self.capacity['worker_limit'])
    @staticmethod
    def _builtin(entry):
        from functools import partial
        from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
        from sfm_fx_new_age.tabs.tab3.public_features import Features
        from sfm_fx_new_age.contracts.public_strategies import BY_KEY
        m,h,f=entry
        return (m.key in BY_KEY and m==BY_KEY[m.key] and f is Features and isinstance(h,partial)
                and h.func is evaluate and h.args==(m.key,) and not h.keywords)
    def invalidate(self,symbol):
        self.generations[symbol]=self.generations.get(symbol,0)+1
        if self.pool:self.pool.invalidate(symbol)
    def poll_compute(self):
        if not self.pool:return 0
        committed=0
        for lane,job,result in self.pool.poll(max_results=1):
            symbol,frame=lane;authority=self.market.authority(symbol)
            if (authority!=job['inputs']['authority'] or self.market.scope_id!=job['inputs']['scope_id']
                or not self.consumers.enabled('analysis.scanner') or not self.consumers.enabled('analysis.pair.'+symbol)):
                self.discarded_compute+=1;continue
            expected={b['strategy_id']:b for b in job['entries']}
            if len(result['bodies'])!=len(expected) or {b['strategy_id'] for b in result['bodies']}!=set(expected):raise ValueError('Incomplete projection worker cohort')
            with self.db.batch_writes():
                for body in result['bodies']:
                    original=expected[body['strategy_id']]
                    if any(body[k]!=original[k] for k in ('fingerprint','scope_id','source_epoch','symbol','timeframe','definition_hash')):raise ValueError('Projection result source identity mismatch')
                    definition=self.methods[body['strategy_id']][0]
                    if not self.enabled(definition):continue
                    if body.get('valid_until') and instant(self.clock())>instant(body['valid_until']):
                        self.discarded_compute+=1;continue
                    self._validate(body,job['inputs']['_evaluation_at'])
                    key=self.key(body['scope_id'],body['source_epoch'],body['symbol'],body['timeframe'],body['strategy_id'])
                    revision_key=digest([key,body['fingerprint']]);stored=self.db.get('strategy_projection',revision_key)
                    if stored:
                        body['available_at']=stored['available_at']
                        if stored!=body:raise ValueError('Immutable public projection collision')
                    else:self.db.put('strategy_projection',revision_key,body)
                    self.db.put('projection_current',key,body);committed+=1
                    if self.signal_sink:self.signal_sink(body,job['inputs'],job['deps'])
            for key,n in result['runs'].items():self.runs[key]=self.runs.get(key,0)+n
            self.feature_builds+=result['feature_builds']
        return committed
    def compute_status(self):
        return dict(mode='SPAWNED_PURE_PROJECTION_PROCESSES' if self.pool else 'SERIAL',capacity=self.capacity,
            discarded_at_commit=self.discarded_compute,pool=self.pool.metrics() if self.pool else None)
    def close(self):
        if self.pool:self.pool.close()
    @staticmethod
    def _validate(body,cutoff):
        if set(body)&{'orders','signals','market_candidates','units'}:raise ValueError('Projection cannot carry execution outputs')
        if len(body['series'])>8 or len(body['zones'])>32 or len(body['markers'])>64:raise ValueError('Projection budget exceeded')
        stamps=[body['available_at']]
        for row in body['zones']:
            low,high=float(row['low']),float(row['high'])
            if not math.isfinite(low) or not math.isfinite(high) or not 0<low<=high:raise ValueError('Invalid projection zone')
            stamps.append(row['available_at'])
        for row in body['markers']:
            value=float(row['price'])
            if not math.isfinite(value) or value<=0 or row['side'] not in {'BUY','SELL','NEUTRAL'}:raise ValueError('Invalid projection marker')
            if instant(row['time'])>instant(cutoff) or instant(row['time'])>instant(row['available_at']):raise ValueError('Future marker time')
            chronology=[instant(stage['time']) for stage in row.get('stages',())]
            if chronology!=sorted(chronology) or any(t>instant(row['available_at']) for t in chronology):raise ValueError('Invalid causal stage order')
            stamps.append(row['available_at'])
        for series in body['series']:
            if len(series['points'])>256:raise ValueError('Series budget exceeded')
            for row in series['points']:
                value=float(row['price'])
                if instant(row['time'])>instant(cutoff):raise ValueError('Future series time')
                if not math.isfinite(value) or value<=0:raise ValueError('Invalid price series')
                stamps.append(row['available_at'])
        if any(instant(s)>instant(cutoff) for s in stamps):raise ValueError('Future projection output')
        body['available_at']=max(stamps,key=instant)
        if len(json.dumps(body,allow_nan=False))>500000:raise ValueError('Projection payload too large')
    def read(self,symbol,frame,*,as_of=None,dirty=False,apply_current_filters=False):
        authority=self.market.authority(symbol)
        if not authority:return []
        scope=self.market.scope_id;epoch=authority['source_epoch'];cutoff=as_of or self.clock();rows=[]
        display_enabled=self.consumers.enabled('analysis.scanner') and self.consumers.enabled('analysis.pair.'+symbol)
        active=display_enabled and not dirty
        enabled=self.enabled_states()
        selected=[m for m,_,_ in self.methods.values()
                  if (as_of is not None or active and enabled[m.key])
                  and (not apply_current_filters or display_enabled and enabled[m.key])]
        if self.pool and as_of is None:
            pending=self.pending_methods.get((symbol,frame),set()) if self.pool.pending((symbol,frame)) else set()
            selected=[m for m in selected if m.key not in pending and not (self.pool.failed and self._builtin(self.methods[m.key]))]
        keys={}
        if as_of is not None:
            history=self.db.projection_history(scope=scope,epoch=epoch,symbol=symbol,timeframe=frame,
                methods=[m.key for m in selected],cutoff=cutoff)
            current={}
        else:
            history={}
            keys={m.key:self.key(scope,epoch,symbol,frame,m.key) for m in selected}
            current=self.db.get_many('projection_current',list(keys.values()))
        for definition in selected:
            # Current display preferences also apply to a historically inspected chart.
            # Audit reads may retain disabled revisions without projecting them.
            if as_of is None:
                row=current.get(keys[definition.key])
                if row and instant(row['available_at'])<=instant(cutoff):rows.append(row)
            else:
                # Already materialized immutable revisions only; no current-only state under an as-of label.
                row=history.get(definition.key)
                if row:rows.append(row)
        # Read-time withdrawal closes the gap before the next scheduled refresh.
        # It does not mutate the immutable observed revision or invent a new one.
        return [dict(row,state='DATA_UNAVAILABLE',reason='Source or time-sensitive projection validity elapsed; awaiting fresh evaluation',series=[],zones=[],markers=[],metrics={},display_validity='EXPIRED_AT_REQUEST_CUTOFF')
                if row.get('valid_until') and (instant(cutoff)>=instant(row['valid_until']) if row.get('valid_until_exclusive') else instant(cutoff)>instant(row['valid_until'])) and row['state'] in {'READY','NO_SETUP'} else row for row in rows]
    def catalogue(self,symbol,frame='H4',*,dirty=False):
        current={r['strategy_id']:r for r in self.read(symbol,frame,dirty=dirty)}
        enabled=self.enabled_states()
        return [dict(record(m),recipe_id=m.recipe_id,method_version=m.method_version,definition_hash=m.profile_hash,required_nodes=list(m.required_nodes),
             enabled=enabled[m.key],evaluation={k:v for k,v in current.get(m.key,{}).items() if k in {'state','reason','bars_used','warmup','metrics','available_at','fingerprint'}},
             scope_id=self.market.scope_id,symbol=symbol,timeframe=frame) for m,_,_ in self.methods.values()]
