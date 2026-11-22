# NA-D39 — Requirements, Design and Test Traceability

**Document:** NA-D39 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** TRACEABILITY_REFERENCE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Trace model
The companion provides two distinct crosswalks. The NA requirements matrix derives as-built software constraints and links each to its owner source, exact existing test function and relevant main document. The original supplied-document matrix preserves all 91 frozen requirement IDs, source-document SHA/line, mapped method IDs and qualification category. It is not reconstructed from the 83-method roster.

## Method-level trace
Each public method row links its stable key, recipe/version/profile hash, rules/warm-up/required data, policy ID/hash/trigger, the two exact V23 positive/binding test cases and owning implementation references. The full active method/pair/frame set is generated and checked against the actual catalogue/universe. A complete identity set is not a guarantee that every lane has a positive current setup.

## Verification semantics
A link means the source/test was found and inspected for the named behavior. It is not line/branch coverage or proof that all paths were executed during this task. Historical terminal outcomes come from the retained V23 receipts; fresh outcomes come from this task's JUnit/check files. These classes are never merged into a fabricated new full-suite result.

## Change propagation
A requirements change should identify affected definition, producer, persistence representation, current pointer, query, UI consumer, binding/preflight owner and test nodes. Update the crosswalk only after examining semantics. A name match or inherited class name alone is not enough to assert coverage.

## Gaps
No owner-approved requirement for profitable returns, autonomous position protection, universal fees/margin policy, formal regulatory certification or every possible feed was found in this release scope. Such gaps remain explicitly out of scope or undecided; they are not converted into invented requirements merely to make the table complete.

## Source and authority anchors

- [contracts/data/public_document_requirements.json](../../src/sfm_fx_new_age/contracts/data/public_document_requirements.json#L1)
- [contracts/public_strategies.py](../../src/sfm_fx_new_age/contracts/public_strategies.py#L10)
- [contracts/strategy_signals.py](../../src/sfm_fx_new_age/contracts/strategy_signals.py#L13)
- [tests/test_document_public_strategies.py](../../tests/test_document_public_strategies.py#L26)
- [tests/test_strategy_signal_positive.py](../../tests/test_strategy_signal_positive.py#L14)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
