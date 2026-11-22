"""Bitstamp public full-order book, with native UUID predecessor continuity.

A locally incremented ordinal is never a venue sequence. Bootstrap requires
buffered native events, a full group=2 REST seed, and exact all-order parity
with a second independent full REST checkpoint. Any gap poisons the book.
This contains no authentication, execution or order-writing interface.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from uuid import UUID

from sfm_fx_new_age.contracts.domain import instant

PAIRS = ('EURUSD', 'GBPUSD')
KIND = 'VENUE_NATIVE_CHAIN_BOOK'
PROVIDER = 'BITSTAMP_PUBLIC_NATIVE_CHAIN_V1'
MAX_ORDERS = 20000
MAX_LEVELS = 4096


def micros(value):
    if not isinstance(value, str) or not value.isdigit():
        raise ValueError('Literal native microtimestamp required')
    return int(value)


def clock(value):
    return (datetime(1970, 1, 1, tzinfo=timezone.utc)
            + timedelta(microseconds=micros(value))).isoformat().replace('+00:00', 'Z')


def native_id(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError('Canonical native market event UUID required')
    return value


def snapshot_orders(raw):
    body = json.loads(raw)
    stamp = micros(body['microtimestamp'])
    orders = {}
    for side in ('bids', 'asks'):
        rows = body[side]
        if not isinstance(rows, list) or not rows or len(rows) > MAX_ORDERS:
            raise ValueError('Bounded complete group=2 two-sided snapshot required')
        for row in rows:
            if not isinstance(row, list) or len(row) != 3:
                raise ValueError('Individual native order IDs required')
            price, quantity = Decimal(row[0]), Decimal(row[1])
            identity = row[2]
            if (not isinstance(identity, str) or not identity.isdigit()
                    or identity in orders or not price.is_finite()
                    or not quantity.is_finite() or price <= 0 or quantity <= 0):
                raise ValueError('Unique native orders and positive quantities required')
            orders[identity] = (side, price, quantity)
    if len(orders) > MAX_ORDERS:
        raise ValueError('Native full order budget exceeded')
    return stamp, orders


class NativeChainBook:
    def __init__(self, symbol):
        if symbol not in PAIRS:
            raise ValueError('Production fiat instrument not qualified')
        self.symbol = symbol
        self.orders = {}
        self.cursor = self.predecessor = None
        self.time = self.received_at = None
        self.ready = False
        self.seed_hash = self.checkpoint_hash = self.chain_hash = None
        self.updates = 0
        self.seed_time = self.checkpoint_time = None

    def bootstrap(self, seed_raw, checkpoint_raw, events):
        self.ready = False
        seed_time, self.orders = snapshot_orders(seed_raw)
        check_time, target = snapshot_orders(checkpoint_raw)
        if seed_time >= check_time:
            raise ValueError('Later independent full checkpoint required')
        rows = [(m, received) for m, received in events
                if m.get('channel') == 'live_orders_' + self.symbol.lower()
                and m.get('event') in {'order_created', 'order_changed', 'order_deleted'}]
        before = [m for m, _ in rows if micros(m['data']['microtimestamp']) <= seed_time]
        if not before:
            raise ValueError('Buffered native event before seed required')
        # Validate the entire buffered market chain, including the seed boundary.
        for previous, current in zip(rows, rows[1:]):
            if native_id(current[0]['pre_event_id']) != native_id(previous[0]['event_id']):
                raise ValueError('Native predecessor gap in bootstrap')
            if micros(current[0]['data']['microtimestamp']) < micros(previous[0]['data']['microtimestamp']):
                raise ValueError('Native event clock regressed')
        self.cursor = native_id(before[-1]['event_id'])
        self.predecessor = native_id(before[-1]['pre_event_id'])
        self.seed_hash = sha256(seed_raw.encode()).hexdigest()
        self.checkpoint_hash = sha256(checkpoint_raw.encode()).hexdigest()
        self.chain_hash = self.seed_hash
        self.seed_time, self.checkpoint_time = seed_time, check_time
        self.time = clock(str(seed_time))
        checkpoint_seen = False
        self.updates = 0
        for message, received in rows:
            stamp = micros(message['data']['microtimestamp'])
            if stamp <= seed_time:
                continue
            if stamp > check_time and not checkpoint_seen:
                if self.orders != target:
                    raise ValueError('Full native order checkpoint mismatch')
                checkpoint_seen = True
            self._apply(message, received)
        if not checkpoint_seen:
            raise ValueError('Native event beyond checkpoint required')
        self.ready = True

    def _apply(self, message, received_at):
        if self.time is None or self.chain_hash is None:
            raise ValueError('Native seed required')
        if message.get('channel') != 'live_orders_' + self.symbol.lower():
            raise ValueError('Wrong native instrument')
        identity = native_id(message['event_id'])
        predecessor = native_id(message['pre_event_id'])
        if predecessor != self.cursor or identity == self.cursor:
            raise ValueError('Native market-event chain gap or replay')
        data = message['data']
        at = clock(data['microtimestamp'])
        if instant(at) < instant(self.time) or instant(at) > instant(received_at):
            raise ValueError('Future or regressed native event')
        order = data['id_str']
        price, quantity = Decimal(data['price_str']), Decimal(data['amount_str'])
        if (not isinstance(order, str) or not order.isdigit()
                or type(data['order_type']) is not int or data['order_type'] not in (0, 1)
                or not price.is_finite() or price <= 0 or not quantity.is_finite() or quantity < 0):
            raise ValueError('Invalid native order fields')
        side = 'bids' if data['order_type'] == 0 else 'asks'
        event = message['event']
        if event == 'order_created':
            if order in self.orders or quantity <= 0:
                raise ValueError('Duplicate or empty native create')
            self.orders[order] = (side, price, quantity)
        elif event in ('order_changed', 'order_deleted'):
            previous = self.orders.get(order)
            if previous is None or previous[:2] != (side, price):
                raise ValueError('Unknown or contradictory native order mutation')
            if event == 'order_deleted':
                del self.orders[order]
            elif quantity > 0:
                self.orders[order] = (side, price, quantity)
            else:
                raise ValueError('Zero native change requires explicit deletion')
        else:
            raise ValueError('Unsupported native event')
        if len(self.orders) > MAX_ORDERS:
            raise ValueError('Native full order budget exceeded')
        self.chain_hash = sha256((self.chain_hash + json.dumps(message, sort_keys=True,
                                     separators=(',', ':'))).encode()).hexdigest()
        self.predecessor, self.cursor = predecessor, identity
        self.time, self.received_at = at, received_at
        self.updates += 1

    def apply(self, message, received_at):
        was_ready = self.ready
        self.ready = False
        if not was_ready:
            raise ValueError('New independently corroborated bootstrap required')
        self._apply(message, received_at)
        self.ready = True

    def row(self, now):
        if not self.ready or self.received_at is None or self.time is None or self.cursor is None:
            return None
        if any(not 0 <= (instant(now) - instant(t)).total_seconds() <= 5
               for t in (self.time, self.received_at)):
            return None
        quantities = {s: defaultdict(Decimal) for s in ('bids', 'asks')}
        for side, price, quantity in self.orders.values():
            quantities[side][price] += quantity
        if any(not 0 < len(quantities[s]) <= MAX_LEVELS for s in quantities):
            raise ValueError('Full displayed price-level budget exceeded')
        if max(quantities['bids']) >= min(quantities['asks']):
            raise ValueError('Crossed native book refused')
        return dict(id='BITSTAMP:L3:' + self.cursor, time=self.time,
                    available_at=self.received_at, event_id=self.cursor,
                    pre_event_id=self.predecessor,
                    bids=[[str(p), str(q)] for p, q in sorted(quantities['bids'].items(), reverse=True)],
                    asks=[[str(p), str(q)] for p, q in sorted(quantities['asks'].items())])

    def parameters(self):
        return dict(native_sequence=True, sequence_model='NATIVE_UUID_PREDECESSOR_CHAIN',
                    full_book_complete=True, scope='FULL_PUBLIC_DISPLAYED_ORDERS',
                    clock_basis='NATIVE_EVENT_TIME', snapshot_hash=self.seed_hash,
                    checkpoint_hash=self.checkpoint_hash, chain_hash=self.chain_hash,
                    full_order_count=len(self.orders), checkpoint_verified=True)
