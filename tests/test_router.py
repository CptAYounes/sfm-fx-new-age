from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.contracts.models import Event
from sfm_fx_new_age.core.router import PriorityEventRouter


def test_priority_router_delivers_p0_before_p3() -> None:
    router = PriorityEventRouter()
    delivered: list[str] = []
    router.subscribe("TEST", lambda event: delivered.append(str(event.payload["name"])))
    router.publish(Event("TEST", "TEST_SOURCE", {"name": "low"}, Priority.P3))
    router.publish(Event("TEST", "TEST_SOURCE", {"name": "high"}, Priority.P0))
    assert router.drain() == 2
    assert delivered == ["high", "low"]


def test_last_known_is_partitioned() -> None:
    router = PriorityEventRouter()
    event = Event("BAR.FINAL", "CACHE", {"close": "1.1"}, partition_key="EURUSD:D1")
    router.publish(event)
    router.drain()
    assert router.last_known("BAR.FINAL", "EURUSD:D1") == event
