# NA-D49 — Architecture Decision Register and Rationale

**Document:** NA-D49 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** RETROSPECTIVE_DECISION_RECORDS · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Register purpose
The companion ADRs reconstruct rationale for decisions demonstrable in the current source and dated New Age diary. They are labelled retrospective as-built records, not newly signed approvals, exact historical quotations or permission to change behavior. A new proposal must be separately identified and cannot overwrite an existing decision's history.

## Decision set
| ADR | Decision | Main consequence |
|---|---|---|
| 001 | Local modular desktop/shared runtime | No duplicate per-tab service ownership |
| 002 | Four workspaces and 42 stable backend contracts | Tab 2 stays a dynamic tools workspace |
| 003 | Scoped TabApi and command/data allowlists | Tabs are consumers, not connector/SQL owners |
| 004 | Broker/endpoint/account/origin plus epoch identity | Saved rows cannot restore current authority |
| 005 | Causal immutable observation history | Corrections do not rewrite past as-of results |
| 006 | One deliberate pending Limit Issue edge | Binding/preview never submit |
| 007 | Durable reservation and UNKNOWN reconciliation | No blind retry after possible send |
| 008 | Strict source semantics with disclosed alternatives | Quote activity is not relabelled executed volume |
| 009 | SQLite WAL/FULL with operation savepoints | Durability and atomic workflow boundaries stay explicit |
| 010 | Owner admission plus pure spawned math | Parallelism does not distribute authority |
| 011 | Isolated replay and explicit study clocks | Historical models cannot become live permission |
| 012 | Versioned semantics and literal-choice preservation | Upgrades do not invent user preferences |

## Decision form
Each record states context, observed decision, alternatives, consequences, source anchors and revisitation triggers. Proposed alternatives are analysis, not evidence that they were historically evaluated by the owner. Date of documentation differs from date of original product decision.

## Change control
Revisit a decision only for a named requirement or measured defect. Compare affected owners/tests before changing it. Record a successor ADR rather than editing history to make the earlier decision appear different. A document set cannot retroactively approve an unimplemented account-risk policy, autonomous protection or provider entitlement.

## Source and authority anchors

- [PROGRESS.md](../../PROGRESS.md#L1)
- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [contracts/strategy_signals.py](../../src/sfm_fx_new_age/contracts/strategy_signals.py#L13)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
