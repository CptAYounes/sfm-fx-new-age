# NA-D55 — Change Impact and Dependency Analysis

**Document:** NA-D55 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** ENGINEERING_REFERENCE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Impact matrix
| Change | Required propagation review |
|---|---|
| Pair/frame universe | Domain, source discovery, scheduler/history denominators, GUI selection, historical preservation, tests |
| Method rules/version | Catalogue, immutable recipe metadata, parameters, compute eligibility, projection fingerprint, policy, UI disclosure |
| Source semantics | Adapter decode, units/clocks/completeness, admission, cache identity/expiry, inspector and current eligibility |
| Signal policy | Policy hash, original trigger clock, opportunity identity, bind validation, Issue recheck and acknowledgement |
| Tab dataset/command | Registry, API allowlist, payload schema, owner handler, snapshot dependencies, disposal and tests |
| Persistence schema | Migration, transactions/indexes, old-state read, backup/restore and installed compatibility |
| Native transport | TLS/pacing, request correlation, source epoch, uncertainty/reconcile and shutdown |
| UI handoff | Inspection envelope/hash, destination permissions, source-change failure and Return state |
| Worker optimization | Serial numerical/fingerprint parity, token rejection, queue bounds and joined close |

## Dependency rule
Trace producer → admission → persistence → current pointer → bounded query → UI → binding/preflight for changes affecting current research. A locally fixed producer is not complete if downstream whitelists/current pointers still omit its fields. Conversely, a ready boolean in a consumer is not proof of upstream source authority.

## Historical compatibility
Do not change immutable definition bytes or backdate original observations to satisfy a new consumer. Preserve retired pair history, known literal recipe choices and explicit old metadata. Introduce a semantic successor and tested migration where necessary.

## Review evidence
Use exact source symbols and the generated import/contract catalogue to identify owners, then inspect semantics and tests. Static import edges are lexical dependencies, not a complete dynamic call graph or proof of runtime execution. Record any unresolved impact and the smallest safe acceptance gate before implementation.

## Task boundary
The present package changes no product source, test, launcher or operational state, so its impact is documentation-only. Its hashes and validation receipts are separate from the product's sealed release and cannot silently replace that release manifest.

## Source and authority anchors

- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [contracts/registry.py](../../src/sfm_fx_new_age/contracts/registry.py#L18)
- [services/public_projections.py](../../src/sfm_fx_new_age/services/public_projections.py#L13)
- [services/strategy_signals.py](../../src/sfm_fx_new_age/services/strategy_signals.py#L17)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
