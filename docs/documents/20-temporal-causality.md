# NA-D20 — Temporal Model, Causality and Freshness Design

**Document:** NA-D20 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_TEMPORAL_CONTRACT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Clock model
Market event time, first receipt time, publication time, availability, evaluation cutoff and expiry serve different purposes. A later publication must not renew an old quote, book or trigger. Monotonic clocks govern bounded waiting; aware UTC instants govern persisted market/research ordering. Formatting offsets do not change identity of an instant.

## Causal bars and corrections
Completed bars require open < close <= availability. Confirmed pivots become available only after their required confirming bars. Late backfill cannot make an opportunity historically observed before receipt. Corrections append new immutable revisions and change current selection without rewriting earlier as-of results. The latest eligible correction is selected before expiry; expiration must not revive an older revision.

## Freshness gates
Bid and ask retain independent observation clocks, and shared quote freshness uses the older side. An unchanged native last-price snapshot may be older after a new connection; ordering is compared within epoch, not falsely across epochs. Broker DOM expires from its original local receipt; checksum/native-chain books retain their respective original event/receipt constraints. Heartbeats are not market observations.

## Research lifetime
A strategy trigger's lifetime is at most 14,400 seconds from its original event/confirmation and may be shortened by source expiry. Re-enable, recalculation or late backfill cannot restart it. An observed invalidation/objective crossing is terminal for that setup, even if price later returns.

## Historical information clocks
AS_OBSERVED uses actual recorded availability. HISTORICAL_CLOSE_ASSUMPTION is an explicit model clock for historical study, not a repair of original observations or proof of real-time tradability. Pinned historical charts withhold current-only account/quote state. Replay shares an isolated run cursor and never borrows live projections.

## Review rule
For every time-sensitive field ask: whose clock, what observation, which epoch, and what can renew it? If the answer is merely a refresh timer or reloaded cache row, freshness has not been established.

## Source and authority anchors

- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [services/market.py](../../src/sfm_fx_new_age/services/market.py#L16)
- [services/public_projections.py](../../src/sfm_fx_new_age/services/public_projections.py#L13)
- [services/strategy_signals.py](../../src/sfm_fx_new_age/services/strategy_signals.py#L17)
- [services/replay.py](../../src/sfm_fx_new_age/services/replay.py#L13)
- [connector/quote_history.py](../../src/sfm_fx_new_age/connector/quote_history.py#L21)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
