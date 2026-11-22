# ADR-008 — Distinct source semantics and disclosed activity alternatives

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

FX quotes, displayed depth, venue executions and futures context are not interchangeable evidence.

## Observed decision

Use typed input kinds, units/clocks/coverage and visible alternate interpretation names where provided.

## Alternatives considered by this analysis

Rename quote counts as volume; impose optional full-book requirements on ordinary broker DOM. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Preserves legitimate weaker-source use without making stronger false claims.

## Revisit trigger

Provider protocol/requirements change or a new evidence kind. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [contracts/supplemental.py](../../src/sfm_fx_new_age/contracts/supplemental.py#L14)
- [services/supplemental.py](../../src/sfm_fx_new_age/services/supplemental.py#L13)
- [connector/broker_depth.py](../../src/sfm_fx_new_age/connector/broker_depth.py#L22)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
