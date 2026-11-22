from sfm_fx_new_age.tabs.base import TabPlugin


def build_plugin() -> TabPlugin:
    """Return the independently owned Tab 3 widget contribution registry."""
    from sfm_fx_new_age.ui.inspection_panels import InspectionPanel,ReplayPanel
    from .workspace import StrategyPanel
    from .public_workspace import PublicStrategiesPanel
    from .authoring import RuleBuilderPanel,ParameterEditorPanel
    plugin=TabPlugin(tab_id=3)
    for i in range(1,14):plugin.register('3.'+str(i),PublicStrategiesPanel if i==1 else RuleBuilderPanel if i==10 else ParameterEditorPanel if i==11 else ReplayPanel if i==12 else StrategyPanel if i==5 else InspectionPanel)
    return plugin
