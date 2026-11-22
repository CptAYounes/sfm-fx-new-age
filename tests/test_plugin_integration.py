import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

from PySide6.QtWidgets import QApplication, QLabel
import pytest

import sfm_fx_new_age.app as app_module
from sfm_fx_new_age.core.tab_api import TabApi
from sfm_fx_new_age.tabs.base import TabPlugin


def test_all_four_plugin_lanes_replace_real_shell_panels_without_shared_edits(runtime,monkeypatch):
    app=QApplication.instance() or QApplication([])
    plugins={tab:TabPlugin(tab) for tab in range(1,5)}
    seen=[]
    def factory(api,model,parent):
        assert isinstance(api,TabApi)
        snapshot=api.snapshot(model.subtab_id)
        seen.append((api.tab_id,snapshot.subtab_id))
        return QLabel(f'Plugin consumes shared snapshot {snapshot.subtab_id}',parent)
    for tab,plugin in plugins.items():
        if tab==2:plugin.register_tool('test-tool','Test tool',lambda api,parent:factory(api,runtime.api(2).definitions[0],parent))
        else:plugin.register(f'{tab}.1',factory)
    monkeypatch.setattr(app_module,'load_tab_plugins',lambda:plugins)
    window=app_module.create_main_window(runtime)
    try:
        assert seen==[(1,'1.1'),(3,'3.1'),(4,'4.1')] # tools are lazy and never created at startup
        frame=window.tools.open_tool('test-tool')
        assert isinstance(frame.widget().widget(),QLabel) and seen[-1]==(2,'2.1')
        for index in range(4):
            if index==1:continue
            widget=window.main_tabs.widget(index).widget(0).widget()
            assert isinstance(widget,QLabel)
    finally:window.close()


def test_plugin_rejects_nonexistent_subtab_and_duplicate_registration():
    plugin=TabPlugin(1)
    with pytest.raises(ValueError):plugin.register('1.999',lambda *args:None)
    factory=lambda *args:None
    plugin.register('1.1',factory)
    with pytest.raises(ValueError):plugin.register('1.1',factory)
