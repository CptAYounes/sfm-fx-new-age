from sfm_fx_new_age.tabs.base import TabPlugin


def build_plugin() -> TabPlugin:
    """Return the independently owned Tab 4 widget contribution registry."""
    from sfm_fx_new_age.ui.inspection_panels import InspectionPanel,SignalDetailPanel
    from .pending import PendingOrdersPanel
    from .capital import CapitalPanel
    from .strategy_signals import SignalQueueWorkspace
    plugin=TabPlugin(tab_id=4)
    plugin.register('4.1',SignalQueueWorkspace)
    for i in range(2,10):plugin.register('4.'+str(i),SignalDetailPanel if i==2 else PendingOrdersPanel if i==3 else CapitalPanel if i==7 else InspectionPanel)
    return plugin
