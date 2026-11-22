import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QLabel

from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.tabs.base import TabPlugin


def test_all_four_plugin_consumers_receive_updates_and_shell_disposes_them(runtime, monkeypatch):
    import sfm_fx_new_age.app as app_module
    app = QApplication.instance() or QApplication([])
    plugins = {tab: TabPlugin(tab) for tab in (1, 2, 3, 4)}
    seen = {tab: [] for tab in plugins}
    apis = {}
    for tab, plugin in plugins.items():
        def factory(api, model, parent=None, tab=tab):
            apis[tab] = api
            widget = QLabel('Independent tab consumer', parent)
            api.subscribe_snapshots(model.subtab_id, seen[tab].append)
            return widget
        if tab==2:plugin.register_tool('test-consumer','Test consumer',lambda api,parent:factory(api,runtime.api(2).definitions[0],parent,tab=2))
        else:plugin.register(f'{tab}.1', factory)
    monkeypatch.setattr(app_module, 'load_tab_plugins', lambda: plugins)
    baseline = runtime.router.metrics()['subscriber_count']
    window = create_main_window(runtime)
    window.show(); app.processEvents()
    window.tools.open_tool('test-consumer');app.processEvents()
    assert not window.windowIcon().isNull()
    assert window.main_tabs.count() == 4
    runtime.api(1).command('1.1', 'SELECT_PAIR', {'symbol': 'USDCHF'})
    assert all(values[-1].data['symbol'] == 'USDCHF' for values in seen.values())
    window.close(); app.processEvents()
    assert runtime.router.metrics()['subscriber_count'] == baseline
    assert all(api._closed for api in apis.values())
    assert not runtime.closed  # injected runtime belongs to the coordinator, not a tab
