"""Connector-owned, public GET-only NZDUSD reported-execution history.

No FXOpen account, authentication, trading endpoint, websocket or order authority.
Normal authenticated cTrader feed intent owns the analytical binding and teardown.
Historic originals are reused; only a corroborated trailing-day suffix is polled.
"""
from collections import deque
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic
from urllib.request import Request, urlopen
from uuid import uuid4
import json
import re

from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES, instant, record
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.contracts.analytics import digest
from .lanes import project_binding,lane_matches,prune_admissions
from .fxopen_reported import (PROVIDER, VENUE, SYMBOL, KINDS, TTL, MAX_ROWS,
    milliseconds, stamp, signature, addressed, corroborate, extend, evidences)

BASE = 'https://ttlivewebapi.fxopen.net/api/v2/'
REFRESH_SECONDS = 30


def public_get(endpoint, stop):
    if endpoint != 'public/symbol/NZDUSD' and not re.fullmatch(
            r'coingecko/trades/NZDUSD\?limit=0&start=[0-9]{1,16}&end=[0-9]{1,16}', endpoint):
        raise ValueError('Fixed public NZDUSD read-only endpoint allowlist')
    if stop.is_set():
        raise InterruptedError('Public read stopped')
    url = BASE + endpoint
    with urlopen(Request(url, headers={'User-Agent': 'SFMFXNewAge-ReadOnly/1.0'}), timeout=5) as response:
        if response.geturl() != url:
            raise ValueError('Unexpected public-source redirect')
        raw = response.read(4000001)
    if len(raw) > 4000000:
        raise ValueError('Public original response budget exceeded')
    return raw, stamp(datetime.now(timezone.utc))


class ConnectedFXOpenReported:
    def __init__(self, connector, *, excluded_kinds=()):
        self.r = connector.r
        self.store = self.r.analytics.supplemental
        self.excluded = frozenset(excluded_kinds)
        if 'TRADED_PRINTS' in self.excluded:
            self.excluded |= KINDS
        self.binding = None
        self.worker = None
        self.stop = Event()
        self.results = Queue(maxsize=1)
        self.closed = False
        self.next_start = 0.
        self.state = 'WAITING_CONNECTION'
        self.error_type = None
        self.error_reason = None
        self.tape = None
        self.current = {}
        self.revisions = {}
        self.generation = 0
        self.publications = 0
        self.requests = 0
        self.last_directory = None
        self.audit = deque(maxlen=32)

    def _withdraw(self):
        changed = self.store.providers.pop(PROVIDER, None) is not None
        self.store.admissions.pop(PROVIDER, None)
        self.current.clear()
        if changed:
            self.r.emit('ANALYTICS.INPUT', 'CT_OPEN_API_CONNECTOR',
                dict(symbol=SYMBOL, scope_id=self.r.market.scope_id,
                     source_epoch='FXOPEN_REPORTED_INPUT_WITHDRAWN', kind='PUBLIC_REPORTED_EXECUTIONS'),
                Priority.P2, self.r.market.scope_id)

    def disconnect(self):
        self.stop.set()
        if self.worker is not None:
            self.worker.join(timeout=8)
            if self.worker.is_alive():
                raise RuntimeError('Public reported-execution read worker did not stop')
        self.worker = None
        while True:
            try:
                self.results.get_nowait()
            except Empty:
                break
        self._withdraw()
        self.binding = None
        self.tape = None
        self.next_start = 0.
        self.revisions.clear()
        self.last_directory = None
        self.state = 'WAITING_CONNECTION'

    def _read(self, binding, start, end, previous, directory):
        receipts = []
        slot = self.generation % 16
        try:
            def get(endpoint, label):
                if receipts and self.stop.wait(.3):
                    raise InterruptedError('Public read stopped')
                raw, at = public_get(endpoint, self.stop)
                filename = ('bootstrap-' if previous is None else 'refresh-%02d-' % slot) + label + '.json'
                (directory / filename).write_bytes(raw)
                receipts.append(dict(endpoint=endpoint, file=filename, received_at=at,
                                     bytes=len(raw), sha256=sha256(raw).hexdigest()))
                return raw, at
            if previous is None:
                raw, _ = get('public/symbol/NZDUSD', 'symbol')
                symbols = json.loads(raw, parse_float=Decimal)
                if (not isinstance(symbols, list) or len(symbols) != 1
                    or symbols[0].get('Symbol') != SYMBOL
                    or symbols[0].get('MarginCurrency') != 'NZD'
                    or symbols[0].get('ProfitCurrency') != 'USD'
                    or symbols[0].get('MarginMode') != 'Forex'
                    or symbols[0].get('ProfitMode') != 'Forex'
                    or symbols[0].get('IsTradeAllowed') is not True):
                    raise ValueError('Exact listed live native NZDUSD Forex contract required')
            middle = (start + end) // 2
            bodies = []
            times = []
            for label, lo, hi in (('full', start, end), ('left', start, middle), ('right', middle, end)):
                endpoint = 'coingecko/trades/NZDUSD?limit=0&start=' + str(lo) + '&end=' + str(hi - 1)
                raw, at = get(endpoint, label)
                bodies.append(raw)
                times.append(at)
            tape = extend(previous, corroborate(bodies[0], bodies[1], bodies[2], start, middle, end, times))
            if self.stop.is_set():
                return
            proof = dict(tape.proof, receipts=receipts, combined_original_rows=len(tape.native),
                         available_at=tape.available_at, native_sequence=False, known_aggressors=False)
            filename = 'proof-%02d.json' % slot
            (directory / filename).write_text(json.dumps(proof, indent=2) + '\n')
            self.results.put_nowait((binding, tape, proof, None))
        except Exception as exc:
            if not self.stop.is_set():
                failure = dict(error_type=type(exc).__name__, reason=str(exc)[:180], receipts=receipts)
                (directory / ('failure-%02d.json' % slot)).write_text(json.dumps(failure, indent=2) + '\n')
                self.results.put_nowait((binding, None, failure, type(exc).__name__))

    def _bars(self):
        authority = self.r.market.authority(SYMBOL)
        if authority is None:
            return {}
        return {frame: tuple(record(bar) for bar in self.r.market.bars(
            SYMBOL, frame, self.r.clock(), authority['source_epoch'])[-21:]) for frame in FRAMES}

    def _admit(self, tape, proof):
        authority = self.r.market.authority(SYMBOL)
        account = self.r.accounts.current
        if (not lane_matches(self.r,self.binding,SYMBOL) or account is None or authority is None
            or (account.scope_id, authority['source_epoch']) != (self.binding[0], dict(self.binding[1])[SYMBOL])):
            raise ValueError('Obsolete public reported-execution binding')
        # Restore the first genuine observation clock, including across reconnect.
        rows = addressed(tape.native, tape.available_at)
        seen = dict(tape.first_seen)
        # Original matching is content-address based, never zero/reused trade_id.
        originals = {}
        counts = {}
        for native in tape.native:
            root = sha256(signature(native).encode()).hexdigest()
            occurrence = counts.get(root, 0)
            counts[root] = occurrence + 1
            identity = 'FXOPEN:LOCAL_ROW_SHA256:' + root + ':' + str(occurrence).zfill(5)
            originals[identity] = native
        inserts = []
        for row in rows:
            old = self.r.database.get('fxopen_native_reported_execution', row['id'])
            if old is not None:
                if old['native'] != json.loads(signature(originals[row['id']])):
                    raise ValueError('Stored original reported execution changed')
                seen[row['id']] = min((seen[row['id']], old['first_observed_at']), key=instant)
            else:
                inserts.append((row['id'], dict(native=json.loads(signature(originals[row['id']])),
                    first_observed_at=seen[row['id']], local_id_not_native_id=True)))
        tape = replace(tape, first_seen=seen)
        spec = self.r.market.spec(account.account_id, SYMBOL)
        if spec is None:
            raise ValueError('Unchanged broker chart specification required')
        values = evidences(tape, self.binding[0], authority['source_epoch'], spec.tick_size,
                           self._bars().get('W1', ()), excluded=self.excluded, revisions=self.revisions)
        if not values:
            raise ValueError('No admissible original reported-execution inputs')
        if instant(self.r.clock()) > instant(values[0].valid_until):
            raise ValueError('Reported-execution acquisition expired before admission')
        added = PROVIDER not in self.store.providers
        if added:
            self.store.register_provider(PROVIDER, kinds=KINDS - self.excluded, origin='LIVE_OBSERVED')
        try:
            self.store.accept_many(values)
        except Exception:
            if added:
                self.store.providers.pop(PROVIDER, None)
            raise
        self.store.admissions.setdefault(PROVIDER,set()).update(digest(record(e)) for e in values)
        with self.r.database.transaction() as connection:
            connection.executemany('INSERT OR IGNORE INTO records(kind,id,body) VALUES(?,?,?)',
                [('fxopen_native_reported_execution', identity, json.dumps(body, sort_keys=True))
                 for identity, body in inserts])
            for kind in KINDS:
                connection.execute("""DELETE FROM records WHERE kind='supplemental_evidence'
                    AND json_extract(body,'$.provider_id')=? AND json_extract(body,'$.kind')=?
                    AND id NOT IN (SELECT id FROM records WHERE kind='supplemental_evidence'
                    AND json_extract(body,'$.provider_id')=? AND json_extract(body,'$.kind')=?
                    ORDER BY json_extract(body,'$.available_at') DESC LIMIT 4)""", (PROVIDER, kind, PROVIDER, kind))
        self.tape = tape
        prune_admissions(self.r,self.store,PROVIDER,self.binding)
        for value in values:
            self.current[value.kind] = dict(valid_until=value.valid_until, rows=len(value.records))
            self.revisions[(value.kind, value.window_start, value.window_end)] = value.revision
        if len(self.revisions) > 32:
            self.revisions = dict(list(self.revisions.items())[-16:])
        self.audit.append(proof)
        self.publications += 1
        self.state = 'CORROBORATED_PUBLIC_REPORTED_EXECUTIONS'
        self.r.emit('ANALYTICS.INPUT', 'CT_OPEN_API_CONNECTOR',
            dict(symbol=SYMBOL, scope_id=self.binding[0], source_epoch=authority['source_epoch'],
                 kind='PUBLIC_REPORTED_EXECUTIONS'), Priority.P2, self.binding[0])

    def poll(self, binding):
        if SYMBOL not in PAIRS:
            if self.binding is not None or self.worker is not None:
                self.disconnect()
            self.state = 'OUTSIDE_ACTIVE_UNIVERSE'
            return
        binding=project_binding(binding,(SYMBOL,))
        if self.closed:
            return
        if binding != self.binding:
            self.disconnect()
            self.binding = binding
        if binding is None or KINDS <= self.excluded:
            return
        if self.r.database.path == ':memory:':
            self.state = 'NO_PERSISTENT_STATE'
            return
        if self.worker is not None and not self.worker.is_alive():
            self.worker.join()
            self.worker = None
            try:
                identity, tape, proof, error = self.results.get_nowait()
            except Empty:
                identity, tape, proof, error = binding, None, {}, 'MISSING_RESULT'
            if identity == self.binding:
                self.requests += len(proof.get('receipts', ()))
                if not error:
                    try:
                        self._admit(tape, proof)
                    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                        error = type(exc).__name__
                        proof = dict(error_type=error, reason=str(exc)[:180])
                if error:
                    self._withdraw()
                    self.tape = None
                    self.error_type = error
                    self.error_reason = proof.get('reason')
                    self.state = 'PUBLIC_REPORTED_SOURCE_UNAVAILABLE'
                self.next_start = monotonic() + (60 if error else REFRESH_SECONDS)
        if self.worker is not None or monotonic() < self.next_start:
            return
        bars = self._bars()
        starts = [milliseconds(rows[0]['open_time']) for rows in bars.values() if rows]
        if not starts:
            self.state = 'WAITING_NATIVE_BAR_INTERVALS'
            return
        start = min(starts)
        end = milliseconds(self.r.clock()) - 1000
        previous = self.tape
        if previous is not None and previous.start <= start and previous.end < end:
            start = max(previous.start, previous.end - 86400000)
        else:
            previous = None
        if end - start < 2 or end - start > 180 * 86400000:
            self.state = 'BOUNDED_NATIVE_HISTORY_INTERVAL_UNAVAILABLE'
            return
        if self.last_directory is None:
            directory = Path(self.r.database.path).parent / 'native-fxopen-reported' / str(uuid4())
            directory.mkdir(mode=0o700, parents=True, exist_ok=False)
            self.last_directory = str(directory)
        self.stop = Event()
        self.generation += 1
        self.error_type = self.error_reason = None
        self.state = 'CORROBORATING_PUBLIC_REPORTED_EXECUTIONS'
        self.worker = Thread(target=self._read, args=(binding, start, end, previous, Path(self.last_directory)),
                             name='SFM-FXOpen-public-reported-read', daemon=False)
        self.worker.start()

    def status(self):
        now = instant(self.r.clock())
        fresh = sorted(kind for kind, value in self.current.items() if now <= instant(value['valid_until']))
        return dict(state=self.state, provider=PROVIDER, venue=VENUE, symbol=SYMBOL,
            fresh_kinds=fresh, qualified_pairs=[SYMBOL] if 'TRADED_PRINTS' in fresh else [],
            publications=self.publications, requests=self.requests,
            worker_alive=bool(self.worker and self.worker.is_alive()),
            error_type=self.error_type, error_reason=self.error_reason,
            original_reported_rows=len(self.tape.native) if self.tape is not None else 0,
            known_aggressors=False, native_sequence=False, full_book=False,
            broker_fill_claim=False, market_wide_volume=False,
            refresh_seconds=REFRESH_SECONDS, ttl_seconds=TTL,
            scope_note='FXOpen public reported NZDUSD FX-contract executions only; not all ECN/client trades, cTrader fills, consolidated FX or documented aggressors. Native IDs may be zero/reused; local content addresses do not change them.')

    def close(self):
        self.closed = True
        self.disconnect()
