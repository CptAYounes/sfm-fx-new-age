# NA-D28 — Replay, Backtesting and Walk-Forward Specification

**Document:** NA-D28 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_RESEARCH_MODEL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Scope
Historical studies support 14 declared self-contained closed-price marker profiles, not all 83 analytical profiles as executable strategies. The model is `NEXT_OBSERVED_OPEN_FIXED_BPS_OHLC_V1`: next-observed-open entry, explicit basis-point stop axis, target-R axis, holding limit and roundtrip model cost. These are research assumptions, not broker execution reconstruction or live order settings.

## Dataset and information clock
Runs use isolated immutable datasets and a causal cursor. A paused new replay reveals no bars until stepped. AS_OBSERVED preserves actual recorded availability, including late receipt. HISTORICAL_CLOSE_ASSUMPTION explicitly uses historical close timing/first revisions for simulation without rewriting original observations. The report retains both dataset and model-input hashes.

## Outcomes and selection
Gap behavior follows original bar opens. Ambiguous intrabar stop/target ordering and unfinished trades remain unresolved, never counted as wins. The first configuration is the baseline, not the ex-post winner. Walk-forward chooses configurations from resolved training outcomes only, applies deterministic ties and disjoint test windows, and refuses training payoff leakage across the boundary.

## Budgets
Requests validate one active pair/frame, 2–2,000 original revisions, at most 64 stop/target combinations and bounded work/output. Holding, training/test and cost axes have explicit typed limits. Insufficient history is reported rather than manufactured into an OOS result.

## Persistence and authority
Study identities are immutable/idempotent and result hashes are checked on reuse. Saved studies survive restart and are available through the research dataset/API. Reports cannot select an account, publish a live signal, bind a candidate or call a broker.

## Interpretation
Zero model cost means gross results, not known net return. OHLC cannot reconstruct tick-side spread, fill ordering, slippage or broker latency. A positive study does not calibrate the live research policies or establish profitable edge; additional independently designed empirical research would be separate work.

## Source and authority anchors

- [contracts/backtest.py](../../src/sfm_fx_new_age/contracts/backtest.py#L11)
- [services/replay.py](../../src/sfm_fx_new_age/services/replay.py#L13)
- [services/backtesting.py](../../src/sfm_fx_new_age/services/backtesting.py#L11)
- [ui/research_study.py](../../src/sfm_fx_new_age/ui/research_study.py#L12)
- [tests/test_backtest_workflow.py](../../tests/test_backtest_workflow.py#L9)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
