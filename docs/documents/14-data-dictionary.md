# NA-D14 — Data Dictionary and Serialization Contracts

**Document:** NA-D14 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_DATA_REFERENCE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Authoritative field reference
The generated contract catalogue lists every inspected class field, annotation and default from the contract modules, with source lines. It is the exhaustive field appendix; this document supplies semantic rules that type annotations alone cannot express. Decimal-valued domain objects serialize as strings. Aware timestamps represent instants; naive timestamps are refused.

| Field group | Meaning and constraints |
|---|---|
| `scope_id`, `source_epoch`, `origin` | Namespace and provenance; cannot be replaced by display pair names |
| `available_at`, original event/receipt clocks | Causal eligibility versus market/transport time |
| `revision`, `version`, `expected_version` | Object correction/definition and CAS concurrency; booleans are not integer revisions |
| `symbol`, `timeframe` | Active six-pair/four-frame coordinates for current operations |
| `entry_price`, `invalidation_price`, `units` | Finite Decimal geometry and explicit native-valid quantity |
| `profile_hash`, `fingerprint`, source hashes | Exact semantic/input binding; not independent source authentication |
| `broker_order_id`, `position_id` | Separately observed native identities; local acceptance cannot invent them |
| `quote_basis`, `construction`, `tick_volume` | Explicit bid/ask/mid/unknown and native/derived construction; tick activity is not execution quantity |

## Null, empty and unavailable
A missing quote is not zero spread. An unavailable conversion is not one-to-one currency parity. Empty position rows are unknown without an explicitly observed complete native snapshot. Missing historical intervals are not zero-volume intervals. A calendar with no admitted coverage is not news clearance. A missing field cannot be supplied by an optimistic GUI default.

## Payload and page discipline
`DataRequest` restricts datasets by subtab, supports bounded pagination and requires a stable data hash for continuation. The typed command payload registry rejects unknown fields and wrong primitive types. Supplemental wire validation rejects extra execution fields and applies per-kind units/completeness contracts before admission.

## Schema interpretation
The physical database is deliberately small: generic typed JSON records, dedicated order reservations and event journal. A record-kind catalogue is not a list of independent SQL tables. The extracted schema and typed-contract catalogue must be read together; neither alone proves a complete semantic data model.

## Source and authority anchors

- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [contracts/analytics.py](../../src/sfm_fx_new_age/contracts/analytics.py#L14)
- [contracts/models.py](../../src/sfm_fx_new_age/contracts/models.py#L12)
- [contracts/supplemental.py](../../src/sfm_fx_new_age/contracts/supplemental.py#L14)
- [contracts/tab_data.py](../../src/sfm_fx_new_age/contracts/tab_data.py#L30)
- [contracts/backtest.py](../../src/sfm_fx_new_age/contracts/backtest.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
