from __future__ import annotations

import csv
from functools import lru_cache
from importlib.resources import files

from .enums import Priority
from .models import RouteDefinition, SubtabDefinition

_TAB_TITLES = {
    1: "Chart Engine",
    2: "Trading Tools",
    3: "Strategy Research, Scanner & LogicTiles",
    4: "Signals & cTrader Trading Operations",
}


def tab_titles() -> dict[int, str]:
    return dict(_TAB_TITLES)


def _rows(name: str) -> list[dict[str, str]]:
    path = files("sfm_fx_new_age.contracts.data").joinpath(name)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _items(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(";") if item.strip())


@lru_cache(maxsize=1)
def load_subtabs() -> tuple[SubtabDefinition, ...]:
    result = tuple(
        SubtabDefinition(
            main_tab=int(row["main_tab"]),
            main_tab_title=_TAB_TITLES[int(row["main_tab"])],
            subtab_id=row["subtab_id"],
            title=row["subtab"],
            backend_owner=row["backend_owner"],
            subscribed_topics=_items(row["subscribed_topics"]),
            commands=_items(row["gui_to_owner_commands"]),
            priority=Priority[row["presentation_priority"]],
            purpose=row["purpose"],
        )
        for row in _rows("tab_subtab_wiring.csv")
    )
    counts = {tab: sum(item.main_tab == tab for item in result) for tab in _TAB_TITLES}
    if len(result) != 42 or counts != {1: 10, 2: 10, 3: 13, 4: 9}:
        raise RuntimeError(f"Invalid tab registry: total={len(result)} counts={counts}")
    if len({item.subtab_id for item in result}) != len(result):
        raise RuntimeError("Duplicate subtab identity")
    return result


@lru_cache(maxsize=1)
def load_routes() -> tuple[RouteDefinition, ...]:
    return tuple(
        RouteDefinition(
            source=row["from"],
            destination=row["to"],
            topic=row["topic"],
            trigger=row["trigger"],
            priority=Priority[row["priority"]],
            rule=row["rule"],
            status=row["status"],
        )
        for row in _rows("host_typed_routes.csv")
    )
