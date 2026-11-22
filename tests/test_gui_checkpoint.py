import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton

from sfm_fx_new_age.app import SubtabPanel, create_main_window
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.ui.theme import COLORS, FONT


def test_calculator_palette_and_real_issue_button_flow(runtime):
    app=QApplication.instance() or QApplication([])
    window=create_main_window(runtime)
    window.show();app.processEvents()
    try:
        assert COLORS['bg']=='#0B1220' and COLORS['panel']=='#141F30'
        assert FONT=='DejaVu Sans'
        assert '#56BDF5' in app.styleSheet()
        window.main_tabs.setCurrentIndex(3)
        nested=window.main_tabs.widget(3)
        workspace=nested.widget(0).widget()
        workspace.pages.setCurrentIndex(1);app.processEvents();panel=workspace.queue
        assert isinstance(panel,SubtabPanel)
        assert panel.table.rowCount()==1
        issue=panel.findChild(QPushButton,'command_4_1_issue')
        assert issue.text()=='Issue'
        assert not issue.isEnabled()
        panel.table.selectRow(0)
        panel.findChild(QCheckBox,'researchAcknowledgement').setChecked(True)
        app.processEvents()
        assert issue.isEnabled()
        QTest.mouseClick(issue,Qt.LeftButton)
        app.processEvents()
        assert runtime.database.orders()[0]['state']=='ACCEPTED_PENDING'
        assert 'ACCEPTED_PENDING' in panel.result_label.text()
        assert not issue.isEnabled()
        assert 'SYNTHETIC FIXTURE' in window.session_label.text()
    finally:window.close()


def test_connector_footer_uses_current_state_without_claiming_account_login():
    app=QApplication.instance() or QApplication([])
    runtime=ApplicationRuntime();window=create_main_window(runtime)
    try:
        runtime.connector.state='AUTHENTICATED'
        window.show();app.processEvents();window.refresh_current()
        assert 'cTrader adapter authenticated' in window.statusBar().currentMessage()
        assert 'No account selected' in window.account_label.text()
    finally:
        window.close();runtime.close()


def test_32_user_pages_and_10_internal_contracts_can_be_refreshed(runtime):
    app=QApplication.instance() or QApplication([])
    window=create_main_window(runtime)
    window.show();app.processEvents()
    visited=[]
    try:
        for tab in range(4):
            if tab==1:
                assert len(runtime.api(2).definitions)==10
                for definition in runtime.api(2).definitions:runtime.api(2).snapshot(definition.subtab_id)
                continue
            window.main_tabs.setCurrentIndex(tab)
            nested=window.main_tabs.widget(tab)
            for index in range(nested.count()):
                nested.setCurrentIndex(index);window.refresh_current();app.processEvents()
                panel=nested.widget(index).widget()
                assert panel.width()>0 and panel.height()>0
                visited.append(panel.objectName())
        assert len(visited)==len(set(visited))==32
        assert not runtime.router.errors
        window.resize(1000,680);app.processEvents()
        assert window.width()==1000
        assert window.subtab_picker.count()==9
        assert not window.main_tabs.widget(3).tabBar().isVisible()
        window.subtab_picker.setCurrentIndex(4);app.processEvents()
        assert window.main_tabs.widget(3).currentIndex()==4
        assert window.subtab_picker.currentText()=='Account Link and State'
    finally:window.close()


def test_normal_gui_has_no_synthetic_values_or_automatic_issue():
    app=QApplication.instance() or QApplication([])
    r=ApplicationRuntime()
    window=create_main_window(r)
    try:
        panel=window.main_tabs.widget(3).widget(0).widget()
        assert panel.table.rowCount()==0
        assert not panel.findChild(QPushButton,'command_4_1_issue').isEnabled()
        assert 'disconnected' in window.session_label.text()
    finally:window.close();r.close()
