# NA-D54 — Performance, Capacity and Responsiveness Qualification

**Document:** NA-D54 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** RETAINED_MEASUREMENTS_AND_AS_BUILT_LIMITS · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Workload model
The current analytical workload is six pairs × four frames × 83 public methods. The 24 history lanes and 1,992 method identities are different denominators. Pure projection jobs may use bounded spawned processes; source intake, admission, persistence, GUI and broker ownership remain serial at their owners. Automatic worker capacity is adaptive, not a benchmark speedup claim.

## Retained V23 measurements
The source qualification recorded 913.5614971089999 operating seconds, maximum owner pump 0.8578982530016219 s, maximum heartbeat lateness 1.083879207001155 s and p95 lateness 0.32815226200036707 s. The installed lane recorded 913.4688070670018 s, pump 0.8538757159985835 s, maximum lateness 1.0887467900014598 s and p95 0.25513653100133526 s. These are values read from retained FINAL-ACCEPTANCE, not new benchmarks.

## Acceptance policy
The documented policy requires at least 900 operating seconds per build, first heartbeat within 5 seconds, operating maximum lateness <=2 seconds and p95 <=0.5 seconds, individual owner pump <=1 second, bounded queues, zero callback/worker errors or broker mutations, all requested histories and joined shutdown within 30 seconds. Startup is measured separately. Historical failed attempts remain failed.

## Implemented controls
Bounded native turns, transaction savepoints/commit sharing, scan/result alternation, exact-source indexes, local feature reuse and render-bounds coordinate caching reduce owner work without changing original clocks/fingerprints. Latest-only computation coalesces superseded jobs. These optimizations do not relax source freshness or broker-action gates.

## Capacity planning limits
No arbitrary throughput, all-core saturation, indefinite endurance or cross-host realtime SLA is promised. Increasing methods, pairs, frames or input retention changes the workload and requires new measurements. This documentation task ran no connected dwell or performance benchmark. CPU/memory values from prior hosts must not be represented as the current user's guaranteed capacity.

## Source and authority anchors

- [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11)
- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [tests/test_owner_responsiveness.py](../../tests/test_owner_responsiveness.py#L9)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
