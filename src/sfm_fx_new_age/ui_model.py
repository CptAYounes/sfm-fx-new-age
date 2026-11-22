from __future__ import annotations

from dataclasses import dataclass

from sfm_fx_new_age.core.runtime import ApplicationRuntime


@dataclass(frozen=True, slots=True)
class SubtabViewModel:
    subtab_id: str
    title: str
    purpose: str
    backend_owner: str
    topics: tuple[str, ...]
    commands: tuple[str, ...]
    availability: str


@dataclass(frozen=True, slots=True)
class TabViewModel:
    tab_id: int
    title: str
    subtabs: tuple[SubtabViewModel, ...]


def build_ui_model(runtime: ApplicationRuntime) -> tuple[TabViewModel, ...]:
    return tuple(
        TabViewModel(
            tab.tab_id,
            tab.title,
            tuple(
                SubtabViewModel(
                    bridge.definition.subtab_id,
                    bridge.definition.title,
                    bridge.definition.purpose,
                    bridge.definition.backend_owner,
                    bridge.definition.subscribed_topics,
                    bridge.definition.commands,
                    bridge.projection().availability.value,
                )
                for bridge in tab.subtabs
            ),
        )
        for tab in runtime.tabs
    )
