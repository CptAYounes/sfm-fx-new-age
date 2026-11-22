"""Actual Tab3/Tab4 widgets and owner commands, including compact geometry."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication,QCheckBox
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.contracts.public_strategies import METHODS
from test_strategy_signal_positive import bindable_runtime


@pytest.fixture
def signal_shell():
    app=QApplication.instance() or QApplication([]);r=bindable_runtime();w=create_main_window(r);w.show()
    w.main_tabs.setCurrentIndex(3);app.processEvents()
    workspace=w.main_tabs.currentWidget().currentWidget().widget()
    workspace.refresh();app.processEvents()
    yield app,r,w,workspace
    w.close();r.close();app.processEvents()


def test_registered_signal_workspace_shows_every_policy_and_explicit_current_state(signal_shell):
    app,r,w,workspace=signal_shell;p=workspace.research_signals
    assert workspace.pages.count()==2 and workspace.pages.currentIndex()==0
    assert p.table.rowCount()==83 and {x['strategy_id'] for x in p._rows}=={m.key for m in METHODS}
    assert '1/83 enabled' in p.summary.text()
    p.filter.setCurrentText('Signals only');app.processEvents()
    assert [p._rows[i]['strategy_id'] for i in range(83) if not p.table.isRowHidden(i)]==['engulfing']
    p.table.selectRow(next(i for i,v in enumerate(p._rows) if v['strategy_id']=='engulfing'));app.processEvents()
    assert 'New research entry policy' in p.details.toPlainText() and 'SYNTHETIC_FIXTURE' in p.details.toPlainText()
    assert not p.bind.isEnabled()
    p.search.setText('no such strategy');app.processEvents();assert p.selected() is None and not p.bind.isEnabled()
    assert not r.orders.transport.submissions


def test_operator_units_review_and_bind_goes_to_existing_issue_queue_without_order(signal_shell):
    app,r,w,workspace=signal_shell;p=workspace.research_signals
    p.table.selectRow(next(i for i,v in enumerate(p._rows) if v['strategy_id']=='engulfing'))
    p.units.setText('1000');app.processEvents();assert not p.bind.isEnabled()
    p.ack.setChecked(True);app.processEvents();assert p.bind.isEnabled()
    p.bind.click();app.processEvents()
    assert workspace.pages.currentIndex()==1 and 'ACCEPTED' in p.feedback.text()
    assert sum((s.get('market_candidate_id') or '').startswith('strategy:') for s in r.signals.all())==1
    assert not r.orders.transport.submissions and not r.database.orders()
    workspace.pages.setCurrentIndex(0);app.processEvents();p.refresh()
    assert next(v for v in p._rows if v['strategy_id']=='engulfing')['state']=='BOUND'
    assert not p.bind.isEnabled()


@pytest.mark.parametrize('size',[(960,640),(1440,900)])
def test_research_actions_and_original_issue_actions_remain_visible_without_outer_scroll(signal_shell,size):
    app,r,w,workspace=signal_shell;w.resize(*size);app.processEvents();workspace.refresh();app.processEvents()
    scroll=w.main_tabs.currentWidget().currentWidget();p=workspace.research_signals
    assert scroll.verticalScrollBar().maximum()==0
    for widget in (p.pair,p.frame,p.filter,p.search,p.units,p.ack,p.bind,p.chart,p.feedback):
        assert widget.isVisible()
        assert widget.mapTo(scroll.viewport(),QPoint(0,0)).y()>=0
        assert widget.mapTo(scroll.viewport(),QPoint(widget.width(),widget.height())).y()<=scroll.viewport().height(),widget.objectName()
        assert widget.mapTo(scroll.viewport(),QPoint(widget.width(),widget.height())).x()<=scroll.viewport().width(),widget.objectName()
    assert p.table.horizontalScrollBar().maximum()==0
    workspace.pages.setCurrentIndex(1);app.processEvents()
    assert scroll.verticalScrollBar().maximum()==0
    assert workspace.queue.table.horizontalScrollBar().maximum()==0
    for button in workspace.buttons.values():
        assert button.isVisible() and button.mapTo(scroll.viewport(),QPoint(0,button.height())).y()<=scroll.viewport().height()


def test_pair_frame_changes_do_not_leak_acknowledged_old_signal_selection(signal_shell):
    app,r,w,workspace=signal_shell;p=workspace.research_signals
    p.table.selectRow(next(i for i,v in enumerate(p._rows) if v['strategy_id']=='engulfing'));p.units.setText('1000');p.ack.setChecked(True)
    assert p.bind.isEnabled()
    p.pair.setCurrentText('GBPUSD');app.processEvents()
    assert all(v['symbol']=='GBPUSD' for v in p._rows) and not p.ack.isChecked() and not p.bind.isEnabled()
    p.frame.setCurrentText('W1');app.processEvents();assert all(v['timeframe']=='W1' for v in p._rows)
    assert not r.orders.transport.submissions
