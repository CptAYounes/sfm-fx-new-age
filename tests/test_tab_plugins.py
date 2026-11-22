import pytest

from sfm_fx_new_age.tabs.base import TabPlugin
from sfm_fx_new_age.tabs.loader import load_tab_plugins


def test_all_four_parallel_tab_lanes_load() -> None:
    plugins = load_tab_plugins()
    assert sorted(plugins) == [1, 2, 3, 4]
    assert set(plugins[3].factories)=={f'3.{i}' for i in range(1,14)}
    assert set(plugins[4].factories)=={f'4.{i}' for i in range(1,10)}
    assert not plugins[1].factories and not plugins[2].factories


def test_tab_plugin_cannot_claim_another_tabs_subtab() -> None:
    plugin = TabPlugin(tab_id=1)
    with pytest.raises(ValueError):
        plugin.register("2.1", lambda runtime, model, parent: None)  # type: ignore[arg-type]
