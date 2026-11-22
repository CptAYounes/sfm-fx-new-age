"""One read-only native-money and research lot-estimation owner.
No portfolio permission or broker protection is inferred from an internal price.
The supplied 45% figure has an unresolved denominator; it is not a trade budget.
"""
from decimal import Decimal as D,ROUND_FLOOR
import json
from sfm_fx_new_age.contracts.domain import decimal,instant,record,PAIRS
from sfm_fx_new_age.storage.database import StateConflict

DEFAULT_POLICY={'classification':'RESEARCH_ONLY','capital_base':'UNCONFIGURED','capital_fraction':'0.45','budget_money':None}


class ResearchMoneyService:
    def __init__(self,runtime):self.r=runtime
    def policy(self):
        account=self.r.accounts.current
        return self.r.database.get('research_money_policy',account.scope_id) if account else None
    def set_policy(self,policy,*,expected_version):
        account=self.r.accounts.current
        if not account:raise ValueError('Selected account scope required for research policy')
        if type(policy) is not dict or set(policy)!=set(DEFAULT_POLICY):raise ValueError('Exact research-only capital policy fields required')
        if policy['classification']!='RESEARCH_ONLY' or policy['capital_base'] not in {'UNCONFIGURED','BALANCE','EQUITY'}:raise ValueError('Research-only explicit base required')
        fraction=decimal(policy['capital_fraction'])
        if not 0<fraction<=1:raise ValueError('Capital fraction must be >0 and <=1')
        if policy['budget_money'] is not None:decimal(policy['budget_money'],positive=True)
        body={'scope_id':account.scope_id,'policy':dict(policy),'version':expected_version+1,'account_currency':account.currency}
        with self.r.database.transaction() as conn:
            old=self.r.database.get('research_money_policy',account.scope_id)
            if (old or {}).get('version',0)!=expected_version:raise StateConflict('Research policy version conflict')
            self.r.database.write(conn,'research_money_policy',account.scope_id,body)
        self.r.emit('CONFIG.VERSION','PORTFOLIO_PRE_ISSUE_VIEW',{'scope_id':account.scope_id,'version':body['version'],'classification':'RESEARCH_ONLY'})
        return body
    def _fresh(self,stamp):
        if not stamp:return False
        age=(instant(self.r.clock())-instant(stamp)).total_seconds()
        return 0<=age<=self.r.catalogues.parameter_value('feed.quote_max_age_seconds')
    def context(self):
        account=self.r.accounts.current;saved=self.policy();policy=(saved or {}).get('policy',DEFAULT_POLICY)
        money=self.r.database.get('account_money_snapshot',account.scope_id) if account else None
        valid=bool(account and account.authenticated and money and money.get('origin')==account.origin.value
            and money.get('account_currency')==account.currency and self._fresh(money.get('observed_at')))
        if valid:
            authorities=[self.r.market.authority(s) for s in PAIRS]
            valid=any(a and a['source_epoch']==money['source_epoch'] for a in authorities)
        position=self.r.positions.snapshot();pending=self.r.database.get('broker_pending_snapshot',account.scope_id) if account else None
        blockers=[]
        if policy['capital_base']=='UNCONFIGURED':blockers.append('CAPITAL_BASE_UNCONFIGURED')
        if not valid:blockers.append('NATIVE_MONEY_MISSING_STALE_OR_WRONG_EPOCH')
        base=(money or {}).get('balance') if policy['capital_base']=='BALANCE' else None
        if policy['capital_base']=='EQUITY':blockers.append('NATIVE_EQUITY_NOT_AVAILABLE')
        return {'status':'UNCONFIGURED' if policy['capital_base']=='UNCONFIGURED' else 'BLOCKED' if blockers else 'RESEARCH_CONTEXT_AVAILABLE',
            'classification':'RESEARCH_ONLY','scope_id':account.scope_id if account else None,
            'account_currency':account.currency if account else None,'policy':dict(policy),'policy_version':(saved or {}).get('version',0),
            'valuation_base':policy['capital_base'],'capital_fraction':policy['capital_fraction'],
            'native_money':money,'native_money_current':valid,'research_fraction_amount':str(D(base)*D(policy['capital_fraction'])) if base is not None and valid else None,
            'approved_amount':None,'account_risk_permission':False,'blockers':blockers,
            'position_inventory_state':'LAST_KNOWN_COMPLETE' if position and position['complete'] else 'INCOMPLETE' if position else 'UNKNOWN',
            'pending_inventory_state':'LAST_KNOWN_COMPLETE' if pending and pending.get('complete') else 'INCOMPLETE' if pending else 'UNKNOWN',
            'exposure_economics':'UNCONFIGURED_NO_NETTING_OR_RECYCLING_ASSUMPTION',
            'disclosure':'Internal invalidation is not broker SL or maximum loss. No margin, gap, slippage, fees or portfolio permission is inferred.'}
    def _conversion(self,source,target,epoch):
        if source==target:return D(1),[]
        graph={};account=self.r.accounts.current
        for spec in self.r.market.scoped_rows('symbol_currency'):
            if spec.get('source_epoch')!=epoch:continue
            q=self.r.market.quote(account.account_id,spec['symbol']);authority=self.r.market.authority(spec['symbol'])
            if not q or q.source_epoch!=epoch or not authority or authority['source_epoch']!=epoch or not self._fresh(q.available_at):continue
            a,b=spec['base_currency'],spec['quote_currency']
            graph.setdefault(a,[]).append((b,q.ask,spec['symbol'],q.available_at))
            graph.setdefault(b,[]).append((a,D(1)/q.bid,spec['symbol'],q.available_at))
        todo=[(source,D(1),[])];seen={source}
        while todo:
            node,rate,path=todo.pop(0)
            for nxt,factor,symbol,stamp in graph.get(node,[]):
                if nxt in seen:continue
                route=path+[{'symbol':symbol,'observed_at':stamp,'rate':str(factor)}]
                if nxt==target:return rate*factor,route
                if len(route)<3:seen.add(nxt);todo.append((nxt,rate*factor,route))
        raise ValueError('Current native currency-conversion path unavailable')
    def estimate(self,*,symbol,entry,invalidation,side,budget_money=None):
        account=self.r.accounts.current;context=self.context()
        result={'status':'BLOCKED','classification':'RESEARCH_ONLY','account_risk_permission':False,
            'broker_protection':False,'symbol':symbol,'suggested_units':None,'blockers':[],
            'disclosure':context['disclosure']}
        try:
            if not account or not account.authenticated:raise ValueError('Authenticated selected account required')
            authority=self.r.market.authority(symbol)
            if not authority:raise ValueError('Current source required')
            if not context['native_money_current'] or context['native_money']['source_epoch']!=authority['source_epoch']:
                raise ValueError('Current native monetary snapshot for the exact symbol epoch required')
            budget=budget_money if budget_money is not None else context['policy']['budget_money']
            if budget is None:raise ValueError('Explicit research money budget unconfigured')
            budget=decimal(budget,positive=True);a,b=decimal(entry,positive=True),decimal(invalidation,positive=True)
            if side not in {'BUY','SELL'} or (b>=a if side=='BUY' else b<=a):raise ValueError('Directional internal invalidation required')
            spec=self.r.market.spec(account.account_id,symbol)
            if not spec or spec.origin!=account.origin:raise ValueError('Matching native symbol specifications required')
            currencies=self.r.market.scoped_rows('symbol_currency')
            currency=next((v for v in currencies if v['symbol']==symbol and v.get('source_epoch')==authority['source_epoch']),None)
            if not currency:raise ValueError('Native symbol currency metadata unavailable')
            rate,path=self._conversion(currency['quote_currency'],account.currency,authority['source_epoch'])
            per_unit=abs(a-b)*rate;raw=budget/per_unit
            if raw<spec.volume_min:raise ValueError('Budget below broker minimum volume at this internal distance')
            units=spec.volume_min+((min(raw,spec.volume_max)-spec.volume_min)/spec.volume_step).to_integral_value(rounding=ROUND_FLOOR)*spec.volume_step
            spec.validate_order(a,units)
            result.update(status='RESEARCH_ESTIMATE',suggested_units=str(units),suggested_lots=str(units/spec.units_per_lot),
                distance_pips=str(abs(a-b)/spec.pip_size),account_currency=account.currency,budget_money=str(budget),
                estimate_at_invalidation=str(per_unit*units),units_per_lot=str(spec.units_per_lot),conversion_path=path,
                conversion_basis='CONSERVATIVE_SNAPSHOT_LOSS_CONVERSION',source_epoch=authority['source_epoch'],
                source_scope=account.scope_id,money_observed_at=context['native_money']['observed_at'])
        except ValueError as exc:result['blockers']=[str(exc)]
        return result

    def estimate_candidate(self,candidate,variant):
        line=candidate['lineage'];symbol=line['symbol']
        key=json.dumps([line['source_scope'],line['source_epoch'],candidate['recipe_id'],symbol])
        from sfm_fx_new_age.contracts.analytics import digest
        status=self.r.analytics.recipe_status.get(key,{})
        state=self.r.database.get('recipe_state',candidate['recipe_id']) or {}
        coherent=bool(state.get('enabled') and status.get('state')=='EVALUATED' and status.get('candidate_hashes',{}).get(candidate['candidate_id'])==digest(candidate)
            and symbol not in self.r._analytics_dirty and self.r.consumers.enabled('analysis.scanner') and self.r.consumers.enabled('analysis.pair.'+symbol))
        estimate=self.estimate(symbol=symbol,entry=candidate['entry'],invalidation=variant['stop_price'],side=candidate['side']) if coherent else {
            'status':'WITHHELD','classification':'RESEARCH_ONLY','suggested_units':None,'account_risk_permission':False,'blockers':['CANDIDATE_NOT_OWNED_BY_CURRENT_ENABLED_RECIPE']}
        return dict(estimate,candidate_id=candidate['candidate_id'],candidate_revision=candidate['revision'],variant_id=variant['variant_id'],
            candidate_qualification='WITHHELD' if candidate['blockers'] or variant['blockers'] else 'RESEARCH_ONLY',
            candidate_blockers=list(candidate['blockers'])+list(variant['blockers']))
