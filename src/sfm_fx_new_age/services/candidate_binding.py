"""Core-owned, human-only research→signal binding; this service never sends broker commands."""
from decimal import Decimal
import json
from typing import Any

from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import Candidate,Origin,instant,PAIRS
from sfm_fx_new_age.storage.database import StateConflict


class CandidateBindingService:
    def __init__(self,market,research,signals,accounts,analytics,consumers,clock,pending):
        self.market,self.research,self.signals,self.accounts=market,research,signals,accounts
        self.analytics,self.consumers,self.clock,self.pending=analytics,consumers,clock,pending
        self.strategy_signals:Any=None

    def _current(self,identity,revision,variant_id):
        account=self.accounts.current
        if not account or not account.authenticated or account.origin is Origin.HISTORICAL_REPLAY:raise ValueError('Authenticated non-replay selected account required')
        now=self.clock();found=[]
        for symbol in PAIRS:
            authority=self.market.authority(symbol)
            if not authority:continue
            rows=self.research.query('market_candidate',scope=account.scope_id,epoch=authority['source_epoch'],symbol=symbol,as_of=now,limit=5000)
            found.extend(row for row in rows if row['candidate_id']==identity)
        if len(found)!=1 or found[0]['revision']!=revision:raise ValueError('Current uniquely scoped candidate revision required')
        row=found[0];line=row['lineage'];symbol=line['symbol'];epoch=line['source_epoch']
        if line['origin']!=account.origin.value or instant(row['expires_at'])<=instant(now):raise ValueError('Candidate origin/expiry mismatch')
        if row['blockers'] or row['confidence'] is None or row['quality'] is None:raise ValueError('Research qualification is incomplete')
        gates=dict(row.get('gates',[]))
        if set(gates)!={f'QG{i:02d}' for i in range(1,15)} or any(value is not True for value in gates.values()):raise ValueError('All 14 explicit qualification gates must pass')
        if self.pending(symbol) or not self.consumers.enabled('analysis.scanner') or not self.consumers.enabled('analysis.pair.'+symbol):raise ValueError('Analytical evaluation is pending or disabled')
        state=self.analytics.db.get('recipe_state',row['recipe_id'])
        key=json.dumps([account.scope_id,epoch,row['recipe_id'],symbol])
        evaluated=self.analytics.recipe_status.get(key,{})
        if (not state or not state['enabled'] or state['version']!=row['recipe_version'] or evaluated.get('state')!='EVALUATED'
            or evaluated.get('candidate_hashes',{}).get(identity)!=digest(row) or evaluated.get('profile_hash')!=line['profile_hash']):raise ValueError('No current enabled recipe evaluation owns this candidate')
        levels=self.research.query('level',scope=account.scope_id,epoch=epoch,symbol=symbol,as_of=now)
        if not any(level['level_id']==row['zone_id'] and level['state'] in {'CONFIRMED','TOUCHED'} for level in levels):raise ValueError('Candidate zone is missing or no longer confirmed')
        evidence={item['evidence_id']:item for item in self.research.query('evidence',scope=account.scope_id,epoch=epoch,symbol=symbol,as_of=now)}
        if any(key not in evidence or not evidence[key]['confirmed'] or instant(evidence[key]['expires_at'])<=instant(now) for key in row['evidence_ids']):raise ValueError('Candidate evidence is missing, provisional or expired')
        variants=[v for v in row['variants'] if v['variant_id']==variant_id]
        if len(variants)!=1 or variants[0]['blockers']:raise ValueError('Qualified unique candidate variant required')
        return row,variants[0]

    def bind(self,*,candidate_id,candidate_revision,variant_id,units,expected_version,user_initiated):
        if candidate_id.startswith('strategy:'):
            return self.strategy_signals.bind(candidate_id=candidate_id,candidate_revision=candidate_revision,variant_id=variant_id,
                units=units,expected_version=expected_version,user_initiated=user_initiated)
        if user_initiated is not True:raise ValueError('Explicit human selection required')
        row,variant=self._current(candidate_id,candidate_revision,variant_id)
        identity=digest([self.market.scope_id,row['lineage']['source_epoch'],candidate_id,variant_id])
        previous=self.signals.get(identity)
        if (previous or {}).get('revision',0)!=expected_version:raise StateConflict('Bound signal version conflict')
        candidate=Candidate(identity,row['setup_id'],expected_version+1,row['lineage']['symbol'],row['side'],Decimal(row['entry']),
            Decimal(variant['stop_price']),Decimal(units),row['expires_at'],row['lineage']['available_at'],row['lineage']['source_epoch'],
            Origin(row['lineage']['origin']),scope_id=self.market.scope_id,market_candidate_id=candidate_id,
            market_candidate_revision=candidate_revision,source_candidate_hash=digest(row),variant_id=variant_id)
        return self.signals.propose(candidate)

    def validate(self,signal):
        if signal['market_candidate_id'].startswith('strategy:'):
            return self.strategy_signals.validate(signal)
        row,variant=self._current(signal['market_candidate_id'],signal['market_candidate_revision'],signal['variant_id'])
        if (digest(row)!=signal['source_candidate_hash'] or row['setup_id']!=signal['setup_id'] or row['side']!=signal['side']
            or row['lineage']['symbol']!=signal['symbol'] or Decimal(row['entry'])!=Decimal(signal['entry_price'])
            or Decimal(variant['stop_price'])!=Decimal(signal['invalidation_price']) or row['expires_at']!=signal['expires_at']):raise ValueError('Bound candidate lineage or geometry changed')
