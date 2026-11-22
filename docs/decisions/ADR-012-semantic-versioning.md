# ADR-012 — Version immutable semantics and preserve literal user choices

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Changing rules in place would make old metadata and saved enablement ambiguous.

## Observed decision

Retain stable IDs where declared, publish semantic successors, keep old bytes/history and migrate only known literal choices.

## Alternatives considered by this analysis

Rewrite immutable version 1; default malformed/absent choices to enabled. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Preserves operator decisions and auditable semantics; requires migration discipline.

## Revisit trigger

A new persisted contract requiring a separately reviewed successor migration. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [contracts/public_strategies.py](../../src/sfm_fx_new_age/contracts/public_strategies.py#L10)
- [tests/test_recipe_upgrade_preservation.py](../../tests/test_recipe_upgrade_preservation.py#L13)
- [PROGRESS.md](../../PROGRESS.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
