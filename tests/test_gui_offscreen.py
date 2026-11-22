import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QTabWidget
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.tabs.tab2.workspace import ToolsWorkspace


def test_four_user_tabs_and_42_backend_contracts():
    app=QApplication.instance() or QApplication([]);window=create_main_window()
    try:
        assert window.objectName()=='sfmFxNewAgeMainWindow'
        assert window.main_tabs.count()==4
        assert window.main_tabs.tabText(0)=='Chart Engine'
        assert window.main_tabs.tabText(1)=='Trading Tools'
        assert isinstance(window.main_tabs.widget(1),ToolsWorkspace)
        assert [len(window.tab_apis[i].definitions) for i in (1,2,3,4)]==[10,10,13,9]
        assert [window.main_tabs.widget(i).count() for i in (0,2,3)]==[10,13,9]
        assert window.main_tabs.tabText(2).replace('&&','&')=='Strategy Research, Scanner & LogicTiles'
        assert window.main_tabs.tabText(3).replace('&&','&')=='Signals & cTrader Trading Operations'
    finally:window.close()
