# ADR-009 — SQLite WAL/FULL with explicit atomic/savepoint boundaries

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

A local desktop needs durable state and duplicate reservations without inventing distributed transactions.

## Observed decision

Use one locked connection per runtime, SQL uniqueness, atomic workflows and savepoint-preserving bounded commit batching.

## Alternatives considered by this analysis

Pure in-memory production state; arbitrary main-file copies; batching every workflow as if atomic. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Simple local persistence; durability still has I/O cost and remote actions remain outside SQL.

## Revisit trigger

Measured capacity or multi-host requirements beyond the local design. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [tests/test_owner_responsiveness.py](../../tests/test_owner_responsiveness.py#L9)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
