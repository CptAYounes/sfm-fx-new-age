from sfm_fx_new_age.tabs.base import TabPlugin


def build_plugin() -> TabPlugin:
    """Return the independently owned Tab 2 widget contribution registry."""
    from .calculator import CalculatorWidget
    plugin=TabPlugin(tab_id=2)
    plugin.register_tool('forex-calculator','Forex P/L Calculator',lambda api,parent:CalculatorWidget(parent,api=api))
    return plugin
