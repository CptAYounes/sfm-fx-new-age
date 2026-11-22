"""Bounded owner work without weakening persistence or source authority."""
import ast
from pathlib import Path
from types import SimpleNamespace
import pytest
from sfm_fx_new_age.storage.database import Database


def test_grouped_writes_commit_once_and_keep_full_synchronous(tmp_path):
    db=Database(tmp_path/'durable.db');trace=[];db.connection.set_trace_callback(trace.append)
    try:
        with db.batch_writes():
            for i in range(20):db.put('proof',str(i),dict(i=i))
        assert sum(s=='COMMIT' for s in trace)==1
        assert len(db.list('proof'))==20
        assert db.connection.execute('PRAGMA synchronous').fetchone()[0]==2
        other=Database(tmp_path/'durable.db')
        try:assert len(other.list('proof'))==20
        finally:other.close()
    finally:db.close()


def test_nested_transaction_rolls_back_only_failed_operation():
    db=Database()
    try:
        with db.batch_writes():
            db.put('proof','accepted',dict(value=1))
            with pytest.raises(ValueError):
                with db.transaction() as conn:
                    db.write(conn,'proof','refused',dict(value=2))
                    raise ValueError('refused')
            db.put('proof','next',dict(value=3))
        assert [r['value'] for r in db.list('proof')]==[1,3]
        assert db.get('proof','refused') is None
    finally:db.close()


def test_batch_exception_preserves_prior_success_as_individual_commits_did():
    db=Database()
    try:
        with pytest.raises(RuntimeError):
            with db.batch_writes():
                db.put('proof','accepted',dict(value=1))
                raise RuntimeError('later independent operation failed')
        assert db.get('proof','accepted')==dict(value=1)
        assert not db.connection.in_transaction
    finally:db.close()


def test_atomic_outer_transaction_still_rolls_back_nested_writes():
    db=Database()
    try:
        with pytest.raises(ValueError):
            with db.transaction():
                with db.batch_writes():db.put('proof','no',dict(value=1))
                raise ValueError('atomic rollback')
        assert db.get('proof','no') is None
    finally:db.close()


def test_view_refresh_never_pumps_connector():
    import sfm_fx_new_age.app as app
    import inspect,textwrap
    node=ast.parse(textwrap.dedent(inspect.getsource(app.MainWindow.refresh_current)))
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='pump' for n in ast.walk(node))


def test_admission_prune_reads_only_exact_provider():
    from sfm_fx_new_age.connector.lanes import prune_admissions
    calls=[]
    def candidates(**kw):calls.append(kw);return []
    store=SimpleNamespace(admissions={'A':{'old'}},providers={'A':None,'B':None})
    runtime=SimpleNamespace(clock=lambda:'2026-11-16T12:00:00Z',database=SimpleNamespace(supplemental_candidates=candidates))
    prune_admissions(runtime,store,'A',('scope',(('EURUSD','epoch'),)))
    assert tuple(calls[0]['providers'])==('A',)
    assert store.admissions['A']==set()


@pytest.mark.parametrize('minute',[-1,0,15,59,60,90,119,120,150,179,180,240])
def test_chart_time_mapping_exactly_matches_original_loop(minute):
    from datetime import datetime,timedelta,timezone
    from sfm_fx_new_age.ui.chart_canvas import CandleCanvas
    from sfm_fx_new_age.contracts.domain import instant
    base=datetime(2026,11,16,tzinfo=timezone.utc)
    stamp=lambda m:(base+timedelta(minutes=m)).isoformat()
    rows=[dict(open_time=stamp(0),close_time=stamp(60)),dict(open_time=stamp(120),close_time=stamp(180))]
    canvas=SimpleNamespace(_bounds=(None,rows,12.,0,1,4.))
    def original(value):
        target=instant(value)
        for i,row in enumerate(rows):
            opened,closed=instant(row['open_time']),instant(row['close_time'])
            if target<=opened:return 4.+i*12.
            if target<closed:return 4.+(i+(target-opened).total_seconds()/max(1,(closed-opened).total_seconds()))*12.
        return 28.
    assert CandleCanvas.known_x(canvas,stamp(minute))==original(stamp(minute))
    assert CandleCanvas.known_x(canvas,stamp(minute))==original(stamp(minute))
    canvas._bounds=(None,rows,6.,0,1,4.)
    assert CandleCanvas.known_x(canvas,stamp(minute))==4.+(original(stamp(minute))-4.)/2


def test_scanner_preserves_every_original_fingerprint():
    from decimal import Decimal
    from sfm_fx_new_age.services.scanner import ScannerScheduler
    from sfm_fx_new_age.contracts.analytics import digest
    scheduler=ScannerScheduler();inputs={'bars':{'H1':[{'close':Decimal('1.25'),'unicode':'€'}]},'_evaluation_at':'private'}
    selector_key=scheduler.order[-1]
    scheduler.selectors[selector_key]=lambda i,d:({'selected':True},{'different':'dependency'})
    results=scheduler.execute('source',inputs)
    for key,row in results.items():
        selected={k:v for k,v in inputs.items() if not k.startswith('_')}
        deps={d:results[d].fingerprint for d in scheduler.nodes[key]['depends_on']}
        if key==selector_key:selected,deps=scheduler.selectors[key](inputs,{})
        assert row.fingerprint==digest(['source',selected,key,deps])


def test_ephemeral_admission_prune_never_restores_membership_or_old_epoch():
    from sfm_fx_new_age.services.supplemental import SupplementalEvidenceStore
    from sfm_fx_new_age.connector.lanes import prune_admissions
    from sfm_fx_new_age.contracts.domain import instant
    store=SupplementalEvidenceStore(None,None,None,None)
    store.admissions={'A':{'admitted','expired','old_epoch'}}
    store._admission_index={'A':{
        ('scope','epoch','EURUSD','K'):((instant('2026-11-16T11:00:00Z'),1),{'admitted':instant('2026-11-16T13:00:00Z'),'not_admitted':instant('2026-11-16T13:00:00Z'),'expired':instant('2026-11-16T11:00:00Z')}),
        ('scope','old','EURUSD','K'):((instant('2026-11-16T11:00:00Z'),1),{'old_epoch':instant('2026-11-16T13:00:00Z')})}}
    runtime=SimpleNamespace(clock=lambda:'2026-11-16T12:00:00Z')
    prune_admissions(runtime,store,'A',('scope',(('EURUSD','epoch'),)))
    assert store.admissions['A']=={'admitted'}
    assert len(store._admission_index['A'])==1


def test_connector_yields_without_losing_native_fifo(runtime,monkeypatch):
    from itertools import count
    import sfm_fx_new_age.connector.service as service
    connector=runtime.connector;observed=[];polled=[]
    messages=[{'kind':'TEST','i':i} for i in range(3)]
    worker=SimpleNamespace(poll=lambda:(polled.append(True) or messages))
    connector.workers={'LIVE':worker}
    monkeypatch.setattr(service,'monotonic',lambda:next(ticks))
    ticks=count()
    monkeypatch.setattr(connector,'handle',lambda endpoint,m:observed.append(m['i']))
    try:
        for i in range(3):
            connector.poll();assert observed==list(range(i+1))
        assert polled==[True]
    finally:connector.workers.clear()


def test_projection_poll_retains_completed_lanes_for_later_turns():
    from sfm_fx_new_age.services.compute_pool import ProjectionPool
    from test_multicore_projection import ManualExecutor,task
    pool=ProjectionPool(3,executor_factory=ManualExecutor)
    try:
        for i,symbol in enumerate(['EURUSD','GBPUSD','USDJPY']):pool.offer((symbol,'H1'),task(str(i)))
        for future,job in pool.executor.tasks:future.set_result(dict(token=job['token'],pid=999,cpu_seconds=.01,bodies=[],runs={},feature_builds=0))
        assert len(pool.poll(max_results=1))==1
        assert len(pool.active)==2
        assert len(pool.poll(max_results=1))==1
        assert len(pool.poll(max_results=1))==1
        assert not pool.active and not pool.desired
    finally:pool.close()
