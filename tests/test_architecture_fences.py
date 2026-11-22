import ast
from pathlib import Path
import socket
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/'src/sfm_fx_new_age'


def imports(path):
    tree=ast.parse(path.read_text())
    return [node.module or '' for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)] + [
        alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names]


def test_tabs_do_not_import_sql_or_broker_sdk_and_backend_does_not_import_qt():
    for path in (PKG/'tabs').rglob('*.py'):
        assert not any(name.startswith(('sqlite3','ctrader_open_api','sfm_fx_new_age.services.orders')) for name in imports(path)),path
    for area in ['services','storage','contracts','core']:
        for path in (PKG/area).rglob('*.py'):
            assert not any(name.startswith(('PySide6','tkinter')) for name in imports(path)),path


def test_normal_runtime_has_no_network_import_or_implicit_fixture_startup():
    for area in ['services','storage','contracts','core']:
        for path in (PKG/area).rglob('*.py'):
            assert not any(name.startswith(('socket','requests','urllib.request','ctrader_open_api')) for name in imports(path)),path
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    r=ApplicationRuntime()
    try:assert r.orders.transport is None
    finally:r.close()


def test_offline_checkpoint_denies_socket_connections(monkeypatch):
    from sfm_fx_new_age.testing.checkpoint import run_checkpoint
    calls=[]
    def denied(*args,**kwargs):
        calls.append(args);raise AssertionError('Offline checkpoint tried a socket operation')
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(socket.socket,'connect_ex',denied)
    monkeypatch.setattr(socket,'create_connection',denied)
    assert run_checkpoint()['ok']
    assert calls==[]


def test_headless_cli_never_imports_gui_or_waits_for_display():
    code="import sys; from sfm_fx_new_age.__main__ import main; sys.argv=['sfm','--offline-checkpoint']; assert main()==0; assert 'sfm_fx_new_age.app' not in sys.modules; assert 'PySide6.QtWidgets' not in sys.modules"
    completed=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=30)
    assert completed.returncode==0,completed.stderr
    assert 'OFFLINE_SYNTHETIC_FIXTURE_ONLY' in completed.stdout


def test_no_competing_project_progress_notebooks():
    ignored={'.git','.venv','.pytest_cache','__pycache__','build','dist'}
    notebooks=[]
    for path in ROOT.rglob('*.md'):
        if any(part in ignored for part in path.relative_to(ROOT).parts):continue
        relative=path.relative_to(ROOT)
        if relative.parts[0] in {'docs','.github'}:
            assert path.name.upper() not in {'STATUS.MD','HANDOFF.MD','TODO.MD','NOTES.MD','DIARY.MD'},path
            continue
        if path.name not in {'README.md','PROGRESS.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','SECURITY.md','SUPPORT.md','AGENTS.md'}:
            if qualified_research_artifact(path):continue
            # A sealed, read-only diary snapshot is evidence, never a second
            # editable progress notebook. Verify its exact owning manifest.
            if path.name=='PROGRESS.snapshot.md' and path.relative_to(ROOT).parts[0]=='.runtime':
                import json,hashlib
                manifest=path.parent/'final-evidence.json'
                if manifest.is_file() and path.stat().st_mode&0o777==0o444:
                    row=json.loads(manifest.read_text()).get('entries',{}).get(path.name,{})
                    if row.get('sha256')==hashlib.sha256(path.read_bytes()).hexdigest():continue
            notebooks.append(path)
    assert notebooks==[]


RESEARCH_READBACK_SHA256='b06a35e28328ea55d52c06a9cdea9eadb1b82a3efaa9aed71570f3a738367d4f'
RESEARCH_NAMES=frozenset({'BROKER_AND_BLOCKER_RESEARCH.md','NEXT_HERMES_WORKER_PROMPT.md','SOURCE_EVIDENCE.md'})


def qualified_research_artifact(path,root=ROOT):
    """Allow only original immutable research, never another editable diary."""
    import hashlib,json,stat
    folder=root/'.runtime/remaining-source-access-v15'
    manifest=folder/'final-readback.json'
    if path.parent!=folder or path.name not in RESEARCH_NAMES:return False
    try:
        for target in (path,manifest):
            mode=target.lstat().st_mode
            if not stat.S_ISREG(mode) or stat.S_IMODE(mode)!=0o444:return False
        original=manifest.read_bytes()
        if hashlib.sha256(original).hexdigest()!=RESEARCH_READBACK_SHA256:return False
        row=json.loads(original)['artifacts'][path.name]
        return hashlib.sha256(path.read_bytes()).hexdigest()==row
    except (OSError,ValueError,KeyError,TypeError):return False


@pytest.mark.parametrize('fault',['none','changed_document','changed_readback','writable_document','writable_readback','extra_name','wrong_directory','symlink'])
def test_research_exception_is_exact_original_and_immutable(tmp_path,fault,monkeypatch):
    import shutil,hashlib,json
    # Explicit synthetic immutable evidence, not a private runtime archive.
    original=tmp_path/'synthetic-original';original.mkdir()
    fixture_name='BROKER_AND_BLOCKER_RESEARCH.md'
    (original/fixture_name).write_text('# Synthetic immutable research fixture\n')
    readback=json.dumps({'artifacts':{fixture_name:hashlib.sha256((original/fixture_name).read_bytes()).hexdigest()}},sort_keys=True).encode()
    (original/'final-readback.json').write_bytes(readback)
    monkeypatch.setitem(globals(),'RESEARCH_READBACK_SHA256',hashlib.sha256(readback).hexdigest())
    folder=tmp_path/'.runtime/remaining-source-access-v15';folder.mkdir(parents=True)
    name='BROKER_AND_BLOCKER_RESEARCH.md'
    for token in (name,'final-readback.json'):
        shutil.copyfile(original/token,folder/token);(folder/token).chmod(0o444)
    path=folder/name;manifest=folder/'final-readback.json'
    if fault=='changed_document':path.chmod(0o644);path.write_bytes(path.read_bytes()+b'\nALTERED');path.chmod(0o444)
    elif fault=='changed_readback':manifest.chmod(0o644);manifest.write_bytes(manifest.read_bytes()+b'\n');manifest.chmod(0o444)
    elif fault=='writable_document':path.chmod(0o644)
    elif fault=='writable_readback':manifest.chmod(0o644)
    elif fault=='extra_name':path=folder/'ANOTHER_PROGRESS.md';shutil.copyfile(original/name,path);path.chmod(0o444)
    elif fault=='wrong_directory':path=tmp_path/name;shutil.copyfile(original/name,path);path.chmod(0o444)
    elif fault=='symlink':path=folder/'SOURCE_EVIDENCE.md';path.symlink_to(folder/name)
    assert qualified_research_artifact(path,tmp_path) is (fault=='none')
