# ADR-010 — Pure spawned analytical math with owner-side admission

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Analytical load benefits from CPU parallelism but account/session/persistence authority must stay coherent.

## Observed decision

Send only bounded immutable pure-compute jobs; coalesce per lane and recheck current tokens/source/switch/expiry before commit.

## Alternatives considered by this analysis

Share live DB/Qt/broker handles with workers; accept late results blindly. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Selective scalable math and joined shutdown; owner serial work still limits latency.

## Revisit trigger

New parallel workload or measured owner bottleneck requiring a different split. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11)
- [services/public_projections.py](../../src/sfm_fx_new_age/services/public_projections.py#L13)
- [services/projection_math.py](../../src/sfm_fx_new_age/services/projection_math.py#L6)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
