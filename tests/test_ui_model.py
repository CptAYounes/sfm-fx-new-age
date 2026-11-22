from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.ui_model import build_ui_model


def test_ui_model_exposes_exact_registry() -> None:
    model = build_ui_model(ApplicationRuntime())
    assert len(model) == 4
    assert [len(tab.subtabs) for tab in model] == [10, 10, 13, 9]
    assert sum(len(tab.subtabs) for tab in model) == 42
