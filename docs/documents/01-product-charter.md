# NA-D01 — Product Charter and Product Requirements

**Document:** NA-D01 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** PRODUCT_BASELINE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Purpose and value
SFM FX New Age is a local Debian/X11 desktop application for inspecting Forex observations, conducting explicitly bounded analytical research, reviewing source-bound research signals, and deliberately requesting pending Limit orders through cTrader. It makes provenance, missing inputs, stale state and human decisions visible rather than filling gaps with invented observations.

The product baseline is version 0.2.0 / V23 candidate-04. Its six active pairs are EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD and AUDUSD. Research uses W1, D1, H4 and H1. NZDUSD remains historical-only. The public catalogue contains 83 profiles; the historical study selector has 14 self-contained price-marker models. These are different product denominators.

## Product outcomes
- Inspect broker-scoped price history and chart objects without confusing drawings with observations.
- Enable each analytical method independently and inspect exact current states.
- Distinguish a present trigger from a qualified local proposal and from a broker-accepted pending order.
- Retain immutable corrections, saved preferences and causal research results across restart without restoring authentication from database metadata.
- Expose uncertainty and source failure without silently changing providers, accounts or execution intent.

## Success and exclusions
Successful software behavior means the defined workflows, ownership boundaries and acceptance cases operate as specified. It does not mean all methods produce a setup simultaneously, predict profit, reconstruct a consolidated FX tape, or manage open positions autonomously. Broker SL/TP, chart-driven order mutation, autonomous entries and the unavailable local-exit addon are not shipped release promises.

## Product authority
The owner supplies trading decisions and explicit Issue intent. The program owns validation, persistence and transport correlation. This charter describes the existing product, not additional trading consent or a new strategy approval. Future scope changes require a recorded owner decision, source changes and matching acceptance evidence.

## Source and authority anchors

- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [README.md](../../README.md#L1)
- [PROGRESS.md](../../PROGRESS.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
