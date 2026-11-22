from pathlib import Path

from sfm_fx_new_age.checks import run_checks
from sfm_fx_new_age.contracts.registry import load_routes, load_subtabs


def test_exact_four_tab_42_subtab_contract() -> None:
    definitions = load_subtabs()
    assert len(definitions) == 42
    assert {tab: sum(item.main_tab == tab for item in definitions) for tab in range(1, 5)} == {
        1: 10, 2: 10, 3: 13, 4: 9,
    }
    assert len({item.subtab_id for item in definitions}) == 42


def test_issue_is_active_new_order_language() -> None:
    definitions = load_subtabs()
    signal_queue = next(item for item in definitions if item.subtab_id == "4.1")
    assert "ISSUE" in signal_queue.commands
    assert "CANCEL_ALL_UNISSUED" in signal_queue.commands
    assert next(item for item in definitions if item.subtab_id == "4.2").title.startswith("ISSUE")
    assert run_checks()["legacy_execution_term_matches"] == []


def test_routes_reference_registered_components() -> None:
    result = run_checks()
    assert result["unknown_owners"] == []
    assert result["unknown_route_components"] == []
    assert len(load_routes()) == 41


def test_single_progress_diary_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "PROGRESS.md").is_file()
    competing = [
        path for path in root.rglob("*.md")
        if path.name.upper() in {"STATUS.MD", "HANDOFF.MD", "TODO.MD", "NOTES.MD", "DIARY.MD"}
    ]
    assert competing == []
