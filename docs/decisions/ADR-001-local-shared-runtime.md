# ADR-001 — Local modular desktop with one shared runtime

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Four workspaces need coherent observations, preferences and action state. Independent per-tab services would create competing ownership.

## Observed decision

Use ApplicationRuntime as the composition/lifecycle owner and Qt-neutral domain services behind scoped APIs.

## Alternatives considered by this analysis

Per-tab applications; distributed services; direct widget-to-broker calls. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Keeps identity and persistence coherent; concentrates owner-thread scheduling responsibility.

## Revisit trigger

Remote multi-user deployment or independently operated services require a new architecture. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [tests/test_architecture_fences.py](../../tests/test_architecture_fences.py#L13)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
