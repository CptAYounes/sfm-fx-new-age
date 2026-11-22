from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sfm_fx_new_age.contracts.enums import Availability, CommandStatus
from sfm_fx_new_age.contracts.models import Command, CommandResult

CommandHandler = Callable[[Command], CommandResult]


@dataclass(frozen=True, slots=True)
class ComponentState:
    component_id: str
    availability: Availability
    detail: str


class ComponentRegistry:
    def __init__(self, component_ids: set[str]) -> None:
        self._states = {
            component_id: ComponentState(
                component_id=component_id,
                availability=Availability.WIRED,
                detail="Foundation contract registered; domain implementation may remain pending.",
            )
            for component_id in sorted(component_ids)
        }
        self._handlers: dict[str, CommandHandler] = {}

    def bind_handler(self, component_id: str, handler: CommandHandler) -> None:
        if component_id not in self._states:
            raise KeyError(component_id)
        self._handlers[component_id] = handler

    def dispatch(self, command: Command) -> CommandResult:
        if command.target_component not in self._states:
            return CommandResult(command.command_id, CommandStatus.REJECTED, "Unknown target component")
        handler = self._handlers.get(command.target_component)
        if handler is None:
            return CommandResult(
                command.command_id,
                CommandStatus.NOT_IMPLEMENTED,
                f"{command.target_component} is contract-wired but has no domain handler yet",
            )
        return handler(command)

    def set_state(self, component_id: str, availability: Availability, detail: str) -> None:
        if component_id not in self._states:
            raise KeyError(component_id)
        self._states[component_id] = ComponentState(component_id, availability, detail)

    def states(self) -> tuple[ComponentState, ...]:
        return tuple(self._states.values())
