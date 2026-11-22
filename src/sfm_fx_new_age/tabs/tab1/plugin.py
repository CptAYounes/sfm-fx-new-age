from sfm_fx_new_age.tabs.base import TabPlugin


def build_plugin() -> TabPlugin:
    """Return the independently owned Tab 1 widget contribution registry."""
    return TabPlugin(tab_id=1)
