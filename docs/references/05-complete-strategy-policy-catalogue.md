# R05 — Complete Analytical Method and Research-Entry Policy Catalogue

All 83 profiles are individually enumerated. The following rules/policies are source-declared bounded uncalibrated engineering definitions. Positive test cases are explicitly synthetic, not connected-market setups or profitability proof. Original external reference URLs are retained as code attribution only and were not fetched/revalidated for this publication.

## 01. SMA crossover — `sma_cross`

| Attribute | Value |
|---|---|
| Family | Trend |
| Recipe | public.forex.sma_cross.v1 |
| Definition/version | PUBLIC_FOREX_SMA_CROSS_V1 |
| Profile SHA-256 | 2773ae7958eed3b74e56b25881a5b33b987dc95e24355ea6924f58b812d29f9f |
| Warm-up bars | 51 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_SMA_CROSS_V1 |
| Policy hash | cfab505487b6b20f73467686d8184acf1d1f5cbc8f64c84744d819a62f3e1e53 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** 20/50 completed-close SMA crossing; equality is not a new cross.

**Parameters:** `[["fast", 20], ["slow", 50]]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[sma_cross]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[sma_cross]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/trend/simple-moving-average/`

## 02. EMA crossover — `ema_cross`

| Attribute | Value |
|---|---|
| Family | Trend |
| Recipe | public.forex.ema_cross.v1 |
| Definition/version | PUBLIC_FOREX_EMA_CROSS_V1 |
| Profile SHA-256 | ad76cbacb16de3d2da6ae6b52f98ac5cc141a60d358fe6cb05d76590e30f35c6 |
| Warm-up bars | 51 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_EMA_CROSS_V1 |
| Policy hash | cb885c03a19ff26d0180a642e708f51020fddba357c9c5d0ae1c9ff22453b340 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** 20/50 close EMA, arithmetic-mean seed at each full period; strict crossover.

**Parameters:** `[["fast", 20], ["slow", 50]]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[ema_cross]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[ema_cross]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/trend/exponential-moving-average/`

## 03. MACD signal crossover — `macd`

| Attribute | Value |
|---|---|
| Family | Momentum |
| Recipe | public.forex.macd.v1 |
| Definition/version | PUBLIC_FOREX_MACD_V1 |
| Profile SHA-256 | d59c4721902b507b4055bd26efc89a18a1d7ed41824581de34a8c4a955657e19 |
| Warm-up bars | 35 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_MACD_V1 |
| Policy hash | 3890cb169d06765a628e979b2407f29d62bd4d181515e9d58e2aa9b4d9e2df94 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** 12/26 close EMAs; 9-period EMA of valid MACD values. Strict signal crossover; no price-axis oscillator line.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[macd]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[macd]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/oscillators/macd-crossover/`

## 04. RSI oversold/overbought re-entry — `rsi`

| Attribute | Value |
|---|---|
| Family | Momentum |
| Recipe | public.forex.rsi.v1 |
| Definition/version | PUBLIC_FOREX_RSI_V1 |
| Profile SHA-256 | 02d14773d8f01c633f24520b5aeaddb9d6a43b7c788c65aebceb677dfd838243 |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_RSI_V1 |
| Policy hash | 1988b947e853ca89406db6311e16952fbe6252327ca42d8dfddfd20b2c79cff5 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Wilder RSI(14), mean seed; BUY crossing back above 30, SELL back below 70. Flat=50; no loss=100.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[rsi]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[rsi]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/oscillators/relative-strength-index/`

## 05. Stochastic extreme crossover — `stochastic`

| Attribute | Value |
|---|---|
| Family | Momentum |
| Recipe | public.forex.stochastic.v1 |
| Definition/version | PUBLIC_FOREX_STOCHASTIC_V1 |
| Profile SHA-256 | bcc75fc14a19cab4f652a644b6822ab2f0c0cd69d40f9b0e025d5750e2293a87 |
| Warm-up bars | 19 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_STOCHASTIC_V1 |
| Policy hash | f362f6a0b6f617a0b1594a3324dae26e0f65377fa5921feb1b3d79d37740db34 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** 14-bar raw %K; SMA(3) slow K and SMA(3) D; cross from K<=20 BUY / K>=80 SELL. Flat range=50.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[stochastic]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[stochastic]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/oscillators/stochastic-oscillator/`

## 06. ADX directional crossover — `adx`

| Attribute | Value |
|---|---|
| Family | Trend |
| Recipe | public.forex.adx.v1 |
| Definition/version | PUBLIC_FOREX_ADX_V1 |
| Profile SHA-256 | fcc8276669886e7a0c0392280f264826e34d19cfb690f0904d91b4f94a607278 |
| Warm-up bars | 29 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_ADX_V1 |
| Policy hash | 44a6d4f3ca3c19426873e894787bf9452e648e306d50adf9f426e172d295ec25 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Wilder TR/DM(14), DX and ADX(14); DI crossover only with current ADX>=25. Negative DM uses previous low minus current low.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[adx]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[adx]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/trend/directional-movement-system/`

## 07. Ichimoku cloud breakout — `ichimoku`

| Attribute | Value |
|---|---|
| Family | Trend |
| Recipe | public.forex.ichimoku.v1 |
| Definition/version | PUBLIC_FOREX_ICHIMOKU_V1 |
| Profile SHA-256 | 434336a82ccc17ce7119b7c4e05a481e988e8d057e2464a63a29e4ee51c7a4f5 |
| Warm-up bars | 79 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_ICHIMOKU_V1 |
| Policy hash | ef89d73d4ed8515c9a941b73bccf73c639768a1a26abd32829eb500aba62363b |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** 9/26/52 midranges. Cloud at index i uses spans computed i-26; close crosses outside cloud with matching Tenkan/Kijun direction. Never backdate current close as evidence.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[ichimoku]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[ichimoku]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/other/ichimoku-kinko-hyo/`

## 08. Donchian channel breakout — `donchian`

| Attribute | Value |
|---|---|
| Family | Breakout |
| Recipe | public.forex.donchian.v1 |
| Definition/version | PUBLIC_FOREX_DONCHIAN_V1 |
| Profile SHA-256 | 7b554cb359d78c615f153d1c1301b4ceeaf31335770b908a41280cd8d507b74b |
| Warm-up bars | 21 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_DONCHIAN_V1 |
| Policy hash | fe7cb5a485c9a1ebbba77d0f7a12f2dbafec06cb9d09de43a3502a52514240e9 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Strict completed close beyond previous 20-bar high/low, excluding the breakout bar. One crossing event, not one per trend bar.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[donchian]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[donchian]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/volatility/donchian-channel/`

## 09. Time-series momentum — `momentum`

| Attribute | Value |
|---|---|
| Family | Momentum |
| Recipe | public.forex.momentum.v1 |
| Definition/version | PUBLIC_FOREX_MOMENTUM_V1 |
| Profile SHA-256 | a2ba84397d5b6c1ed23eace22568cc86431b82043af001201b07169e071f6ab7 |
| Warm-up bars | 22 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_MOMENTUM_V1 |
| Policy hash | 6827de1ff04e9457f371d4138e5d0306f4574a31246d5f0997cd131cc3b3b10b |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** 20-bar close ratio minus one; crossing zero projects direction. This is a price momentum lens, not the custom M38/M39 portfolio rules.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[momentum]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[momentum]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/oscillators/momentum-oscillator/`

## 10. Bollinger band re-entry — `bollinger`

| Attribute | Value |
|---|---|
| Family | Mean reversion |
| Recipe | public.forex.bollinger.v1 |
| Definition/version | PUBLIC_FOREX_BOLLINGER_V1 |
| Profile SHA-256 | 4dc2b2001887a9f3a6601b6eb7128428aa67b8be7431dab876fcc144faa298d6 |
| Warm-up bars | 22 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_BOLLINGER_V1 |
| Policy hash | ae6e86217adb7e785988f2e540859a6944f3a2f35198b0230c96286d25808ebe |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** SMA(20) +/-2 population standard deviations. BUY on return inside from below lower band, SELL from above upper band.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[bollinger]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[bollinger]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/volatility/bollinger-bands/`

## 11. Bullish / bearish engulfing — `engulfing`

| Attribute | Value |
|---|---|
| Family | Candlesticks |
| Recipe | public.forex.engulfing.v1 |
| Definition/version | PUBLIC_FOREX_ENGULFING_V1 |
| Profile SHA-256 | 6326bc8c646e5d098e23d4e8e99f771aa77b4eea0add2fe169096ef76f4e1ec3 |
| Warm-up bars | 2 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_ENGULFING_V1 |
| Policy hash | 306e2f64caa2a78dc090e657271c0890b46d9a1cc21b6b4493d9240137307411 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Opposite non-doji bodies; current body strictly exceeds and contains previous body. Shape observation only, not a context-qualified trade. Prior trend and optional volume qualification are not inferred.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[engulfing]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[engulfing]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarkets.com/en-gb/technical-analysis/bullish-and-bearish-candle-stick-patterns`

## 12. Hammer / shooting-star rejection — `pinbar`

| Attribute | Value |
|---|---|
| Family | Candlesticks |
| Recipe | public.forex.pinbar.v1 |
| Definition/version | PUBLIC_FOREX_PINBAR_V1 |
| Profile SHA-256 | c1aa1e90037f84b5ab0211eb665adbaea693b8be5fb408c549bebfed41bfbecd |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_PINBAR_V1 |
| Policy hash | 1ffe62c6360b995b99ad11a91ae4792d765b14a55ba157d6ed2950dc471168a4 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Dominant wick>=2*body and >=60% range; opposite wick<=20% range and body<=30%. Shape only; no fabricated trend or volume confirmation.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[pinbar]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[pinbar]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.learntotradethemarket.com/forex-trading-strategies/price-action-setups-pin-bars-fakeys-inside-bars`

## 13. Inside-bar breakout — `inside_break`

| Attribute | Value |
|---|---|
| Family | Candlesticks |
| Recipe | public.forex.inside_break.v1 |
| Definition/version | PUBLIC_FOREX_INSIDE_BREAK_V1 |
| Profile SHA-256 | 99e0733fabbaa5b129963e77e14add9625f2385402ec4ed398fc8957f335b5dd |
| Warm-up bars | 3 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_INSIDE_BREAK_V1 |
| Policy hash | e68ad6ec57dbf46492fad1aaf1fc721e2e3e2e6b8de49bee09837b571cdc9b74 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Strict inside bar followed by strict completed close outside its mother high/low.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[inside_break]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[inside_break]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.learntotradethemarket.com/forex-trading-strategies/price-action-setups-pin-bars-fakeys-inside-bars`

## 14. Market structure · BOS / CHoCH — `structure`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.structure.v1 |
| Definition/version | PUBLIC_FOREX_STRUCTURE_V1 |
| Profile SHA-256 | e3801398bec58fbc93f5a78c9ed04573f3b24bf5ed11cf7cb851afe468528dc4 |
| Warm-up bars | 6 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_STRUCTURE_V1 |
| Policy hash | c31d95b69be29d2d769f145a72087ac0353c45cad7b20e52fb1df0b860dfcc3e |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** First strict close across latest already-confirmed shared-profile swing (default 2-left/2-right). Same-direction break=BOS, opposite prior break=CHoCH; initial direction=BOS. Each pivot consumed once.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[structure]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[structure]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/break-of-structure/`

## 15. Liquidity sweep and reclaim — `liquidity`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.liquidity.v1 |
| Definition/version | PUBLIC_FOREX_LIQUIDITY_V1 |
| Profile SHA-256 | 33b8caedbc4069dcdf0293e684514005579d6f3f0779be32b2a35fee89af3335 |
| Warm-up bars | 6 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_LIQUIDITY_V1 |
| Policy hash | 122f1bd5c45929f8cc83191c476a46fedd75ba937fdbba8fb0c62fcf9b620220 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Wick strictly breaches an already-confirmed pivot but closes back inside; labels price-derived liquidity, not actual institutional orders. Includes measured equal-high/low clusters.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[liquidity]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[liquidity]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/liquidity-sweep/`

## 16. Order blocks — `order_block`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | sfm.order_block.research.v1 |
| Definition/version | PUBLIC_FOREX_ORDER_BLOCK_V1 |
| Profile SHA-256 | 028d86cc1c60e2b0ee1d9858fd975b46544f5676baef2ca781c5033ba8f65dc5 |
| Warm-up bars | 20 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | ORDER_BLOCK |
| Policy | PUBLIC_LIMIT_RESEARCH_ORDER_BLOCK_V1 |
| Policy hash | 5d7fca44826e88937ac57581dd88a6d2c954e74367b4ddbbac76c8b58822a6e3 |
| Trigger | NATIVE_OB_ZONE |

**Analytical rules:** Existing causal opposite-candle / displacement / pivot-break producer; full source high/low, touch and close-beyond-distal invalidation. Its SFM stable ID is retained, not excluded.

**Parameters:** `[]`

**Research entry:** Confirmed native Order Block zone; proximal Limit entry and distal invalidation. This single-method profile is NOT the separately gated D1/H4 MTF recipe.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[order_block]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[order_block]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/order-block/`

## 17. Fair-value gaps — `fvg`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.fvg.v1 |
| Definition/version | PUBLIC_FOREX_FVG_V1 |
| Profile SHA-256 | 6cf8e14f65893ac03322888fb9c06d7da970601cd9e719fdf10c8059064e3605 |
| Warm-up bars | 3 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_FVG_V1 |
| Policy hash | 37c8259865f06404bc1be0b834306564f80af8f6ac136bdd05f5cde23674eb6f |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Strict three-closed-bar high/low gap. Subsequent contact=TOUCHED, full wick traversal=FILLED, strict distal close=INVALIDATED. Starts only after confirmation.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[fvg]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[fvg]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/fair-value-gap/`

## 18. Order-block pullback / mitigation — `pullback_ob`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.pullback_ob.v1 |
| Definition/version | PUBLIC_FOREX_PULLBACK_OB_V1 |
| Profile SHA-256 | 4fa77c963ea936081960c458fd722f0fb9bc512f338925798189270927554a54 |
| Warm-up bars | 21 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SMC_STRUCTURE |
| Policy | PUBLIC_LIMIT_RESEARCH_PULLBACK_OB_V1 |
| Policy hash | 3eb4146ff9117bb80232033e9817e4b4adec3bd78a460ba914ef5fce71312d87 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** First later intersection of a causally confirmed order block, directional candle response and close back beyond proximal. Distinct from the custom M21 capital/qualification rules.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[pullback_ob]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[pullback_ob]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/order-block/`

## 19. FVG pullback / mitigation — `pullback_fvg`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.pullback_fvg.v1 |
| Definition/version | PUBLIC_FOREX_PULLBACK_FVG_V1 |
| Profile SHA-256 | 56e1c426686cda3c5ac24c920ec93bec0cf7d401055da4c963b6d457eecae5dc |
| Warm-up bars | 4 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_PULLBACK_FVG_V1 |
| Policy hash | 2ce93ad639d2a5ffac949fa0e76ebe184c4cb22da79de997d2292e78d60e2904 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** First later gap intersection with directional candle response and close beyond proximal, before invalidation/full fill.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[pullback_fvg]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[pullback_fvg]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/fair-value-gap/`

## 20. Wyckoff · Spring / UTAD / SOS / SOW — `wyckoff`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.wyckoff.v1 |
| Definition/version | PUBLIC_FOREX_WYCKOFF_V1 |
| Profile SHA-256 | b46a3fb6e4409fb80993125a2fdce58f96f676f70d5d684318c209c571656341 |
| Warm-up bars | 22 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_WYCKOFF_V1 |
| Policy hash | 9b85c9f632f381b8e269c87da97287e06b7c1bc86ec89e329ae643f28df7228b |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Bounded 20-bar range hypothesis; >=2 separated tests on each boundary within 10% width. Sweep/reclaim=Spring/UTAD; later lower-range test without a new low or upper test without a new high=TEST. Strong close outside range=SOS/SOW. OHLC hypothesis, not volume-confirmed phase certainty.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[wyckoff]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[wyckoff]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.wyckoffanalytics.com/wyckoff-method/`

## 21. Elliott impulse hypothesis — `elliott_impulse`

| Attribute | Value |
|---|---|
| Family | Patterns |
| Recipe | public.forex.elliott_impulse.v1 |
| Definition/version | PUBLIC_FOREX_ELLIOTT_IMPULSE_V1 |
| Profile SHA-256 | 0783eb1015a21972377333326c7fcea129f212f6613488b9badd95ff728fbb5f |
| Warm-up bars | 26 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_ELLIOTT_IMPULSE_V1 |
| Policy hash | 7dcece1d574c42e57191b598ffb279943e0bc227af5fd3e20ad15ebe0bf715ee |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Six consecutive alternating confirmed pivots. Wave2<100% wave1, wave3 exceeds wave1 and is not shortest, wave4 does not overlap wave1, wave5 exceeds wave3. No recursive degree, diagonal or truncation claim.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[elliott_impulse]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[elliott_impulse]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.elliottwave.com/waveopedia/impulse/`
- `https://www.elliottwave.com/waveopedia/motive-waves/`

## 22. Elliott ABC zigzag hypothesis — `elliott_abc`

| Attribute | Value |
|---|---|
| Family | Patterns |
| Recipe | public.forex.elliott_abc.v1 |
| Definition/version | PUBLIC_FOREX_ELLIOTT_ABC_V1 |
| Profile SHA-256 | 19de7b9b4598bc07577f9f32517ec3a916bdbf89cecf05211a698bdc440846b7 |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_ELLIOTT_ABC_V1 |
| Policy hash | 2bc0c5a1c576155c6e4bb923d6ed629eb1cb1295904d3d6661ef9ba2ce4b270c |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Four consecutive alternating confirmed pivots; B retraces less than A and C extends beyond A. Completed-pivot price skeleton only; no claim of verified 5-3-5 internal subdivisions.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[elliott_abc]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[elliott_abc]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.elliottwave.com/waveopedia/zigzags/`

## 23. Harmonic AB=CD — `abcd`

| Attribute | Value |
|---|---|
| Family | Patterns |
| Recipe | public.forex.abcd.v1 |
| Definition/version | PUBLIC_FOREX_ABCD_V1 |
| Profile SHA-256 | 1cb5e898cde618400c19abe03e14cd404f10e9f459df0a7f15d006bc6a8bff6a |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_ABCD_V1 |
| Policy hash | 62ad2e5c73bd85583be43b4dcbfaf51d506ff0240476311b803e7e7f5382a779 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Four consecutive alternating confirmed pivots: BC/AB .382-.886; CD/BC 1.13-2.618; CD/AB=1 +/-5%. Price-ratio skeleton, not time symmetry or calibration.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[abcd]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[abcd]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://harmonictrader.com/harmonic-patterns/abcd-pattern/`

## 24. Harmonic Gartley — `gartley`

| Attribute | Value |
|---|---|
| Family | Patterns |
| Recipe | public.forex.gartley.v1 |
| Definition/version | PUBLIC_FOREX_GARTLEY_V1 |
| Profile SHA-256 | fc9523dae3db3b413bdb7ac58216eed3bb68ffef1e3e8652691fcab31585f519 |
| Warm-up bars | 21 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_GARTLEY_V1 |
| Policy hash | a84bb18c7e42937939f41855a0ed1ae54b2d490f3d9b87312ab51ba083b7f673 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Five consecutive alternating confirmed pivots. B/XA=.618 +/-5%, BC/AB .382-.886, AD/XA=.786 +/-5%, CD/BC 1.27-1.618 and CD/AB=1 +/-5%. Relative tolerance is engineering configuration.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[gartley]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[gartley]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://harmonictrader.com/harmonic-patterns/gartley-pattern/`

## 25. Harmonic Bat — `bat`

| Attribute | Value |
|---|---|
| Family | Patterns |
| Recipe | public.forex.bat.v1 |
| Definition/version | PUBLIC_FOREX_BAT_V1 |
| Profile SHA-256 | 5b369633f8e519a6434de16c8de435e77642a2e012ee1aa03a3bc3b280c90d26 |
| Warm-up bars | 21 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_BAT_V1 |
| Policy hash | 5631c23b65cdc2129a28f4b35da04d1cbcb61b0afb789cc23b9958f414b8b440 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Five consecutive alternating confirmed pivots. B/XA .382-.5, BC/AB .382-.886, AD/XA=.886 +/-5%, CD/BC 1.618-2.618 and CD/AB>=.95. Explicit bounded price skeleton, not calibrated prediction.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[bat]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[bat]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://harmonictrader.com/harmonic-patterns/bat-pattern/`

## 26. Harmonic Butterfly — `butterfly`

| Attribute | Value |
|---|---|
| Family | Patterns |
| Recipe | public.forex.butterfly.v1 |
| Definition/version | PUBLIC_FOREX_BUTTERFLY_V1 |
| Profile SHA-256 | e6bf48d1b439083a6ad007db89449e313cad5dfa004b4789d3a82c98974ec6b3 |
| Warm-up bars | 21 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_BUTTERFLY_V1 |
| Policy hash | 87378145a14c0291eb10cc4c094e46e6b3643d9c2bc14ce42eb6cd78473292cd |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Five consecutive alternating confirmed pivots. B/XA=.786 +/-5%, BC/AB .382-.886, AD/XA=1.27 +/-5%, CD/BC 1.618-2.618 and CD/AB .95-1.3335. Explicit bounded price skeleton.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[butterfly]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[butterfly]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://harmonictrader.com/harmonic-patterns/butterfly-pattern/`

## 27. Confirmed swing support / resistance — `support_resistance`

| Attribute | Value |
|---|---|
| Family | Levels |
| Recipe | public.forex.support_resistance.v1 |
| Definition/version | PUBLIC_FOREX_SUPPORT_RESISTANCE_V1 |
| Profile SHA-256 | cb7e31101504043a125515d33c6e34c9c0c77f752d26d80cf24f3c7fd56c8ecb |
| Warm-up bars | 6 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_SUPPORT_RESISTANCE_V1 |
| Policy hash | d04cf0fe276d11603b2c3ef65fcd0afdbf9b7b5df2739a068dc08d27cb67e01c |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Last eight causally confirmed swing highs/lows, each line starts at its confirmation time, not its earlier pivot time.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[support_resistance]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[support_resistance]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/break-of-structure/`

## 28. Fibonacci retracement — `fibonacci`

| Attribute | Value |
|---|---|
| Family | Levels |
| Recipe | public.forex.fibonacci.v1 |
| Definition/version | PUBLIC_FOREX_FIBONACCI_V1 |
| Profile SHA-256 | 9d230016b5733696422ed01193323015eee77345f26534c8dc3da6297620dbe9 |
| Warm-up bars | 10 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_FIBONACCI_V1 |
| Policy hash | 78e40f90a6b91dcd34dc9fa0844564f3a1dded3b4b29be0c733790a5d7c93c11 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Latest alternating confirmed swing leg; .382/.5/.618/.786 measurements from leg end toward origin. No predictive success claim.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[fibonacci]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[fibonacci]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/fibonacci-retracement/`

## 29. Optimal trade entry (OTE) — `ote`

| Attribute | Value |
|---|---|
| Family | Levels |
| Recipe | public.forex.ote.v1 |
| Definition/version | PUBLIC_FOREX_OTE_V1 |
| Profile SHA-256 | dccf1c551fb827fcde1c45614d38b9d22d56091a6a91cc0b3890e06260501bf5 |
| Warm-up bars | 10 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_OTE_V1 |
| Policy hash | 1a68a17bfa5342188a134a59973f424236cf8e50510a1b1fa59e538aa5b41415 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Confirmed leg .62-.79 retracement zone and .705 midpoint. Versioned explicit decimal convention, not automatic entry.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[ote]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[ote]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/optimal-trade-entry/`

## 30. Previous D1 / W1 high and low — `previous_extremes`

| Attribute | Value |
|---|---|
| Family | Levels |
| Recipe | public.forex.previous_extremes.v1 |
| Definition/version | PUBLIC_FOREX_PREVIOUS_EXTREMES_V1 |
| Profile SHA-256 | 2ccadb8f1931997cfa8cba9f391488496a543b0f5ad2b4812a9eba602d693ca0 |
| Warm-up bars | 2 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_PREVIOUS_EXTREMES_V1 |
| Policy hash | 99ead9dcb1b97b729750fe5a014166ed052f89bf0ea597a008c3532df0ab2335 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Latest causally completed D1/W1 high and low projected onto each pair chart with original source-frame labels. No broker-calendar reconstruction.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[previous_extremes]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[previous_extremes]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/liquidity-sweep/`

## 31. D1 / W1 open and midpoint — `open_midpoint`

| Attribute | Value |
|---|---|
| Family | Levels |
| Recipe | public.forex.open_midpoint.v1 |
| Definition/version | PUBLIC_FOREX_OPEN_MIDPOINT_V1 |
| Profile SHA-256 | 0a764d9a573d65b1e4733aa6e923cb27a6cbfcf5ad7190e9b69ce911d2604998 |
| Warm-up bars | 2 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_OPEN_MIDPOINT_V1 |
| Policy hash | 253985faff99c4cec03306a096f658728904bcfb9678fc4c343f76877054ef3a |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Observed latest completed D1/W1 open plus (high+low)/2; explicitly last-completed, never invented current-session OHLC.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[open_midpoint]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[open_midpoint]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/smart-money-concepts/`

## 32. Compression breakout — `compression`

| Attribute | Value |
|---|---|
| Family | Breakout |
| Recipe | public.forex.compression.v1 |
| Definition/version | PUBLIC_FOREX_COMPRESSION_V1 |
| Profile SHA-256 | 42798a1d661022b6086f1b011c2e5c7e35429743c6f60e53b85a142a17d0186c |
| Warm-up bars | 42 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_COMPRESSION_V1 |
| Policy hash | 6ee2f2b04ab4b931c2be978011011986bf63e6557830a33178d7f6250da4916c |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Previous 10-bar range<=50% preceding 30-bar range; current directional body>=60% own range and close strictly outside compression. No custom M20 execution lifecycle.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[compression]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[compression]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/volatility/donchian-channel/`

## 33. Price displacement — `displacement`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.displacement.v1 |
| Definition/version | PUBLIC_FOREX_DISPLACEMENT_V1 |
| Profile SHA-256 | fbcd9741d6f1b19dceb1324dce65aee947bba699ae40d976a9b6a555bb9168cc |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_DISPLACEMENT_V1 |
| Policy hash | aa8dd22c04de2f09fd9ef0b5eced64c9da262b9d2186329f2d23edefd6d5308c |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Completed directional body >=60% own range and >=1.0 times previous 14-bar mean true range, excluding current bar. Price pressure only, not traded volume.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[displacement]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[displacement]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/ict-trading/`

## 34. Market structure shift · sweep / displacement — `mss`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.mss.v1 |
| Definition/version | PUBLIC_FOREX_MSS_V1 |
| Profile SHA-256 | 1a17e383743b8ad42341d92cde9614b9b1f2aa5d08194b86d7dea39c5928f243 |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_MSS_V1 |
| Policy hash | 734c84d0fb8de00033990525b4a12e0c48f6eb737ead6bc00968c5349a7c63ca |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Confirmed pivot sweep/reclaim, later opposite displacement, then close-confirmed break of an already-known controlling opposite pivot within 8 bars. No same-bar chronological inference.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[mss]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[mss]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/ict-trading/`

## 35. Sweep depth / severity context — `sweep_context`

| Attribute | Value |
|---|---|
| Family | Liquidity |
| Recipe | public.forex.sweep_context.v1 |
| Definition/version | PUBLIC_FOREX_SWEEP_CONTEXT_V1 |
| Profile SHA-256 | ff377b35ef3929fb78c0073e8785cef8303d2c35485679aa8228f604f6e588be |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_SWEEP_CONTEXT_V1 |
| Policy hash | cb2874cd81ec5d2b7c559ab339daa1a3e1a4c560708fedd8795784d354f2fdf2 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Unique confirmed pivot breach and reclaim. Report observed overshoot divided by prior 14 true-range mean and bars since confirmation. No estimate of actual stop volume.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[sweep_context]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[sweep_context]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/liquidity-sweep/`

## 36. Liquidity pools · lifecycle / density — `liquidity_pools`

| Attribute | Value |
|---|---|
| Family | Liquidity |
| Recipe | public.forex.liquidity_pools.v1 |
| Definition/version | PUBLIC_FOREX_LIQUIDITY_POOLS_V1 |
| Profile SHA-256 | 25ab070e484127ea76811aa093c38d873363277f0c887b137bdd231178223909 |
| Warm-up bars | 6 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_LIQUIDITY_POOLS_V1 |
| Policy hash | 070bb9948275ee8ea7d4e259217e21fe9e2956304be45facbc105e9706946749 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Confirmed swing and <=2 native-tick equal-extreme clusters. Freeze pool roots/bounds at confirmation; count later contacts; reclaim=consumed sweep, close beyond=broken, expiry=128 own-frame bars. Density counts price roots, not orders.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[liquidity_pools]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[liquidity_pools]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/liquidity-sweep/`

## 37. Liquidity pool · confirmed rejection — `pool_rejection`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.pool_rejection.v1 |
| Definition/version | PUBLIC_FOREX_POOL_REJECTION_V1 |
| Profile SHA-256 | b5548ba59e947c2f88da216f5c0193a050238015ca66896330ee9058d7a6bda4 |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_POOL_REJECTION_V1 |
| Policy hash | 932362bf2e02ecf3cdfe216138a2c2805ce568d686450093d4b15d371093870d |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Price-pool sweep/reclaim -> later displacement -> controlling close break -> later origin retest with directional response. Sweep extreme invalidates; 8-bar confirmation and 16-bar retest deadlines.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[pool_rejection]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[pool_rejection]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/liquidity-sweep/`

## 38. Liquidity pool · acceptance / held retest — `pool_breakout`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.pool_breakout.v1 |
| Definition/version | PUBLIC_FOREX_POOL_BREAKOUT_V1 |
| Profile SHA-256 | a87bc9c7da2a677dd35ae36774979ee99df16afc0484eedc57866d535f89286c |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_POOL_BREAKOUT_V1 |
| Policy hash | f50c5943d7276857ccf12d02445af52011747a09fad2c6c7394f560f61b619e1 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Frozen confirmed pivot boundary -> displacement close beyond -> second later close accepted beyond -> still later held boundary retest and directional close. Prior broken geometry is not a reversal by default.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[pool_breakout]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[pool_breakout]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/trading-with-support-and-resistance-zones/`

## 39. Sweep reversal · confirmed origin retest — `sweep_reversal`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.sweep_reversal.v1 |
| Definition/version | PUBLIC_FOREX_SWEEP_REVERSAL_V1 |
| Profile SHA-256 | ad20a501c3c954e4c262c09b691395bc257e384579de58f58852e62077d14df1 |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_SWEEP_REVERSAL_V1 |
| Policy hash | f133f5fff519a403d43e07546e4f4333643436f1ffe18bc0405c25b816ac6eef |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Confirmed pivot sweep/reclaim -> later displacement -> opposite structure break -> last opposite source candle no earlier than two bars before the sweep, or newly created FVG -> first subsequent directional held retest. No retrospective fill or automatic signal.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[sweep_reversal]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[sweep_reversal]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/liquidity-sweep/`
- `https://cmcmarketsfunded.com/learn/ict-trading/`

## 40. Compression breakout · acceptance / retest — `compression_retest`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.compression_retest.v1 |
| Definition/version | PUBLIC_FOREX_COMPRESSION_RETEST_V1 |
| Profile SHA-256 | 025c5de7021d86dd74d5ecb24864e5826f490fc050f920f9636282ed9d26b0bc |
| Warm-up bars | 42 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_COMPRESSION_RETEST_V1 |
| Policy hash | da9c8590da632af3826c64d25170b9f92ee2a5d4a69bd5cc8283ae70e34d6329 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Previous 10-bar range <=50% preceding 30-bar range; displacement break -> later accepted close -> later held retest within 16 bars. Close back inside invalidates before retest. Engineering profile, not archived M20 acceptance.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[compression_retest]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[compression_retest]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/volatility/donchian-channel/`

## 41. Break confirmation · failed reclaim / micro break — `break_confirmation`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.break_confirmation.v1 |
| Definition/version | PUBLIC_FOREX_BREAK_CONFIRMATION_V1 |
| Profile SHA-256 | fce74a299af16eb2bd20537837a3bd48a5e63b6ea93af7fbac6c0da81d47bf4a |
| Warm-up bars | 23 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_BREAK_CONFIRMATION_V1 |
| Policy hash | d337e97e377ce429396ed4891d853dbbc6b78d668266d24d014d7fa6444ada98 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Prior 20-bar boundary -> displacement breakout -> later acceptance -> failed reclaim/held retest -> still later close beyond retest candle high/low within 8 bars. No new entry family or broker command.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[break_confirmation]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[break_confirmation]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/trading-with-support-and-resistance-zones/`

## 42. Continuation pullback · order block — `trend_ob`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.trend_ob.v1 |
| Definition/version | PUBLIC_FOREX_TREND_OB_V1 |
| Profile SHA-256 | 278c73d481a14834944528e8742ef68c2fd035993a4eb26b98ce936215f368db |
| Warm-up bars | 20 |
| Supporting frames | D1, W1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SMC_STRUCTURE, SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_TREND_OB_V1 |
| Policy hash | 2843088cabcd54e41a02e052a0886d573f3f6e5c1d8e8784e04010d6c696387a |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Existing displacement/BOS source candle; same-direction preceding D1 structure context (W1 for D1/W1), directional later OB retest, intact distal and opposite confirmed swing objective. FVG is never substituted for the OB.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[trend_ob]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[trend_ob]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/order-block/`

## 43. Continuation pullback · FVG — `trend_fvg`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.trend_fvg.v1 |
| Definition/version | PUBLIC_FOREX_TREND_FVG_V1 |
| Profile SHA-256 | e3b9212d558859dd0f1d8747b57124d2aa81aae489cf18bc2dcc752d76007b6d |
| Warm-up bars | 20 |
| Supporting frames | D1, W1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SMC_STRUCTURE, SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_TREND_FVG_V1 |
| Policy hash | 203f982a5a8ce7afcf7f1ca4489fe970bd4a8897b111670eba5d88e0837a45fb |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Close-confirmed displacement structure and same-direction preceding D1 context (W1 for D1/W1); later first held FVG mitigation before full traversal or invalidation; open opposing swing objective.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[trend_fvg]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[trend_fvg]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/fair-value-gap/`

## 44. Structure / displacement · OB or FVG retest — `smc_zone_retest`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.smc_zone_retest.v1 |
| Definition/version | PUBLIC_FOREX_SMC_ZONE_RETEST_V1 |
| Profile SHA-256 | ba3dcfe2186ac2d62629393e7ba15e89dfa18a05d936a4ece0b0ab960943e420 |
| Warm-up bars | 20 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SMC_STRUCTURE, SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_SMC_ZONE_RETEST_V1 |
| Policy hash | ff4606c2ccf681afb2130ccdf18b73c7d9ef02aeae1295b0f376b746d62c738d |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Known controlling BOS/CHoCH with displacement -> causally formed OB or FVG -> first later directional held retest. Distinct source-zone roots; no MTF or volume consensus fabricated.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[smc_zone_retest]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[smc_zone_retest]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/ict-trading/`

## 45. Breaker block · failed OB conversion — `breaker`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.breaker.v1 |
| Definition/version | PUBLIC_FOREX_BREAKER_V1 |
| Profile SHA-256 | 4ac62e39dc77935076bba39dbff17febc3a40b99707236e0a9fb449b2959a113 |
| Warm-up bars | 20 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_BREAKER_V1 |
| Policy hash | 39d0e44d8a496a564fe2d66509e326dd4ac780538e60e174d2b1fd334328beff |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Causally formed order block -> later liquidity sweep -> opposite displacement and controlling structure break through its distal -> later retest from flipped side. Each stage ordered; original OB failure is retained.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[breaker]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[breaker]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/breaker-block/`

## 46. Mitigation block · failure swing / MSS — `mitigation_block`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.mitigation_block.v1 |
| Definition/version | PUBLIC_FOREX_MITIGATION_BLOCK_V1 |
| Profile SHA-256 | 32f244e09c16aa63283b1cf1827f2e53956e3beec82476c62f44cf46b6c6cb8c |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_MITIGATION_BLOCK_V1 |
| Policy hash | dac6ea139c67d0671ce8b15c7b36d6772b04697fbf70382a2332dcfab691373f |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Known high-low-high lower-high or low-high-low higher-low failure swing, without taking the first extreme -> later displacement close through intervening swing -> source candle of failed leg -> later opposite held retest.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[mitigation_block]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[mitigation_block]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/mitigation-blocks-how-may-traders-identify-and-trade-them/`

## 47. Inducement · internal sweep / origin response — `inducement`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.inducement.v1 |
| Definition/version | PUBLIC_FOREX_INDUCEMENT_V1 |
| Profile SHA-256 | 465da3632d7b2b5a084c12ea2df6df8e868872f59f554606de286a602c3446e6 |
| Warm-up bars | 20 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_INDUCEMENT_V1 |
| Policy hash | 07cde442419630322da43ec2de18221af64f613d3e3da497e145b51101705acc |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Known controlling displacement break establishes origin; newly confirmed internal pivot stays between origin and break extreme; later internal sweep then subsequent directional origin retest. Public price hypothesis, never proof of intentional trapping.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[inducement]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[inducement]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/inducement-trading/`

## 48. Liquidity void · multi-candle return — `liquidity_void`

| Attribute | Value |
|---|---|
| Family | Structure |
| Recipe | public.forex.liquidity_void.v1 |
| Definition/version | PUBLIC_FOREX_LIQUIDITY_VOID_V1 |
| Profile SHA-256 | 9641ad3c2bc6b668c3ba38b903ac36de937bb480064f0d67701144129ff85dfa |
| Warm-up bars | 18 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_LIQUIDITY_VOID_V1 |
| Policy hash | 16c502d1ce9a01aee8cd52e5973bd48da419b69ab81d5a6c9405ba04b234380b |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Three same-direction >=60%-body candles, each body overlap <=25% smaller body, total move >=2 preceding 14-bar mean TR. Later return into frozen body corridor with directional response; far-edge close invalidates. Not three-bar FVG or genuine order-flow measurement.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[liquidity_void]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[liquidity_void]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/fair-value-gaps-vs-liquidity-voids-in-trading/amp`

## 49. Previous-day high/low · sweep reversal — `previous_day_sweep`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.previous_day_sweep.v1 |
| Definition/version | PUBLIC_FOREX_PREVIOUS_DAY_SWEEP_V1 |
| Profile SHA-256 | 97fa1870eee97bff443ce4d2b92f4c3a8ae48c02fad3c16c99d317982ffbb330 |
| Warm-up bars | 16 |
| Supporting frames | D1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_PREVIOUS_DAY_SWEEP_V1 |
| Policy hash | 772f25214f0325035bf2a6f18fa08b8ba0d97cfec82d6533a535781a9d2917ed |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** At each bar select D1 closed and available before its open. Breach/reclaim -> later displacement / controlling pivot break -> later held origin retest. Daily identity freezes at sweep; no future daily boundary or duplicate order.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[previous_day_sweep]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[previous_day_sweep]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/liquidity-sweep/`

## 50. Previous-day high/low · acceptance retest — `previous_day_breakout`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.previous_day_breakout.v1 |
| Definition/version | PUBLIC_FOREX_PREVIOUS_DAY_BREAKOUT_V1 |
| Profile SHA-256 | 7bbf1ca9d978699528d435f2ae7fbe9693ddfd75e23bfdd2c15d282870d85346 |
| Warm-up bars | 16 |
| Supporting frames | D1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_PREVIOUS_DAY_BREAKOUT_V1 |
| Policy hash | 34198d6132d3c634f38806229bfd3e5a5e445e66e2532a132a95289c81647da0 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Frozen prior available D1 high/low -> displacement close beyond -> later accepted close -> later held boundary retest. A new D1 record cannot re-anchor an existing sequence.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[previous_day_breakout]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[previous_day_breakout]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/trading-with-support-and-resistance-zones/`

## 51. Asian session · complete range — `session_asia`

| Attribute | Value |
|---|---|
| Family | Sessions |
| Recipe | public.forex.session_asia.v1 |
| Definition/version | PUBLIC_FOREX_SESSION_ASIA_V1 |
| Profile SHA-256 | 0bba7147432e8bdce646372ff347df68b3c62eff419f1dd2df0b342d52c0075a |
| Warm-up bars | 1 |
| Supporting frames | H1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_SESSION_ASIA_V1 |
| Policy hash | ee8b2c6c6a19184f67b130fd80a0655f588e0ddc2cb867e2c2b181366a55cd2f |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Asia/Tokyo 09:00–15:00 local, six contiguous closed H1 bars. Emit only at session completion; retain exact UTC interval and H1 roots. This explicit research window is not a universal broker session.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[session_asia]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[session_asia]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/forex-trading-time-zones-market-hours-and-overlaps`

## 52. London session · complete range — `session_london`

| Attribute | Value |
|---|---|
| Family | Sessions |
| Recipe | public.forex.session_london.v1 |
| Definition/version | PUBLIC_FOREX_SESSION_LONDON_V1 |
| Profile SHA-256 | 69f312cf9459d6685a2fb5d1d9343e1cdddc73f4e09bf20618edff7d866212ad |
| Warm-up bars | 1 |
| Supporting frames | H1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_SESSION_LONDON_V1 |
| Policy hash | d60c56fe2d44b9cb5d9986a9664fc4b03661da4fa04239c363a57d9bc5acd812 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Europe/London 08:00–16:00 local with IANA DST, eight contiguous H1 bars. Missing/inexact session support is unavailable, not an invented range.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[session_london]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[session_london]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/forex-trading-time-zones-market-hours-and-overlaps`

## 53. New York session · complete range — `session_new_york`

| Attribute | Value |
|---|---|
| Family | Sessions |
| Recipe | public.forex.session_new_york.v1 |
| Definition/version | PUBLIC_FOREX_SESSION_NEW_YORK_V1 |
| Profile SHA-256 | d31b40a53699eed927a5551133980207c6c0c2958448297bb671ba9ffcbac564 |
| Warm-up bars | 1 |
| Supporting frames | H1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_SESSION_NEW_YORK_V1 |
| Policy hash | 0d61950e0153deccf7473212a0258ef0e177d2247a65b389e23f0e849a15137e |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** America/New_York 08:00–17:00 local with IANA DST, nine contiguous H1 bars. Only actual fully observed completed sessions produce range levels.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[session_new_york]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[session_new_york]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/forex-trading-time-zones-market-hours-and-overlaps`

## 54. Session extremes · confirmed sweep response — `session_sweep`

| Attribute | Value |
|---|---|
| Family | Sessions |
| Recipe | public.forex.session_sweep.v1 |
| Definition/version | PUBLIC_FOREX_SESSION_SWEEP_V1 |
| Profile SHA-256 | 7a52ec155cc6d551ad3a988f5d141eb4f4c19fd827f0b763703c6b7f731fa913 |
| Warm-up bars | 1 |
| Supporting frames | H1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_SESSION_SWEEP_V1 |
| Policy hash | fff1b81e9fa47d4ed99573105632282316b03b63d6aaadc03dd6306f0d9142b2 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Last complete Asia/London/New York H1 session range -> later breach/reclaim -> subsequent H1 displacement and structure break -> later held origin retest. Max 24 observed H1 bars after session; no calendar/news assumption.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[session_sweep]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[session_sweep]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://cmcmarketsfunded.com/learn/liquidity-sweep/`
- `https://fxopen.com/blog/en/forex-trading-time-zones-market-hours-and-overlaps`

## 55. Session range · breakout / acceptance retest — `session_breakout`

| Attribute | Value |
|---|---|
| Family | Sessions |
| Recipe | public.forex.session_breakout.v1 |
| Definition/version | PUBLIC_FOREX_SESSION_BREAKOUT_V1 |
| Profile SHA-256 | 6ae611b28526089f33cb1269ddf76962ff7c56f6fb6fadf09f61706500a02fa6 |
| Warm-up bars | 1 |
| Supporting frames | H1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_SESSION_BREAKOUT_V1 |
| Policy hash | 11bf99c7e01a1a1663f61a94a0aa43a10d90f77c24940366b94ee513ed46b973 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Complete named-session H1 range -> later displacement break -> accepted close -> later held retest, within 24 observed H1 bars after session end. Original session bounds remain fixed.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[session_breakout]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[session_breakout]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/trading-with-support-and-resistance-zones/`
- `https://fxopen.com/blog/en/forex-trading-time-zones-market-hours-and-overlaps`

## 56. ICT killzones · DST-aware time context — `killzones`

| Attribute | Value |
|---|---|
| Family | Sessions |
| Recipe | public.forex.killzones.v1 |
| Definition/version | PUBLIC_FOREX_KILLZONES_V1 |
| Profile SHA-256 | f869a73088df4629a71acadaf88cb8c7dc7a85cb5243e65f8e7ea46572ef9668 |
| Warm-up bars | 1 |
| Supporting frames | H1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_KILLZONES_V1 |
| Policy hash | 85d2458e656d4ac0de7797eb36ecdeca3923140e7b54713821d5c9049eb2f857 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Explicit America/New_York windows: Asia 20–24, London 02–05, NY 07–10, London-close 10–12. Label only observed contiguous H1 windows; timing context is not confirmation or a broker-open claim.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[killzones]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[killzones]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/kill-zone-trading-in-forex/`

## 57. Range equilibrium · confirmed boundary rotation — `range_rotation`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.range_rotation.v1 |
| Definition/version | PUBLIC_FOREX_RANGE_ROTATION_V1 |
| Profile SHA-256 | 4483b8b205d053a66a35cb161da6d1eba9bbda68bbcb1f3e63e9ad4202cb7298 |
| Warm-up bars | 61 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_RANGE_ROTATION_V1 |
| Policy hash | 2618a8de842824672b4d2fb05a7527dfcd59bd532411ce06c2391128b587ccba |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** 20-bar range with >=2 separated tests each side within 10% width, current ATR14 <= prior 40-bar mean ATR, no 20-bar trend break; directional boundary reclaim -> later internal break. Display midpoint objective only, not partial-close instructions.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[range_rotation]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[range_rotation]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/how-to-trade-in-ranges-range-trading-strategies`

## 58. Wyckoff · causal price-phase hypotheses — `wyckoff_phase`

| Attribute | Value |
|---|---|
| Family | Wyckoff |
| Recipe | public.forex.wyckoff_phase.v1 |
| Definition/version | PUBLIC_FOREX_WYCKOFF_PHASE_V1 |
| Profile SHA-256 | 2a7d34d800408cf7fbae69329b8dd2bcb388d80942a96ca1bc2050006427a162 |
| Warm-up bars | 22 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_WYCKOFF_PHASE_V1 |
| Policy hash | 5e88b75b2b1eb97656705cd497ebc7982b3260724020d3973df5457456f37ab9 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Frozen tested 20-bar range; B=range, C=Spring/UTAD, D=SOS/SOW plus held retest, E=later continuation outside. Optional A requires prior climax/automatic response. Price-only phase uncertainty remains explicit; no volume-confirmed institutional claim.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[wyckoff_phase]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[wyckoff_phase]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.wyckoffanalytics.com/wyckoff-method/`

## 59. Wyckoff Spring · secondary test / response — `wyckoff_spring_test`

| Attribute | Value |
|---|---|
| Family | Wyckoff |
| Recipe | public.forex.wyckoff_spring_test.v1 |
| Definition/version | PUBLIC_FOREX_WYCKOFF_SPRING_TEST_V1 |
| Profile SHA-256 | 053cc7fcf65bd857700e94830683d1781e6596593f5764f87a494e292783deca |
| Warm-up bars | 22 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_WYCKOFF_SPRING_TEST_V1 |
| Policy hash | 62291f56f0caaf6b7187bc9bc0efc2a89c1be2f9c1b66fae651c71b295b2b1e1 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Tested frozen range -> low sweep and reclaim (Spring) -> later lower-boundary secondary test without new low -> later bullish response above test high within 10 bars. Spring extreme invalidates.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[wyckoff_spring_test]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[wyckoff_spring_test]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.wyckoffanalytics.com/wyckoff-method/`

## 60. Wyckoff UTAD · secondary test / response — `wyckoff_utad_test`

| Attribute | Value |
|---|---|
| Family | Wyckoff |
| Recipe | public.forex.wyckoff_utad_test.v1 |
| Definition/version | PUBLIC_FOREX_WYCKOFF_UTAD_TEST_V1 |
| Profile SHA-256 | e847e33ded5fc5818cd398502229fc00d31ae82f0fa20d4ee74cc008b9ba2f6c |
| Warm-up bars | 22 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_WYCKOFF_UTAD_TEST_V1 |
| Policy hash | a3b0f69470011f1ccc3a85a8cd26482dd499a94b9d8d6239883f5d8a116224fd |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Tested frozen range -> upper sweep and reclaim (UTAD) -> later upper-boundary test without new high -> later bearish response below test low. Explicit price-only distribution hypothesis.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[wyckoff_utad_test]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[wyckoff_utad_test]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.wyckoffanalytics.com/wyckoff-method/`

## 61. Wyckoff SOS / SOW · held range retest — `wyckoff_break_retest`

| Attribute | Value |
|---|---|
| Family | Wyckoff |
| Recipe | public.forex.wyckoff_break_retest.v1 |
| Definition/version | PUBLIC_FOREX_WYCKOFF_BREAK_RETEST_V1 |
| Profile SHA-256 | daecbde37c315c609d8f057c3f56fd704b0c01808417c0300f79348fc750b583 |
| Warm-up bars | 24 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_WYCKOFF_BREAK_RETEST_V1 |
| Policy hash | 00165d706a6d360ecb2f9b1f4cd857e77f819813c8929848bd9879ada2a4638f |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Tested frozen range and preceding Spring/UTAD/test context -> displacement SOS/SOW -> later accepted close -> subsequent held range-boundary retest. Does not count Spring and its sweep as independent votes.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[wyckoff_break_retest]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[wyckoff_break_retest]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.wyckoffanalytics.com/wyckoff-method/`

## 62. Elliott · competing counts / invalidation / Fib — `elliott_alternatives`

| Attribute | Value |
|---|---|
| Family | Patterns |
| Recipe | public.forex.elliott_alternatives.v1 |
| Definition/version | PUBLIC_FOREX_ELLIOTT_ALTERNATIVES_V1 |
| Profile SHA-256 | 97601fb168171a06df20d0dc12e6b912f6f6fa1b991b78f00b79cc8df3eea26e |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_ELLIOTT_ALTERNATIVES_V1 |
| Policy hash | 0cc13376a33ad72e23c2d7a9bb033def891256423c97dc19efdbb487194cc8af |
| Trigger | WAVE_RESPONSE |

**Analytical rules:** At each new confirmation compare consecutive 4-pivot ABC, 5-pivot developing impulse and 6-pivot impulse windows. Preserve competing IDs and hard-rule invalidation. Project .618/1.0/1.618 first-leg measured alternatives from the latest confirmed anchor: along a developing impulse, against a completed impulse or ABC. No recursive all-degrees claim.

**Parameters:** `[]`

**Research entry:** A prior available wave completion/invalidation zone plus a later directional closed-bar reclaim; competing counts remain competing, not extra votes.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[elliott_alternatives]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[elliott_alternatives]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.elliottwave.com/waveopedia/impulse/`
- `https://www.elliottwave.com/waveopedia/zigzags/`

## 63. W1 extreme / Elliott · linked structural retest — `macro_elliott`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.macro_elliott.v1 |
| Definition/version | PUBLIC_FOREX_MACRO_ELLIOTT_V1 |
| Profile SHA-256 | 3c050338a1e467a4502ed77c601a563e3e90a7e381e162dbcdfc16af522fe535 |
| Warm-up bars | 20 |
| Supporting frames | W1, D1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_MACRO_ELLIOTT_V1 |
| Policy hash | 07a5a4147fa4c80d21a0b04a717839c355e489f452c4cc13912f35310b5f809b |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Causal W1 13-bar extreme context and valid competing wave hypothesis, matching D1 structure, linked own-frame displacement zone retest within W1 extreme range. Optional COT is not a mandatory hidden gate; waves alone emit no setup.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[macro_elliott]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[macro_elliott]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.elliottwave.com/waveopedia/impulse/`
- `https://cmcmarketsfunded.com/learn/ict-trading/`

## 64. Harmonic PRZ · independent later response — `harmonic_prz`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.harmonic_prz.v1 |
| Definition/version | PUBLIC_FOREX_HARMONIC_PRZ_V1 |
| Profile SHA-256 | 95c3c9eecc9457099fa88390049cfea9ec3c894ce27090869f333828d7335a29 |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | SWING_MAP |
| Policy | PUBLIC_LIMIT_RESEARCH_HARMONIC_PRZ_V1 |
| Policy hash | a621af06c28397c9f3a154c41637404640eb1396dd1f053234d8214c97344ff8 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Confirmed AB=CD/Gartley/Bat/Butterfly ratios -> intersection of +/-5% 1:1 AB=CD (Gartley/AB=CD), or 1.27/1.618 AB=CD extension (Bat/Butterfly), and applicable XA/BC projection bands -> later zone visit with directional response and later local structure break. X/D invalidation, no hindsight D fill.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[harmonic_prz]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[harmonic_prz]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://harmonictrader.com/harmonic-patterns/`

## 65. Previous-body recovery · completed bar — `previous_body`

| Attribute | Value |
|---|---|
| Family | Candlesticks |
| Recipe | public.forex.previous_body.v1 |
| Definition/version | PUBLIC_FOREX_PREVIOUS_BODY_V1 |
| Profile SHA-256 | 880488caba7a00d703f0d73ed869bc80a1c3345a6c9aafc948eafc70e95fce2b |
| Warm-up bars | 2 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_PREVIOUS_BODY_V1 |
| Policy hash | 24180cfed9c6791bd6a41abe23e04589e25d472c43da0008e5ea0ce3a454fddb |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Previous completed bearish/bullish body high/low traversed by a later completed close in the opposite direction. Does not require engulfing opening position and is not live intrabar evidence.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[previous_body]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[previous_body]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/ctrader-algo/references/MarketData/Bars/Bar/`

## 66. Previous-body recovery · provisional quote — `previous_body_live`

| Attribute | Value |
|---|---|
| Family | Candlesticks |
| Recipe | public.forex.previous_body_live.v1 |
| Definition/version | PUBLIC_FOREX_PREVIOUS_BODY_LIVE_V1 |
| Profile SHA-256 | 8671f72130708c2809fa3c6a8fe8b6712c29b18731dd4c09804e6759cf34217c |
| Warm-up bars | 2 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | LIVE_QUOTE |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_PREVIOUS_BODY_LIVE_V1 |
| Policy hash | 8631eb77a1efeb72d6092aca0d65a327142dcae41ef65f9d5888fba15bde7283 |
| Trigger | LIVE_BODY |

**Analytical rules:** Fresh same-source coherent Bid/Ask midpoint beyond preceding completed bearish body high or bullish body low. Previous close <= quote event time; future, stale and crossed sides rejected. Provisional price observation, not a reconstructed forming OHLC bar.

**Parameters:** `[]`

**Research entry:** Fresh coherent same-source midpoint recovery of a previous body; provisional quote trigger, not completed OHLC confirmation. Body-boundary Limit retest with original side-clock expiry.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[previous_body_live]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[previous_body_live]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/ctrader-algo/references/MarketData/Bars/Bar/`

## 67. Previous-body recovery · HTF level / retest — `previous_body_retest`

| Attribute | Value |
|---|---|
| Family | Composed |
| Recipe | public.forex.previous_body_retest.v1 |
| Definition/version | PUBLIC_FOREX_PREVIOUS_BODY_RETEST_V1 |
| Profile SHA-256 | bb5dd262a9f6c8f8cad1edde7a25f56c9d5aa71b6f3fb0f2067a5ab5f7e6d737 |
| Warm-up bars | 4 |
| Supporting frames | D1, W1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_PREVIOUS_BODY_RETEST_V1 |
| Policy hash | 62bf524417d5cbc72479d038c1775532c6721f52b9da5f88db5d6ec8a962bbc5 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Own-frame completed previous-body recovery overlapping an available completed D1/W1 high/low; later held body-boundary retest with directional response, within 8 bars. H1 is the R06 documented completed-bar alternative; no invented live traversal.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[previous_body_retest]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[previous_body_retest]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/ctrader-algo/references/MarketData/Bars/Bar/`

## 68. Observed 13 / 52 / 104-week extremes — `rolling_extremes`

| Attribute | Value |
|---|---|
| Family | Levels |
| Recipe | public.forex.rolling_extremes.v1 |
| Definition/version | PUBLIC_FOREX_ROLLING_EXTREMES_V1 |
| Profile SHA-256 | cd1af32aaaadb8459dfdd3f219c123a388380d2bda665952b5b2f27b521c5bb4 |
| Warm-up bars | 1 |
| Supporting frames | W1 |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_ROLLING_EXTREMES_V1 |
| Policy hash | 5eaf70e9889132f42c1248e03f0c972ebc42909581f6dfd8a04850bb96c87fdb |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Separate 13/52/104-completed-W1 maximum/minimum levels. Missing lookback stays warm-up; finite history is never labelled all-time high/low.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[rolling_extremes]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[rolling_extremes]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/volatility/donchian-channel/`

## 69. Round-number liquidity context — `round_numbers`

| Attribute | Value |
|---|---|
| Family | Levels |
| Recipe | public.forex.round_numbers.v1 |
| Definition/version | PUBLIC_FOREX_ROUND_NUMBERS_V1 |
| Profile SHA-256 | c2785d8d8f2db533f851d903d7b1bcefc7d95c8f38144dc143c1b3eeabd39024 |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_ROUND_NUMBERS_V1 |
| Policy hash | f4a6eaff7d3bf2269111f60da8097779c1cf802a6afd19e9fcb02967b89ad0b9 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Nearest five 100-native-pip increments to latest close, snapped to native TickSize. No symbol-dependent guessed pip, actual depth or stop-count claim.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[round_numbers]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[round_numbers]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://fxopen.com/blog/en/trading-with-support-and-resistance-zones/`

## 70. Balance of Power · price-only pressure — `candle_pressure`

| Attribute | Value |
|---|---|
| Family | Momentum |
| Recipe | public.forex.candle_pressure.v1 |
| Definition/version | PUBLIC_FOREX_CANDLE_PRESSURE_V1 |
| Profile SHA-256 | 38fc7f63df7f707d05d31e5d1ce9a3dca3a89d3c520dd3e927ee6286ccef93f3 |
| Warm-up bars | 15 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_CANDLE_PRESSURE_V1 |
| Policy hash | aecba756999b0b0d787acbfe6c5b3560bb3b7110d51a802c98aa4c3178da960b |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** (close-open)/(high-low), zero for zero range, 14-bar average; zero-cross observation. Explicit OHLC proxy, not actual volume, delta or institutional identity.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[candle_pressure]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[candle_pressure]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.tradingview.com/support/solutions/43000589100-balance-of-power-bop`

## 71. Trend / range / volatility context — `regime_context`

| Attribute | Value |
|---|---|
| Family | Trend |
| Recipe | public.forex.regime_context.v1 |
| Definition/version | PUBLIC_FOREX_REGIME_CONTEXT_V1 |
| Profile SHA-256 | e6271febe5f04803160d5dfa7c22b24f67213226ab5a9cd98967347ea4da794e |
| Warm-up bars | 60 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_REGIME_CONTEXT_V1 |
| Policy hash | 0f39446569cf44b2c1a052a381962c6db4ee82255ce923d5e1f1b3d9618df4d5 |
| Trigger | REGIME_RECOVERY |

**Analytical rules:** Wilder ADX14 >=25 trend, <=20 range, otherwise transition; current ATR14 / previous 40 valid ATR mean gives expansion >=1.5 or contraction <=.67. Context only, no strategy auto-switch or risk changes.

**Parameters:** `[]`

**Research entry:** Observed TREND regime (ADX>=25) plus completed previous-body recovery; regime alone never chooses direction. Range/transition waits.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[regime_context]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[regime_context]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/trend/directional-movement-system/`

## 72. Trend persistence · directional efficiency — `trend_persistence`

| Attribute | Value |
|---|---|
| Family | Trend |
| Recipe | public.forex.trend_persistence.v1 |
| Definition/version | PUBLIC_FOREX_TREND_PERSISTENCE_V1 |
| Profile SHA-256 | be0409b83e1845c4d312a5061a4f2648297b094c9c8e063931fd630840a76d46 |
| Warm-up bars | 22 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_TREND_PERSISTENCE_V1 |
| Policy hash | 3264d26645bf2662f396a4cba3cf09e47bd800aa5cf3ef19b13c8bcaaea70a7d |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** 20-bar net-change / sum absolute close changes, plus proportion positive/negative returns. Signed efficiency crossing +/-0.5 identifies persistent price direction; not the local portfolio-weighted M39 policy.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[trend_persistence]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[trend_persistence]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/oscillators/momentum-oscillator/`

## 73. ATR anchor trail · display only — `atr_trail`

| Attribute | Value |
|---|---|
| Family | Trend |
| Recipe | public.forex.atr_trail.v1 |
| Definition/version | PUBLIC_FOREX_ATR_TRAIL_V1 |
| Profile SHA-256 | bacb242170d2b353d6c688941278338cd1764f5805f83c70691153a1f39c1e70 |
| Warm-up bars | 23 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | declared closed-price/source dependencies |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_ATR_TRAIL_V1 |
| Policy hash | 6f83e64bd9a3cf5e031ecc0aaa99bdcb56f850c9a324ea7f6821c2e53b1deff2 |
| Trigger | TRAIL_CROSS |

**Analytical rules:** Chandelier-style 22-bar high minus 3*ATR14 / low plus 3*ATR14. Separate long/short research lines; no stop mutation, position adoption or account sizing.

**Parameters:** `[]`

**Research entry:** Completed close crosses the prior available Chandelier research line. Trigger-body retracement Limit; no existing position or broker stop is modified.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[atr_trail]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[atr_trail]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://help.ctrader.com/indicators/built-in/volatility/average-true-range/`

## 74. Volume-backed displacement — `volume_displacement`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.volume_displacement.v1 |
| Definition/version | PUBLIC_FOREX_VOLUME_DISPLACEMENT_V1 |
| Profile SHA-256 | c638f6f1dd13bf21dd55f0818b51648dbf363d507cf414b0497a529507cee292 |
| Warm-up bars | 16 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | TRADED_PRINTS |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_VOLUME_DISPLACEMENT_V1 |
| Policy hash | 04b5cf41a717a02aac6be6beddb67a0c48e156d31fb3d794c6b205a95b58e9b3 |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Price displacement plus own-bar genuine venue traded quantity >=1.5 prior 14-bar mean traded quantity. Tick count, missing weights, mapped foreign-contract prices and unknown provenance are not genuine pair volume.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[volume_displacement]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[volume_displacement]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.wyckoffanalytics.com/wyckoff-method/`

## 75. Wyckoff effort / result · absorption — `effort_result`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.effort_result.v1 |
| Definition/version | PUBLIC_FOREX_EFFORT_RESULT_V1 |
| Profile SHA-256 | 81cdcc4ef7c6c8d76b0b5df9ac924b37443b7875959ba5a66668f33af73b01a9 |
| Warm-up bars | 21 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | TRADED_PRINTS |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_EFFORT_RESULT_V1 |
| Policy hash | d629753d552dd6b43a1308582b6d9502e009fee61da2d81dea8915a7ac94c8bb |
| Trigger | LATEST_DIRECTIONAL_EVENT |

**Analytical rules:** Genuine traded quantity >=1.5 prior 20-bar mean with own body <=50% prior 20-bar mean body; bullish/bearish price reaction near prior range edge. Price/volume divergence hypothesis, not known trader identity.

**Parameters:** `[]`

**Research entry:** Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. No retrospective fill, automatic sizing, confidence probability or automatic Issue.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[effort_result]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[effort_result]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.wyckoffanalytics.com/wyckoff-method/`

## 76. Wyckoff P&F · automatic / explicit count — `cause_effect`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.cause_effect.v1 |
| Definition/version | PUBLIC_FOREX_CAUSE_EFFECT_V1 |
| Profile SHA-256 | fa2c948d52d39af58990d303f34cce225c810ef7d232fd02fa9a2e2a7b24c3ff |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | POINT_FIGURE_TICKS |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_CAUSE_EFFECT_V1 |
| Policy hash | 5e48e47669b6d219f62f2735b658fc3901a9770f2f6b153214a5abe9bde591bc |
| Trigger | PNF_RESPONSE |

**Analytical rules:** Default automatic research profile PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1: original own-frame closes; first 20 true ranges seed a native-tick-ceiling ATR20 box frozen at bar 21. Three-box reversals; equal preceding X highs / O lows plus third-column break define a five-column triple top/bottom. Objective = pattern low + (5*box*3), or pattern high minus extension. Retire objectives already observed or later reached/invalidated; no inferred intrabar path. Finite-window reconstruction, not calibrated prediction. Explicit POINT_FIGURE_TICKS publications override automatic mode and retain their declared count settings.

**Parameters:** `[["automatic_profile", "PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1"]]`

**Research entry:** An unreached original P&F objective plus aligned completed-body recovery; objective must remain beyond entry and untraded. Count is not an entry by itself.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[cause_effect]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[cause_effect]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.wyckoffanalytics.com/wyckoff-method/`
- `https://chartschool.stockcharts.com/table-of-contents/chart-analysis/point-and-figure-charts/point-and-figure-basics/introduction-to-point-and-figure-charts`
- `https://chartschool.stockcharts.com/table-of-contents/chart-analysis/point-and-figure-charts/p-and-f-price-objectives/p-and-f-price-objectives-horizontal-counts`

## 77. Market Profile / TPO · POC / value / IB — `profile_tpo`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.profile_tpo.v1 |
| Definition/version | PUBLIC_FOREX_PROFILE_TPO_V1 |
| Profile SHA-256 | 7ff9d40f5a519ce0d2f6ed5af9525d37d8fb7d52280d0e6452735fb0ae382639 |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | INTRABAR_PRICES |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_PROFILE_TPO_V1 |
| Policy hash | 595236f8312d823155b3fdbc2550495472235fea78da9f5a38436358da0252d0 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Observed intrabar price samples grouped by explicit session and 30-minute UTC slots; one TPO per visited tick bin per slot. 70% contiguous value expansion from max-TPO POC; first two complete slots form IB. No filling unobserved OHLC price bins.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[profile_tpo]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[profile_tpo]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.sierrachart.com/index.php?page=doc/StudiesReference/TimePriceOpportunityCharts.html`

## 78. Volume Profile · POC / value area — `volume_profile`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.volume_profile.v1 |
| Definition/version | PUBLIC_FOREX_VOLUME_PROFILE_V1 |
| Profile SHA-256 | 5baebbef7ddeccdb70df4e1f1cb7e36e990c77a78533e155365e1d4a6d182ca8 |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | TRADED_PRINTS |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_VOLUME_PROFILE_V1 |
| Policy hash | 952591b027f5537bc15f27173a499b6901c3ffdc8c2ce5c41a8020a0112e1971 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Actual eligible executed-print quantity per native tick bin, explicit session anchor. 70% contiguous value expansion from highest-volume bin; deterministic nearest-midpoint/lower-price ties. No tick-volume conversion.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[volume_profile]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[volume_profile]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=141&Name=Volume_by_Price`

## 79. Anchored VWAP · genuine weighted bands — `vwap_bands`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.vwap_bands.v1 |
| Definition/version | PUBLIC_FOREX_VWAP_BANDS_V1 |
| Profile SHA-256 | d88d5d04643a3dc35ba23895ee170f2ae6b058eeaef5a7f88b73a63f81b4e4d6 |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | TRADED_PRINTS |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_VWAP_BANDS_V1 |
| Policy hash | 1713eb6bd1334295fc9cbe630a149a4a7e0e4e68b7ff5a077ce1400fef3c2e68 |
| Trigger | PRIOR_LEVEL_RESPONSE |

**Analytical rules:** Explicit session-anchored sum(price*traded quantity)/sum(quantity); weighted population price deviation gives +/-1 and +/-2 sigma. Stable weighted moments, real executed prices/weights only.

**Parameters:** `[]`

**Research entry:** Freeze this method on observations available BEFORE the trigger bar opens. A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; require the declared directional zone side when present. Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[vwap_bands]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[vwap_bands]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=108`

## 80. Broker / venue DOM · displayed-size imbalance — `dom_imbalance`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.dom_imbalance.v1 |
| Definition/version | PUBLIC_FOREX_DOM_IMBALANCE_V2 |
| Profile SHA-256 | 68be07b430ed8e3aa25041d74c2d2c3d04d5f2e5973d4c7cbef90f052c3838ff |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | VENUE_BOOK |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_DOM_IMBALANCE_V1 |
| Policy hash | 7b7991bdc1d2b2ad7466442f99e6ba50fb56040e5a8335fcff11581670d9ebec |
| Trigger | FLOW_RECOVERY |

**Analytical rules:** Fresh genuine broker- or venue-scoped displayed depth, top five observed bid/ask levels; imbalance=(bid size-ask size)/(sum). >=.2 BUY / <=-.2 SELL context at observed midpoint. Broker input uses its original <=15s local receipt, never a native event clock/sequence or full-book claim. Native-chain and checksum venue scopes remain distinct. Not global FX book or executed volume.

**Parameters:** `[]`

**Research entry:** Original displayed-depth directional imbalance plus aligned completed-body recovery; quote must be fresh. Displayed sizes are never executed volume.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[dom_imbalance]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[dom_imbalance]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.sierrachart.com/index.php?page=doc/StudiesReference.php&ID=375`
- `https://help.ctrader.com/trading-with-ctrader/depth-of-market/`

## 81. Footprint / delta · executed aggressors — `footprint_delta`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.footprint_delta.v1 |
| Definition/version | PUBLIC_FOREX_FOOTPRINT_DELTA_V1 |
| Profile SHA-256 | 0cb4bef15ab7986403d590a20ae769bcd9dd8db137e826c05f40d5355a81a63e |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | AGGRESSOR_PRINTS |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_FOOTPRINT_DELTA_V1 |
| Policy hash | 55eeaf2aeb834565a402119d59d0d195e62c86dc69043418234e77315895b935 |
| Trigger | FLOW_RECOVERY |

**Analytical rules:** Executed quantity aggregated per actual tick price and documented BUY/SELL aggressor; delta=buy-sell, cumulative sum in explicit session. Unknown aggressors unavailable; quote/tick direction is not substituted.

**Parameters:** `[]`

**Research entry:** Original documented executed-aggressor directional delta plus aligned completed-body recovery; no quote-direction substitution.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[footprint_delta]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[footprint_delta]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.sierrachart.com/index.php?page=doc/NumbersBars.php`

## 82. COT · published futures positioning context — `cot_macro`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.cot_macro.v1 |
| Definition/version | PUBLIC_FOREX_COT_MACRO_V1 |
| Profile SHA-256 | c49346e4089856693d9570bca6a55a2dd5062d748ccd7fb06c5e057bb502714a |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | CFTC_REPORT |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_COT_MACRO_V1 |
| Policy hash | 6005facadb909db68f205809c2a4de1ffbc6240b6ff8464130557c2f57070104 |
| Trigger | COT_RECOVERY |

**Analytical rules:** Published CFTC currency-futures mapping with report date separate from actual release time; (noncommercial long-short)/open interest, USD-base sign reversed. Label futures proxy and observed FX reference only; no position-derived entry.

**Parameters:** `[]`

**Research entry:** Previously available published COT futures bias plus aligned completed-body recovery. Futures positioning is context, not a spot entry or a new publication-time claim.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[cot_macro]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[cot_macro]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm`

## 83. Official calendar · release-risk context — `calendar_context`

| Attribute | Value |
|---|---|
| Family | Genuine data |
| Recipe | public.forex.calendar_context.v1 |
| Definition/version | PUBLIC_FOREX_CALENDAR_CONTEXT_V1 |
| Profile SHA-256 | 9314d8561c080f6a4e209e915d028c601914161f158d8fd6199b0bef4c27f1bc |
| Warm-up bars | 1 |
| Supporting frames | selected/supporting source as defined |
| Required data kind | OFFICIAL_CALENDAR |
| Required nodes | method-owned |
| Policy | PUBLIC_LIMIT_RESEARCH_CALENDAR_CONTEXT_V1 |
| Policy hash | 0bc61a1fb7b48db49f159d66414333dbea2bf1f7f2691f86e69bceeb50cbfb25 |
| Trigger | CALENDAR_RECOVERY |

**Analytical rules:** Explicit official release observation/publication times, affected pair currency and [release-30m, release+30m) window. Known scheduled release markers only; empty/incomplete feed cannot imply no event risk.

**Parameters:** `[]`

**Research entry:** Explicit provider schedule coverage and no affected event within the declared +/-30-minute blackout, plus completed-body recovery. An empty/unknown calendar is never clearance; releases never assign direction.

**Exact retained positive cases:**

- `test_each_real_algorithm_positive_trigger_is_materialized_in_tab4[calendar_context]`
- `test_each_method_reaches_explicit_local_binding_and_issue_preview_without_submission[calendar_context]`

**Origin:** SYNTHETIC_FIXTURE_EXPLICIT_NOT_MARKET_EVIDENCE; native broker submissions in these cases: 0.

**Declared source references (not revalidated):**

- `https://www.federalreserve.gov/newsevents/calendar.htm`
