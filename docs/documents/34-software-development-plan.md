# NA-D34 — Software Development and Lifecycle Plan

**Document:** NA-D34 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** MAINTENANCE_PROCESS_PROPOSAL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Lifecycle model
Use evidence-gated changes in dependency order: contracts/registries, shared core, runtime integration, lane-specific behavior, offline vertical slices, connector/native acquisition where relevant, then packaging and operator qualification. This is the existing project's engineering sequence, not a new implementation backlog or competing progress tracker.

## Change initiation
A change request identifies the operator outcome, affected current behavior, source owner, authority/mutation boundary, compatibility impact and testable acceptance. Separate a bug repair from new strategy, source entitlement or trading permission. Prefer the largest safe dependency-complete change over unrelated partial edits.

## Implementation discipline
Read the sole `PROGRESS.md` before editing. Preserve existing historical entries and append verified work there only after checks. Shared-spine changes require the coordinator role; lane work stays within its declared folders and consumes shared contracts. Do not create per-agent diaries or silently rewrite sealed acceptance evidence.

## Verification gates
1. Source/requirement discovery and a focused failing case when repairing behavior.
2. Positive and refusal-path implementation tests.
3. Cross-owner integration/identity/lifecycle checks.
4. Relevant source/installed package parity.
5. Native read-only or broker-changing acceptance only when the change needs it and the exact action is authorized.
6. Immutable receipts and honest failure disposition for a release claim.

## Completion definition
Code presence, build success and a plan marked complete are insufficient. The named reachable workflow must operate in its intended startup path, existing tests must retain their meaning, and evidence must be bound to the exact source. Missing provider access remains a dependency rather than a fabricated PASS.

## Governance limit
The project has no observed formal organization-wide staffing schedule, signed RACI, mandatory external release board or automated CI service. Role assignments and proposed process gates here are documentation guidance, not invented organizational adoption.

## Source and authority anchors

- [PROGRESS.md](../../PROGRESS.md#L1)
- [pyproject.toml](../../pyproject.toml#L1)
- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [tests/test_architecture_fences.py](../../tests/test_architecture_fences.py#L13)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
