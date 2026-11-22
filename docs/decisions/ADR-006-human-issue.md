# ADR-006 — One deliberate pending Limit Issue edge

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Research, chart interaction and local proposals must not become automatic order submission.

## Observed decision

Separate method enablement, analytical signal, human local binding, shared preview and deliberate Issue.

## Alternatives considered by this analysis

Auto-submit on Ready; chart QuickTrade; implicit unit selection. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Keeps review/action explicit; does not independently prove physical human presence to malicious local callers.

## Revisit trigger

Any proposed autonomous execution or additional broker mutation. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [services/strategy_signals.py](../../src/sfm_fx_new_age/services/strategy_signals.py#L17)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [contracts/commands.py](../../src/sfm_fx_new_age/contracts/commands.py#L58)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
