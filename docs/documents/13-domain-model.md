# NA-D13 — Domain Model and Bounded Contexts

**Document:** NA-D13 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_DOMAIN_DESIGN · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Bounded contexts
Market observation, analytical research, local signal intent, broker correlation and replay are distinct contexts joined by explicit identities. They share typed contracts but not authority. A Level describes a price object; Evidence describes support; a MarketCandidate describes analytical geometry/qualification; a Candidate is a local proposal with chosen units. Their similar prices do not make them interchangeable.

## Identity graph
`AccountContext.scope_id` serializes broker ID, endpoint class, account ID and origin. Market authority adds source epoch and pair. Bars add timeframe/open time/revision; projections add method/version/profile/input fingerprints. An analytical opportunity carries original trigger roots and current policy identity. A bound local signal preserves the opportunity ID/revision/hash and selected variant. A local order adds its own UUID/client order ID; native broker order/position IDs are separately mapped after observation.

## Aggregates and invariants
| Aggregate | Invariant |
|---|---|
| Bar | Completed open < close <= availability, finite valid OHLC, explicit origin/epoch |
| Quote | Finite bid/ask, coherent source, freshness bound to oldest side |
| SymbolSpec | Positive native tick/pip/volume definitions and legal order grid |
| Research object | Causal lineage, immutable revisions and source/profile identity |
| Local signal | Stable setup/pair/origin identity; only queued proposals may receive newer revisions |
| Local order | Unique scope/signal reservation and nonrebindable broker identity |
| Native position snapshot | Explicit observed completeness; empty local rows do not prove flatness |
| Replay run | Isolated dataset, cursor and information clock; no live execution authority |

## Context translation
Connector protocol adapters decode native fixed-point values before domain validation. Research policies translate observations into disclosed research geometry, not vendor intent. Human binding supplies units; the order owner translates a validated proposal to pending Limit protocol fields. A display or navigation handoff preserves identity and cannot strip a broker record into a research object.

## Consequence for future design
Do not collapse these contexts into a generic mutable “trade” record. Doing so loses the distinction between an analytical hypothesis, a local command and an observed broker fact—the distinctions needed for safe restart, auditing and honest reports.

## Source and authority anchors

- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [contracts/analytics.py](../../src/sfm_fx_new_age/contracts/analytics.py#L14)
- [services/research.py](../../src/sfm_fx_new_age/services/research.py#L15)
- [services/signals.py](../../src/sfm_fx_new_age/services/signals.py#L12)
- [services/positions.py](../../src/sfm_fx_new_age/services/positions.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
