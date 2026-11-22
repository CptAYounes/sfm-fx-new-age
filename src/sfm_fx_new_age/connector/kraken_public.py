"""Credential-free Kraken fiat venue observations; never broker/order authority.

Public v2 trade.side is the documented taker side. Native executed-hour totals
are a different evidence kind, never fabricated trade prints. The cTrader price
source stays unchanged. Every output discloses its separate execution venue.
"""
from collections import deque,OrderedDict
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from hashlib import sha256
from queue import Queue, Empty, Full
from threading import Event, Thread, Lock
from time import monotonic
from urllib.request import Request, urlopen
import json
import re
from pathlib import Path
from .kraken_book import NativeBook
from .lanes import project_binding,lane_matches,prune_admissions

from sfm_fx_new_age.contracts.domain import PAIRS, instant, record
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.contracts.analytics import digest as evidence_digest

PROVIDER = 'KRAKEN_PUBLIC_FIAT_V1'
VENUE = 'KRAKEN_SPOT_FIAT'
KINDS = frozenset({'TRADED_PRINTS', 'AGGRESSOR_PRINTS', 'EXECUTED_BAR_QUANTITIES','EXECUTED_WEEK_QUANTITIES','VENUE_L2_CHECKSUM_BOOK'})
BASE = 'https://api.kraken.com/0/public/'


class PublicationMailbox:
    """Coalesce complete publication snapshots, never native protocol messages.

    The worker still validates every execution ID and every book CRC. Only its
    already-validated latest complete per-pair window waits for the core owner.
    First-receipt/native clocks and the binding are not changed by replacement.
    """
    def __init__(self,maxsize=24):
        self.maxsize=maxsize;self.items=OrderedDict();self.lock=Lock();self.coalesced=0

    def put_nowait(self,value):
        binding,kind,payload=value
        symbol=payload[0] if kind in {'TRADES','HOURS','BOOK','PAIR_ERROR'} else None
        key=(binding,kind,symbol)
        with self.lock:
            if kind in {'TRADES','HOURS','BOOK'}:
                self.items.pop((binding,'PAIR_ERROR',symbol),None)
            if key in self.items:self.coalesced+=1
            elif len(self.items)>=self.maxsize:raise Full
            self.items[key]=value

    def get_nowait(self):
        with self.lock:
            if not self.items:raise Empty
            return self.items.popitem(last=False)[1]

    def qsize(self):
        with self.lock:return len(self.items)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def native_get(endpoint, stop):
    """Only fixed public market-data GETs; bounded verified HTTPS, no secrets."""
    if stop.is_set():
        raise InterruptedError('Source stopped')
    if not (endpoint == 'AssetPairs' or re.fullmatch(r'OHLC\?pair=[A-Z]{6,12}&interval=60',endpoint)):
        raise ValueError('Read-only native endpoint allowlist')
    request = Request(BASE + endpoint, headers={'User-Agent': 'SFMFXNewAge-ReadOnly/1.0'})
    with urlopen(request, timeout=5) as response:
        if response.geturl().split('?')[0] != request.full_url.split('?')[0]:
            raise ValueError('Unexpected public-source redirect')
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError('Native response budget exceeded')
    body = json.loads(raw, parse_float=Decimal)
    if body.get('error') or not isinstance(body.get('result'), dict):
        raise ValueError('Native market-data response rejected')
    return body['result'], sha256(raw).hexdigest(), raw


def discover(result):
    """Native listed fiat/fiat instruments only; no synthetic cross conversion."""
    pairs = {}
    for key, item in result.items():
        name = item.get('wsname', '')
        parts = name.split('/')
        if len(parts) != 2 or ''.join(parts) not in PAIRS or item.get('status') != 'online':
            continue
        if item.get('aclass_base') != 'currency' or item.get('aclass_quote') != 'currency':
            continue
        tick = Decimal(item['tick_size'])
        if not tick.is_finite() or tick <= 0:
            raise ValueError('Invalid native venue grid')
        pairs[''.join(parts)] = dict(native_pair=key, wsname=name, tick_size=str(tick))
    return pairs


class NativeTrades:
    """Snapshot-first contiguous per-book native IDs; bounded immutable prints."""
    def __init__(self):
        self.rows = deque(maxlen=12000)
        self.last_id = None
        self.last_time = None
        self.ready = False

    def apply(self, rows, message_type, received_at):
        if message_type == 'snapshot':
            self.rows.clear(); self.last_id = None; self.last_time = None; self.ready = False
        elif message_type != 'update' or not self.ready:
            raise ValueError('Native trade snapshot required')
        for item in rows:
            identity = item['trade_id']
            if type(identity) is not int or identity < 1:
                raise ValueError('Native positive trade sequence required')
            if self.last_id is not None and identity != self.last_id + 1:
                raise ValueError('Unproven contiguous trade interval')
            time = item['timestamp']; at = instant(time)
            if at > instant(received_at) or self.last_time is not None and at < self.last_time:
                raise ValueError('Invalid native trade clock')
            price, quantity = Decimal(str(item['price'])), Decimal(str(item['qty']))
            if any(not v.is_finite() or v <= 0 for v in (price, quantity)) or item['side'] not in {'buy', 'sell'}:
                raise ValueError('Actual native price / quantity / taker required')
            self.rows.append(dict(id=f'KRAKEN:{identity:020d}', time=time, available_at=received_at,
                                  price=str(price), quantity=str(quantity), aggressor=item['side'].upper()))
            self.last_id = identity; self.last_time = at
        self.ready = bool(self.rows)

    def closed_interval(self):
        if not self.ready or len(self.rows) < 2:
            return None
        # Last timestamp group is excluded, so a future batch cannot add a
        # same-timestamp execution to an allegedly closed publication interval.
        end = self.rows[-1]['time']; start = self.rows[0]['time']
        if instant(start) >= instant(end):
            return None
        rows = tuple(dict(r) for r in self.rows if instant(r['time']) < instant(end)
                     and (len(self.rows)<12000 or instant(r['time'])>instant(start)))
        if not rows:return None
        start=rows[0]['time']
        return start, end, rows


def closed_hours(result, pair, received_at):
    rows = result.get(pair)
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError('Native executed-hour history missing')
    output = []
    previous = None
    # Native documentation: the last row is always the uncommitted candle.
    for item in rows[:-1]:
        if len(item) != 8 or type(item[0]) is not int:
            raise ValueError('Native OHLC tuple shape required')
        start = datetime.fromtimestamp(item[0], timezone.utc); end = start + timedelta(hours=1)
        quantity = Decimal(str(item[6])); count = item[7]
        if (previous is not None and start <= previous or end > instant(received_at)
                or not quantity.is_finite() or quantity < 0 or type(count) is not int or count < 0
                or (quantity == 0) != (count == 0)):
            raise ValueError('Invalid closed executed-hour total')
        previous = start
        output.append(dict(id='KRAKEN:H1:'+str(item[0]), time=stamp(start), available_at=received_at,
                           end_time=stamp(end), quantity=str(quantity), trade_count=count))
    return tuple(output)


class ConnectedKrakenFeed:
    """One connector-owned read worker. Admission and notifications stay on core."""
    def __init__(self, connector, *, excluded_kinds=()):
        self.c = connector; self.r = connector.r; self.store = self.r.analytics.supplemental
        self.excluded = frozenset(excluded_kinds); self.binding = None
        if 'TRADED_PRINTS' in self.excluded:self.excluded=self.excluded|{'EXECUTED_BAR_QUANTITIES','EXECUTED_WEEK_QUANTITIES'}
        if 'VENUE_BOOK' in self.excluded or 'BROKER_DEPTH' in self.excluded:self.excluded=self.excluded|{'VENUE_L2_CHECKSUM_BOOK'}
        self.worker = None; self.stop = Event(); self.results = PublicationMailbox(maxsize=24)
        self.socket = None; self.closed = False; self.next_start = 0
        self.state = 'WAITING_CONNECTION'; self.pairs = {}; self.states = {}; self.publications = 0
        self.last_published = {}; self.revisions = {}; self.error_type = None
        self.audit = deque(maxlen=256)
        self.http_audit = deque(maxlen=16)
        self.admitted = {kind:set() for kind in KINDS}
        self.archived_print_ids = {}; self.archived_hours = set()
        self.validity={};self.history_state='NOT_ACQUIRED';self.history_metadata=None
        from .kraken_weekly import ConnectedWeeklyRecovery
        self.weekly=ConnectedWeeklyRecovery(self)

    def _withdraw(self):
        self.weekly.disconnect()
        changed = self.store.providers.pop(PROVIDER, None) is not None
        self.store.admissions.pop(PROVIDER, None)
        self.admitted = {kind:set() for kind in KINDS}
        self.validity.clear()
        if changed:
            for symbol in PAIRS:
                self.r.emit('ANALYTICS.INPUT', 'CT_OPEN_API_CONNECTOR',
                            dict(symbol=symbol, scope_id=self.r.market.scope_id,
                                 source_epoch='PUBLIC_VENUE_WITHDRAWN', kind='PUBLIC_VENUE_STATUS'),
                            Priority.P2, self.r.market.scope_id)

    def disconnect(self):
        self.weekly.disconnect()
        self.stop.set()
        sock = self.socket
        if sock is not None:
            try: sock.close(timeout=1)
            except Exception: pass
        if self.worker is not None:
            self.worker.join(timeout=8)
            if self.worker.is_alive():
                raise RuntimeError('Public venue read worker did not stop')
        self.worker = None; self.socket = None; self._withdraw(); self.binding = None
        self.last_published.clear(); self.revisions.clear(); self.pairs = {}; self.states = {}
        self.archived_print_ids.clear(); self.archived_hours.clear()
        while True:
            try: self.results.get_nowait()
            except Empty: break
        self.state = 'WAITING_CONNECTION'

    def _send(self, binding, kind, payload):
        if self.stop.is_set(): return
        try: self.results.put_nowait((binding, kind, payload))
        except Full:
            # A dropped update must not leave any accepted source authoritative.
            self.error_type='PUBLICATION_MAILBOX_CAPACITY'
            self.stop.set()

    def _run(self, binding):
        try:
            import websocket
            data, source_hash, raw = native_get('AssetPairs', self.stop)
            self.http_audit.append(dict(endpoint='AssetPairs',sha256=source_hash,raw=raw.decode(),binding=binding))
            pairs = {s:v for s,v in discover(data).items() if s in dict(binding[1])}
            self._send(binding, 'PAIRS', pairs)
            if not pairs: raise ValueError('No supported native fiat instruments')
            historic={}
            if 'EXECUTED_BAR_QUANTITIES' not in self.excluded:
                try:
                    from .kraken_history import acquire_hour_history,history_rows
                    cache=Path(self.r.database.path).parent/'market-cache/kraken-hour-history'
                    self.history_metadata=acquire_hour_history(tuple(pairs),cache,self.stop)
                    for symbol in pairs:historic[symbol]=history_rows(cache,symbol,self.history_metadata,stamp(datetime.now(timezone.utc)))
                    self.history_state='NATIVE_ARCHIVE_CACHED_WITH_EXPLICIT_GAPS'
                except (OSError,ValueError,KeyError,ArithmeticError) as exc:self.history_state='HISTORY_UNAVAILABLE:'+type(exc).__name__
            books = {symbol: NativeTrades() for symbol in pairs}
            depth={symbol:NativeBook() for symbol in pairs};last_depth_publish={}
            source_hashes = {symbol:'' for symbol in pairs}
            sock = websocket.create_connection('wss://ws.kraken.com/v2', timeout=5)
            self.socket = sock; sock.settimeout(.25)
            sock.send(json.dumps(dict(method='subscribe', params=dict(channel='trade',
                           symbol=[v['wsname'] for v in pairs.values()], snapshot=True))))
            # Acquisition is paced; at most one GET between stream drains.
            if 'VENUE_L2_CHECKSUM_BOOK' not in self.excluded:
                sock.send(json.dumps(dict(method='subscribe',params=dict(channel='book',depth=10,
                           symbol=[v['wsname'] for v in pairs.values()],snapshot=True))))
            scheduled = deque(pairs); next_http = monotonic(); next_refresh = monotonic()+300
            next_publish = 0.; last_message = monotonic()
            while not self.stop.is_set():
                try:
                    raw = sock.recv()
                    if not raw: raise ConnectionError('Public stream closed')
                    message = json.loads(raw, parse_float=Decimal)
                    at = stamp(datetime.now(timezone.utc)); last_message = monotonic()
                    if message.get('success') is False: raise ValueError('Native subscription refused')
                    if message.get('channel') == 'status':
                        if any(row.get('system') != 'online' for row in message['data']):
                            raise ConnectionError('Venue not online')
                    if message.get('channel') == 'trade':
                        grouped = {}
                        for row in message['data']:
                            symbol = row['symbol'].replace('/', '')
                            if symbol not in books: raise ValueError('Unsubscribed venue symbol')
                            grouped.setdefault(symbol, []).append(row)
                        for symbol, rows in grouped.items():
                            books[symbol].apply(rows, message['type'], at)
                            source_hashes[symbol]=sha256((source_hashes[symbol]+raw).encode()).hexdigest()
                        self.audit.append(dict(received_at=at,raw=raw,message=json.loads(raw)))
                    elif message.get('channel')=='book':
                        for item in message['data']:
                            symbol=item['symbol'].replace('/','')
                            if symbol not in depth:raise ValueError('Unsubscribed book symbol')
                            depth[symbol].apply(item,message['type'],at,raw)
                            row=depth[symbol].row(at)
                            if row and monotonic()-last_depth_publish.get(symbol,-10)>=1:
                                self._send(binding,'BOOK',(symbol,pairs[symbol],row,at,depth[symbol].snapshot_hash))
                                last_depth_publish[symbol]=monotonic()
                        self.audit.append(dict(received_at=at,raw=raw,message=json.loads(raw)))
                except websocket.WebSocketTimeoutException:
                    pass
                if monotonic()-last_message > 15: raise TimeoutError('Public stream heartbeat missing')
                if monotonic() >= next_http and scheduled and not self.stop.is_set():
                    symbol = scheduled.popleft(); info = pairs[symbol]
                    try:
                        endpoint='OHLC?pair='+info['native_pair']+'&interval=60'
                        result, digest, raw = native_get(endpoint, self.stop)
                        self.http_audit.append(dict(endpoint=endpoint,sha256=digest,raw=raw.decode(),binding=binding))
                        at = stamp(datetime.now(timezone.utc))
                        rows = closed_hours(result, info['native_pair'], at)
                        if symbol in historic:
                            combined={r['time']:dict(r,available_at=self.history_metadata['first_verified_at']) for r in historic[symbol]}
                            combined.update({r['time']:r for r in rows});rows=tuple(combined[t] for t in sorted(combined))
                            digest=sha256((self.history_metadata['pairs'][symbol]['sha256']+digest).encode()).hexdigest()
                        self._send(binding, 'HOURS', (symbol, info, rows, at, digest))
                    except (OSError, ValueError, ArithmeticError, KeyError) as exc:
                        self._send(binding, 'PAIR_ERROR', (symbol, type(exc).__name__))
                    next_http = monotonic()+1.1
                if monotonic() >= next_refresh and not scheduled:
                    scheduled.extend(pairs); next_refresh = monotonic()+300
                if monotonic() >= next_publish:
                    at = stamp(datetime.now(timezone.utc))
                    for symbol, book in books.items():
                        interval = book.closed_interval()
                        if interval is not None:
                            self._send(binding, 'TRADES', (symbol, pairs[symbol], interval, at, source_hashes[symbol]))
                    next_publish = monotonic()+15
        except Exception as exc:
            self._send(binding, 'ERROR', type(exc).__name__)
        finally:
            if self.socket is not None:
                try: self.socket.close(timeout=1)
                except Exception: pass

    def _accept(self, symbol, info, rows, at, kind, start, end, source_hash):
        if kind in self.excluded: return
        if not lane_matches(self.r,self.binding,symbol):raise ValueError('Disconnected or unavailable venue pair')
        authority = self.r.market.authority(symbol)
        if not authority or (self.r.market.scope_id, authority['source_epoch']) != (self.binding[0], dict(self.binding[1])[symbol]):
            raise ValueError('Obsolete public venue binding')
        spec = self.r.market.spec(self.r.accounts.current.account_id, symbol)
        if not spec: raise ValueError('Current chart instrument specification required')
        # Bins remain on the broker's unchanged chart grid. A coarser venue grid
        # is fine only when every native execution is also chart-grid aligned.
        tick = Decimal(str(spec.tick_size))
        if kind == 'TRADED_PRINTS' and any(Decimal(r['price']) % tick for r in rows):
            raise ValueError('Venue execution does not align to current chart grid')
        params = {'tick_size': str(tick)} if kind == 'TRADED_PRINTS' else {}
        if kind=='VENUE_L2_CHECKSUM_BOOK':params=dict(depth=10,native_sequence=False,full_book_complete=False,checksum_algorithm='KRAKEN_V2_CRC32_TOP10',snapshot_hash=info['snapshot_hash'],clock_basis='LOCAL_RECEIPT_OF_VERIFIED_SNAPSHOT_OR_UPDATE')
        key = (symbol, kind, start, end)
        revision = self.revisions.get(key, 0)+1
        ref=('https://api.kraken.com/0/public/OHLC#native-week-derivation-sha256=' if kind=='EXECUTED_WEEK_QUANTITIES' else 'https://api.kraken.com/0/public/OHLC#native-closed-intervals-derivation-sha256=' if kind=='EXECUTED_BAR_QUANTITIES' else 'wss://ws.kraken.com/v2#message-chain-sha256=')+source_hash
        until=stamp(min(instant(at)+timedelta(seconds=4),instant(rows[-1]['available_at'])+timedelta(seconds=5))) if kind=='VENUE_L2_CHECKSUM_BOOK' else stamp(instant(at)+timedelta(seconds=400 if kind in {'EXECUTED_BAR_QUANTITIES','EXECUTED_WEEK_QUANTITIES'} else 45))
        evidence = SupplementalEvidence(PROVIDER, kind, self.binding[0], authority['source_epoch'], symbol,
                    'LIVE_OBSERVED', ref, VENUE, symbol, 'SPOT_PAIR',
                    'DISPLAYED_BASE_UNITS' if kind=='VENUE_L2_CHECKSUM_BOOK' else 'EXECUTED_BASE_UNITS', start, end, at, until,
                    True, tuple(rows), params, revision=revision)
        # A child reconnect or pair-membership change can repeat an interval
        # inside the same account epoch. Local counters are not durable revision
        # authority; preserve immutable rows and advance from their exact key.
        previous = self.r.database.supplemental_revision(evidence)
        if previous is not None:
            if instant(at) <= instant(previous['available_at']):
                raise ValueError('Venue re-observation must advance its actual publication clock')
            revision = max(revision, previous['revision'] + 1)
            evidence = replace(evidence, revision=revision)
        validate_wire_shape(evidence)
        if PROVIDER not in self.store.providers:
            self.store.register_provider(PROVIDER, kinds=KINDS-self.excluded, origin='LIVE_OBSERVED')
        self.store.accept(evidence); self.revisions[key] = revision
        self.store.admissions.setdefault(PROVIDER,set()).add(evidence_digest(record(evidence)))
        # Bound overlapping live publications, retain normalized originals once.
        # Other providers, broker bars and strategy records are never deleted.
        with self.r.database.transaction() as conn:
            conn.execute("""DELETE FROM records WHERE kind='supplemental_evidence'
                AND json_extract(body,'$.provider_id')=? AND json_extract(body,'$.symbol')=?
                AND json_extract(body,'$.kind')=? AND id NOT IN (
                    SELECT id FROM records WHERE kind='supplemental_evidence'
                    AND json_extract(body,'$.provider_id')=? AND json_extract(body,'$.symbol')=?
                    AND json_extract(body,'$.kind')=?
                    ORDER BY json_extract(body,'$.available_at') DESC LIMIT 16)""",
                         (PROVIDER,symbol,kind,PROVIDER,symbol,kind))
        prune_admissions(self.r,self.store,PROVIDER,self.binding)
        self.admitted[kind].add(symbol)
        self.validity[(kind,symbol)]=until
        # Do not accumulate native window revision counters indefinitely.
        for old in list(self.revisions):
            if old[:2] == key[:2] and old != key: self.revisions.pop(old)
        self.publications += 1; self.states[symbol] = 'VENUE_EXECUTIONS_ADMITTED'

    def _archive(self,symbol,rows,kind):
        values=[];current=set()
        if kind=='TRADES':
            last=self.archived_print_ids.get(symbol,'')
            for row in rows:
                if row['id']<=last:continue
                body=dict(row,venue=VENUE,symbol=symbol,native_channel='trade/v2')
                values.append((symbol+':'+row['id'],json.dumps(body,sort_keys=True)))
            category='kraken_native_execution'
        else:
            for row in rows:
                key=symbol+':'+row['id']+':'+sha256(json.dumps({k:v for k,v in row.items() if k!='available_at'},sort_keys=True).encode()).hexdigest()
                current.add(key)
                if key in self.archived_hours:continue
                channel='REST_TRADES_EXHAUSTED_H1' if row['id'].startswith('KRAKEN:EXHAUSTED_H1:') else 'OHLC/60'
                values.append((key,json.dumps(dict(row,venue=VENUE,symbol=symbol,native_channel=channel),sort_keys=True)))
            category='kraken_native_hour_quantity'
        if values:
            with self.r.database.transaction() as conn:
                conn.executemany('INSERT OR IGNORE INTO records(kind,id,body) VALUES(?,?,?)',[(category,key,body) for key,body in values])
        if kind=='TRADES' and rows:self.archived_print_ids[symbol]=rows[-1]['id']
        elif kind=='HOURS':
            self.archived_hours={k for k in self.archived_hours if not k.startswith(symbol+':')}|current

    def poll(self, binding):
        binding=project_binding(binding,PAIRS)
        if self.closed: return
        if binding != self.binding:
            self.disconnect(); self.binding = binding;self.weekly.binding=binding; self.next_start = 0
        if binding is None or self.r.database.path == ':memory:' or KINDS <= self.excluded: return
        if self.worker is None and monotonic() >= self.next_start:
            self.stop = Event(); self.state = 'PUBLIC_VENUE_CONNECTING'; self.error_type = None
            self.worker = Thread(target=self._run, args=(binding,), name='SFM-Kraken-read', daemon=False)
            self.worker.start()
        deadline=monotonic()+0.025
        while monotonic()<deadline:
            try: identity, kind, payload = self.results.get_nowait()
            except Empty: break
            if identity != self.binding: continue
            if kind == 'PAIRS':
                self.pairs = {s:v for s,v in payload.items() if s in dict(binding[1])}
                self.states = {p: 'UNAVAILABLE_BROKER_METADATA' if p not in dict(binding[1]) else 'WAITING_NATIVE_EXECUTIONS' if p in self.pairs else 'NOT_LISTED_BY_VENUE' for p in PAIRS}
                self.state = 'PUBLIC_VENUE_CONNECTED'
            elif kind == 'AUDIT': self.audit.append(payload)
            elif kind == 'PAIR_ERROR': self.states[payload[0]] = 'HOUR_HISTORY_UNAVAILABLE:'+payload[1]
            elif kind == 'ERROR':
                self.error_type = payload; self._withdraw(); self.state = 'PUBLIC_VENUE_UNAVAILABLE'
            elif kind in {'TRADES', 'HOURS','BOOK'}:
                try:
                    symbol, info, data, at, digest = payload
                    if kind=='BOOK':
                        bookinfo=dict(info,snapshot_hash=digest)
                        start=data['time'];end=stamp(min(instant(at),instant(start)+timedelta(microseconds=1)))
                        if instant(end)<=instant(start):continue
                        if (instant(self.r.clock())-instant(data['available_at'])).total_seconds()>5:continue
                        self._accept(symbol,bookinfo,(data,),at,'VENUE_L2_CHECKSUM_BOOK',start,end,data['id'].split(':')[-1])
                    elif kind == 'HOURS':
                        repairs=self.weekly.recovered_hours.get(symbol,{})
                        self._archive(symbol,data,'HOURS')
                        self.weekly.hour_inputs[symbol]=data
                        if repairs:data=tuple(repairs)+tuple(r for r in data if instant(r['time'])>=instant(repairs[-1]['end_time']))
                        self._accept(symbol, info, data, at, 'EXECUTED_BAR_QUANTITIES', data[0]['time'], data[-1]['end_time'], digest)
                    else:
                        start, end, rows = data
                        self._archive(symbol,rows,'TRADES')
                        self._accept(symbol, info, tuple({k:v for k,v in row.items() if k != 'aggressor'} for row in rows), at, 'TRADED_PRINTS', start, end, digest)
                        self._accept(symbol, info, rows, at, 'AGGRESSOR_PRINTS', start, end, digest)
                except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                    self.states[payload[0]] = 'VENUE_ADMISSION_REFUSED:'+type(exc).__name__
        if self.worker is not None and not self.worker.is_alive():
            self.worker.join(); self.worker = None; self._withdraw()
            self.state = 'PUBLIC_VENUE_UNAVAILABLE'; self.next_start = monotonic()+60
        if self.stop.is_set(): self._withdraw()
        elif self.state=='PUBLIC_VENUE_CONNECTED':self.weekly.poll(binding)

    def status(self):
        now=instant(self.r.clock())
        fresh={k:sorted(s for s in values if (k,s) in self.validity and now<=instant(self.validity[(k,s)])) for k,values in self.admitted.items()}
        return dict(state=self.state, provider=PROVIDER, venue=VENUE, pairs=dict(self.states),
                    admitted_pairs=fresh,history_state=self.history_state,weekly=self.weekly.status(),
                    publications=self.publications, worker_alive=bool(self.worker and self.worker.is_alive()),
                    error_type=self.error_type,coalesced_publications=self.results.coalesced,pending_publications=self.results.qsize(), requires_credentials=False, broker_fills=False,
                    market_wide_volume=False, strict_full_book=False,checksum_l2_depth=10,
                    live_publications_retained_per_pair_kind=16,normalized_native_observations_retained=True,
                    scope_note='Separate Kraken fiat venue executions/taker sides; not cTrader fills or consolidated FX. Hour totals require exact closed-bar coverage.')

    def close(self):
        self.closed = True; self.disconnect()
