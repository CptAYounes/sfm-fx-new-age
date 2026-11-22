# NA-D38 — Acceptance Test Specification and Release Criteria

**Document:** NA-D38 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** DERIVED_ACCEPTANCE_SPECIFICATION · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Acceptance scenarios
| ID | Preconditions/action | Required observable result |
|---|---|---|
| AC-01 | Fresh normal offline startup | Four workspaces, no fixture prices, no network/order side effects |
| AC-02 | Query every declared view contract | 42 scoped immutable snapshots, correct 10/10/13/9 identity set |
| AC-03 | Enable each method on labelled deterministic input | Exact analytical/policy/Tab-4 positive paths or truthful non-signal states |
| AC-04 | Bind selected eligible current opportunity | Explicit native-valid units; local queue only; no transport send |
| AC-05 | Issue deliberately under fixture preflight | One reservation/send and cross-tab identity; double click refused |
| AC-06 | Lose submit acknowledgement/restart | UNKNOWN persists; matching reconcile resolves without resend |
| AC-07 | Withdraw one pair/source or reconnect | Old authority/results refused; healthy sibling lanes continue |
| AC-08 | Change review selection/revision | Acknowledgement resets and stale binding refuses |
| AC-09 | Run supported historical study | Immutable saved/reopenable result, explicit clock and unresolved ambiguity |
| AC-10 | Close tool/runtime | Consumer disposal and joined task-owned children |
| AC-11 | Source/installed acceptance | Exact case/outcome/product membership parity |
| AC-12 | Native finite operating qualification | Original policy limits, source-bound lifecycle, zero unauthorized mutations |

## Preconditions matter
AC-03 fixture positives are software proof, not genuine current market setups. AC-05 does not authorize a real account request. AC-12 needs an intentionally isolated accepted harness and explicit read-only scope; it must not be casually executed against the user's normal database.

## Release decision
Completion requires every declared acceptance row, source identity and evidence class to be known. A failed attempt stays failed even if a later one succeeds. Optional excluded capabilities remain named but do not reopen accepted scope. A current source mismatch invalidates reuse of unchanged-source claims for the changed files.

## Unperformed acceptance
No new live-market, installed-wheel, clean-container, sustained timing or broker-action acceptance was executed in this documentation task. Their retained evidence is cited with original dates. Human signoff is not supplied by generation of these documents; owner acceptance of future risk/scope changes remains explicit.

## Source and authority anchors

- [tests/test_order_flow.py](../../tests/test_order_flow.py#L15)
- [tests/test_strategy_signal_positive.py](../../tests/test_strategy_signal_positive.py#L14)
- [tests/test_strategy_signal_lifecycle.py](../../tests/test_strategy_signal_lifecycle.py#L19)
- [tests/test_workspace_ui_workflows.py](../../tests/test_workspace_ui_workflows.py#L22)
- [tests/test_backtest_workflow.py](../../tests/test_backtest_workflow.py#L9)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
