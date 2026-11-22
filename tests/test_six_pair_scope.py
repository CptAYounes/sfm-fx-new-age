"""Explicit six-pair scope migration; synthetic controls, never market proof."""
from pathlib import Path
import pytest
from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES, symbol_check
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.services.market import market_key
from sfm_fx_new_age.testing.fixtures import fixture_runtime

EXPECTED=('EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD')

def test_exact_six_pair_scope_and_removed_pair_rejection():
    assert PAIRS==EXPECTED and len(PAIRS)*len(FRAMES)==24
    with pytest.raises(ValueError):symbol_check('NZDUSD')

def test_removed_pair_history_preserved_but_never_current(tmp_path):
    path=tmp_path/'state.sqlite3'
    r=fixture_runtime(str(path))
    try:
        scope=r.market.scope_id
        old=dict(symbol='NZDUSD',source_epoch='LEGACY',origin='SYNTHETIC_FIXTURE',scope_id=scope)
        r.database.put('authority',market_key(scope,'NZDUSD'),old)
        r.database.put('setting','selected_pair',dict(value='NZDUSD'))
        assert r.market.authority('NZDUSD') is None
        assert not any(v.get('symbol')=='NZDUSD' for v in r.market.scoped_rows('authority'))
        assert r.database.get('authority',market_key(scope,'NZDUSD'))==old
        with pytest.raises(ValueError):r.market.activate_source('NZDUSD','NEW','SYNTHETIC_FIXTURE')
    finally:r.close()
    r=ApplicationRuntime(path)
    try:
        assert r.selected_pair=='EURUSD'
        assert r.database.get('authority',market_key(scope,'NZDUSD'))==old
    finally:r.close()

def test_removed_pair_producer_is_inert_even_with_old_binding(tmp_path,monkeypatch):
    from sfm_fx_new_age.connector.fxopen_feed import ConnectedFXOpenReported
    r=fixture_runtime()
    try:
        r.database.path=str(tmp_path/'NONMARKET.sqlite')
        feed=ConnectedFXOpenReported(r.connector)
        feed.poll((r.market.scope_id,(('NZDUSD','LEGACY'),),(('NZDUSD',7),)))
        assert feed.binding is None and feed.worker is None and feed.last_directory is None
        assert feed.status()['qualified_pairs']==[]
        assert feed.status()['state']=='OUTSIDE_ACTIVE_UNIVERSE'
        feed.close()
    finally:r.close()

def test_six_pair_ui_status_has_no_obsolete_denominators(runtime):
    from PySide6.QtWidgets import QApplication
    from sfm_fx_new_age.ui.feed_connection import FeedDialog
    app=QApplication.instance() or QApplication([])
    d=FeedDialog(runtime.api(2),runtime.api(4),fixture_mode=True)
    try:
        d.refresh()
        text=d.status.text()+' '+d.analytical_status.text()
        assert '/7' not in text and '/28' not in text
        assert 'NZDUSD' not in text
    finally:d.close();d.deleteLater();app.processEvents()
