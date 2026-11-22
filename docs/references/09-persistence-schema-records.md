# R09 — Physical Schema and Record Kind Reference

The three SQL tables and six observed explicit indexes are represented by the extracted schema. This file is a reference, not a migration runner. Generic records do not have universal SQL-enforced immutability; owners enforce their historical semantics.

```sql
-- Source-derived in-memory SQLite user_version=2 schema. Reference only; do not apply blindly to live state.

CREATE INDEX analytical_scope_idx ON records(
            kind,json_extract(body,'$.lineage.source_scope'),json_extract(body,'$.lineage.source_epoch'),
            json_extract(body,'$.lineage.symbol'));

CREATE INDEX market_series_idx ON records(
            kind, json_extract(body,'$.scope_id'), json_extract(body,'$.symbol'),
            json_extract(body,'$.timeframe'), json_extract(body,'$.source_epoch'),
            json_extract(body,'$.open_time')) WHERE kind='bar';

CREATE INDEX public_projection_history_scope_idx ON records(
            json_extract(body,'$.scope_id'),json_extract(body,'$.source_epoch'),
            json_extract(body,'$.symbol'),json_extract(body,'$.timeframe'),
            json_extract(body,'$.strategy_id')) WHERE kind='strategy_projection';

CREATE INDEX supplemental_interval_idx ON records(
            json_extract(body,'$.scope_id'),json_extract(body,'$.source_epoch'),
            json_extract(body,'$.symbol'),json_extract(body,'$.kind'),
            json_extract(body,'$.provider_id'),json_extract(body,'$.window_start'),
            json_extract(body,'$.window_end'),json_extract(body,'$.revision'))
            WHERE kind='supplemental_evidence';

CREATE INDEX supplemental_provider_publication_idx ON records(
            json_extract(body,'$.provider_id'),json_extract(body,'$.symbol'),
            json_extract(body,'$.kind'),json_extract(body,'$.available_at') DESC)
            WHERE kind='supplemental_evidence';

CREATE TABLE events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL, topic TEXT NOT NULL, body TEXT NOT NULL
            );

CREATE TABLE orders (
                id TEXT PRIMARY KEY, account_id TEXT NOT NULL, signal_id TEXT NOT NULL,
                scope_id TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(scope_id, signal_id)
            );

CREATE TABLE records (
                kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                PRIMARY KEY(kind, id)
            );

CREATE TABLE sqlite_sequence(name,seq);
```

## Statically resolved literal record kinds

Dynamic kind arguments and analytical kinds owned through generic publication APIs are not exhaustively resolvable by this simple extraction. This is an explicitly partial static index, not a full runtime inventory.

| Kind | Source owners |
|---|---|
| account_metadata | src/sfm_fx_new_age/services/orders.py |
| account_money_snapshot | src/sfm_fx_new_age/connector/service.py; src/sfm_fx_new_age/services/research_money.py |
| analytics_snapshot | src/sfm_fx_new_age/services/scanner.py |
| atr_checkpoint | src/sfm_fx_new_age/services/market.py |
| authority | src/sfm_fx_new_age/services/catalogues.py; src/sfm_fx_new_age/services/market.py |
| backfill | src/sfm_fx_new_age/connector/service.py; src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/continuity.py |
| bar | src/sfm_fx_new_age/core/runtime.py; src/sfm_fx_new_age/services/market.py; src/sfm_fx_new_age/testing/checkpoint.py |
| broker_pending_snapshot | src/sfm_fx_new_age/connector/service.py; src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/research_money.py; src/sfm_fx_new_age/services/workflow.py |
| calendar | src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/continuity.py; src/sfm_fx_new_age/services/orders.py |
| chart_workspace | src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/workflow.py |
| consumer | src/sfm_fx_new_age/services/consumers.py |
| fxopen_native_reported_execution | src/sfm_fx_new_age/connector/fxopen_feed.py |
| kraken_week_derivation | src/sfm_fx_new_age/connector/kraken_weekly.py |
| mutable_surface | src/sfm_fx_new_age/services/catalogues.py |
| native_activity | src/sfm_fx_new_age/connector/service.py; src/sfm_fx_new_age/core/tab_data.py |
| native_history_job | src/sfm_fx_new_age/connector/history.py |
| native_history_record | src/sfm_fx_new_age/connector/history.py |
| native_quote_history_corroboration | src/sfm_fx_new_age/connector/quote_history.py |
| native_quote_history_decoded | src/sfm_fx_new_age/connector/quote_history.py |
| native_quote_history_job | src/sfm_fx_new_age/connector/analytical_feed.py; src/sfm_fx_new_age/connector/original_capture.py; src/sfm_fx_new_age/connector/quote_history.py |
| native_quote_history_page | src/sfm_fx_new_age/connector/quote_history.py |
| native_quote_history_received | src/sfm_fx_new_age/connector/quote_history.py |
| native_symbol_binding | src/sfm_fx_new_age/connector/service.py |
| pair_parameter | src/sfm_fx_new_age/services/catalogues.py |
| pair_parameter_revision | src/sfm_fx_new_age/services/catalogues.py |
| parameter | src/sfm_fx_new_age/core/runtime.py; src/sfm_fx_new_age/services/catalogues.py; src/sfm_fx_new_age/services/orders.py; src/sfm_fx_new_age/services/scanner.py; src/sfm_fx_new_age/services/strategy_signals.py |
| parameter_definition | src/sfm_fx_new_age/services/catalogues.py |
| parameter_revision | src/sfm_fx_new_age/services/catalogues.py |
| position_snapshot | src/sfm_fx_new_age/services/positions.py |
| projection_current | src/sfm_fx_new_age/services/public_projections.py; src/sfm_fx_new_age/services/strategy_signals.py |
| quote | src/sfm_fx_new_age/services/market.py |
| recipe | src/sfm_fx_new_age/services/research.py |
| recipe_state | src/sfm_fx_new_age/core/analytical_api.py; src/sfm_fx_new_age/core/command_handlers.py; src/sfm_fx_new_age/core/runtime.py; src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/public_projections.py; src/sfm_fx_new_age/services/research_money.py; src/sfm_fx_new_age/services/scanner.py |
| replay_dataset | src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/replay.py |
| replay_run | src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/replay.py |
| research_money_policy | src/sfm_fx_new_age/services/research_money.py |
| research_study | src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/replay.py |
| rule | src/sfm_fx_new_age/core/runtime.py; src/sfm_fx_new_age/services/catalogues.py |
| rule_output | src/sfm_fx_new_age/services/catalogues.py |
| rule_revision | src/sfm_fx_new_age/services/catalogues.py |
| setting | src/sfm_fx_new_age/connector/service.py; src/sfm_fx_new_age/core/command_handlers.py; src/sfm_fx_new_age/core/runtime.py; src/sfm_fx_new_age/services/workflow.py |
| signal | src/sfm_fx_new_age/services/signals.py |
| signal_revision | src/sfm_fx_new_age/services/research.py; src/sfm_fx_new_age/services/signals.py |
| signal_state_history | src/sfm_fx_new_age/core/tab_data.py; src/sfm_fx_new_age/services/signals.py |
| spec | src/sfm_fx_new_age/services/market.py |
| strategy_opportunity | src/sfm_fx_new_age/services/strategy_signals.py |
| strategy_projection | src/sfm_fx_new_age/services/public_projections.py |
| strategy_signal_current | src/sfm_fx_new_age/services/strategy_signals.py |
| strategy_signal_observation | src/sfm_fx_new_age/services/strategy_signals.py |
| strategy_signal_revoked | src/sfm_fx_new_age/services/strategy_signals.py |
| stream_gap | src/sfm_fx_new_age/services/continuity.py; src/sfm_fx_new_age/services/orders.py; src/sfm_fx_new_age/services/scanner.py; src/sfm_fx_new_age/services/strategy_signals.py |
| supplemental_evidence | src/sfm_fx_new_age/connector/quote_history.py; src/sfm_fx_new_age/services/supplemental.py |
| symbol_currency | src/sfm_fx_new_age/connector/service.py |
| variable | src/sfm_fx_new_age/services/catalogues.py |
| variable_definition | src/sfm_fx_new_age/services/catalogues.py |
| walk_forward | src/sfm_fx_new_age/core/command_handlers.py |
