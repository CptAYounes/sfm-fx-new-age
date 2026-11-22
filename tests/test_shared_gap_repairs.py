import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from dataclasses import replace
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import pytest

from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.contracts.enums import CommandStatus
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW, FIXTURE_EPOCH


@pytest.mark.parametrize('command', ['CANCEL_SIGNAL', 'CANCEL_ALL_UNISSUED'])
def test_actual_cancel_buttons_obey_strict_schema(runtime, command):
    app = QApplication.instance() or QApplication([])
    window = create_main_window(runtime)
    window.show(); window.main_tabs.setCurrentIndex(3); app.processEvents()
    workspace = window.main_tabs.widget(3).widget(0).widget()
    workspace.pages.setCurrentIndex(1);app.processEvents();panel=workspace.queue
    panel.table.selectRow(0); app.processEvents()
    QTest.mouseClick(panel.buttons[command], Qt.LeftButton); app.processEvents()
    assert 'ACCEPTED' in panel.result_label.text()
    assert runtime.signals.get('FIXTURE-SIGNAL-1')['state'] == 'CANCELED'
    assert runtime.orders.transport.cancellations == 0
    window.close()


def test_rule_preview_is_pure_and_save_is_versioned(runtime):
    rule = {'op': 'EQ', 'variable': 'fixture.d1_ready', 'unit': 'boolean', 'value': True}
    before = runtime.database.connection.total_changes
    preview = runtime.catalogues.preview_rule('new-rule', rule)
    assert preview['preview'] == 'TRUE'
    assert runtime.database.connection.total_changes == before
    assert runtime.database.get('rule', 'new-rule') is None
    first = runtime.catalogues.save_rule('new-rule', rule)
    second = runtime.catalogues.save_rule('new-rule', dict(rule, value=False))
    assert (first['version'], second['version']) == (1, 2)
    assert len([r for r in runtime.database.list('rule_revision') if r['rule_id'] == 'new-rule']) == 2
    before = runtime.database.connection.total_changes
    result = runtime.api(3).command('3.10', 'SAVE_PREVIEW_ACTIVATE_RULE',
        {'rule_id': 'new-rule', 'rule': rule, 'action': 'preview'})
    assert result.status is CommandStatus.ACCEPTED
    assert runtime.database.connection.total_changes == before


def test_optional_h1_has_effective_consumer_lifecycle(runtime):
    assert runtime.api(1).snapshot('1.5').status == 'DISABLED'
    seen = []
    api = runtime.api(1); off = api.subscribe('1.5', seen.append)
    old = runtime.market.bars('EURUSD', 'H1', FIXTURE_NOW, FIXTURE_EPOCH)[-1]
    runtime.market.ingest(replace(old, revision=2, available_at='2026-11-05T13:00:00Z'))
    assert seen == []
    assert api.command('1.5', 'ENABLE_OPTIONAL_H1', {'enabled': True}).status is CommandStatus.ACCEPTED
    assert api.snapshot('1.5').status == 'AVAILABLE'
    seen.clear()
    runtime.market.ingest(replace(old, revision=3, available_at='2026-11-05T14:00:00Z'))
    assert seen
    off()


def test_effective_display_consumer_switch_pauses_and_rehydrates(runtime):
    api = runtime.api(1); snapshots = []
    off = api.subscribe_snapshots('1.3', snapshots.append, initial=False)
    runtime.api(2).command('2.1', 'SET_CONSUMER_SWITCH', {'consumer_id': 'display.1.3', 'enabled': False})
    snapshots.clear()
    runtime.api(1).command('1.1', 'SELECT_PAIR', {'symbol': 'GBPUSD'})
    assert snapshots == []
    assert api.snapshot('1.3').status == 'DISABLED'
    runtime.api(2).command('2.1', 'SET_CONSUMER_SWITCH', {'consumer_id': 'display.1.3', 'enabled': True})
    assert snapshots and snapshots[-1].data['symbol'] == 'GBPUSD'
    off()


def test_completed_atr_is_cached_across_all_consumers_and_restart(runtime, monkeypatch):
    calls = []
    original = runtime.market.wilder_atr
    def counted(*args, **kwargs):
        calls.append(1); return original(*args, **kwargs)
    monkeypatch.setattr(runtime.market, 'wilder_atr', counted)
    for _ in range(5):
        for key in ('1.2', '1.3', '1.4', '3.2', '3.3', '3.4'):
            runtime.api(int(key[0])).snapshot(key)
    assert len(calls) <= 1
    old = runtime.market.bars('EURUSD', 'W1', FIXTURE_NOW, FIXTURE_EPOCH)[-1]
    correction = replace(old, revision=2, available_at='2026-11-05T13:00:00Z', high=old.high + 1)
    before = runtime.market.context('EURUSD', FIXTURE_NOW, FIXTURE_EPOCH)['w1_atr14']
    runtime.market.ingest(correction)
    assert runtime.market.context('EURUSD', FIXTURE_NOW, FIXTURE_EPOCH)['w1_atr14'] == before
    after = runtime.market.context('EURUSD', '2026-11-05T14:00:00Z', FIXTURE_EPOCH)['w1_atr14']
    assert after != before
    assert len(calls) <= 2
    assert runtime.database.list('atr_checkpoint')
