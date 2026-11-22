# ADR-004 — Exact namespace plus connection epoch

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Same account identifiers and prices can exist at different brokers/endpoints/origins; reconnect changes authority.

## Observed decision

Bind account scope to broker/endpoint/account/origin and current market facts to source epoch.

## Alternatives considered by this analysis

Global pair-only caches; restore authority from saved metadata. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Prevents cross-source reuse; requires explicit revalidation/recovery after source changes.

## Revisit trigger

A new account/source federation requirement. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
