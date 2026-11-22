"""Positive method→policy→Tab4 and explicit binding on labelled fixture inputs."""
from decimal import Decimal as D
from datetime import timedelta
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.testing.fixtures import stamp
import pytest
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.domain import Bar,Quote,Origin
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW
from test_public_strategies import seed,enable,bars,EPOCH
from test_strategy_signal_pipelines import rows


def method_runtime(key,*,targets=False,path=':memory:'):
    from strategy_signal_cases import case,with_observed_target
    from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
    own,supports,data,now=case(key)
    if targets:supports=with_observed_target(own,supports)
    r=seed(path=path,rows=own,frame=own[-1]['timeframe']);r.clock=lambda:now;r.analytics.clock=r.orders.clock=r.continuity.clock=lambda:r.clock()
    for bs in supports.values():
        for b in bs:r.market.ingest(Bar(**b))
    if data:
        data['scope_id']=r.market.scope_id
        r.analytics.supplemental.register_provider(data['provider_id'],kinds=(data['kind'],),origin='SYNTHETIC_FIXTURE')
        r.analytics.supplemental.accept(SupplementalEvidence(**data))
    if key=='previous_body_live':
        r.market.set_quote(Quote(r.accounts.current.account_id,'EURUSD',D('1.1049'),D('1.1051'),now,EPOCH,Origin.SYNTHETIC_FIXTURE))
    enable(r,key)
    return r,own[-1]['timeframe'],now


@pytest.mark.parametrize('method',METHODS,ids=lambda m:m.key)
def test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission(method):
    r,frame,now=method_runtime(method.key,targets=True)
    try:
        before=next(x for x in rows(r,frame) if x['strategy_id']==method.key)
        assert before['opportunity_id'],before
        entry=D(before['entry']);buy=before['side']=='BUY';bid=entry+D('.0006') if buy else entry-D('.0008')
        quote_at=stamp(instant(now)+timedelta(milliseconds=1));r.clock=lambda:quote_at
        r.market.set_quote(Quote(r.accounts.current.account_id,'EURUSD',bid,bid+D('.0002'),quote_at,EPOCH,Origin.SYNTHETIC_FIXTURE));r.pump()
        row=next(x for x in rows(r,frame) if x['strategy_id']==method.key)
        assert row['state']=='SIGNAL' and all(row['gates'].values()),row
        request=dict(candidate_id=row['opportunity_id'],candidate_revision=row['revision'],variant_id='native-stop',units='1000',expected_version=0,user_initiated=True)
        result=r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',request)
        assert result.status.value=='ACCEPTED',result
        assert next(x for x in rows(r,frame) if x['strategy_id']==method.key)['state']=='BOUND'
        signal=r.signals.get(r.strategy_signals.signal_id(row))
        assert signal['market_candidate_id']==row['opportunity_id'] and signal['source_epoch']==EPOCH
        assert r.orders.preview(signal['signal_id'],signal['revision'],acknowledge_research=True)['signal_id']==signal['signal_id']
        assert not r.database.orders() and not r.orders.transport.submissions
    finally:r.close()


@pytest.mark.parametrize('method',METHODS,ids=lambda m:m.key)
def test_each_real_algorithm_positive_trigger_is_materialized_in_tab4(method):
    from strategy_signal_cases import case
    from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
    own,supports,data,now=case(method.key)
    r=seed(rows=own,frame=own[-1]['timeframe'])
    r.clock=r.analytics.clock=lambda:now
    try:
        for bs in supports.values():
            for b in bs:r.market.ingest(Bar(**b))
        if data:
            data['scope_id']=r.market.scope_id
            r.analytics.supplemental.register_provider(data['provider_id'],kinds=(data['kind'],),origin='SYNTHETIC_FIXTURE')
            r.analytics.supplemental.accept(SupplementalEvidence(**data))
        if method.key=='previous_body_live':
            r.market.set_quote(Quote(r.accounts.current.account_id,'EURUSD',D('1.1049'),D('1.1051'),now,EPOCH,Origin.SYNTHETIC_FIXTURE))
        enable(r,method.key)
        found=next(x for x in rows(r,own[-1]['timeframe']) if x['strategy_id']==method.key)
        assert found['opportunity_id'] and found['state'] in {'SIGNAL','BLOCKED','STALE','INVALIDATED','EXPIRED'},found
        assert found['trigger']['root_ids'] and found['policy_id']
        assert D(found['stop'])<D(found['entry']) if found['side']=='BUY' else D(found['stop'])>D(found['entry'])
        assert not r.strategy_signals.errors and not r.router.errors and not r.analytics.scheduler.errors
        assert not r.orders.transport.submissions and not r.database.orders()
    finally:r.close()


def bindable_runtime():
    shape=[(1.1,1.101,1.099,1.1)]*60+[(1.1,1.101,1.09,1.095),(1.094,1.103,1.093,1.102)]
    shape[5]=(1.1,1.14,1.099,1.1)
    r=seed(rows=bars(shape));r.market.set_quote(Quote(r.accounts.current.account_id,'EURUSD',D('1.1031'),D('1.1033'),FIXTURE_NOW,EPOCH,Origin.SYNTHETIC_FIXTURE))
    enable(r,'engulfing');return r


def test_actual_signal_can_be_human_bound_and_previewed_but_never_auto_submitted():
    r=bindable_runtime()
    try:
        row=next(x for x in rows(r) if x['strategy_id']=='engulfing')
        assert row['state']=='SIGNAL',row
        payload=dict(candidate_id=row['opportunity_id'],candidate_revision=1,variant_id='native-stop',units='1000',expected_version=0,user_initiated=True)
        assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',dict(payload,user_initiated=False)).status.value=='REJECTED'
        assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',dict(payload,units='1001')).status.value=='REJECTED'
        result=r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload)
        assert result.status.value=='ACCEPTED',result
        signal=next(s for s in r.signals.all() if s.get('market_candidate_id')==row['opportunity_id'])
        assert signal['state']=='QUEUED' and signal['origin']=='SYNTHETIC_FIXTURE'
        preview=r.orders.preview(signal['signal_id'],signal['revision'],acknowledge_research=True)
        assert preview and not r.database.orders() and not r.orders.transport.submissions
        assert r.api(4).command('4.2','BIND_RESEARCH_CANDIDATE',payload).status.value=='REJECTED'
        enable(r,'engulfing',False)
        with pytest.raises(ValueError):r.orders.preview(signal['signal_id'],signal['revision'],acknowledge_research=True)
        assert not r.orders.transport.submissions
    finally:r.close()
