"""Nonmarket flow-control/timeout controls; not positive market observations."""
from pathlib import Path
from queue import Queue,Empty,Full
from threading import Event
from types import SimpleNamespace
import ast,json
import pytest
from sfm_fx_new_age.connector.kraken_public import PublicationMailbox,ConnectedKrakenFeed

SYMBOLS=('EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD')


def test_predecessor_fifo_reproduces_full_on_valid_publication_burst():
    # Complete-publication control values only; no generated prices/trades.
    fifo=Queue(maxsize=24)
    values=[(('CONTROL',()),'BOOK',(s,{'original_receipt_token':cycle})) for cycle in range(5) for s in SYMBOLS]
    with pytest.raises(Full):
        for value in values:fifo.put_nowait(value)
    assert fifo.qsize()==24


def test_latest_snapshot_mailbox_bounds_every_pair_kind_without_retiming():
    box=PublicationMailbox(maxsize=24);binding=('CONTROL',());latest={}
    for cycle in range(20):
        for kind in ('BOOK','TRADES','HOURS'):
            for symbol in SYMBOLS:
                payload=(symbol,{'original_receipt_token':cycle,'channel':kind})
                value=(binding,kind,payload);latest[(kind,symbol)]=value;box.put_nowait(value)
                assert box.qsize()<=18
    rows=[]
    while True:
        try:rows.append(box.get_nowait())
        except Empty:break
    assert len(rows)==18 and box.coalesced==342
    assert {(v[1],v[2][0]) for v in rows}==set(latest)
    assert all(v is latest[(v[1],v[2][0])] for v in rows)


def test_snapshot_replacement_is_fair_and_keeps_original_binding():
    box=PublicationMailbox(maxsize=2);a=('A',());b=('B',())
    first=(a,'BOOK',('EURUSD','OLD_CONTROL'));next_pair=(a,'BOOK',('GBPUSD','OTHER_CONTROL'));latest=(a,'BOOK',('EURUSD','LATEST_CONTROL'))
    box.put_nowait(first);box.put_nowait(next_pair);box.put_nowait(latest)
    assert box.get_nowait() is latest
    assert box.get_nowait() is next_pair
    box.put_nowait(first);box.put_nowait((b,'BOOK',('EURUSD','DIFFERENT_BINDING')))
    with pytest.raises(Full):box.put_nowait((a,'BOOK',('USDJPY','OVER_BUDGET')))
    assert box.qsize()==2


def test_true_capacity_failure_remains_fail_closed():
    r=SimpleNamespace(analytics=SimpleNamespace(supplemental=None));feed=ConnectedKrakenFeed(SimpleNamespace(r=r));feed.results=PublicationMailbox(maxsize=1)
    feed._send(('CONTROL',()),'BOOK',('EURUSD','CONTROL'))
    feed._send(('CONTROL',()),'BOOK',('GBPUSD','CONTROL'))
    assert feed.stop.is_set() and feed.error_type=='PUBLICATION_MAILBOX_CAPACITY'


def test_disconnect_resets_weekly_cooldown_for_new_source_binding():
    # Lifecycle controls only. No constructed market observations or networking.
    r=SimpleNamespace(analytics=SimpleNamespace(supplemental=None))
    feed=ConnectedKrakenFeed(SimpleNamespace(r=r));weekly=feed.weekly
    weekly.binding=('OLD_CONTROL',());weekly.next_start=float('inf')
    weekly.hour_inputs['EURUSD']='OLD_CONTROL';weekly.completed_pairs=['EURUSD']
    weekly.results.put_nowait(('OLD_CONTROL','EURUSD',(),{},None))
    weekly.disconnect()
    assert weekly.binding is None and weekly.next_start==0.
    assert weekly.stop.is_set() and not weekly.hour_inputs and not weekly.completed_pairs
    with pytest.raises(Empty):weekly.results.get_nowait()
    # Parent binding adoption must not restore the old source's cooldown.
    weekly.binding=('NEW_CONTROL',())
    assert weekly.next_start==0.


def test_timeout_handler_persists_primary_before_guarded_diagnostics_and_final_exit():
    source=Path(__file__).with_name('kraken_recovery_desktop.py').read_text();tree=ast.parse(source)
    inspect=next(v for v in ast.walk(tree) if isinstance(v,ast.FunctionDef) and v.name=='inspect')
    assert any(isinstance(s,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='window' for t in s.targets) for s in inspect.body[:3])
    handler=next(v for v in inspect.body if isinstance(v,ast.Try)).handlers[0]
    try_node=next(v for v in handler.body if isinstance(v,ast.Try))
    assert isinstance(try_node.body[0],ast.Expr) and isinstance(try_node.body[0].value,ast.Call) and try_node.body[0].value.args[0].value=='primary-failure.json'
    assert any(isinstance(v,ast.Try) for v in ast.walk(try_node.body[1]))
    assert [ast.unparse(v) for v in try_node.finalbody]==['timer.stop()','app.quit()']


def test_repaired_timeout_path_survives_missing_window_and_diagnostic_failure(tmp_path):
    source=Path(__file__).with_name('kraken_recovery_desktop.py').read_text();tree=ast.parse(source)
    inspect=next(v for v in ast.walk(tree) if isinstance(v,ast.FunctionDef) and v.name=='inspect')
    handler=next(v for v in inspect.body if isinstance(v,ast.Try)).handlers[0]
    # Exercise exactly the original handler AST, not a model of its behavior.
    body=ast.Module(body=handler.body,type_ignores=[]);ast.fix_missing_locations(body)
    import traceback
    calls=[];proof={};original=TimeoutError('CONTROL_ONLY_NO_NATIVE_RUNTIME')
    env=dict(exc=original,proof=proof,phase='CONTROL_PHASE',observed={},envelopes={},window=None,runtime=None,
        Path=Path,traceback=traceback,METHOD_KEYS=(),save=lambda name,value:(tmp_path/name).write_text(json.dumps(value)),
        timer=SimpleNamespace(stop=lambda:calls.append('STOP')),app=SimpleNamespace(quit=lambda:calls.append('QUIT')))
    exec(compile(body,'retained-timeout-handler','exec'),env)
    first=json.loads((tmp_path/'primary-failure.json').read_text());last=json.loads((tmp_path/'failure-diagnostics.json').read_text())
    assert first['error_type']=='TimeoutError' and first['phase_at_failure']=='CONTROL_PHASE'
    assert len(last['diagnostic_errors'])==4 and calls==['STOP','QUIT']
