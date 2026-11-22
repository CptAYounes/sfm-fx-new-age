"""User-requested compact shell; product registries and shared owners stay intact."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import pytest
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QComboBox,QLabel,QTableWidget

from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.contracts.registry import tab_titles
from sfm_fx_new_age.contracts.domain import PAIRS


@pytest.fixture
def shell(runtime):
    app=QApplication.instance() or QApplication([])
    window=create_main_window(runtime);window.show();app.processEvents()
    yield app,window
    window.close();app.processEvents()


def test_main_navigation_replaces_pair_and_timeframe_strip(shell):
    app,w=shell
    assert w.findChild(QComboBox,'pairPicker') is None
    assert not any('D1 primary  /' in label.text() or label.text()=='CURRENCY PAIR' for label in w.findChildren(QLabel))
    bar=w.main_tabs.tabBar()
    assert bar.mapTo(w,QPoint(0,0)).y()<100
    assert bar.mapTo(w,QPoint(0,bar.height())).y()<=w.subtab_picker.mapTo(w,QPoint(0,0)).y()
    assert [w.main_tabs.tabText(i).replace('&&','&') for i in range(4)]==list(tab_titles().values())
    assert all(not w.main_tabs.widget(i).tabBar().isVisible() for i in (0,2,3))


def test_single_component_inspector_replaces_raw_44_row_table(shell,runtime):
    app,w=shell
    w.main_tabs.setCurrentIndex(1);app.processEvents()
    assert not w.view_toolbar.isVisible()
    assert w.tools.findChild(QTableWidget,'snapshotTable') is None
    assert w.findChild(QComboBox,'scannerComponentPicker') is None
    assert len(runtime.api(2).snapshot('2.2').data['rows'])==44
    assert w.main_tabs.tabText(1)=='Trading Tools'


def test_pair_view_selection_uses_shared_pair_without_broker_calls(shell,runtime):
    app,w=shell
    w.subtab_picker.setCurrentIndex(1);app.processEvents()
    assert runtime.selected_pair=='GBPUSD'
    assert runtime.orders.transport.submissions==[]
    w.main_tabs.setCurrentIndex(2);w.subtab_picker.setCurrentIndex(2);app.processEvents()
    assert 'GBPUSD' in w.main_tabs.currentWidget().currentWidget().widget().origin.text()


def test_all_subtabs_remain_reachable_with_one_selector_and_remember_position(shell):
    app,w=shell;seen=[]
    for tab,count in enumerate((10,10,13,9)):
        if tab==1:continue # 2.* are agent-owned internal contracts, not user pages.
        w.main_tabs.setCurrentIndex(tab);app.processEvents()
        assert w.subtab_picker.count()==(len(PAIRS) if tab==0 else count)
        for view in range(count):
            (w.chart_tabs if tab==0 else w.subtab_picker).setCurrentIndex(view);app.processEvents()
            assert w.main_tabs.currentWidget().currentIndex()==view
            seen.append(w.main_tabs.currentWidget().currentWidget().widget().objectName())
        if tab==0:w.chart_tabs.setCurrentIndex(count-2)
        else:w.previous_view.click()
        app.processEvents()
        assert w.main_tabs.currentWidget().currentIndex()==count-2
    assert len(seen)==len(set(seen))==32
    w.main_tabs.setCurrentIndex(0);app.processEvents()
    assert w.chart_tabs.currentIndex()==8
    w.subtab_picker.setCurrentIndex(len(PAIRS)-1);app.processEvents()
    assert not w.next_view.isEnabled()


@pytest.mark.parametrize('width,height',[(960,640),(1280,720),(1440,900)])
def test_navigation_fits_window_and_has_no_horizontal_page_overflow(shell,width,height):
    app,w=shell;w.resize(width,height);app.processEvents()
    for tab in range(4):
        w.main_tabs.setCurrentIndex(tab);app.processEvents()
        bar=w.main_tabs.tabBar()
        assert bar.tabRect(3).right()<=bar.width()
        if tab==1:
            assert w.tools.area.width()>600 and not w.view_toolbar.isVisible()
            continue
        assert w.subtab_picker.width()>=300
        assert w.next_view.mapTo(w,QPoint(w.next_view.width(),0)).x()<=w.width()
        scroll=w.main_tabs.currentWidget().currentWidget()
        assert scroll.horizontalScrollBar().maximum()==0


def test_idle_startup_does_not_load_all_42_snapshots(runtime,monkeypatch):
    app=QApplication.instance() or QApplication([]);calls=[];old=runtime.snapshot
    monkeypatch.setattr(runtime,'snapshot',lambda identity:(calls.append(identity),old(identity))[1])
    w=create_main_window(runtime)
    try:
        assert set(calls)=={'1.1'}
        assert w.poll_timer.interval()==500
        assert w.core_timer.interval()<=100
    finally:w.close()


def test_keyboard_section_shortcuts_and_focus_indicator(shell):
    app,w=shell;w.activateWindow();w.raise_();app.processEvents()
    QTest.keyClick(w,Qt.Key_3,Qt.ControlModifier);app.processEvents()
    assert w.main_tabs.currentIndex()==2
    QTest.keyClick(w,Qt.Key_K,Qt.ControlModifier);app.processEvents()
    assert w.subtab_picker.hasFocus()
    assert w.subtab_picker.accessibleName()=='Subtab navigation'
    assert w.main_tabs.tabBar().accessibleName()=='Main sections'


def test_theme_does_not_repolish_all_windows_on_each_open(shell,monkeypatch):
    from sfm_fx_new_age.ui.theme import apply_theme
    app,w=shell;calls=[];previous=app.setStyleSheet
    monkeypatch.setattr(app,'setStyleSheet',lambda value:(calls.append(value),previous(value)))
    apply_theme(app);apply_theme(app)
    assert calls==[]


def test_empty_component_inspection_is_explicitly_unevaluated():
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    app=QApplication.instance() or QApplication([]);r=ApplicationRuntime();w=create_main_window(r)
    try:
        from sfm_fx_new_age.ui.scanner_overview import ScannerOverview
        panel=ScannerOverview(r.api(2),None);panel.refresh()
        assert 'No market data' in panel.summary.text()
        assert 'not evaluated' in panel.summary.text()
        assert panel.picker.count()==44
    finally:panel.close();w.close();r.close()


def test_compact_chart_and_queue_actions_need_no_outer_scrolling(shell):
    app,w=shell;w.resize(960,640);app.processEvents()
    chart=w.main_tabs.widget(0).widget(0).widget()
    assert chart.canvas.width()>400 and chart.canvas.height()>150
    assert w.subtab_picker.count()==len(PAIRS)
    w.main_tabs.setCurrentIndex(3);app.processEvents()
    scroll=w.main_tabs.currentWidget().currentWidget();panel=scroll.widget()
    # Strategy research and the original deliberate Issue queue are separate.
    panel.pages.setCurrentIndex(1);app.processEvents()
    assert scroll.verticalScrollBar().maximum()==0
    assert panel.table.horizontalScrollBar().maximum()==0
    for button in panel.buttons.values():
        assert button.mapTo(scroll.viewport(),QPoint(0,button.height())).y()<=scroll.viewport().height()
    assert panel.acknowledge.mapTo(scroll.viewport(),QPoint(0,panel.acknowledge.height())).y()<=scroll.viewport().height()
    panel.table.selectRow(0)
    panel.buttons['CANCEL_SIGNAL'].click();app.processEvents()
    assert 'ACCEPTED' in panel.result_label.text()
    assert scroll.verticalScrollBar().maximum()==0
