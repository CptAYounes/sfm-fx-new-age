# R04 — View, Dataset, Route and Subscription Catalogue

All 42 backend identities are listed. The ten `2.*` identities are internal contracts, not ten visible tool pages. Routes are declared host contracts, not claims of full domain implementation.

| ID | Title | Owner | Presentation | Datasets |
|---|---|---|---|---|
| 1.1 | Forex Pair Watchlist | FOREX_SYMBOL_REGISTRY | FIXED_USER_VIEW | watchlist, chart |
| 1.2 | W1 Macro Context | CONTEXT_SNAPSHOT_SERVICE | FIXED_USER_VIEW | bars, analytics, chart |
| 1.3 | D1 Primary Chart | CONTEXT_SNAPSHOT_SERVICE | FIXED_USER_VIEW | bars, levels, overlays, annotations, chart |
| 1.4 | H4 Entry Chart | CONTEXT_SNAPSHOT_SERVICE | FIXED_USER_VIEW | bars, levels, overlays, chart |
| 1.5 | H1 Optional Inspect | CONTEXT_SNAPSHOT_SERVICE | FIXED_USER_VIEW | bars, chart |
| 1.6 | Market Structure and Liquidity | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | levels, evidence, chart |
| 1.7 | ATR Bands and Fibonacci | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | geometry, analytics, chart |
| 1.8 | Signal Overlays | CHART_OVERLAY_PROTOCOL | FIXED_USER_VIEW | overlays, market_candidates, chart |
| 1.9 | Chart Replay | RESEARCH_REPLAY | FIXED_USER_VIEW | replay, chart |
| 1.10 | Order and Position Visuals | READONLY_POSITION_MONITOR | FIXED_USER_VIEW | orders, positions, chart |
| 2.1 | Central PCB Switchboard | LOCAL_EVENT_ROUTER | INTERNAL_ENGINEERING_CONTRACT | consumers, components |
| 2.2 | 44 Scanner Components | TELEMETRY_BOARD | INTERNAL_ENGINEERING_CONTRACT | scanner_nodes |
| 2.3 | Sources and Connectivity | CT_OPEN_API_CONNECTOR | INTERNAL_ENGINEERING_CONTRACT | connector, accounts |
| 2.4 | Data Freshness and LKV | BAR_AND_QUOTE_CACHE | INTERNAL_ENGINEERING_CONTRACT | coverage, backfill |
| 2.5 | Pair Contracts and Sessions | FOREX_SYMBOL_REGISTRY | INTERNAL_ENGINEERING_CONTRACT | specifications, calendars |
| 2.6 | Pipeline Routing and Queues | LOCAL_EVENT_ROUTER | INTERNAL_ENGINEERING_CONTRACT | routes, router_metrics |
| 2.7 | Variable Catalogue | GLOBAL_VARIABLE_REGISTRY | INTERNAL_ENGINEERING_CONTRACT | variables, variable_definitions |
| 2.8 | Parameter/Mutable Surface Registry | GLOBAL_PARAMETER_REGISTRY | INTERNAL_ENGINEERING_CONTRACT | parameters, parameter_definitions, mutable_surfaces |
| 2.9 | Local Services and Health | TELEMETRY_BOARD | INTERNAL_ENGINEERING_CONTRACT | components |
| 2.10 | Storage and Diagnostics | LOCAL_CONFIG_STORE | INTERNAL_ENGINEERING_CONTRACT | diagnostics, audit, configuration |
| 3.1 | Strategy and Recipe Library | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | recipes, strategy_catalogue |
| 3.2 | D1 Campaign and Phase | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | bars, analytics |
| 3.3 | W1 Macro and ATR | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | bars, analytics |
| 3.4 | H4 Entry Qualification | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | analytics, levels |
| 3.5 | Structure Producers | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | analytics, levels, evidence |
| 3.6 | Wyckoff and Liquidity | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | analytics, levels, evidence |
| 3.7 | Elliott and Harmonics | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | analytics, levels |
| 3.8 | ATR Geometry and Risk per Pip | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | geometry, market_candidates |
| 3.9 | Zone Confidence and OSQL | STRATEGY_RECIPE_HOST | FIXED_USER_VIEW | market_candidates, evidence, analytics |
| 3.10 | LogicTiles Builder | LOGICTILES_TABBRIDGE | FIXED_USER_VIEW | rules, variables, variable_definitions, rule_history, mutable_surfaces |
| 3.11 | Strategy Parameter Tuning | GLOBAL_PARAMETER_REGISTRY | FIXED_USER_VIEW | parameters, parameter_definitions, parameter_history, mutable_surfaces, pair_parameters, pair_parameter_history |
| 3.12 | Backtesting and Walk Forward | RESEARCH_REPLAY | FIXED_USER_VIEW | replay, replay_datasets, replay_runs, research_studies |
| 3.13 | Candidate Signal History | SIGNAL_VIEW_STORE | FIXED_USER_VIEW | market_candidates, signal_history, signals |
| 4.1 | Signal Queue | SIGNAL_QUEUE | FIXED_USER_VIEW | signals, strategy_signals |
| 4.2 | ISSUE Detail and Risk Preview | BROKER_INTENT_GATE | FIXED_USER_VIEW | issue_preview, signals, market_candidates, strategy_signals, levels, evidence, specifications, capital_context |
| 4.3 | Broker Pending Orders | BROKER_RECONCILER | FIXED_USER_VIEW | orders, broker_pending |
| 4.4 | Order Correlation | ORDER_CORRELATION_STORE | FIXED_USER_VIEW | order_history, signal_history |
| 4.5 | Account Link and State | ACCOUNT_LINK | FIXED_USER_VIEW | accounts, connector |
| 4.6 | Position Monitor | READONLY_POSITION_MONITOR | FIXED_USER_VIEW | positions |
| 4.7 | Capital Context 45% | PORTFOLIO_PRE_ISSUE_VIEW | FIXED_USER_VIEW | capital_context |
| 4.8 | Historical Broker Activity | BROKER_RECONCILER | FIXED_USER_VIEW | order_history, audit, broker_history, broker_history_jobs |
| 4.9 | Optional Local Exit Addon | OPTIONAL_LOCAL_POSITION_SERVICE | FIXED_USER_VIEW | optional_exit_capability |

## Exact declared host routes

| From | To | Topic | Priority | Trigger | Declared rule/status |
|---|---|---|---|---|---|
| CT_OPEN_API_CONNECTOR | SOURCE_AUTHORITY_ROUTER | MARKET.RAW_QUOTE | 0 | quote_tick | One subscription per symbol/data kind / ACTIVE_FOUNDATION_CONTRACT |
| CT_OPEN_API_CONNECTOR | BAR_AND_QUOTE_CACHE | BAR.NATIVE_FINAL | 1 | broker_bar_close | Native W1 D1 H4 bar if supported and reconciled / ACTIVE_FOUNDATION_CONTRACT |
| CT_OPEN_API_CONNECTOR | BROKER_RECONCILER | BROKER.EXECUTION_EVENT | 0 | on_broker_event | Never coalesce executions / ACTIVE_FOUNDATION_CONTRACT |
| CT_OPEN_API_CONNECTOR | FOREX_SYMBOL_REGISTRY | SYMBOL.SPEC | 1 | on_connect_and_change | Broker symbol ID and precision authoritative / ACTIVE_FOUNDATION_CONTRACT |
| ACCOUNT_LINK | CT_OPEN_API_CONNECTOR | ACCOUNT.AUTH_CONTEXT | 0 | user_login | OAuth token through protected local store / ACTIVE_FOUNDATION_CONTRACT |
| SOURCE_AUTHORITY_ROUTER | BAR_AND_QUOTE_CACHE | MARKET.NORMALIZED_QUOTE | 1 | per_quote | One source epoch per symbol / ACTIVE_FOUNDATION_CONTRACT |
| BAR_AND_QUOTE_CACHE | CONTEXT_SNAPSHOT_SERVICE | BAR.FINAL | 1 | on_completed_bar | Timeframe-aware as-of snapshots / ACTIVE_FOUNDATION_CONTRACT |
| BAR_AND_QUOTE_CACHE | CONTEXT_SNAPSHOT_SERVICE | QUOTE.LKV | 2 | on_quote_or_query | Value and freshness separate / ACTIVE_FOUNDATION_CONTRACT |
| CONTEXT_SNAPSHOT_SERVICE | GLOBAL_VARIABLE_REGISTRY | VARIABLE.VALUE | 1 | on_material_change | Typed semantic value / ACTIVE_FOUNDATION_CONTRACT |
| GLOBAL_VARIABLE_REGISTRY | LOGICTILES_EVALUATOR | VARIABLE.CHANGED | 2 | on_dirty_dependency | No independent variable polling / ACTIVE_FOUNDATION_CONTRACT |
| GLOBAL_PARAMETER_REGISTRY | LOGICTILES_EVALUATOR | PARAM.EFFECTIVE | 2 | on_config_activation | Apply a complete versioned profile / ACTIVE_FOUNDATION_CONTRACT |
| MUTABLE_SURFACE_INDEX | GLOBAL_PARAMETER_REGISTRY | PARAM.AUTHORIZED_TARGET | 2 | on_parameter_write | Backend owner validation / ACTIVE_FOUNDATION_CONTRACT |
| LOGICTILES_EVALUATOR | STRATEGY_RECIPE_HOST | OBS.LOGICTILES | 2 | rule_true_or_transition | Analysis only; no order access / ACTIVE_FOUNDATION_CONTRACT |
| CONTEXT_SNAPSHOT_SERVICE | STRATEGY_RECIPE_HOST | CONTEXT.W1_D1_H4 | 2 | bar_close_or_material_change | W1 context, D1 authority, H4 setup / ACTIVE_FOUNDATION_CONTRACT |
| STRATEGY_RECIPE_HOST | SIGNAL_VIEW_STORE | CANDIDATE.PROPOSED | 2 | qualified_candidate | Subject to scanner gates and origin label / ACTIVE_FOUNDATION_CONTRACT |
| SIGNAL_VIEW_STORE | SIGNAL_QUEUE | SIGNAL.STATE_CHANGE | 2 | on_signal_revision | No replay signal promotion into operational queue / ACTIVE_FOUNDATION_CONTRACT |
| SIGNAL_VIEW_STORE | CHART_OVERLAY_PROTOCOL | OVERLAY.SIGNAL_LEVEL | 3 | on_material_change | Chart display only / ACTIVE_FOUNDATION_CONTRACT |
| CHART_OVERLAY_PROTOCOL | GUI_STATE_CONTROLLER | OVERLAY.UPDATE | 3 | on_display_subscription | No own indicator computation / ACTIVE_FOUNDATION_CONTRACT |
| SIGNAL_QUEUE | GUI_STATE_CONTROLLER | SIGNAL.QUEUE_SNAPSHOT | 2 | on_change | ISSUE and local cancellation controls / ACTIVE_FOUNDATION_CONTRACT |
| GUI_STATE_CONTROLLER | SIGNAL_QUEUE | SIGNAL.USER_CANCEL | 2 | explicit_user_action | Cancel local unissued proposals only / ACTIVE_FOUNDATION_CONTRACT |
| GUI_STATE_CONTROLLER | BROKER_INTENT_GATE | SIGNAL.USER_ISSUE | 0 | explicit_user_issue | User is the only trigger of pending creation / ACTIVE_FOUNDATION_CONTRACT |
| SIGNAL_QUEUE | BROKER_INTENT_GATE | SIGNAL.CURRENT_REVISION | 0 | issue_validation | Immutable selected revision / ACTIVE_FOUNDATION_CONTRACT |
| FOREX_SYMBOL_REGISTRY | BROKER_INTENT_GATE | SYMBOL.TRADE_CONSTRAINTS | 0 | issue_validation | Pip, volume, tick grid, session and limits / ACTIVE_FOUNDATION_CONTRACT |
| BROKER_RECONCILER | BROKER_INTENT_GATE | BROKER.CURRENT_ACCOUNT_STATE | 0 | issue_validation | Fresh account and order reconciliation / ACTIVE_FOUNDATION_CONTRACT |
| PORTFOLIO_PRE_ISSUE_VIEW | BROKER_INTENT_GATE | PORTFOLIO.BROKER_OBLIGATIONS | 0 | issue_validation | No invented exposure valuation / ACTIVE_FOUNDATION_CONTRACT |
| BROKER_INTENT_GATE | PENDING_ORDER_GATEWAY | ORDER.PENDING_INTENT | 0 | after_issue_checks | Single submission owner / ACTIVE_FOUNDATION_CONTRACT |
| PENDING_ORDER_GATEWAY | ORDER_CORRELATION_STORE | ORDER.REQUEST_STATE | 0 | before_and_after_send | Persist single-flight and unknown state / ACTIVE_FOUNDATION_CONTRACT |
| PENDING_ORDER_GATEWAY | CT_OPEN_API_CONNECTOR | ORDER.BROKER_SUBMIT | 0 | once_after_idempotency_check | Pending Limit request with signal ID / ACTIVE_FOUNDATION_CONTRACT |
| CT_OPEN_API_CONNECTOR | BROKER_RECONCILER | BROKER.RECONCILE_RESPONSE | 0 | on_restart_reconnect_unknown | Pending orders, positions and deals / ACTIVE_FOUNDATION_CONTRACT |
| BROKER_RECONCILER | ORDER_CORRELATION_STORE | ORDER.MAP_UPDATE | 0 | confirmed_broker_facts | Account-scoped order ID and partial fills / ACTIVE_FOUNDATION_CONTRACT |
| BROKER_RECONCILER | READONLY_POSITION_MONITOR | POSITION.UPDATED | 0 | on_fill_or_reconnect | No automatic close / ACTIVE_FOUNDATION_CONTRACT |
| BROKER_RECONCILER | PORTFOLIO_PRE_ISSUE_VIEW | BROKER.ACCOUNT_UPDATE | 0 | on_broker_change | Shared capital context / ACTIVE_FOUNDATION_CONTRACT |
| LOCAL_EVENT_ROUTER | TELEMETRY_BOARD | PIPELINE.HEALTH | 2 | on_material_health_change | Tab 2 health projection / ACTIVE_FOUNDATION_CONTRACT |
| CT_OPEN_API_CONNECTOR | TELEMETRY_BOARD | BROKER.CONNECTION_HEALTH | 0 | on_connection_state | Health independent of charts / ACTIVE_FOUNDATION_CONTRACT |
| CONTEXT_SNAPSHOT_SERVICE | RESEARCH_REPLAY | REPLAY.DATASET | 3 | user_starts_replay | Frozen dataset and replay clock / ACTIVE_FOUNDATION_CONTRACT |
| RESEARCH_REPLAY | STRATEGY_RECIPE_HOST | REPLAY.ISOLATED_CONTEXT | 3 | offline_only | No downstream operational queue / ACTIVE_FOUNDATION_CONTRACT |
| GLOBAL_VARIABLE_REGISTRY | LOGICTILES_TABBRIDGE | VARIABLE.CATALOGUE | 3 | on_editor_open | Discoverable variables / ACTIVE_FOUNDATION_CONTRACT |
| GLOBAL_PARAMETER_REGISTRY | LOGICTILES_TABBRIDGE | PARAM.CATALOGUE | 3 | on_editor_open | Tunable values by scope / ACTIVE_FOUNDATION_CONTRACT |
| LOGICTILES_TABBRIDGE | GUI_STATE_CONTROLLER | RULE.EDITOR_MODEL | 3 | ui_event | One editor shared across tabs / ACTIVE_FOUNDATION_CONTRACT |
| LOCAL_CONFIG_STORE | GLOBAL_PARAMETER_REGISTRY | CONFIG.RESTORED | 2 | startup | Restore versions, not inferred live state / ACTIVE_FOUNDATION_CONTRACT |
| LOCAL_EVENT_ROUTER | HERMES_ARCHITECTURE_CONSUMER | ARCH.METRICS | 3 | read_only_query | No broker command channel / ACTIVE_FOUNDATION_CONTRACT |
