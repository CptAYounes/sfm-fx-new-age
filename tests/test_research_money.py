"""Money/lot calculations are analytical, scoped, freshness checked and offline."""
from dataclasses import replace
from decimal import Decimal as D
import pytest
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,FIXTURE_EPOCH
from sfm_fx_new_age.contracts.tab_data import DataRequest


def seed_money(r):
    a=r.accounts.current
    r.database.put('account_money_snapshot',a.scope_id,{'scope_id':a.scope_id,'account_currency':a.currency,'balance':'10000.12345678',
        'observed_at':FIXTURE_NOW,'source_epoch':FIXTURE_EPOCH,'origin':'SYNTHETIC_FIXTURE'})
    for pair in ['EURUSD','USDJPY']:
        r.database.put('symbol_currency',a.scope_id+':'+pair,{'scope_id':a.scope_id,'symbol':pair,'source_epoch':FIXTURE_EPOCH,
            'base_currency':pair[:3],'quote_currency':pair[3:]})


def test_unconfigured_capital_has_no_approved_amount_or_account_permission(runtime):
    c=runtime.api(4).query('4.7',DataRequest('capital_context'))['rows'][0]
    assert c['status']=='UNCONFIGURED' and c['approved_amount'] is None and not c['account_risk_permission']


def test_real_shared_sizing_rounds_down_to_exact_native_min_step_not_fixed_lots(runtime):
    seed_money(runtime);runtime.money.set_policy({'classification':'RESEARCH_ONLY','capital_base':'BALANCE','capital_fraction':'0.45','budget_money':'123'},expected_version=0)
    c=runtime.money.context();assert c['native_money_current'] and c['research_fraction_amount']=='4500.0555555510'
    x=runtime.money.estimate(symbol='EURUSD',entry='1.10000',invalidation='1.09000',side='BUY')
    assert x['status']=='RESEARCH_ESTIMATE' and x['suggested_units']=='12000' and x['suggested_lots']=='0.12'
    assert x['estimate_at_invalidation']=='120.00000' and not x['account_risk_permission'] and not x['broker_protection']
    assert not runtime.database.orders() and not runtime.orders.transport.submissions


def test_conversion_is_native_epoch_fresh_and_conservative_inverse_for_loss(runtime):
    seed_money(runtime);q=runtime.market.quote(runtime.accounts.current.account_id,'USDJPY')
    runtime.market.set_quote(replace(q,bid=D('150'),ask=D('150.1'),sequence=1))
    x=runtime.money.estimate(symbol='USDJPY',entry='149.000',invalidation='148.000',side='BUY',budget_money='100')
    assert x['status']=='RESEARCH_ESTIMATE' and x['suggested_units']=='15000'
    assert len(x['conversion_path'])==1
    runtime.clock=lambda:'2026-11-05T12:01:00Z'
    assert runtime.money.estimate(symbol='USDJPY',entry='149.000',invalidation='148.000',side='BUY',budget_money='100')['status']=='BLOCKED'


def test_policy_exact_fields_types_account_scope_cas_and_no_native_mutation(runtime):
    seed_money(runtime);p={'classification':'RESEARCH_ONLY','capital_base':'BALANCE','capital_fraction':'0.45','budget_money':'100'}
    result=runtime.api(4).command('4.7','SET_RESEARCH_POLICY',{'policy':p,'expected_version':0,'expected_scope_id':runtime.market.scope_id})
    assert result.status.value=='ACCEPTED'
    assert runtime.api(4).command('4.7','SET_RESEARCH_POLICY',{'policy':p,'expected_version':0,'expected_scope_id':runtime.market.scope_id}).status.value=='REJECTED'
    for wrong in [dict(p,capital_fraction=True),dict(p,budget_money='NaN'),dict(p,classification='LIVE_APPROVED'),dict(p,capital_fraction='1.1')]:
        assert runtime.api(4).command('4.7','SET_RESEARCH_POLICY',{'policy':wrong,'expected_version':1,'expected_scope_id':runtime.market.scope_id}).status.value=='REJECTED'
    assert runtime.money.policy()['version']==1 and not runtime.orders.transport.submissions


def test_sizing_never_crosses_epoch_or_silently_uses_unknown_currency(runtime):
    seed_money(runtime);a=runtime.accounts.current
    money=runtime.database.get('account_money_snapshot',a.scope_id);money['source_epoch']='OLD';runtime.database.put('account_money_snapshot',a.scope_id,money)
    assert runtime.money.estimate(symbol='EURUSD',entry='1.1',invalidation='1.09',side='BUY',budget_money='100')['status']=='BLOCKED'
    seed_money(runtime);runtime.market.activate_source('EURUSD','NEW','SYNTHETIC_FIXTURE')
    assert runtime.money.estimate(symbol='EURUSD',entry='1.1',invalidation='1.09',side='BUY',budget_money='100')['status']=='BLOCKED'
