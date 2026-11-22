"""Dependency-ordered, source-keyed scanner execution; unsupported methods stay unavailable."""
from __future__ import annotations
from dataclasses import dataclass
from graphlib import TopologicalSorter
from importlib.resources import files
from decimal import Decimal
import json
import hashlib
from typing import Callable,Any

from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import record,instant


@dataclass(frozen=True)
class Computation:
    state:str
    value:Any=None
    reason:str=''


@dataclass(frozen=True)
class NodeResult:
    node_id:str
    state:str
    fingerprint:str
    output:Any=None
    reason:str=''


class ScannerScheduler:
    """Only registered implementations execute; bounded cache and explicit partial-input collectors."""
    def __init__(self,capacity=2048):
        from collections import OrderedDict
        raw=json.loads(files('sfm_fx_new_age.contracts.data').joinpath('scanner_component_dag_44.json').read_text())
        self.nodes={n['id']:n for n in raw['items']}
        self.order=tuple(TopologicalSorter({k:n['depends_on'] for k,n in self.nodes.items()}).static_order())
        self.handlers={};self.selectors={};self.partial=set();self.cache=OrderedDict();self.capacity=capacity;self.runs={};self.errors=[]

    def register(self,node_id:str,handler:Callable,*,partial_inputs=False,selector=None):
        if node_id not in self.nodes or node_id in self.handlers:raise ValueError('Known uniquely-owned scanner node required')
        self.handlers[node_id]=handler
        if selector:self.selectors[node_id]=selector
        if partial_inputs:self.partial.add(node_id)

    def execute(self,scope_key:str,inputs:dict,*,enabled=True,node_enabled=None)->dict[str,NodeResult]:
        results={}
        common_inputs={k:v for k,v in inputs.items() if not k.startswith('_')}
        prefix=None
        for key in self.order:
            deps={d:results[d] for d in self.nodes[key]['depends_on']}
            selected_inputs=common_inputs
            selected_deps={d:r.fingerprint for d,r in deps.items()}
            if key in self.selectors:selected_inputs,selected_deps=self.selectors[key](inputs,deps)
            if key in self.selectors:
                fingerprint=digest([scope_key,selected_inputs,key,selected_deps])
            else:
                # Reuse canonical bytes, not a digest-of-digests: the resulting
                # SHA is byte-for-byte identical to the original four-item JSON.
                if prefix is None:
                    wire=json.dumps([scope_key,common_inputs],sort_keys=True,separators=(',', ':'),allow_nan=False,default=str)
                    prefix=hashlib.sha256((wire[:-1]+',').encode())
                hashed=prefix.copy()
                hashed.update(json.dumps([key,selected_deps],sort_keys=True,separators=(',', ':'),allow_nan=False,default=str)[1:].encode())
                fingerprint=hashed.hexdigest()
            cache_key=(key,fingerprint)
            if not enabled or node_enabled is not None and not node_enabled.get(key,True):
                results[key]=NodeResult(key,'DISABLED',fingerprint,reason='Analysis consumer disabled');continue
            if key not in self.handlers:
                results[key]=NodeResult(key,'UNAVAILABLE',fingerprint,reason='No registered source-attested implementation/data capability');continue
            failed=[d for d,r in deps.items() if r.state not in {'READY','DEGRADED'}]
            if failed and key not in self.partial:
                results[key]=NodeResult(key,'BLOCKED',fingerprint,reason='Required upstream unavailable: '+','.join(failed));continue
            if cache_key in self.cache:
                results[key]=self.cache[cache_key];self.cache.move_to_end(cache_key);continue
            try:
                output=self.handlers[key](inputs,deps)
                if isinstance(output,Computation):
                    result=NodeResult(key,output.state,fingerprint,output.value,output.reason)
                else:
                    state='NO_DATA' if output is None else 'DEGRADED' if failed else 'READY'
                    result=NodeResult(key,state,fingerprint,output,'Partial available inputs: '+','.join(failed) if failed else '')
                self.runs[key]=self.runs.get(key,0)+1
            except Exception as exc:
                result=NodeResult(key,'ERROR',fingerprint,reason=type(exc).__name__)
                self.errors=(self.errors+[{'node_id':key,'error_type':type(exc).__name__}])[-100:]
            self.cache[cache_key]=result;results[key]=result
            while len(self.cache)>self.capacity:self.cache.popitem(last=False)
        return results


def primitives(bars:list[dict])->dict|None:
    if not bars:return None
    bar=bars[-1];o,h,l,c=(Decimal(bar[k]) for k in ('open','high','low','close'))
    body=abs(c-o);span=h-l
    return {'bar_id':digest(bar),'body':str(body),'range':str(span),'upper_wick':str(h-max(o,c)),
            'lower_wick':str(min(o,c)-l),'direction':'UP' if c>o else 'DOWN' if c<o else 'FLAT',
            'body_fraction':str(body/span) if span else '0','available_at':bar['available_at']}


def confirmed_swings(bars:list[dict],left=2,right=2)->list[dict]:
    """Explicit research fractal profile, confirmation available only after right-hand completed bars."""
    if type(left) is not int or type(right) is not int or not 1<=min(left,right)<=max(left,right)<=20:raise ValueError('Bounded explicit pivot profile required')
    swings=[]
    for i in range(left,len(bars)-right):
        pivot=bars[i];window=bars[i-left:i+right+1]
        hi,lo=Decimal(pivot['high']),Decimal(pivot['low'])
        for kind,value,field,test in [('HIGH',hi,'high',max),('LOW',lo,'low',min)]:
            prices=[Decimal(b[field]) for b in window]
            if value==test(prices) and prices.count(value)==1:
                swings.append({'id':digest([pivot,kind,left,right]),'kind':kind,'price':str(value),
                    'pivot_time':pivot['open_time'],'available_at':bars[i+right]['available_at'],
                    'state':'CONFIRMED','method':'RESEARCH_FRACTAL_V1','left':left,'right':right})
    return swings


class AnalyticsService:
    """One market-data computation owner, invoked by core pump/bar events, never by tab rendering."""
    def __init__(self,db,market,consumers,emit,clock):
        self.db,self.market,self.consumers,self.emit,self.clock=db,market,consumers,emit,clock
        self.activity_alternatives=False
        self.scheduler=ScannerScheduler();self.latest={}
        self.producer_metadata={};self.composers={};self.recipe_status={}
        self.research:Any=None
        from .public_projections import PublicProjectionService
        self.projections=PublicProjectionService(db,market,consumers,lambda:self.clock())
        from .supplemental import SupplementalEvidenceStore
        self.supplemental=SupplementalEvidenceStore(db,market,lambda:self.clock(),emit)
        s=self.scheduler
        s.register('CTRADER_SOURCE',lambda i,d:i['authority'])
        s.register('INGRESS_NORMALIZER',lambda i,d: {'origin':i['authority']['origin'],'source_epoch':i['authority']['source_epoch']},partial_inputs=True)
        s.register('SYMBOL_SESSION_REGISTRY',lambda i,d:i.get('spec'))
        s.register('AVAILABILITY_WATERMARK',lambda i,d:{'as_of':i['cutoff']})
        s.register('BAR_TIMELINE',lambda i,d:i['bars'],partial_inputs=True)
        s.register('FEATURE_CACHE',lambda i,d:{frame:primitives(rows) for frame,rows in i['bars'].items()})
        s.register('OHLC_GEOM',lambda i,d:d['FEATURE_CACHE'].output)
        s.register('LIVE_PREV_BODY',lambda i,d:{f:{'completed_current':primitives(rows),'previous':primitives(rows[:-1]),'forming':'NOT_OBSERVED'} for f,rows in i['bars'].items()})
        s.register('RANGE_VOL',lambda i,d:{'w1_atr14':i['atr'],'status':'READY' if i['atr'] is not None else 'WARMUP'})
        s.register('EXTREME',lambda i,d:{f:None if not rows else {'high':str(max(Decimal(r['high']) for r in rows)),
            'low':str(min(Decimal(r['low']) for r in rows)),'bars':len(rows),'method':'OBSERVED_HISTORY_EXTREMA_V1'} for f,rows in i['bars'].items()})
        s.register('SWING_MAP',lambda i,d:{f:confirmed_swings(rows,i['pivot_left'],i['pivot_right']) for f,rows in i['bars'].items()})
        s.register('FVG_IMBALANCE',self._fvg)

    @staticmethod
    def _fvg(inputs,deps):
        result={}
        for frame,bars in inputs['bars'].items():
            zones=[]
            for a,mid,c in zip(bars,bars[1:],bars[2:]):
                high_a,low_a,high_c,low_c=map(Decimal,(a['high'],a['low'],c['high'],c['low']))
                if high_a<low_c:side,low,high='BUY',high_a,low_c
                elif high_c<low_a:side,low,high='SELL',high_c,low_a
                else:continue
                later=[b for b in bars if instant(b['available_at'])>instant(c['available_at'])]
                state='INVALIDATED' if any(Decimal(b['close'])<low if side=='BUY' else Decimal(b['close'])>high for b in later) else 'TOUCHED' if any(Decimal(b['low'])<=high and Decimal(b['high'])>=low for b in later) else 'CONFIRMED'
                zones.append({'id':digest([a,mid,c,side]),'side':side,'low':str(low),'high':str(high),'state':state,
                              'available_at':c['available_at'],'method':'THREE_COMPLETED_BAR_GAP_RESEARCH_V1'})
            result[frame]=zones
        return result

    def refresh(self,symbol):
        authority=self.market.authority(symbol)
        if not authority:return None
        cutoff=self.clock();epoch=authority['source_epoch']
        bars={f:[record(b) for b in self.market.bars(symbol,f,cutoff,epoch)] for f in ('W1','D1','H4','H1')}
        weekly=tuple(self.market.bars(symbol,'W1',cutoff,epoch));atr=self.market.completed_atr(weekly)
        # Fingerprint uses data availability, not the continuously advancing wall clock.
        available=max((r['available_at'] for rows in bars.values() for r in rows),key=instant,default=cutoff)
        account=self.market.account();spec=self.market.spec(account.account_id,symbol) if account else None
        parameters={p['key']:p for p in self.db.list('parameter')}
        parameters.update({p['key']:p for p in self.market.scoped_rows('pair_parameter') if p['symbol']==symbol})
        left=parameters.get('scanner.pivot_left',{}).get('value',2)
        right=parameters.get('scanner.pivot_right',{}).get('value',2)
        inputs={'authority':authority,'bars':bars,'cutoff':available,'spec':record(spec) if spec else None,
                'pivot_left':left,'pivot_right':right,
                'scope_id':self.market.scope_id,'symbol':symbol,'_evaluation_at':cutoff,
                'parameters':[parameters[k] for k in sorted(parameters)],'producer_metadata':self.producer_metadata,
                'atr':None if atr is None else str(atr),'profile':'EXPLICIT_RESEARCH_PRIMITIVES_V1'}
        inputs['profile_hash']=digest([inputs['parameters'],inputs['profile'],self.producer_metadata])
        optional_evidence=self.supplemental.snapshot(symbol,cutoff)
        quote=self.market.quote(account.account_id,symbol) if account else None
        quote_age=parameters.get('feed.quote_max_age_seconds',{}).get('value',30)
        q=record(quote) if quote else None
        times=[q.get('bid_at') or q['available_at'],q.get('ask_at') or q['available_at']] if q else []
        quote_usable=bool(q and q['source_epoch']==epoch and all(0<=(instant(cutoff)-instant(t)).total_seconds()<=float(quote_age) for t in times) and Decimal(q['bid'])<=Decimal(q['ask']))
        switches={key.removeprefix('analysis.node.'):state['enabled'] for key,state in self.consumers.owners.items() if key.startswith('analysis.node.')}
        for node,metadata in self.producer_metadata.items():
            if recipe_id:=metadata.get('enabled_by_recipe'):
                recipe=self.composers.get(recipe_id)
                state=self.db.get('recipe_state',recipe_id) or {}
                switches[node]=bool(switches.get(node,True) and recipe and state.get('enabled') and state.get('version')==recipe[0].version)
        key=digest([self.market.scope_id,epoch,symbol]);results=self.scheduler.execute(key,inputs,enabled=self.consumers.enabled('analysis.scanner'),node_enabled=switches)
        if self.consumers.enabled('analysis.scanner'):
            self.projections.refresh(dict(inputs,optional_evidence=optional_evidence,quote=q,quote_usable=quote_usable,quote_max_age_seconds=quote_age,
                activity_alternatives=getattr(self,'activity_alternatives',False)),results)
            self._compose(inputs,results)
        rows=[{'id':r.node_id,'status':r.state,'reason':r.reason,'runs':self.scheduler.runs.get(r.node_id,0),'fingerprint':r.fingerprint} for r in results.values()]
        body={'scope_id':self.market.scope_id,'source_epoch':epoch,'symbol':symbol,'as_of':available,'profile_hash':inputs['profile_hash'],
              'classification':'RESEARCH_UNCALIBRATED','nodes':rows,
              'outputs':{k:r.output for k,r in results.items() if r.output is not None},
              'd1_campaign_status':'RESEARCH_PROFILE_ONLY' if 'SMC_STRUCTURE' in self.producer_metadata else 'POLICY_NOT_CONFIGURED',
              'h4_qualification_status':'RESEARCH_EVALUATED' if any(v.get('state')=='EVALUATED' and v.get('candidate_hashes') for k,v in self.recipe_status.items()
                  if json.loads(k)[:2]==[self.market.scope_id,epoch] and json.loads(k)[3]==symbol) else 'NO_CURRENT_QUALIFIED_RESEARCH_OUTPUT',
              'production_calibration':'UNCONFIGURED_OOS_NOT_ACCEPTED'}
        self.latest[key]=body
        self.db.put('analytics_snapshot',key,body)
        return body

    def _compose(self,inputs,results):
        from sfm_fx_new_age.contracts.analytics import MarketCandidate
        from sfm_fx_new_age.contracts.models import freeze

        account=self.market.account()
        quote=self.market.quote(account.account_id,inputs['symbol']) if account else None
        execution_context={'quote':record(quote) if quote else None,
            'quote_max_age_seconds':(self.db.get('parameter','feed.quote_max_age_seconds') or {}).get('value',30),
            'stream_gap':self.db.get('stream_gap',json.dumps([inputs['scope_id'],inputs['symbol'],inputs['authority']['source_epoch']]))}
        composition_snapshot=None;dependency_snapshots={}
        for identity,(recipe,composer) in self.composers.items():
            status_key=json.dumps([inputs['scope_id'],inputs['authority']['source_epoch'],identity,inputs['symbol']])
            configured=self.db.get('recipe_state',identity)
            if not configured or not configured['enabled'] or configured['version']!=recipe.version:
                self.recipe_status[status_key]={'state':'DISABLED'};continue
            missing=[key for key in recipe.required_nodes if results[key].state not in {'READY','DEGRADED'}]
            if missing:self.recipe_status[status_key]={'state':'BLOCKED','required_unavailable':missing};continue
            fingerprint=digest([inputs['scope_id'],inputs['authority']['source_epoch'],inputs['profile_hash'],recipe,
                                {key:results[key].fingerprint for key in recipe.required_nodes},execution_context,
                                int(instant(inputs['_evaluation_at']).timestamp())//30])
            previous=self.recipe_status.get(status_key,{})
            if previous.get('state')=='EVALUATED' and previous.get('fingerprint')==fingerprint:continue
            try:
                if composition_snapshot is None:
                    composition_inputs=dict(inputs,**execution_context,prior_candidates=self.research.query('market_candidate',scope=inputs['scope_id'],
                        epoch=inputs['authority']['source_epoch'],symbol=inputs['symbol'],as_of=inputs['_evaluation_at']),
                        analytical_objects={kind:self.research.query(kind,scope=inputs['scope_id'],
                        epoch=inputs['authority']['source_epoch'],symbol=inputs['symbol'],as_of=inputs['_evaluation_at']) for kind in ('level','evidence','overlay')})
                    composition_snapshot=freeze(composition_inputs)
                dependency_key=tuple(recipe.required_nodes)
                if dependency_key not in dependency_snapshots:
                    dependency_snapshots[dependency_key]=freeze({key:record(results[key]) for key in recipe.required_nodes})
                candidates=composer(composition_snapshot,dependency_snapshots[dependency_key])
                if type(candidates) is not tuple or len(candidates)>1000:raise ValueError('Bounded typed candidate tuple required')
                for candidate in candidates:
                    if type(candidate) is not MarketCandidate or (candidate.recipe_id,candidate.recipe_version)!=(recipe.recipe_id,recipe.version):raise ValueError('Recipe identity mismatch')
                    if (candidate.lineage.source_scope,candidate.lineage.source_epoch,candidate.lineage.symbol)!=(inputs['scope_id'],inputs['authority']['source_epoch'],inputs['symbol']):raise ValueError('Recipe source mismatch')
                    if instant(candidate.lineage.available_at)>instant(inputs['_evaluation_at']):raise ValueError('Future candidate output')
                    if candidate.lineage.profile_hash!=inputs['profile_hash']:raise ValueError('Candidate parameter provenance mismatch')
                self.research.publish_many(candidates)
                # A real publication changes the next composer's prior objects;
                # no-output display recipes share the exact immutable snapshot.
                if candidates:composition_snapshot=None
                self.recipe_status[status_key]={'state':'EVALUATED','fingerprint':fingerprint,'profile_hash':inputs['profile_hash'],
                    'candidate_hashes':{candidate.candidate_id:digest(record(candidate)) for candidate in candidates}}
            except Exception as exc:
                self.recipe_status[status_key]={'state':'ERROR','reason':type(exc).__name__}

    def snapshot(self,symbol):
        authority=self.market.authority(symbol)
        if not authority:return None
        key=digest([self.market.scope_id,authority['source_epoch'],symbol])
        return self.latest.get(key) or self.db.get('analytics_snapshot',key)
