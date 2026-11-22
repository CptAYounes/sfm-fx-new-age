# NA-D05 — Software Requirements Specification

**Document:** NA-D05 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** DERIVED_REQUIREMENTS · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Specification basis
This SRS derives testable requirements from the current implementation and explicit New Age product decisions. It is not a reapproval of trading policy. The companion requirements crosswalk assigns stable NA identifiers, implementation owners, existing exact test functions and document destinations. Those associations are reviewed trace links, not a claim that every possible input is covered.

## Functional requirements
The application shall retain four workspaces and 42 stable backend contracts while rendering Tab 2 as tools. It shall use only the active six-pair/four-frame scope for current admissions. Account class shall be metadata, not an eligibility gate. A tab shall operate only through its scoped API and declared command/data contracts.

Market bars shall retain source scope, epoch, origin, observed clocks and immutable correction history. No empty chart, missing input or failed acquisition shall be replaced with fabricated observations. Reconnection shall not transplant authority from a saved epoch.

Each of the 83 public methods shall have explicit versioned semantics, independent enablement and a disclosed research-entry policy. Missing genuine inputs, disabled methods, unavailable support and No setup shall remain distinguishable. Binding shall revalidate current identity, lineage, freshness and geometry and require explicit native-valid units. Binding shall not send an order.

New pending orders shall require deliberate Issue, current shared preflight and an atomic local reservation. Uncertain external outcomes shall remain UNKNOWN until reconciliation; they shall never automatically replay. Local signal cancellation shall not cancel a broker order. Broker cancellation shall be separately confirmed and identity-bound.

## Nonfunctional and data requirements
Backend services shall remain Qt-neutral; acquisition shall remain connector-owned. Queues and workload bounds shall be explicit. Secret values shall not enter ordinary command payloads or journals. Replay and historical studies shall not acquire live execution authority. Restart shall preserve facts/preferences without treating them as authentication.

## Acceptance interpretation
The frozen 91-item supplied-document crosswalk is an independent analytical-corpus requirement set. It is not replaced by this SRS and must not be inferred from the catalogue count. Requirements concerning profitability, account-wide risk approval, autonomous exits or broader feeds are intentionally not asserted as implemented.

## Source and authority anchors

- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [contracts/registry.py](../../src/sfm_fx_new_age/contracts/registry.py#L18)
- [contracts/commands.py](../../src/sfm_fx_new_age/contracts/commands.py#L58)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [contracts/strategy_signals.py](../../src/sfm_fx_new_age/contracts/strategy_signals.py#L13)
- [contracts/backtest.py](../../src/sfm_fx_new_age/contracts/backtest.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
