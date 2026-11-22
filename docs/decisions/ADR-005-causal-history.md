# ADR-005 — Causal immutable histories and separate current pointers

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Late backfill/corrections must not rewrite what was knowable at an earlier inspection time.

## Observed decision

Retain original availability/revision history and choose exact latest eligible revisions; current pointers remain projections.

## Alternatives considered by this analysis

Overwrite old bars/objects; infer availability from market close; revive an older expired value. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Supports honest as-of research; increases retained history and index complexity.

## Revisit trigger

An explicitly new storage model that proves equivalent causal reads. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [services/market.py](../../src/sfm_fx_new_age/services/market.py#L16)
- [services/research.py](../../src/sfm_fx_new_age/services/research.py#L15)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
