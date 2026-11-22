# NA-D27 — Concurrency, Scheduling and Resource Ownership

**Document:** NA-D27 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_CONCURRENCY_DESIGN · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Ownership rules
The core owner thread drains callbacks, pumps intake, controls command execution and commits current state. The database wraps one connection/lock per runtime; cross-runtime order uniqueness additionally rests on SQL constraints/transactions. GUI refresh renders snapshots and does not recursively pump network ingestion.

SDK reactors use isolated spawned processes. Connector-owned acquisition workers return bounded observations for owner admission. Projection processes receive immutable bounded JSON-compatible math snapshots only. They never receive Qt, secrets, database connections or broker handles.

## Scheduling controls
The runtime inbox has 4,096 slots. Router queues are bounded by priority. Native intake uses bounded FIFO turns. Public publications coalesce already validated complete snapshots by identity; native trade IDs/book checks still occur before coalescing. Dirty analytical pairs rotate instead of one failed pair starving siblings. Result commit and submission alternate under active-pool work.

## Compute capacity
Automatic capacity examines affinity, cgroup quota and available memory, reserves an owner CPU slot where possible, budgets 384 MiB per worker and caps the six-pair/four-frame cohort. It is a ceiling, not a promise to occupy every core. Workers start on demand. An explicit positive limit is clamped; `1` remains deterministic serial.

## Stale work and shutdown
Each lane has latest-desired job identity. Superseded waiting jobs coalesce; late or wrong-token results cannot commit. Source withdrawal, method disablement, profile changes and expiry are checked again by the owner. Closing clears queued work, cancels pending futures where possible and joins bounded active children before persistence closes.

## Residual risk
FULL-durability writes and serial owner responsibilities remain potential latency sources. A passing finite native dwell does not prove hard realtime, indefinite endurance or arbitrary scale. Increase budgets only after measurement and identity/safety regression—not by bypassing bounds when queues are full.

## Source and authority anchors

- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [core/router.py](../../src/sfm_fx_new_age/core/router.py#L15)
- [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11)
- [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [services/public_projections.py](../../src/sfm_fx_new_age/services/public_projections.py#L13)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
