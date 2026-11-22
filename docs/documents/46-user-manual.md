# NA-D46 — User Guide and Operator Workflows

**Document:** NA-D46 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** OPERATOR_GUIDE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Connect without confusing permissions
Open Sign in/Manage cTrader connection and use your registered application's normal authorization path. Select the intended authenticated account. Demo/live class is metadata; the application still needs actual permission scope and current source state. Saved reconnect may resume only the remembered consented session. This guide never asks you to paste secrets into a chat.

## Inspect charts and tools
In Chart Engine select a pair and W1/D1/H4/H1 view. Use Latest/Fit, zoom/pan, source labels, Evidence and Projection details. Old weekend prices are snapshots. Drawings/rulers/settings and calculator scenarios are local only. Trading Tools opens contained calculator/tool windows; manual values are retained until you explicitly adopt or replace a handoff.

## Use research signals
1. Open Tab 3 Strategy and Recipe Library and enable desired methods.
2. Read Method details: numerical rules, warm-up, genuine inputs and disclosed entry policy.
3. Open Tab 4 Strategy signals and choose pair/frame.
4. Understand the state: no input or no trigger is not a live setup.
5. For an eligible current row, review source/geometry and enter explicit legal native units.
6. Select Bind local proposal. This only queues a proposal.
7. Review the separate Issue queue/preview. Issue is a new deliberate broker action, never implied by the earlier steps.

## Understand risk and state
Internal invalidation/target lines are research geometry, not broker protection or guaranteed fills/loss limits. Research monetary estimates are gross scenarios and do not grant account-wide risk permission. UNKNOWN broker state requires reconciliation, not repeated Issue. Canceling an unissued signal is different from canceling a native pending order.

## Run historical research
In Backtesting and Walk Forward choose an immutable dataset, one of the 14 supported marker models and explicit timing/cost assumptions. Save/reopen the report. Ambiguity and unfinished trades remain unresolved. The report cannot create a live signal/order and does not certify profitability.

## Source and authority anchors

- [README.md](../../README.md#L1)
- [app.py](../../src/sfm_fx_new_age/app.py#L30)
- [tabs/tab3/public_workspace.py](../../src/sfm_fx_new_age/tabs/tab3/public_workspace.py#L12)
- [tabs/tab4/strategy_signals.py](../../src/sfm_fx_new_age/tabs/tab4/strategy_signals.py#L12)
- [ui/research_study.py](../../src/sfm_fx_new_age/ui/research_study.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
