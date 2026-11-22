from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from .enums import CommandStatus, Freshness, Priority


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(freeze(item) for item in value)
    return value


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [thaw(item) for item in value]
    return value


def _frozen(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return freeze(value or {})


@dataclass(frozen=True, slots=True)
class Event:
    topic: str
    source_component: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.P2
    partition_key: str = "GLOBAL"
    source_epoch: str = "LOCAL-FOUNDATION"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    produced_at_utc: str = field(default_factory=utc_now)
    freshness: Freshness = Freshness.CURRENT

    def __post_init__(self) -> None:
        if not self.topic or not self.source_component:
            raise ValueError("topic and source_component are required")
        object.__setattr__(self, "payload", _frozen(self.payload))


@dataclass(frozen=True, slots=True)
class Command:
    name: str
    target_component: str
    source_view: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.P2
    command_id: str = field(default_factory=lambda: str(uuid4()))
    created_at_utc: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.name or not self.target_component or not self.source_view:
            raise ValueError("command name, target_component and source_view are required")
        object.__setattr__(self, "payload", _frozen(self.payload))


@dataclass(frozen=True, slots=True)
class CommandResult:
    command_id: str
    status: CommandStatus
    message: str
    emitted_topics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SubtabDefinition:
    main_tab: int
    main_tab_title: str
    subtab_id: str
    title: str
    backend_owner: str
    subscribed_topics: tuple[str, ...]
    commands: tuple[str, ...]
    priority: Priority
    purpose: str


@dataclass(frozen=True, slots=True)
class RouteDefinition:
    source: str
    destination: str
    topic: str
    trigger: str
    priority: Priority
    rule: str
    status: str
