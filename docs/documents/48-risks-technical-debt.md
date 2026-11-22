# NA-D48 — Risk Register, Limitations and Technical Debt Assessment

**Document:** NA-D48 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** SOURCE_GROUNDED_ASSESSMENT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Register interpretation
Items are documented exposure or proposed improvement, not assertions that accepted V23 gates remain unfinished. Qualitative priority names guide review; no financial probability or organizational risk acceptance is inferred.

| ID | Exposure | Existing mitigation | Residual / proposed action |
|---|---|---|---|
| R-01 | Plaintext local credentials | Owner-only private atomic store | Decide encrypted/keychain and recovery requirements separately |
| R-02 | Unresolved external action | UNKNOWN and durable duplicate barrier | Operator/native reconcile still required |
| R-03 | Provider outages/semantic changes | Bounded requests and fail-closed admission | Fresh availability cannot be guaranteed |
| R-04 | Local trust model | Scoped facades and architecture fences | Not a hostile-plugin or multi-user security boundary |
| R-05 | Dependency drift | Retained exact release environment | Add approved lock/update/advisory workflow if desired |
| R-06 | No Git commits yet | Frozen per-file SHA manifests | Establish a real source-control baseline deliberately |
| R-07 | Finite responsiveness proof | Bounded owner/pool design and sustained qualification | No hard-realtime/indefinite endurance claim |
| R-08 | Research mistaken for risk approval | Gross labels, explicit units and separate Issue | No autonomous protection/account-wide risk authorization |
| R-09 | Narrow historical model | Explicit 14-model/clock/ambiguity disclosure | Not 83 executable strategy backtests |
| R-10 | Dense analytical display | Rail paging, focus and full inspector | All simultaneous geometry may remain crowded |
| R-11 | Data/evidence retention growth | Bounded live publications and explicit archives | No approved general retention schedule/backup SLA |
| R-12 | Older diary statements | Dated append-only history/current checkpoint | Read latest applicable semantics, do not combine contradictory epochs |

## Debt versus intentional scope
The unavailable local-exit addon, general FIX entitlement, stronger all-pair full books and profitability calibration are excluded capabilities, not defects to be silently completed under documentation authorization. Conversely, a regression in a declared current workflow is a real defect even if a historical release passed.

## Owner decisions
Prioritize source control, secret storage, backup objectives, dependency policy and support commitments through explicit owner decisions. This package records the choices still needed but does not perform installations, change trading behavior or accept residual risks on the owner's behalf.

## Source and authority anchors

- [README.md](../../README.md#L1)
- [pyproject.toml](../../pyproject.toml#L1)
- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [contracts/backtest.py](../../src/sfm_fx_new_age/contracts/backtest.py#L11)
- [PROGRESS.md](../../PROGRESS.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
