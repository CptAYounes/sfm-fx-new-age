# R08 — Parameter, Variable and Mutable Surface Registry

Extracted from an in-memory offline runtime with the normal installed analytical definitions. These registrations do not authenticate a source or grant account-risk permission.

## Parameter definitions

| activation_boundary | choices | data_type | default | key | maximum | minimum | owner | scope | unit |
|---|---|---|---|---|---|---|---|---|---|
| CORE_EVENT | [] | integer | 30 | feed.quote_max_age_seconds | 3600 | 1 | BAR_AND_QUOTE_CACHE | GLOBAL | seconds |
| CORE_EVENT | [] | number | 0.375 | geometry.band_0 | 20 | 0.0001 | STRATEGY_RECIPE_HOST | GLOBAL | ATR_MULTIPLE |
| CORE_EVENT | [] | number | 0.750 | geometry.band_1 | 20 | 0.0001 | STRATEGY_RECIPE_HOST | GLOBAL | ATR_MULTIPLE |
| CORE_EVENT | [] | number | 1.250 | geometry.band_2 | 20 | 0.0001 | STRATEGY_RECIPE_HOST | GLOBAL | ATR_MULTIPLE |
| CORE_EVENT | [] | number | 1.750 | geometry.band_3 | 20 | 0.0001 | STRATEGY_RECIPE_HOST | GLOBAL | ATR_MULTIPLE |
| CORE_EVENT | [] | number | 2.250 | geometry.band_4 | 20 | 0.0001 | STRATEGY_RECIPE_HOST | GLOBAL | ATR_MULTIPLE |
| CORE_EVENT | [] | number | 0.75 | ob_candidate.evidence_reliability | 1 | 0.01 | STRATEGY_RECIPE_HOST | GLOBAL | RESEARCH_PROFILE |
| CORE_EVENT | [] | integer | 14400 | ob_candidate.expiry_seconds | 604800 | 60 | STRATEGY_RECIPE_HOST | GLOBAL | RESEARCH_PROFILE |
| CORE_EVENT | [] | number | 3 | ob_candidate.max_spread_pips | 100 | 0.01 | STRATEGY_RECIPE_HOST | GLOBAL | RESEARCH_PROFILE |
| CORE_EVENT | [] | number | 1 | ob_candidate.min_reward_r | 100 | 0.01 | STRATEGY_RECIPE_HOST | GLOBAL | RESEARCH_PROFILE |
| CORE_EVENT | [] | number | 0.60 | order_block.body_fraction | 1 | 0.01 | STRATEGY_RECIPE_HOST | GLOBAL | RESEARCH_PROFILE |
| CORE_EVENT | [] | integer | 14 | order_block.lookback | 100 | 2 | STRATEGY_RECIPE_HOST | GLOBAL | RESEARCH_PROFILE |
| CORE_EVENT | [] | number | 1.00 | order_block.range_multiple | 10 | 0.01 | STRATEGY_RECIPE_HOST | GLOBAL | RESEARCH_PROFILE |
| CORE_EVENT | [] | integer | 20 | order_block.source_lookback | 100 | 1 | STRATEGY_RECIPE_HOST | GLOBAL | RESEARCH_PROFILE |
| CORE_EVENT | [] | integer | 2 | scanner.pivot_left | 20 | 1 | STRATEGY_RECIPE_HOST | GLOBAL | completed_bars |
| CORE_EVENT | [] | integer | 2 | scanner.pivot_right | 20 | 1 | STRATEGY_RECIPE_HOST | GLOBAL | completed_bars |
## Mutable surfaces

| classification | command | owner | parameter_keys | subtab_id | surface_id |
|---|---|---|---|---|---|
| RESEARCH_CONFIGURATION | PROPOSE_VERSIONED_PARAM_CHANGE | BAR_AND_QUOTE_CACHE | ['feed.quote_max_age_seconds'] | 2.4 | feed.freshness |
| RESEARCH_CONFIGURATION | PROPOSE_VERSIONED_PARAM_CHANGE | STRATEGY_RECIPE_HOST | ['geometry.band_0', 'geometry.band_1', 'geometry.band_2', 'geometry.band_3', 'geometry.band_4'] | 3.8 | geometry.research_bands |
| RESEARCH_CONFIGURATION | PROPOSE_VERSIONED_PARAM_CHANGE | STRATEGY_RECIPE_HOST | ['scanner.pivot_left', 'scanner.pivot_right'] | 3.5 | scanner.research_pivots |
## Variable definitions

No definitions in this extracted registration set.
