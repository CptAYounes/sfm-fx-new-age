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
