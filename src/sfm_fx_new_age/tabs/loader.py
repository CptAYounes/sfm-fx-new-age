from __future__ import annotations

from importlib import import_module

from .base import TabPlugin


def load_tab_plugins() -> dict[int, TabPlugin]:
    plugins: dict[int, TabPlugin] = {}
    for tab_id in range(1, 5):
        module = import_module(f"sfm_fx_new_age.tabs.tab{tab_id}.plugin")
        plugin = module.build_plugin()
        if not isinstance(plugin, TabPlugin):
            raise TypeError(f"Tab {tab_id} build_plugin() returned {type(plugin)!r}")
        if plugin.tab_id != tab_id:
            raise ValueError(f"Tab plugin identity mismatch: expected {tab_id}, got {plugin.tab_id}")
        plugins[tab_id] = plugin
    return plugins
