# NA-D02 — Stakeholders, User Stories and Use Cases

**Document:** NA-D02 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** DERIVED_REQUIREMENTS · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Stakeholder responsibilities
| Role | Need | Boundary |
|---|---|---|
| Operator/product owner | Reliable inspection and deliberate action | Selects account, methods, units and Issue |
| Maintainer | Recoverable changes and exact evidence | Changes source through declared owners |
| Analytical extension author | Add research producers and tools | No connector, SQL or order-service ownership |
| Reviewer | Determine what a result actually proves | Keeps fixtures, native observations and broker effects separate |
| Broker/venue provider | Protocol-compatible requests | Supplies only its declared source scope |

## UC-01 — Inspect observed market data
Precondition: a current authenticated selected source exists, or the user explicitly opens historical/replay data. Select a pair and frame in Chart Engine; inspect completed bars, source labels and availability. A missing history lane remains unavailable. A historical cutoff never receives newer broker inventory. Postcondition: inspection only; no signal binding or broker request.

## UC-02 — Research a method and bind locally
Enable a method in Tab 3, then open Tab 4 Strategy signals. The system evaluates its disclosed policy and reports Off, Waiting, missing-data, No setup, stale, invalidated, expired, blocked or actionable research state. Review source roots and explicit units. Bind only the current qualified revision. Postcondition: a queued local proposal; zero broker submissions.

## UC-03 — Issue a pending Limit
Precondition: the local proposal is queued at the selected revision, the account has authenticated trading scope, reconciliation is ready and current preflight succeeds. The human acknowledges research and selects Issue. The core reserves once, invokes transport and records the native result. An uncertain result becomes UNKNOWN, not a retry prompt.

## UC-04 — Recover after restart
The program reloads durable facts and preferences but not authentication authority. Reauthenticate the exact namespace and reconcile uncertain orders. Never regenerate a new order merely because acknowledgement was lost.

## UC-05 — Historical study
Choose an immutable replay dataset, one supported marker model and explicit study assumptions. Run and reopen the saved report. Ambiguous outcomes remain unknown; the report cannot bind a live candidate or select an account.

## Source and authority anchors

- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [services/workflow.py](../../src/sfm_fx_new_age/services/workflow.py#L15)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [tabs/tab3/public_workspace.py](../../src/sfm_fx_new_age/tabs/tab3/public_workspace.py#L12)
- [tabs/tab4/strategy_signals.py](../../src/sfm_fx_new_age/tabs/tab4/strategy_signals.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
