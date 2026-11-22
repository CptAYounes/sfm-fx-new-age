# ADR-007 — Durable reservation and UNKNOWN reconciliation

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

A timeout after possible external send cannot tell whether a broker order exists.

## Observed decision

Reserve once durably and use UNKNOWN plus matching native reconcile instead of blind replay.

## Alternatives considered by this analysis

Retry on timeout; delete reservation; treat local transaction rollback as broker undo. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Protects against duplicate intent while allowing uncertainty to remain explicit.

## Revisit trigger

A new broker idempotency/transaction contract proved end to end. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [tests/test_recovery_concurrency.py](../../tests/test_recovery_concurrency.py#L17)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
