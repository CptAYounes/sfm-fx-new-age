# NA-D33 — Software Safety and Hazard Analysis

**Document:** NA-D33 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** DESIGN_ASSESSMENT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Hazard scope
The application can request real pending orders after deliberate human action. Software controls reduce specific failure modes; they cannot guarantee bounded loss, market liquidity, execution price or operator judgment. Risk ratings below are qualitative engineering prioritization, not quantified financial risk or safety certification.

| Hazard | Principal cause | Control | Residual condition |
|---|---|---|---|
| Duplicate pending order | Timeout/double click/restart | Atomic unique reservation and UNKNOWN recovery | External result must still be reconciled |
| Wrong account/source action | Stale selection or namespace loss | Exact broker/endpoint/account/origin/epoch checks | Local user remains trusted |
| Stale setup Issue | Old review, quote or projection | Recheck at binding and immediately before reservation | Fresh data still does not guarantee acceptance |
| False sense of protection | Internal invalidation mistaken for SL | No broker SL/TP fields; explicit UI/document labels | Autonomous protection is not installed |
| Invented flat account | Empty local positions | Explicit last-observed completeness/unknown state | Native observations can age |
| Fabricated research success | Missing input/backdated evidence | Causal clocks, genuine-input gates and unresolved outcomes | Research remains uncalibrated |
| Unauthorized broker cancel | Local cancel conflated with native action | Separate identity-bound confirmed pending cancellation | Cancellation outcome may itself become UNKNOWN |

## Safe failure posture
Stop new action when source identity, continuity, authentication or order state is uncertain. Preserve records and reservations. Do not reset/delete an UNKNOWN row to make Issue available. Do not “repair” missing genuine input with quote counts, model data or future observations. Escalate unresolved native state to the operator with exact sanitized identities.

## Review and acceptance
A future action affecting positions, broker protection, automatic sizing or autonomous entry is a scope change requiring separate hazard review and explicit approval. The present documentation work neither changes safety gates nor authorizes a new broker test. Historical demo Issue/cancel proof is transport evidence for that bounded event only.

## Source and authority anchors

- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [services/strategy_signals.py](../../src/sfm_fx_new_age/services/strategy_signals.py#L17)
- [services/research_money.py](../../src/sfm_fx_new_age/services/research_money.py#L13)
- [services/positions.py](../../src/sfm_fx_new_age/services/positions.py#L11)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
