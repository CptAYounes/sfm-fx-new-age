from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from sfm_fx_new_age.contracts.enums import Availability
from sfm_fx_new_age.contracts.models import Event, SubtabDefinition, thaw


@dataclass(frozen=True, slots=True)
class ViewProjection:
    subtab_id: str
    version: int
    availability: Availability
    data: dict[str, Any] = field(default_factory=dict)


class ProjectionStore:
    def __init__(self, definitions: tuple[SubtabDefinition, ...]) -> None:
        self._lock = RLock()
        self._items = {
            definition.subtab_id: ViewProjection(
                subtab_id=definition.subtab_id,
                version=0,
                availability=Availability.WIRED,
                data={
                    "backend_owner": definition.backend_owner,
                    "last_topic": None,
                    "event_count": 0,
                },
            )
            for definition in definitions
        }

    def apply_event(self, subtab_id: str, event: Event) -> ViewProjection:
        with self._lock:
            current = self._items[subtab_id]
            data = dict(current.data)
            data.update({
                "last_topic": event.topic,
                "last_event_id": event.event_id,
                "last_payload": thaw(event.payload),
                "event_count": int(data.get("event_count", 0)) + 1,
            })
            updated = ViewProjection(subtab_id, current.version + 1, current.availability, data)
            self._items[subtab_id] = updated
            return updated

    def get(self, subtab_id: str) -> ViewProjection:
        with self._lock:
            from copy import deepcopy
            current = self._items[subtab_id]
            return ViewProjection(current.subtab_id, current.version, current.availability, deepcopy(current.data))

    def all(self) -> tuple[ViewProjection, ...]:
        with self._lock:
            return tuple(self.get(identity) for identity in self._items)
