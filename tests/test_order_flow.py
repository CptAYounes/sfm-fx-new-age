from dataclasses import replace
from decimal import Decimal

import pytest

from sfm_fx_new_age.contracts.domain import AccountContext, BrokerOutcome, Candidate, OrderState, Origin, Quote
from sfm_fx_new_age.contracts.enums import CommandStatus
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.services.orders import FixtureBroker
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW, fixture_runtime

PAYLOAD={'signal_id':'FIXTURE-SIGNAL-1','revision':1,'user_initiated':True,'acknowledge_research':True}


def test_human_issue_is_once_and_visible_across_tabs(runtime):
    seen=[]
    off=runtime.api(4).subscribe('4.3',lambda e:seen.append(e.topic))
    result=runtime.api(4).command('4.1','ISSUE',PAYLOAD)
    assert result.status is CommandStatus.ACCEPTED
    order=runtime.database.orders()[0]
    assert order['state']=='ACCEPTED_PENDING'
    assert len(runtime.orders.transport.submissions)==1
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.REJECTED
    assert len(runtime.orders.transport.submissions)==1
    assert runtime.api(1).snapshot('1.10').data['rows'][0]['id']==order['id']
    assert runtime.api(4).snapshot('4.4').data['rows'][0]['id']==order['id']
    assert seen
    off()
    assert not runtime.router.errors


@pytest.mark.parametrize('account_type',['DEMO','LIVE','UNKNOWN'])
def test_account_class_does_not_gate_issue(account_type):
    r=fixture_runtime(account_type=account_type)
    try:
        assert r.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.ACCEPTED
    finally: r.close()


@pytest.mark.parametrize('change',[
    {'user_initiated':False}, {'acknowledge_research':False}, {'revision':999}, {'signal_id':'missing'},
])
def test_invalid_issue_does_not_reserve_or_send(runtime,change):
    result=runtime.api(4).command('4.1','ISSUE',PAYLOAD | change)
    assert result.status is CommandStatus.REJECTED
    assert runtime.database.orders()==[]
    assert runtime.orders.transport.submissions==[]


def test_stale_quote_blocks_issue(runtime):
    runtime.orders.clock = lambda: '2026-11-05T12:01:00Z'
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.REJECTED
    assert runtime.database.orders()==[]


def test_auth_and_trading_scope_required_but_not_account_class(runtime):
    account=runtime.accounts.current
    runtime.accounts.select(replace(account,authenticated=False))
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.REJECTED
    runtime.accounts.select(replace(account,trading_scope=False))
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.REJECTED


def test_local_cancellation_never_cancels_pending_orders(runtime):
    runtime.api(4).command('4.1','ISSUE',PAYLOAD)
    assert runtime.api(4).command('4.1','CANCEL_ALL_UNISSUED').status is CommandStatus.ACCEPTED
    assert runtime.database.orders()[0]['state']=='ACCEPTED_PENDING'
    assert runtime.orders.transport.cancellations==0
    order=runtime.database.orders()[0]
    assert runtime.api(4).command('4.3','SEPARATE_BROKER_CANCEL',{'order_id':order['id'],'user_initiated':True}).status is CommandStatus.ACCEPTED
    assert runtime.database.orders()[0]['state']=='CANCELED'
    assert runtime.orders.transport.cancellations==1


def test_unissued_cancel_and_expiry(runtime):
    assert runtime.api(4).command('4.1','CANCEL_SIGNAL',{'signal_id':'FIXTURE-SIGNAL-1'}).status is CommandStatus.ACCEPTED
    assert runtime.signals.get('FIXTURE-SIGNAL-1')['state']=='CANCELED'
    assert runtime.database.orders()==[]
    body=runtime.signals.get('FIXTURE-SIGNAL-1');body.pop('state')
    runtime.signals.propose(Candidate(**(body | {'signal_id':'expired-signal',
        'available_at':'2026-11-04T00:00:00Z','expires_at':'2026-11-05T10:00:00Z'})))
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD | {'signal_id':'expired-signal'}).status is CommandStatus.REJECTED
    assert runtime.signals.get('expired-signal')['state']=='EXPIRED'
    assert runtime.orders.transport.submissions==[]


def test_unknown_survives_restart_without_blind_retry(tmp_path):
    broker=FixtureBroker(OrderState.UNKNOWN)
    path=tmp_path/'state.sqlite3'
    r=fixture_runtime(path,broker=broker)
    account=r.accounts.current
    r.api(4).command('4.1','ISSUE',PAYLOAD)
    order=r.database.orders()[0]
    r.close()
    recovered=ApplicationRuntime(path,clock=lambda:FIXTURE_NOW,transport=broker)
    try:
        assert recovered.accounts.current is None
        assert recovered.database.orders()[0]['state']=='UNKNOWN'
        with pytest.raises(ValueError): recovered.orders.reconcile(order['id'])
        recovered.accounts.select(account)
        assert recovered.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.REJECTED
        broker.native[order['id']]=BrokerOutcome(OrderState.ACCEPTED_PENDING,'FIXTURE-NATIVE')
        assert recovered.orders.reconcile(order['id'])['broker_order_id']=='FIXTURE-NATIVE'
        assert len(broker.submissions)==1
    finally: recovered.close()


def test_exception_after_send_is_unknown_not_retry(runtime):
    def uncertain(order):
        runtime.orders.transport.submissions.append(order)
        raise TimeoutError('synthetic timeout')
    runtime.orders.transport.submit=uncertain
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.ACCEPTED
    assert runtime.database.orders()[0]['state']=='UNKNOWN'
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.REJECTED
    assert len(runtime.orders.transport.submissions)==1


def test_replay_signal_cannot_issue_even_through_fixture_transport(runtime):
    body=runtime.signals.get('FIXTURE-SIGNAL-1'); body.pop('state')
    runtime.signals.propose(Candidate(**(body | {'signal_id':'replay','origin':Origin.HISTORICAL_REPLAY})))
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD | {'signal_id':'replay'}).status is CommandStatus.REJECTED


def test_fixture_and_live_account_origins_cannot_mix(runtime):
    runtime.accounts.select(replace(runtime.accounts.current,origin=Origin.LIVE_OBSERVED,account_type='LIVE'))
    assert runtime.api(4).command('4.1','ISSUE',PAYLOAD).status is CommandStatus.REJECTED


def test_partial_and_fill_native_transitions(runtime):
    runtime.api(4).command('4.1','ISSUE',PAYLOAD)
    order=runtime.database.orders()[0]
    broker_id=order['broker_order_id']
    runtime.orders._apply(order['id'],BrokerOutcome(OrderState.PARTIALLY_FILLED,broker_id,'FIXTURE-POSITION'))
    assert runtime.database.orders()[0]['state']=='PARTIALLY_FILLED'
    runtime.orders._apply(order['id'],BrokerOutcome(OrderState.FILLED,broker_id,'FIXTURE-POSITION'))
    with pytest.raises(ValueError): runtime.orders._apply(order['id'],BrokerOutcome(OrderState.ACCEPTED_PENDING,broker_id))
    with pytest.raises(ValueError): runtime.orders._apply(order['id'],BrokerOutcome(OrderState.FILLED,'DIFFERENT-ID'))
