from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from sfm_fx_new_age.contracts.registry import load_subtabs

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from sfm_fx_new_age.core.tab_api import TabApi
    from sfm_fx_new_age.ui_model import SubtabViewModel

WidgetFactory = Callable[["TabApi", "SubtabViewModel", "QWidget | None"], "QWidget"]
ToolFactory = Callable[["TabApi", "QWidget | None"], "QWidget"]


@dataclass(frozen=True,slots=True)
class ToolContribution:
    tool_id:str
    title:str
    factory:ToolFactory


@dataclass(slots=True)
class TabPlugin:
    """Stable extension boundary for one independently owned main-tab lane."""

    tab_id: int
    factories: dict[str, WidgetFactory] = field(default_factory=dict)
    tools: dict[str,ToolContribution] = field(default_factory=dict)

    def register_tool(self,tool_id:str,title:str,factory:ToolFactory)->None:
        if self.tab_id!=2:raise ValueError('Only the Trading Tools lane can register tool windows')
        if not tool_id or not title or not callable(factory):raise ValueError('Tool identity, title and factory are required')
        if tool_id in self.tools:raise ValueError('Duplicate tool identity')
        self.tools[tool_id]=ToolContribution(tool_id,title,factory)

    def register(self, subtab_id: str, factory: WidgetFactory) -> None:
        expected_prefix = f"{self.tab_id}."
        if not subtab_id.startswith(expected_prefix):
            raise ValueError(f"Tab {self.tab_id} plugin cannot own {subtab_id}")
        if subtab_id not in {d.subtab_id for d in load_subtabs() if d.main_tab == self.tab_id}:
            raise ValueError(f"Unknown subtab identity: {subtab_id}")
        if subtab_id in self.factories:
            raise ValueError(f"Duplicate widget factory: {subtab_id}")
        self.factories[subtab_id] = factory

    def create_widget(
        self,
        api: "TabApi",
        model: "SubtabViewModel",
        parent: "QWidget | None" = None,
    ) -> "QWidget | None":
        factory = self.factories.get(model.subtab_id)
        return None if factory is None else factory(api, model, parent)
