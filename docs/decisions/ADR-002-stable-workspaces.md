# ADR-002 — Four workspaces, 42 stable contracts, dynamic Trading Tools

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Backend integrations need stable view identities while the user wants contained tools rather than engineering switchboards.

## Observed decision

Retain 10/10/13/9 backend identities; render Tab 2 as dynamic tools and keep its ten contracts internal.

## Alternatives considered by this analysis

Expose all backend contracts as visible pages; remove IDs when presentation changes. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Preserves integrations without forcing 42 visible user pages.

## Revisit trigger

A separately approved navigation/product scope change. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [contracts/registry.py](../../src/sfm_fx_new_age/contracts/registry.py#L18)
- [tabs/tab2/workspace.py](../../src/sfm_fx_new_age/tabs/tab2/workspace.py#L12)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
