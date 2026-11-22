from sfm_fx_new_age.contracts.enums import CommandStatus, Priority
from sfm_fx_new_age.contracts.models import Event
from sfm_fx_new_age.core.runtime import ApplicationRuntime


def test_runtime_builds_parallel_tab_boundaries() -> None:
    runtime = ApplicationRuntime()
    assert runtime.architecture_summary()["subtabs_by_tab"] == {"1": 10, "2": 10, "3": 13, "4": 9}
    assert [tab.tab_id for tab in runtime.tabs] == [1, 2, 3, 4]


def test_event_reaches_only_subscribed_view_projections() -> None:
    runtime = ApplicationRuntime()
    before_w1 = runtime.subtab("1.2").projection().version
    before_signal = runtime.subtab("4.1").projection().version
    delivered = runtime.publish(Event("BAR.FINAL", "BAR_AND_QUOTE_CACHE", {"symbol": "EURUSD"}, Priority.P1))
    assert delivered == 1
    assert runtime.subtab("1.2").projection().version == before_w1 + 1
    assert runtime.subtab("4.1").projection().version == before_signal


def test_issue_requires_explicit_user_and_selected_signal() -> None:
    runtime = ApplicationRuntime()
    bridge = runtime.subtab("4.1")
    assert bridge.dispatch("ISSUE", {"signal_id": "sig-1"}).status is CommandStatus.REJECTED
    assert bridge.dispatch("ISSUE", {"user_initiated": True}).status is CommandStatus.REJECTED
    result = bridge.dispatch("ISSUE", {"user_initiated": True, "signal_id": "sig-1", "revision": 1})
    assert result.status is CommandStatus.REJECTED
    assert runtime.database.orders() == []
    assert runtime.router.queued_count == 0
    runtime.close()


def test_unimplemented_owner_is_truthful() -> None:
    runtime = ApplicationRuntime()
    result = runtime.subtab("2.3").dispatch("CONNECT", {})
    assert result.status is CommandStatus.REJECTED  # Real connector is installed but unconfigured; no network attempt.
    runtime.close()
