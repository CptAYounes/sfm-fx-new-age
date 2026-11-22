# NA-D06 — Quality Attribute Requirements and Scenarios

**Document:** NA-D06 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** DERIVED_QUALITY_BASELINE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Quality priorities
Correct source identity and external-action safety take precedence over filling the screen with output. Availability means a usable application with explicit partial states, not unconditional provider uptime. Performance controls must not alter observed clocks, analytical mathematics or human action boundaries.

| Attribute | Stimulus and required response | Verification |
|---|---|---|
| Integrity | A late correction arrives; prior as-of results remain recoverable | Immutable-history tests and source hashes |
| Safety | Submission raises after possible send; retain UNKNOWN and do not retry | Order/recovery tests |
| Isolation | Switch account or epoch; old current geometry withdraws | Source-switch/lifecycle tests |
| Responsiveness | Native intake and analysis compete; owner work is bounded | Owner-loop tests and qualified timing runs |
| Recoverability | Process exits after reservation; restart retains uncertainty | Recovery checkpoint |
| Extensibility | Open/close a tool; only its subscriptions are released | Plugin/tool lifecycle tests |
| Usability | Compact window; essential controls remain reachable | Existing actual-widget/native acceptance |
| Maintainability | Change a public contract; review every declared consumer | API catalogue and impact matrix |

## Performance boundary
The retained release policy measures startup separately and requires a bounded sustained operating window, heartbeat/pump limits, bounded queues, zero callback/worker errors and joined shutdown. The exact policy and historical measured values are documented in the performance document. They are measured-host acceptance limits, not hard realtime or universal SLAs.

## Unspecified commitments
No approved RTO, RPO, annual uptime percentage, maximum supported dataset size beyond current software budgets, or public service SLA was found. Recommended backup/recovery practices are therefore documented as proposals. Do not assign reassuring numerical defaults merely to complete a specification.

## Tradeoffs
FULL-durability persistence can cost owner-loop time; write batching shares commits while retaining rollback boundaries. Pure projection processes increase compute capacity but not connector/GUI ownership. Bounded rendering can omit offscreen captions without deleting underlying research records. These tradeoffs must remain visible in reviews and tests.

## Source and authority anchors

- [core/router.py](../../src/sfm_fx_new_age/core/router.py#L15)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11)
- [services/workflow.py](../../src/sfm_fx_new_age/services/workflow.py#L15)
- [tests/test_owner_responsiveness.py](../../tests/test_owner_responsiveness.py#L9)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
