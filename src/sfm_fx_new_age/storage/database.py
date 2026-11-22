from __future__ import annotations

from contextlib import contextmanager
from datetime import timezone
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Iterator


class StateConflict(ValueError):
    pass


class Database:
    """SQLite WAL; one lock/connection per runtime. Atomic reservation across runtimes."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.lock = RLock()
        self.connection = sqlite3.connect(self.path, check_same_thread=False, timeout=10, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        # Raw ISO strings sort offsets wrongly; julianday rounds microseconds.
        # Normalize to the same aware-instant ordering as the domain reader.
        from sfm_fx_new_age.contracts.domain import instant
        self.connection.create_function('projection_utc', 1,
            lambda value: instant(value).astimezone(timezone.utc).isoformat(timespec='microseconds'),
            deterministic=True)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA synchronous=FULL")
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1, 2):
            self.connection.close()
            raise ValueError(f"Unsupported database version: {version}")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS records (
                kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                PRIMARY KEY(kind, id)
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, account_id TEXT NOT NULL, signal_id TEXT NOT NULL,
                scope_id TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(scope_id, signal_id)
            );
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL, topic TEXT NOT NULL, body TEXT NOT NULL
            );
        """)
        columns = {row[1] for row in self.connection.execute('PRAGMA table_info(orders)')}
        if 'scope_id' not in columns:
            # Atomic v1 migration. Retain unscoped evidence without guessing its source.
            self.connection.execute('BEGIN IMMEDIATE')
            try:
                self.connection.execute('ALTER TABLE orders RENAME TO orders_legacy_v1')
                self.connection.execute('''CREATE TABLE orders (
                    id TEXT PRIMARY KEY, account_id TEXT NOT NULL, signal_id TEXT NOT NULL,
                    scope_id TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(scope_id, signal_id))''')
                for row in self.connection.execute('SELECT * FROM orders_legacy_v1').fetchall():
                    body = json.loads(row['body'])
                    scope = body.get('scope_id', 'LEGACY_UNBOUND:' + row['account_id'])
                    self.connection.execute('INSERT INTO orders VALUES(?,?,?,?,?)',
                        (row['id'], row['account_id'], row['signal_id'], scope, row['body']))
                self.connection.execute('DROP TABLE orders_legacy_v1')
                self.connection.execute('PRAGMA user_version=2')
                self.connection.commit()
            except BaseException:
                self.connection.rollback()
                raise
        self.connection.execute("PRAGMA user_version=2")
        self.connection.execute("""CREATE INDEX IF NOT EXISTS market_series_idx ON records(
            kind, json_extract(body,'$.scope_id'), json_extract(body,'$.symbol'),
            json_extract(body,'$.timeframe'), json_extract(body,'$.source_epoch'),
            json_extract(body,'$.open_time')) WHERE kind='bar'""")
        self.closed = False
        self.connection.execute("""CREATE INDEX IF NOT EXISTS analytical_scope_idx ON records(
            kind,json_extract(body,'$.lineage.source_scope'),json_extract(body,'$.lineage.source_epoch'),
            json_extract(body,'$.lineage.symbol'))""")
        self.connection.execute("""CREATE INDEX IF NOT EXISTS public_projection_history_scope_idx ON records(
            json_extract(body,'$.scope_id'),json_extract(body,'$.source_epoch'),
            json_extract(body,'$.symbol'),json_extract(body,'$.timeframe'),
            json_extract(body,'$.strategy_id')) WHERE kind='strategy_projection'""")
        self.connection.execute("""CREATE INDEX IF NOT EXISTS supplemental_interval_idx ON records(
            json_extract(body,'$.scope_id'),json_extract(body,'$.source_epoch'),
            json_extract(body,'$.symbol'),json_extract(body,'$.kind'),
            json_extract(body,'$.provider_id'),json_extract(body,'$.window_start'),
            json_extract(body,'$.window_end'),json_extract(body,'$.revision'))
            WHERE kind='supplemental_evidence'""")
        self.connection.execute("""CREATE INDEX IF NOT EXISTS supplemental_provider_publication_idx ON records(
            json_extract(body,'$.provider_id'),json_extract(body,'$.symbol'),
            json_extract(body,'$.kind'),json_extract(body,'$.available_at') DESC)
            WHERE kind='supplemental_evidence'""")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.lock:
            nested = self.connection.in_transaction
            point = ''
            # Keep independent rollback boundaries inside a bounded owner batch.
            if nested:
                self._savepoint_serial = getattr(self, '_savepoint_serial', 0) + 1
                point = 'operation_' + str(self._savepoint_serial)
                self.connection.execute('SAVEPOINT ' + point)
            else:self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
            except BaseException:
                if nested:
                    self.connection.execute('ROLLBACK TO ' + point)
                    self.connection.execute('RELEASE ' + point)
                else:self.connection.rollback()
                raise
            else:
                if nested:self.connection.execute('RELEASE ' + point)
                else:self.connection.commit()

    @contextmanager
    def batch_writes(self) -> Iterator[None]:
        """Share fsync within one bounded owner turn, not an atomic workflow.

        Completed independent operations survive a later failure, as with
        individual commits. Each transaction retains its savepoint rollback.
        FULL durability is unchanged; commit finishes before yielding to Qt.
        Use transaction() instead for an all-or-nothing workflow.
        """
        with self.lock:
            owns = not self.connection.in_transaction
            if owns:self.connection.execute('BEGIN IMMEDIATE')
            try:yield
            finally:
                if owns:
                    try:self.connection.commit()
                    except BaseException:
                        self.connection.rollback()
                        raise

    def get(self, kind: str, identity: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.connection.execute("SELECT body FROM records WHERE kind=? AND id=?", (kind, identity)).fetchone()
        return None if row is None else json.loads(row[0])

    def list(self, kind: str) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute("SELECT body FROM records WHERE kind=? ORDER BY id", (kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def get_many(self, kind: str, identities: list[str]) -> dict[str, dict[str, Any]]:
        """One bounded SELECT, with no persisted or cross-request cache."""
        if len(identities) > 500 or any(not isinstance(value, str) for value in identities):
            raise ValueError('At most 500 explicit record identities required')
        if not identities:
            return {}
        placeholders = ','.join('?' for _ in identities)
        with self.lock:
            rows = self.connection.execute(
                f'SELECT id,body FROM records WHERE kind=? AND id IN ({placeholders})',
                [kind, *identities]).fetchall()
        return {row['id']: json.loads(row['body']) for row in rows}

    def projection_history(self, *, scope: str, epoch: str, symbol: str,
                           timeframe: str, methods: list[str], cutoff: str) -> dict[str, dict[str, Any]]:
        """Latest immutable revision per method in this exact source/frame.

        Select the latest correction before display expiry, retaining disabled
        historical audit rows and the original fingerprint tie-break. Only the
        selected revisions cross the SQL/Python JSON boundary.
        """
        if len(methods) > 500 or any(not isinstance(value, str) for value in methods):
            raise ValueError('At most 500 explicit projection methods required')
        if not methods:
            return {}
        placeholders = ','.join('?' for _ in methods)
        sql = f"""WITH scoped AS (
            SELECT body,json_extract(body,'$.strategy_id') AS method,
                   projection_utc(json_extract(body,'$.available_at')) AS observed,
                   json_extract(body,'$.fingerprint') AS fingerprint
            FROM records WHERE kind='strategy_projection'
                AND json_extract(body,'$.scope_id')=? AND json_extract(body,'$.source_epoch')=?
                AND json_extract(body,'$.symbol')=? AND json_extract(body,'$.timeframe')=?
                AND json_extract(body,'$.strategy_id') IN ({placeholders})
        ), ranked AS (
            SELECT body,method,ROW_NUMBER() OVER (
                PARTITION BY method ORDER BY observed DESC,fingerprint DESC) AS ordinal
            FROM scoped WHERE observed<=projection_utc(?)
        ) SELECT method,body FROM ranked WHERE ordinal=1"""
        with self.lock:
            rows = self.connection.execute(sql, [scope, epoch, symbol, timeframe, *methods, cutoff]).fetchall()
        return {row['method']: json.loads(row['body']) for row in rows}

    def supplemental_revision(self, evidence) -> dict[str, Any] | None:
        """Latest correction metadata for one exact publication interval.

        No record payload is loaded just to check monotonic revision/availability.
        Origin is already bound by the caller's registered source authority.
        """
        with self.lock:
            row = self.connection.execute("""SELECT
                json_extract(body,'$.revision') AS revision,
                json_extract(body,'$.available_at') AS available_at
                FROM records WHERE kind='supplemental_evidence'
                AND json_extract(body,'$.scope_id')=? AND json_extract(body,'$.source_epoch')=?
                AND json_extract(body,'$.symbol')=? AND json_extract(body,'$.kind')=?
                AND json_extract(body,'$.provider_id')=? AND json_extract(body,'$.window_start')=?
                AND json_extract(body,'$.window_end')=?
                ORDER BY json_extract(body,'$.revision') DESC LIMIT 1""",
                (evidence.scope_id,evidence.source_epoch,evidence.symbol,evidence.kind,
                 evidence.provider_id,evidence.window_start,evidence.window_end)).fetchone()
        return dict(row) if row is not None else None

    def supplemental_candidates(self, *, scope, epoch, symbol, origin, providers, cutoff):
        """Latest eligible source publications, retaining exact-rank ties.

        Provider capability filtering precedes ranking. Expiry and active file
        membership are deliberately applied by the store AFTER latest selection.
        Equal available_at/revision rows retain the established body-digest tie
        break in the caller, not the different database record-ID digest.
        """
        if len(providers)>500:
            raise ValueError('At most 500 explicit supplemental source providers')
        selected=[(provider,kind) for provider,(kinds,declared_origin) in providers.items()
                  if declared_origin==origin for kind in sorted(kinds)]
        if not selected:
            return []
        clauses=' OR '.join("(json_extract(body,'$.provider_id')=? AND json_extract(body,'$.kind')=?)"
                            for _ in selected)
        sql=f"""WITH scoped AS (
            SELECT body,json_extract(body,'$.kind') AS input_kind,
                json_extract(body,'$.provider_id') AS provider,
                projection_utc(json_extract(body,'$.available_at')) AS observed,
                json_extract(body,'$.revision') AS revision
            FROM records WHERE kind='supplemental_evidence'
                AND json_extract(body,'$.scope_id')=? AND json_extract(body,'$.source_epoch')=?
                AND json_extract(body,'$.symbol')=? AND json_extract(body,'$.origin')=?
                AND ({clauses})
        ), ranked AS (
            SELECT body,DENSE_RANK() OVER (
                PARTITION BY input_kind,provider ORDER BY observed DESC,revision DESC) AS ordinal
            FROM scoped WHERE observed<=projection_utc(?)
        ) SELECT body FROM ranked WHERE ordinal=1"""
        parameters=[scope,epoch,symbol,origin,*[value for pair in selected for value in pair],cutoff]
        with self.lock:
            rows=self.connection.execute(sql,parameters).fetchall()
        return [json.loads(row['body']) for row in rows]

    def put(self, kind: str, identity: str, body: dict[str, Any]) -> None:
        with self.transaction() as conn:
            self.write(conn, kind, identity, body)

    def market_rows(self, scope: str, symbol: str, timeframe: str, epoch: str,
                    open_time: str | None = None) -> list[dict[str, Any]]:
        sql = """SELECT body FROM records WHERE kind='bar'
            AND json_extract(body,'$.scope_id')=? AND json_extract(body,'$.symbol')=?
            AND json_extract(body,'$.timeframe')=? AND json_extract(body,'$.source_epoch')=?"""
        args = [scope, symbol, timeframe, epoch]
        if open_time is not None:
            sql += " AND json_extract(body,'$.open_time')=?"
            args.append(open_time)
        with self.lock:
            return [json.loads(row[0]) for row in self.connection.execute(sql, args)]

    @staticmethod
    def write(conn: sqlite3.Connection, kind: str, identity: str, body: dict[str, Any]) -> None:
        conn.execute(
            "INSERT INTO records(kind,id,body) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
            (kind, identity, json.dumps(body, sort_keys=True)),
        )

    def append_event(self, event_id: str, topic: str, body: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute("INSERT OR IGNORE INTO events(event_id,topic,body) VALUES(?,?,?)", (event_id, topic, json.dumps(body)))

    def reserve_order(self, body: dict[str, Any], revision: int) -> None:
        with self.transaction() as conn:
            row = conn.execute("SELECT body FROM records WHERE kind='signal' AND id=?", (body['signal_record_id'],)).fetchone()
            if row is None:
                raise StateConflict("Signal not found")
            signal = json.loads(row[0])
            if (signal['state'] != 'QUEUED' or signal['revision'] != revision
                or signal.get('scope_id') != body['scope_id']):
                raise StateConflict("Signal is not queued at the selected revision")
            try:
                conn.execute("INSERT INTO orders(id,account_id,signal_id,scope_id,body) VALUES(?,?,?,?,?)", (
                    body['id'], body['account_id'], body['signal_id'], body['scope_id'], json.dumps(body),
                ))
            except sqlite3.IntegrityError:
                raise StateConflict("Signal/account already has an order; reconcile before retry") from None
            signal['state'] = 'ISSUE_RESERVED'
            self.write(conn, 'signal', body['signal_record_id'], signal)

    def orders(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.connection.execute("SELECT body FROM orders ORDER BY rowid").fetchall()
        return [json.loads(row[0]) for row in rows]

    def order(self, identity: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.connection.execute("SELECT body FROM orders WHERE id=?", (identity,)).fetchone()
        return None if row is None else json.loads(row[0])

    def update_order(self, identity: str, changes: dict[str, Any], *, signal_state: str | None = None) -> dict[str, Any]:
        with self.transaction() as conn:
            row = conn.execute("SELECT body FROM orders WHERE id=?", (identity,)).fetchone()
            if row is None:
                raise KeyError(identity)
            body = json.loads(row[0]); body.update(changes)
            conn.execute("UPDATE orders SET body=? WHERE id=?", (json.dumps(body), identity))
            if signal_state:
                row = conn.execute("SELECT body FROM records WHERE kind='signal' AND id=?", (body['signal_record_id'],)).fetchone()
                signal = json.loads(row[0]); signal['state'] = signal_state
                self.write(conn, 'signal', body['signal_record_id'], signal)
        return body

    def recover_inflight(self) -> int:
        recovered = 0
        for order in self.orders():
            if order['state'] in {'RESERVED', 'SUBMITTING'}:
                self.update_order(order['id'], {'state': 'UNKNOWN', 'detail': 'Restart requires authoritative reconciliation'})
                recovered += 1
        return recovered

    def close(self) -> None:
        with self.lock:
            if not self.closed:
                self.connection.close(); self.closed = True

    def diagnostics(self) -> dict[str, Any]:
        with self.lock:
            return {'journal_mode': self.connection.execute('PRAGMA journal_mode').fetchone()[0],
                    'page_count': self.connection.execute('PRAGMA page_count').fetchone()[0],
                    'records': self.connection.execute('SELECT COUNT(*) FROM records').fetchone()[0],
                    'events': self.connection.execute('SELECT COUNT(*) FROM events').fetchone()[0],
                    'schema_version': self.connection.execute('PRAGMA user_version').fetchone()[0]}

    def query_events(self, *, scope_id: str, topic: str | None = None, limit: int = 500,
                     after_sequence: int = 0) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 5000 or after_sequence < 0:
            raise ValueError('Bounded event query required')
        sql = """SELECT * FROM events WHERE sequence>? AND
            (json_extract(body,'$.payload.scope_id')=? OR topic IN ('UI.SELECTION','CONFIG.VERSION','PARAM.EFFECTIVE'))"""
        args: list[Any] = [after_sequence, scope_id]
        if topic is not None: sql += ' AND topic=?'; args.append(topic)
        sql += ' ORDER BY sequence LIMIT ?'; args.append(limit)
        with self.lock:
            return [{'sequence': row['sequence'], 'event_id': row['event_id'], 'topic': row['topic'],
                     **json.loads(row['body'])} for row in self.connection.execute(sql, args)]

    def backup(self, destination: str | Path) -> dict[str, str]:
        import os, hashlib
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            target = sqlite3.connect(destination)
            with self.lock: self.connection.backup(target)
            integrity = target.execute('PRAGMA integrity_check').fetchone()[0]
            target.close()
            if integrity != 'ok': raise ValueError('Backup integrity check failed')
            return {'path': str(destination), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
