# NA-D24 — Pending Order, Issue and Reconciliation Specification

**Document:** NA-D24 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_EXECUTION_DESIGN · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## One new-order edge
Only deliberate human Issue creates a new pending Limit attempt. It runs the same pure preflight exposed in the detail view, then atomically reserves `(scope_id,signal_id)` before transport submission. Research acknowledgement cannot waive missing source, lineage or native-grid checks. Account type is not a gate; authenticated trading scope and matching current namespace are.

## State model
Local proposals use QUEUED, ISSUE_RESERVED, ISSUED and local terminal states. Orders separately use RESERVED, SUBMITTING, ACCEPTED_PENDING, PARTIALLY_FILLED, FILLED, REJECTED, CANCELED, EXPIRED and UNKNOWN. The actual transition table is in OrderService; diagrams summarize it without inventing external exactly-once guarantees.

An exception after submission may occur after the broker acted. It therefore creates UNKNOWN and retains the reservation. Restart recovery also preserves uncertainty. Reconciliation queries the matching authenticated broker/endpoint/account scope and maps native identities; it does not send a replacement order. A confirmed broker ID cannot be rebound.

## Price and protection semantics
Orders carry explicit native-valid price/units and expiry. Open/unknown sessions retain fresh-price checks. A current native schedule proving closure permits the documented pending-Limit snapshot exception; it does not waive continuity, scope, pending-side or broker validation. New research-policy binding remains independently subject to fresh two-sided quotes.

Broker stop-loss and take-profit fields remain unset. Internal invalidation is research geometry, not active protection or a guaranteed maximum loss. This signal platform does not provide autonomous position exit/partial-close management.

## Cancellation and positions
Canceling an unissued local signal never cancels a broker pending order. Broker cancellation is a separately confirmed action on an exactly identified ACCEPTED_PENDING order; changed hashes/scopes or uncertainty require renewed inspection/reconciliation. Pending acceptance is not a fill and never fabricates a position. Native pending/position inventories remain separately observed, with unknown completeness visible.

## Source and authority anchors

- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [services/signals.py](../../src/sfm_fx_new_age/services/signals.py#L12)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [connector/protocol.py](../../src/sfm_fx_new_age/connector/protocol.py#L8)
- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [services/positions.py](../../src/sfm_fx_new_age/services/positions.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
