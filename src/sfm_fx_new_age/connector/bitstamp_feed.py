"""Connector-owned public Bitstamp L3 reader. No private API or order writer.

Construction is inert; actual authenticated market-feed intent gates startup.
The worker validates every native event before coalescing full publications.
Two full snapshots must corroborate each new connection before admission.
"""
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Empty
from threading import Event, Thread
from time import monotonic
from urllib.request import Request, urlopen
from uuid import uuid4
import json

from sfm_fx_new_age.contracts.domain import instant,record
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from .bitstamp_book import NativeChainBook, PAIRS, KIND, PROVIDER
from .kraken_public import PublicationMailbox
from .lanes import project_binding,lane_matches,prune_admissions


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


class ConnectedBitstampBook:
    def __init__(self, connector, *, excluded=False):
        self.r = connector.r
        self.store = self.r.analytics.supplemental
        self.excluded = excluded
        self.binding = None
        self.worker = None
        self.stop = Event()
        self.results = PublicationMailbox(maxsize=4)
        self.closed = False
        self.next_start = 0.
        self.state = 'WAITING_CONNECTION'
        self.error_type = None
        self.error_reason = None
        self.current = {}
        self.revisions = {}
        self.publications = 0
        self.generation = 0
        self.last_directory = None
        self.audit = deque(maxlen=64)

    def _withdraw(self):
        if self.store is None:
            return
        changed = self.store.providers.pop(PROVIDER, None) is not None
        self.store.admissions.pop(PROVIDER, None)
        self.current.clear()
        if changed:
            for symbol in PAIRS:
                self.r.emit('ANALYTICS.INPUT', 'CT_OPEN_API_CONNECTOR',
                            dict(symbol=symbol, scope_id=self.r.market.scope_id,
                                 source_epoch='BITSTAMP_INPUT_WITHDRAWN', kind=KIND),
                            Priority.P2, self.r.market.scope_id)

    def disconnect(self):
        self.stop.set()
        if self.worker is not None:
            self.worker.join(timeout=25)
            if self.worker.is_alive():
                raise RuntimeError('Bitstamp public read worker did not stop')
            self.worker = None
        while True:
            try:
                self.results.get_nowait()
            except Empty:
                break
        self._withdraw()
        self.binding = None
        self.next_start = 0.
        self.revisions.clear()
        self.state = 'WAITING_CONNECTION'

    def _start(self):
        if self.worker is not None or self.closed or self.binding is None:
            return
        self.stop = Event()
        binding = self.binding
        directory = Path(self.r.database.path).parent / 'native-bitstamp' / str(uuid4())
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.last_directory = str(directory)
        self.state = 'CORROBORATING_NATIVE_FULL_BOOK'
        self.error_type = None
        self.error_reason = None
        self.generation += 1
        self.worker = Thread(target=self._read, args=(binding, directory),
                             name='SFM-Bitstamp-public-L3', daemon=False)
        self.worker.start()

    def _read(self, binding, directory):
        import websocket
        socket = None
        raw_batch = []
        batch_bytes = 0
        slot = 0
        events = []
        books = {}
        try:
            socket = websocket.create_connection('wss://ws.bitstamp.net', timeout=5)
            socket.settimeout(.4)
            pairs=tuple(s for s,_ in binding[1])
            for symbol in pairs:
                socket.send(json.dumps(dict(event='bts:subscribe',
                                            data=dict(channel='live_orders_' + symbol.lower()))))
            def read_one():
                nonlocal batch_bytes
                try:
                    raw = socket.recv()
                except websocket.WebSocketTimeoutException:
                    return None
                if not raw or len(raw.encode()) > 65536:
                    raise ValueError('Closed or over-budget native message')
                received = utcnow()
                message = json.loads(raw)
                if message.get('event') in {'bts:error', 'bts:request_reconnect'}:
                    raise ValueError('Native stream recovery required')
                raw_batch.append(dict(raw=raw, received_at=received))
                batch_bytes += len(raw.encode()) + 128
                return message, received
            def collect(seconds, counts_required=0):
                deadline = monotonic() + seconds
                counts = {s: 0 for s in pairs}
                while not self.stop.is_set() and monotonic() < deadline:
                    value = read_one()
                    if value is None:
                        continue
                    events.append(value)
                    if len(events) > 5000 or batch_bytes > 4000000:
                        raise ValueError('Native bootstrap budget exceeded')
                    m, _ = value
                    for symbol in pairs:
                        if m.get('channel') == 'live_orders_' + symbol.lower() and 'event_id' in m:
                            counts[symbol] += 1
                    if counts_required and min(counts.values()) >= counts_required:
                        return
                if counts_required and min(counts.values()) < counts_required and not self.stop.is_set():
                    raise TimeoutError('Native preseed events unavailable')
            def snapshot(symbol, label):
                if self.stop.is_set():
                    raise InterruptedError('Read stopped')
                url = 'https://www.bitstamp.net/api/v2/order_book/' + symbol.lower() + '/?group=2'
                with urlopen(Request(url, headers={'User-Agent': 'SFMFXNewAge-ReadOnly/1.0'}), timeout=8) as response:
                    raw = response.read(1000001)
                if len(raw) > 1000000:
                    raise ValueError('Native snapshot byte budget exceeded')
                (directory / (symbol + '-' + label + '.json')).write_bytes(raw)
                return raw.decode()
            collect(7, 3)
            # Public REST responses can be cached. Retain a genuine native
            # window before fetching; timestamp/chain/parity checks still gate
            # acceptance and never infer a missing pre-snapshot event.
            collect(2)
            seed = {s: snapshot(s, 'seed') for s in pairs}
            collect(1)
            checkpoints = {s: snapshot(s, 'checkpoint') for s in pairs}
            collect(2)
            if self.stop.is_set():
                return
            for symbol in pairs:
                book = NativeChainBook(symbol)
                book.bootstrap(seed[symbol], checkpoints[symbol], events)
                books[symbol] = book
            def flush():
                nonlocal slot, raw_batch, batch_bytes
                # Bounded circular original-message retention per connection.
                (directory / ('frames-%02d.json' % (slot % 32))).write_text(json.dumps(raw_batch) + '\n')
                slot += 1
                raw_batch = []
                batch_bytes = 0
                for symbol, book in books.items():
                    row = book.row(utcnow())
                    if row is not None:
                        payload = dict(row=row, parameters=book.parameters(), directory=str(directory))
                        self.results.put_nowait((binding, 'BOOK', (symbol, payload)))
            flush()
            last_flush = monotonic()
            while not self.stop.is_set():
                value = read_one()
                if value is not None:
                    message, received = value
                    for symbol, book in books.items():
                        if message.get('channel') == 'live_orders_' + symbol.lower() and message.get('event') in {'order_created', 'order_changed', 'order_deleted'}:
                            book.apply(message, received)
                if batch_bytes > 500000 or monotonic() - last_flush >= 1:
                    flush()
                    last_flush = monotonic()
        except Exception as exc:
            if not self.stop.is_set():
                reason = str(exc)[:180]
                (directory / 'failure-frames.json').write_text(json.dumps(raw_batch) + '\n')
                (directory / 'failure.json').write_text(json.dumps(dict(error_type=type(exc).__name__,reason=reason)) + '\n')
                self.results.put_nowait((binding, 'FAIL', ('', dict(error_type=type(exc).__name__,reason=reason))))
        finally:
            if socket is not None:
                socket.close(timeout=1)

    def _admit(self, symbol, payload):
        if not lane_matches(self.r,self.binding,symbol):
            raise ValueError('Matching active source binding required')
        row = payload['row']
        now = instant(self.r.clock())
        if any(not 0 <= (now - instant(row[k])).total_seconds() <= 5 for k in ('time', 'available_at')):
            return
        if self.current.get(symbol, {}).get('event_id') == row['event_id']:
            return
        stamp = instant(row['time'])
        start = (stamp - timedelta(microseconds=1)).isoformat()
        end = (stamp + timedelta(microseconds=1)).isoformat()
        key = (symbol, start, end)
        revision = self.revisions.get(key, 0) + 1
        evidence = SupplementalEvidence(provider_id=PROVIDER, kind=KIND,
            scope_id=self.binding[0], source_epoch=dict(self.binding[1])[symbol], symbol=symbol,
            origin='LIVE_OBSERVED', source_ref=payload['directory'], venue='BITSTAMP_SPOT_FIAT',
            instrument=symbol, price_domain='SPOT_PAIR', unit='DISPLAYED_BASE_UNITS',
            window_start=start, window_end=end, available_at=row['available_at'],
            valid_until=(stamp + timedelta(seconds=5)).isoformat(), complete=True,
            records=(row,), parameters=payload['parameters'], revision=revision)
        validate_wire_shape(evidence)
        if PROVIDER not in self.store.providers:
            self.store.register_provider(PROVIDER, kinds=[KIND], origin='LIVE_OBSERVED')
        self.store.accept(evidence)
        self.store.admissions.setdefault(PROVIDER,set()).add(digest(record(evidence)))
        with self.r.database.transaction() as connection:
            connection.execute("""DELETE FROM records WHERE kind='supplemental_evidence'
                AND json_extract(body,'$.provider_id')=? AND json_extract(body,'$.symbol')=?
                AND id NOT IN (SELECT id FROM records WHERE kind='supplemental_evidence'
                    AND json_extract(body,'$.provider_id')=? AND json_extract(body,'$.symbol')=?
                    ORDER BY json_extract(body,'$.available_at') DESC LIMIT 32)""",
                (PROVIDER, symbol, PROVIDER, symbol))
        prune_admissions(self.r,self.store,PROVIDER,self.binding)
        self.revisions[key] = revision
        if len(self.revisions) > 128:
            self.revisions.pop(next(iter(self.revisions)))
        self.current[symbol] = dict(event_id=row['event_id'], valid_until=evidence.valid_until,
                                    full_order_count=evidence.parameters['full_order_count'])
        self.publications += 1
        self.audit.append(dict(symbol=symbol, event_id=row['event_id'], time=row['time'],
                               received_at=row['available_at'], displayed_price_levels=len(row['bids']) + len(row['asks']),
                               native_order_count=evidence.parameters['full_order_count']))
        self.state = 'ADMITTED_NATIVE_CHAIN_FULL_DISPLAYED_BOOK'

    def poll(self, binding):
        binding=project_binding(binding,PAIRS)
        if self.closed:
            return
        if binding != self.binding:
            self.disconnect()
            self.binding = binding
        if self.excluded:
            self.state = 'EXTERNAL_CONFIGURATION'
            return
        if self.binding is None:
            return
        if self.r.database.path == ':memory:':
            self.state = 'NO_PERSISTENT_STATE'
            return
        failed = False
        while True:
            try:
                result_binding, kind, (symbol, payload) = self.results.get_nowait()
            except Empty:
                break
            if result_binding != self.binding:
                continue
            if kind == 'FAIL':
                self.error_type = payload['error_type']
                self.error_reason = payload['reason']
                failed = True
            elif not failed:
                try:
                    self._admit(symbol, payload)
                except (ValueError, KeyError, TypeError, ArithmeticError):
                    self.error_type = 'SOURCE_ADMISSION_REFUSED'
                    failed = True
        if failed:
            self.stop.set()
            self._withdraw()
            self.state = 'NATIVE_SOURCE_REFUSED'
            self.next_start = monotonic() + 15
        if self.worker is not None and not self.worker.is_alive():
            self.worker.join()
            self.worker = None
        if self.worker is None and monotonic() >= self.next_start:
            self._start()

    def status(self):
        now = instant(self.r.clock())
        fresh = [s for s, v in self.current.items() if now <= instant(v['valid_until'])]
        return dict(state=self.state, venue='BITSTAMP_SPOT_FIAT', supported_pairs=list(PAIRS),
                    fresh_pairs=sorted(fresh), publications=self.publications, generation=self.generation,
                    error_type=self.error_type, error_reason=self.error_reason, worker_alive=bool(self.worker and self.worker.is_alive()),
                    native_sequence_model='NATIVE_UUID_PREDECESSOR_CHAIN', full_scope='PUBLIC_DISPLAYED_ORDERS',
                    current=dict(self.current), directory=self.last_directory,
                    capability_note='Full public displayed orders, not hidden liquidity, executions, broker fills or consolidated FX.')

    def close(self):
        self.closed = True
        self.disconnect()
