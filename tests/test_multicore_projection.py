"""NONMARKET concurrency policy and owner-thread safety controls."""
from concurrent.futures import Future
import os,time
import pytest


def test_host_capacity_respects_affinity_quota_memory_and_reserve():
    from sfm_fx_new_age.services.compute_pool import worker_limit
    assert worker_limit(16,quota=16,memory_bytes=64*1024**3)==15
    assert worker_limit(16,quota=2,memory_bytes=64*1024**3)==1
    assert worker_limit(16,quota=16,memory_bytes=512*1024**2)==1
    assert worker_limit(4,quota=4,memory_bytes=64*1024**3,requested=99)==3
    assert worker_limit(1,quota=1,memory_bytes=64*1024**3)==1
    with pytest.raises(ValueError):worker_limit(16,requested=0)


class ManualExecutor:
    def __init__(self,**kwargs):self.tasks=[];self.closed=False
    def submit(self,fn,job):
        future=Future();self.tasks.append((future,job));return future
    def shutdown(self,**kwargs):self.closed=True


def task(token):return dict(token=token,entries=[],inputs={},deps={},results={})


def test_latest_only_coalescing_and_bounded_inflight_without_child_start():
    from sfm_fx_new_age.services.compute_pool import ProjectionPool
    pool=ProjectionPool(2,executor_factory=ManualExecutor)
    pool.offer(('EURUSD','H1'),task('A'));pool.offer(('GBPUSD','H1'),task('B'))
    pool.offer(('EURUSD','H1'),task('C'));pool.offer(('EURUSD','H1'),task('D'))
    assert len(pool.active)==2 and len(pool.waiting)==1
    executor=pool.executor;first=executor.tasks[0][0];first.set_result(dict(token='A',pid=999,cpu_seconds=.1,bodies=[],runs={},feature_builds=0))
    assert pool.poll()==[] and pool.metrics()['superseded']==1
    assert len(executor.tasks)==3 and executor.tasks[2][1]['token']=='D'
    pool.close();assert executor.closed


def test_invalidated_generation_is_not_delivered_and_owner_is_enforced():
    from sfm_fx_new_age.services.compute_pool import ProjectionPool
    from threading import Thread
    pool=ProjectionPool(2,executor_factory=ManualExecutor);pool.offer(('EURUSD','H1'),task('A'));pool.invalidate('EURUSD')
    pool.executor.tasks[0][0].set_result(dict(token='A',pid=999,cpu_seconds=.1,bodies=[],runs={},feature_builds=0))
    assert pool.poll()==[]
    errors=[]
    def foreign():
        try:pool.offer(('GBPUSD','H1'),task('B'))
        except RuntimeError:errors.append(True)
    t=Thread(target=foreign);t.start();t.join();assert errors
    pool.close();assert not pool.active and not pool.waiting


def test_no_pool_creation_when_idle_or_serial():
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    with pytest.raises(ValueError):ApplicationRuntime(compute_workers=-1)
    r=ApplicationRuntime(compute_workers='auto')
    try:assert r.analytics.projections.pool.executor is None
    finally:r.close()


def prepared():
    from test_public_strategies import seed
    from sfm_fx_new_age.contracts.public_strategies import METHODS
    r=seed()
    for m in METHODS:r.database.put('recipe_state',m.recipe_id,dict(enabled=True,version=m.version))
    return r


def test_no_output_recipes_share_exact_frozen_snapshot(monkeypatch):
    import sfm_fx_new_age.contracts.models as models
    r=prepared();original=models.freeze;calls=[]
    def freeze(value):
        if isinstance(value,dict) and 'prior_candidates' in value:calls.append(value)
        return original(value)
    monkeypatch.setattr(models,'freeze',freeze)
    try:r.analytics.refresh('EURUSD');assert len(calls)==1
    finally:r.close()


def test_real_spawned_workers_equal_existing_serial_math_and_are_joined():
    from multiprocessing import active_children
    r=prepared();p=r.analytics.projections
    try:
        r.analytics.refresh('EURUSD')
        expected={row['fingerprint']:row for row in r.database.list('projection_current') if row['symbol']=='EURUSD'}
        with r.database.transaction() as db:db.execute("DELETE FROM records WHERE kind IN ('projection_current','strategy_projection')")
        p.configure_compute(3);r.analytics.refresh('EURUSD')
        assert p.pool.active and not p.read('EURUSD','H4')
        deadline=time.monotonic()+30
        while p.pool.desired and time.monotonic()<deadline:p.poll_compute();time.sleep(.01)
        assert not p.pool.desired and not p.pool.failed
        observed={row['fingerprint']:row for row in r.database.list('projection_current') if row['symbol']=='EURUSD'}
        assert observed==expected
        assert p.pool.pids and os.getpid() not in p.pool.pids
        pids=set(p.pool.pids)
    finally:r.close()
    assert not p.pool.active and not [child for child in active_children() if child.pid in pids]


@pytest.mark.parametrize('change',['withdraw','disable','expiry','wrong_token'])
def test_late_results_cannot_bypass_current_authority_switch_or_expiry(change):
    from sfm_fx_new_age.services.compute_pool import ProjectionPool
    from sfm_fx_new_age.services.projection_math import compute_frame
    from sfm_fx_new_age.contracts.public_strategies import BY_KEY
    r=prepared();p=r.analytics.projections;p.pool=ProjectionPool(2,executor_factory=ManualExecutor)
    try:
        r.analytics.refresh('EURUSD')
        jobs=list(p.pool.executor.tasks)
        if change=='withdraw':r.market.withdraw_source('EURUSD',r.market.authority('EURUSD')['source_epoch'])
        if change=='disable':
            for m,_,_ in p.methods.values():r.database.put('recipe_state',m.recipe_id,dict(enabled=False,version=m.version))
        for future,job in jobs:
            result=compute_frame(job)
            if change=='wrong_token':result['token']='OTHER_JOB'
            if change=='expiry':
                for b in result['bodies']:b['valid_until']='2000-01-01T00:00:00Z'
            future.set_result(result)
        p.poll_compute()
        if change=='wrong_token':assert p.pool.failed
        if change in {'withdraw','disable','expiry'}:assert not r.database.list('strategy_projection') or all(row['state']=='WARMUP' for row in r.database.list('strategy_projection'))
    finally:r.close()
