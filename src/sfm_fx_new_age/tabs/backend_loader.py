"""Headless lane extension discovery, separate from Qt widget imports."""
from importlib import import_module
from importlib.util import find_spec


def load_analytical_installers():
    name='sfm_fx_new_age.tabs.tab3.backend'
    if find_spec(name) is None:return ()
    module=import_module(name)
    install=getattr(module,'install',None)
    if not callable(install):raise ValueError('Tab 3 backend module must export install(AnalyticalExtensionApi)')
    return (install,)
