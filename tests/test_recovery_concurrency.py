from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json

import pytest

from sfm_fx_new_age.contracts.domain import BrokerOutcome, OrderState
from sfm_fx_new_age.contracts.enums import CommandStatus, Priority
from sfm_fx_new_age.contracts.models import Event
from sfm_fx_new_age.core.router import BackpressureError, PriorityEventRouter
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW, fixture_runtime

P={'signal_id':'FIXTURE-SIGNAL-1','revision':1,'user_initiated':True,'acknowledge_research':True}


def test_concurrent_double_click_reserves_once(runtime):
    def issue(_): return runtime.api(4).command('4.1','ISSUE',P)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(issue,range(4)))
    assert sum(r.status is CommandStatus.ACCEPTED for r in results)==1
    assert len(runtime.database.orders())==1
    assert len(runtime.orders.transport.submissions)==1
    assert not runtime.router.errors


def test_persisted_submitting_order_recovers_unknown(tmp_path):
    path=tmp_path/'state.sqlite3'
    r=fixture_runtime(path)
    r.api(4).command('4.1','ISSUE',P)
    order=r.database.orders()[0]
    r.database.update_order(order['id'],{'state':'SUBMITTING'})
    r.close()
    restarted=ApplicationRuntime(path,clock=lambda:FIXTURE_NOW)
    try:
        assert restarted.orders.recovered==1
        assert restarted.database.orders()[0]['state']=='UNKNOWN'
        assert restarted.accounts.current is None
        assert restarted.api(4).command('4.1','ISSUE',P).status is CommandStatus.REJECTED
    finally:restarted.close()


def test_two_database_connections_reserve_once(tmp_path):
    path=tmp_path/'shared-state.sqlite3'
    first=fixture_runtime(path)
    broker=first.orders.transport
    second=ApplicationRuntime(path,clock=lambda:FIXTURE_NOW,transport=broker)
    second.accounts.select(first.accounts.current)
    try:
        def issue(runtime):return runtime.api(4).command('4.1','ISSUE',P)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(issue,[first,second]))
        assert sum(r.status is CommandStatus.ACCEPTED for r in results)==1
        assert len(first.database.orders())==1
        assert len(broker.submissions)==1
    finally:
        first.close();second.close()


def test_endpoint_mismatch_never_reconciles_other_connection(runtime):
    runtime.api(4).command('4.1','ISSUE',P)
    order=runtime.database.orders()[0]
    runtime.accounts.select(replace(runtime.accounts.current,endpoint_class='WRONG'))
    with pytest.raises(ValueError):runtime.orders.reconcile(order['id'])


def test_queue_backpressure_never_silently_drops_p0():
    router=PriorityEventRouter(capacity_per_priority=1)
    router.publish(Event('P0','X',priority=Priority.P0))
    with pytest.raises(BackpressureError):router.publish(Event('P0','X',priority=Priority.P0))
    router.publish(Event('P3','X',priority=Priority.P3))
    assert router.drain()==2


def test_failed_subscriber_does_not_starve_broker_state():
    router=PriorityEventRouter(); seen=[]
    def broken(event):raise ValueError('fixture failure')
    router.subscribe('BROKER',broken)
    router.subscribe('BROKER',lambda e:seen.append(e.event_id))
    event=Event('BROKER','CONNECTOR',priority=Priority.P0)
    router.publish(event); assert router.drain()==1
    assert seen==[event.event_id]
    assert router.errors[0]['error_type']=='ValueError'


def test_subscription_cleanup_and_lkv_bound():
    router=PriorityEventRouter(lkv_capacity=1); seen=[]
    release=router.subscribe('TEST',lambda e:seen.append(e.event_id))
    router.publish(Event('TEST','X',partition_key='first'));router.drain()
    release()
    router.publish(Event('TEST','X',partition_key='second'));router.drain()
    assert len(seen)==1
    assert router.last_known('TEST','first') is None
    assert router.last_known('TEST','second') is not None


def test_snapshot_mutation_does_not_modify_backend(runtime):
    projection=runtime.subtab('4.1').projection()
    projection.data['event_count']=-1
    assert runtime.subtab('4.1').projection().data['event_count']!=-1
    with pytest.raises(TypeError):runtime.api(4).snapshot('4.1').data['rows'][0]['state']='BAD'


def test_plain_account_metadata_never_restores_authentication(tmp_path):
    path=tmp_path/'state.sqlite3'
    r=fixture_runtime(path);r.close()
    r=ApplicationRuntime(path)
    try:
        assert r.database.list('account_metadata')[0]['authenticated'] is False
        assert r.accounts.current is None
    finally:r.close()
