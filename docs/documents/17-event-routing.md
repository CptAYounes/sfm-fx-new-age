# NA-D17 — Event Model, Topic Catalogue and Routing Specification

**Document:** NA-D17 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_EVENT_DESIGN · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Event envelope
Events carry topic, source component, immutable payload, priority, partition key, source epoch, production clock and event ID. The router owns callback delivery and tracks queue/latency/error metrics. A declared route describes intended host relationships, not proof that a whole named domain is implemented.

## Delivery semantics
Priority P0 precedes P1/P2/P3; arrival sequence preserves ordering within equal priority. Capacity is 4,096 per priority by default; exhaustion raises BackpressureError rather than silently losing an accepted critical event. The last-known-value cache is bounded and keyed by topic plus partition. It is display/context state, not durable replay or current-source proof.

Only the owning thread may drain callbacks. Reentrant drain returns without recursion. A subscriber exception records its type in a bounded error ring and does not starve other subscribers. Subscription removal is explicit and consumer-owned. This is in-process delivery, not a distributed exactly-once broker.

## Topic families
| Family | Examples/purpose |
|---|---|
| Market | Completed bars, quotes and source-authority changes |
| Analytical | Input changes, research snapshots and parameter effects |
| Signal | Candidate proposal, queue snapshots and deliberate user Issue |
| Broker/order | Native state, reconciliation response and identity-map updates |
| Account/configuration | Current account, consumer and parameter state |

The extracted route catalogue preserves every source, destination, topic, trigger, priority, rule and declared status. The API/view catalogue separately records each view's actual topic subscriptions.

## Persistence and recovery
The runtime journals delivered events with original source epoch and production clock. The journal does not make every callback transactional with a remote broker. Restart uses explicit order recovery/reconciliation instead of replaying Issue events. Latest-only analytical work may coalesce validated snapshots; that does not license dropping native trade IDs or book checks before validation.

## Source and authority anchors

- [core/router.py](../../src/sfm_fx_new_age/core/router.py#L15)
- [core/projections.py](../../src/sfm_fx_new_age/core/projections.py#L12)
- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [contracts/models.py](../../src/sfm_fx_new_age/contracts/models.py#L12)
- [contracts/data/host_typed_routes.csv](../../src/sfm_fx_new_age/contracts/data/host_typed_routes.csv#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
