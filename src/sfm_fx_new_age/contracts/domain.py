"""Qt-neutral shared domain contracts. Decimal fields serialize as strings."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD")
FRAMES = ("W1", "D1", "H4", "H1")


class Origin(str, Enum):
    LIVE_OBSERVED = "LIVE_OBSERVED"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class SignalState(str, Enum):
    QUEUED = "QUEUED"
    ISSUE_RESERVED = "ISSUE_RESERVED"
    ISSUED = "ISSUED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class OrderState(str, Enum):
    RESERVED = "RESERVED"
    SUBMITTING = "SUBMITTING"
    ACCEPTED_PENDING = "ACCEPTED_PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


def instant(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Offset-aware timestamp required")
    return result


def decimal(value: Any, *, positive: bool = False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Finite decimal required") from None
    if not result.is_finite() or (positive and result <= 0):
        raise ValueError("Positive finite decimal required" if positive else "Finite decimal required")
    return result


def symbol_check(symbol: str) -> None:
    if symbol not in PAIRS:
        raise ValueError(f"Symbol outside the active six-pair universe: {symbol}")


def record(value: Any) -> dict[str, Any]:
    def convert(item: Any) -> Any:
        if isinstance(item, Decimal):
            return str(item)
        if isinstance(item, Enum):
            return item.value
        if isinstance(item, dict):
            return {k: convert(v) for k, v in item.items()}
        if isinstance(item, (tuple, list)):
            return [convert(v) for v in item]
        return item
    return convert(asdict(value))


@dataclass(frozen=True, slots=True)
class SymbolSpec:
    account_id: str
    symbol: str
    broker_symbol_id: int
    pip_size: Decimal
    tick_size: Decimal
    volume_min: Decimal
    volume_max: Decimal
    volume_step: Decimal
    units_per_lot: Decimal
    origin: Origin
    scope_id: str = 'UNBOUND'

    def __post_init__(self) -> None:
        symbol_check(self.symbol)
        if not self.account_id or self.broker_symbol_id < 1:
            raise ValueError("Account and broker symbol ID required")
        object.__setattr__(self, "origin", Origin(self.origin))
        for field in ("pip_size", "tick_size", "volume_min", "volume_max", "volume_step", "units_per_lot"):
            object.__setattr__(self, field, decimal(getattr(self, field), positive=True))
        if self.volume_max < self.volume_min:
            raise ValueError("Invalid volume bounds")

    def validate_order(self, price: Decimal, units: Decimal) -> None:
        price, units = decimal(price, positive=True), decimal(units, positive=True)
        if price % self.tick_size != 0:
            raise ValueError("Limit price is off the broker tick grid")
        if not self.volume_min <= units <= self.volume_max or (units - self.volume_min) % self.volume_step:
            raise ValueError("Volume violates broker min/max/step")


@dataclass(frozen=True, slots=True)
class Bar:
    symbol: str
    timeframe: str
    open_time: str
    close_time: str
    available_at: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    source_epoch: str
    origin: Origin
    scope_id: str = 'UNBOUND'
    revision: int = 1
    quote_basis: str = 'UNKNOWN'
    construction: str = 'NATIVE_OBSERVED'
    tick_volume: int | None = None

    def __post_init__(self) -> None:
        symbol_check(self.symbol)
        if self.timeframe not in FRAMES or not self.source_epoch:
            raise ValueError("Supported timeframe and source epoch required")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError('Positive integer historical revision required')
        if self.tick_volume is not None and (type(self.tick_volume) is not int or self.tick_volume < 0):
            raise ValueError('Native tick volume must be a nonnegative integer or unknown')
        if self.quote_basis not in {'BID', 'ASK', 'MID', 'UNKNOWN'} or self.construction not in {'NATIVE_OBSERVED', 'CANONICAL_BID_TICKS'}:
            raise ValueError('Explicit supported bar price/construction contract required')
        if not instant(self.open_time) < instant(self.close_time) <= instant(self.available_at):
            raise ValueError("Completed bars require open < close <= availability")
        for field in ("open", "high", "low", "close"):
            object.__setattr__(self, field, decimal(getattr(self, field), positive=True))
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("Invalid OHLC geometry")
        object.__setattr__(self, "origin", Origin(self.origin))


@dataclass(frozen=True, slots=True)
class Quote:
    account_id: str
    symbol: str
    bid: Decimal
    ask: Decimal
    available_at: str
    source_epoch: str
    origin: Origin
    scope_id: str = 'UNBOUND'
    bid_at: str | None = None
    ask_at: str | None = None
    sequence: int = 0

    def __post_init__(self) -> None:
        symbol_check(self.symbol)
        object.__setattr__(self, "bid", decimal(self.bid, positive=True))
        object.__setattr__(self, "ask", decimal(self.ask, positive=True))
        object.__setattr__(self, "origin", Origin(self.origin))
        instant(self.available_at)
        if self.ask < self.bid or not self.source_epoch or not self.account_id:
            raise ValueError("Invalid quote")
        if type(self.sequence) is not int or self.sequence < 0: raise ValueError('Nonnegative quote sequence required')
        if (self.bid_at is None) != (self.ask_at is None): raise ValueError('Both side timestamps required together')
        if self.bid_at is not None and self.ask_at is not None:
            if instant(self.available_at) != min(instant(self.bid_at), instant(self.ask_at)):
                raise ValueError('Quote freshness must use the oldest bid/ask observation')


@dataclass(frozen=True, slots=True)
class AccountContext:
    account_id: str
    endpoint_class: str
    currency: str
    authenticated: bool
    trading_scope: bool
    origin: Origin
    account_type: str = "UNKNOWN"
    broker_id: str = 'UNSPECIFIED'

    def __post_init__(self) -> None:
        if not self.account_id or not self.endpoint_class or not self.currency:
            raise ValueError("Account identity, endpoint and currency required")
        object.__setattr__(self, "origin", Origin(self.origin))
        if type(self.authenticated) is not bool or type(self.trading_scope) is not bool:
            raise ValueError("Authentication and scope must be booleans")

    @property
    def scope_id(self) -> str:
        import json
        return json.dumps([self.broker_id, self.endpoint_class, self.account_id, self.origin.value], separators=(',', ':'))


@dataclass(frozen=True, slots=True)
class Candidate:
    signal_id: str
    setup_id: str
    revision: int
    symbol: str
    side: str
    entry_price: Decimal
    invalidation_price: Decimal
    units: Decimal
    expires_at: str
    available_at: str
    source_epoch: str
    origin: Origin
    profile: str = "RESEARCH_ONLY"
    scope_id: str = 'UNBOUND'
    market_candidate_id: str | None = None
    market_candidate_revision: int | None = None
    source_candidate_hash: str | None = None
    variant_id: str | None = None

    def __post_init__(self) -> None:
        symbol_check(self.symbol)
        object.__setattr__(self, "origin", Origin(self.origin))
        for field in ("entry_price", "invalidation_price", "units"):
            object.__setattr__(self, field, decimal(getattr(self, field), positive=True))
        if self.side not in {"BUY", "SELL"} or type(self.revision) is not int or self.revision < 1 or not self.signal_id or not self.setup_id:
            raise ValueError("Candidate identity, revision and side required")
        if (self.side == "BUY" and self.invalidation_price >= self.entry_price) or (
            self.side == "SELL" and self.invalidation_price <= self.entry_price
        ):
            raise ValueError("Invalid candidate risk geometry")
        if instant(self.expires_at) <= instant(self.available_at) or not self.source_epoch:
            raise ValueError("Candidate expiry and source required")
        if self.profile not in {"RESEARCH_ONLY", "CONFIGURED"}:
            raise ValueError("Unknown profile classification")
        binding=(self.market_candidate_id,self.market_candidate_revision,self.source_candidate_hash,self.variant_id)
        if any(value is not None for value in binding) and (not all(binding) or type(self.market_candidate_revision) is not int
            or self.market_candidate_revision<1 or len(self.source_candidate_hash or '')!=64):
            raise ValueError('Complete typed analytical binding required')


@dataclass(frozen=True, slots=True)
class BrokerOutcome:
    state: OrderState
    broker_order_id: str | None = None
    position_id: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", OrderState(self.state))
        if self.state not in {OrderState.REJECTED, OrderState.UNKNOWN} and not self.broker_order_id:
            raise ValueError("Native order identity required for confirmed broker state")
