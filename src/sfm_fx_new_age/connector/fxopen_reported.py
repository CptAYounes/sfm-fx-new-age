"""Original FXOpen public reported executions, not a global FX or taker tape.

The provider's native trade_id may be zero or reused. Preserve it verbatim in
originals; never deduplicate by it or manufacture a positive native sequence.
Observation IDs below are explicitly LOCAL CONTENT ADDRESSES, not vendor IDs.
A full limit=0 range must exactly match two disjoint independently read ranges,
including multiplicity. Only that reported-public scope is called complete.
Buy/Sell is an execution-order side, NOT a documented aggressor classification.
"""
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json

from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape

PROVIDER = 'FXOPEN_PUBLIC_REPORTED_EXECUTIONS_V1'
VENUE = 'FXOPEN_TICKTRADER_REPORTED_FX_EXECUTIONS'
SYMBOL = 'NZDUSD'
KINDS = frozenset({'TRADED_PRINTS', 'EXECUTED_BAR_QUANTITIES', 'EXECUTED_WEEK_QUANTITIES'})
FIELDS = {'trade_id', 'price', 'base_volume', 'target_volume', 'trade_timestamp', 'type'}
MAX_ROWS = 12000
TTL = 120


def stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def milliseconds(value):
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = instant(value) - epoch
    return delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000


def from_ms(value):
    return stamp(datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=value))


def signature(row):
    return json.dumps(row, sort_keys=True, separators=(',', ':'), default=str)


def parse_range(raw, start, end, received_at):
    if type(start) is not int or type(end) is not int or not 0 < start < end <= milliseconds(received_at):
        raise ValueError('Exact closed millisecond request interval required')
    rows = json.loads(raw, parse_float=Decimal)
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError('Bounded original execution list required')
    previous = None
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('Exact native reported-execution fields required')
        at = row['trade_timestamp']
        if type(at) is not int or not start <= at < end or previous is not None and at < previous:
            raise ValueError('Native execution outside range or chronological regression')
        previous = at
        numbers = []
        for field in ('trade_id', 'price', 'base_volume', 'target_volume'):
            if isinstance(row[field], bool) or not isinstance(row[field], (Decimal, int)):
                raise ValueError('Original finite native numbers required')
            number = Decimal(row[field])
            if not number.is_finite():
                raise ValueError('Original finite native numbers required')
            numbers.append(number)
        identity, price, quantity, target = numbers
        if identity < 0 or identity != identity.to_integral_value() or min(price, quantity, target) <= 0:
            raise ValueError('Positive actual execution price/quantity; unchanged nonnegative native ID required')
        if abs(price * quantity - target) > Decimal('0.00000001') * max(Decimal(1), target):
            raise ValueError('Native base/target execution quantity contradiction')
        if row['type'] not in {'Buy', 'Sell'}:
            raise ValueError('Original execution-order side required, not inferred aggressor')
    return tuple(rows)


def addressed(rows, first_at):
    counts = Counter()
    result = []
    for row in rows:
        root = sha256(signature(row).encode()).hexdigest()
        occurrence = counts[root]
        counts[root] += 1
        identity = 'FXOPEN:LOCAL_ROW_SHA256:' + root + ':' + str(occurrence).zfill(5)
        result.append(dict(id=identity, time=from_ms(row['trade_timestamp']),
                           available_at=first_at, price=str(row['price']), quantity=str(row['base_volume'])))
    # This ordering is for the envelope's deterministic equal-clock contract;
    # original order and native IDs remain untouched in retained native arrays.
    return tuple(sorted(result, key=lambda row: (instant(row['time']), row['id'])))


@dataclass(frozen=True)
class ReportedTape:
    start: int
    end: int
    native: tuple
    available_at: str
    first_seen: dict
    proof: dict

    def prints(self):
        return tuple(dict(row, available_at=self.first_seen[row['id']])
                     for row in addressed(self.native, self.available_at))


def corroborate(full, left, right, start, middle, end, receipts):
    if len(receipts) != 3 or not start < middle < end:
        raise ValueError('Three original receipts and exact disjoint partition required')
    a = parse_range(full, start, end, receipts[0])
    b = parse_range(left, start, middle, receipts[1])
    c = parse_range(right, middle, end, receipts[2])
    if Counter(map(signature, a)) != Counter(map(signature, b + c)):
        raise ValueError('Public ranged-response multiplicity contradiction; source not admitted')
    available = max(receipts, key=instant)
    seen = {row['id']: receipts[0] for row in addressed(a, receipts[0])}
    proof = dict(model='FULL_LIMIT_ZERO_RANGE_EQUALS_TWO_DISJOINT_NATIVE_RANGES',
                 scope='ALL_EXECUTIONS_REPORTED_BY_THIS_PUBLIC_ENDPOINT_NOT_ALL_BROKER_OR_GLOBAL_TRADES',
                 start_ms=start, middle_ms=middle, end_exclusive_ms=end, rows=len(a),
                 original_sha256=[sha256(raw).hexdigest() for raw in (full, left, right)],
                 native_id_zero_or_reused=sum(Decimal(row['trade_id']) == 0 for row in a),
                 native_id_uniqueness_claim=False, native_sequence_claim=False,
                 local_id_scheme='NATIVE_ROW_CONTENT_SHA256_PLUS_DUPLICATE_OCCURRENCE_NOT_VENDOR_ID',
                 aggressor_proven=False, all_venue_execution_completeness_claim=False)
    return ReportedTape(start, end, a, available, seen, proof)


def extend(previous, current):
    """Replace the entire re-read suffix, preserving genuine multiplicity/clocks."""
    if previous is None:
        return current
    if not previous.start <= current.start <= previous.end <= current.end:
        raise ValueError('Covered overlapping source suffix required')
    native = tuple(row for row in previous.native if row['trade_timestamp'] < current.start) + current.native
    if len(native) > MAX_ROWS:
        raise ValueError('Reported execution retention budget exceeded')
    seen = dict(current.first_seen)
    for row in addressed(native, current.available_at):
        if row['id'] in previous.first_seen:
            seen[row['id']] = previous.first_seen[row['id']]
    proof = dict(current.proof, cached_prefix_original_root=sha256(signature(previous.proof).encode()).hexdigest(),
                 cached_prefix_observed_at=previous.available_at, combined_rows=len(native))
    return ReportedTape(previous.start, current.end, native, current.available_at, seen, proof)


def totals(tape, intervals, label):
    rows = tape.native
    times = [row['trade_timestamp'] for row in rows]
    prefix = [Decimal(0)]
    for row in rows:
        prefix.append(prefix[-1] + Decimal(row['base_volume']))
    result = []
    previous_end = None
    for start, end in intervals:
        lo, hi = milliseconds(start), milliseconds(end)
        if previous_end is not None and lo < previous_end:
            raise ValueError('Derived executed-quantity intervals overlap')
        previous_end = hi
        if not tape.start <= lo < hi <= tape.end:
            raise ValueError('No inferred zero or total outside corroborated reported interval')
        left, right = bisect_left(times, lo), bisect_left(times, hi)
        result.append(dict(id='FXOPEN:DERIVED_REPORTED_' + label + ':' + str(lo),
                           time=from_ms(lo), end_time=from_ms(hi), available_at=tape.available_at,
                           quantity=str(prefix[right] - prefix[left]), trade_count=right - left))
    return tuple(result)


def evidences(tape, scope, epoch, tick_size, weeks, *, excluded=(), revisions=None):
    if not tape.native:
        raise ValueError('No reported executions; do not fabricate an analytical profile')
    tick = Decimal(str(tick_size))
    if not tick.is_finite() or tick <= 0 or any(Decimal(row['price']) % tick for row in tape.native):
        raise ValueError('Original executed prices must align to unchanged broker chart grid')
    first_hour = (tape.start + 3599999) // 3600000 * 3600000
    last_hour = tape.end // 3600000 * 3600000
    hours = [(from_ms(lo), from_ms(lo + 3600000)) for lo in range(first_hour, last_hour, 3600000)]
    periods = [(bar['open_time'], bar['close_time']) for bar in weeks
               if tape.start <= milliseconds(bar['open_time']) < milliseconds(bar['close_time']) <= tape.end]
    records = {'TRADED_PRINTS': tape.prints(),
               'EXECUTED_BAR_QUANTITIES': totals(tape, hours, 'H1'),
               'EXECUTED_WEEK_QUANTITIES': totals(tape, periods, 'W1')}
    root = sha256(signature(tape.proof).encode()).hexdigest()
    reference = ('https://ttlivewebapi.fxopen.net/api/v2/coingecko/trades/NZDUSD'
                 '#reported-interval-proof=' + root + ';LOCAL_ROW_ADDRESSES_NOT_NATIVE_IDS;NO_AGGRESSOR_CLAIM')
    output = []
    for kind, values in records.items():
        if kind in excluded or not values:
            continue
        start = from_ms(tape.start) if kind == 'TRADED_PRINTS' else values[0]['time']
        end = from_ms(tape.end) if kind == 'TRADED_PRINTS' else values[-1]['end_time']
        key = (kind, start, end)
        revision = (revisions or {}).get(key, 0) + 1
        evidence = SupplementalEvidence(PROVIDER, kind, scope, epoch, SYMBOL, 'LIVE_OBSERVED',
            reference, VENUE, SYMBOL, 'SPOT_PAIR', 'EXECUTED_BASE_UNITS', start, end,
            tape.available_at, stamp(instant(tape.available_at) + timedelta(seconds=TTL)),
            True, values, {'tick_size': str(tick)} if kind == 'TRADED_PRINTS' else {}, revision=revision)
        validate_wire_shape(evidence)
        output.append(evidence)
    return tuple(output)
