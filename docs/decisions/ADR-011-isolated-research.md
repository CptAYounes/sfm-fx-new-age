# ADR-011 — Isolated replay and explicit historical model clocks

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Historical availability and modelled candle-close timing answer different questions.

## Observed decision

Keep replay datasets/runs isolated and disclose AS_OBSERVED versus HISTORICAL_CLOSE_ASSUMPTION; studies remain research-only.

## Alternatives considered by this analysis

Retag historical observations as live; count ambiguous OHLC ordering as wins. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Reproducible bounded research without execution/profitability claims.

## Revisit trigger

An independently specified new fill/data model or study family. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [contracts/backtest.py](../../src/sfm_fx_new_age/contracts/backtest.py#L11)
- [services/replay.py](../../src/sfm_fx_new_age/services/replay.py#L13)
- [services/backtesting.py](../../src/sfm_fx_new_age/services/backtesting.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
