from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import json
import hashlib
from typing import Any, Callable

from sfm_fx_new_age.contracts.domain import PAIRS, AccountContext, Bar, Origin, Quote, SymbolSpec, instant, record, symbol_check
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.storage.database import Database, StateConflict

Emit = Callable[..., None]


def market_key(*parts: str) -> str:
    return json.dumps(parts, separators=(',', ':'))


class MarketService:
    """Selected-account namespace + source epochs + append-only causal bar revisions."""
    def __init__(self, database: Database, emit: Emit,
                 account: Callable[[], AccountContext | None]) -> None:
        self.db, self.emit, self.account = database, emit, account
        self.atr_calculations = 0

    @property
    def scope_id(self) -> str:
        context = self.account()
        return context.scope_id if context else 'UNBOUND'

    def _bind(self, value: Any) -> Any:
        account = self.account()
        if account is None:
            raise ValueError('Selected source account is required for market ingestion')
        if value.scope_id not in {'UNBOUND', account.scope_id}:
            raise ValueError('Market record belongs to a different account/source namespace')
        if hasattr(value, 'account_id') and value.account_id != account.account_id:
            raise ValueError('Market record account does not match selected source')
        if value.origin != account.origin:
            raise ValueError('Market record origin differs from selected source')
        return replace(value, scope_id=account.scope_id)

    def scoped_rows(self, kind: str) -> list[dict[str, Any]]:
        return [row for row in self.db.list(kind) if row.get('scope_id') == self.scope_id
                and ('symbol' not in row or row['symbol'] in PAIRS)]

    def authority(self, symbol: str) -> dict[str, Any] | None:
        if symbol not in PAIRS:
            return None
        return self.db.get('authority', market_key(self.scope_id, symbol))

    def activate_source(self, symbol: str, source_epoch: str, origin: str) -> None:
        symbol_check(symbol)
        account = self.account()
        if not source_epoch or account is None or Origin(origin) != account.origin:
            raise ValueError('Selected account, matching origin and source epoch required')
        body = {'symbol': symbol, 'source_epoch': source_epoch, 'origin': Origin(origin).value,
                'scope_id': account.scope_id}
        self.db.put('authority', market_key(account.scope_id, symbol), body)
        self.emit('DATA.AUTHORITY_CHANGE', 'SOURCE_AUTHORITY_ROUTER', body, Priority.P0, market_key(account.scope_id, symbol))

    def withdraw_source(self, symbol: str, source_epoch: str) -> None:
        """Revoke current authority; keep original bars/specifications as history."""
        current=self.authority(symbol)
        if not current or current['source_epoch']!=source_epoch:return
        key=market_key(self.scope_id,symbol)
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM records WHERE kind='authority' AND id=?",(key,))
        self.emit('DATA.AUTHORITY_CHANGE','SOURCE_AUTHORITY_ROUTER',
                  dict(symbol=symbol,scope_id=self.scope_id,source_epoch=source_epoch,available=False),Priority.P0,key)

    def set_spec(self, spec: SymbolSpec) -> None:
        spec = self._bind(spec)
        body = record(spec)
        self.db.put('spec', market_key(spec.scope_id, spec.account_id, spec.symbol), body)
        self.emit('SYMBOL.SPEC', 'FOREX_SYMBOL_REGISTRY', body, Priority.P1, market_key(spec.scope_id, spec.symbol))

    def spec(self, account_id: str, symbol: str) -> SymbolSpec | None:
        if symbol not in PAIRS:
            return None
        row = self.db.get('spec', market_key(self.scope_id, account_id, symbol))
        return None if row is None else SymbolSpec(**row)

    def ingest(self, bar: Bar) -> None:
        bar = self._bind(bar)
        prefix = (bar.scope_id, bar.symbol, bar.timeframe, bar.source_epoch, bar.open_time)
        key = market_key(*prefix, str(bar.revision))
        body = record(bar)
        with self.db.transaction() as conn:
            existing = conn.execute("SELECT body FROM records WHERE kind='bar' AND id=?", (key,)).fetchone()
            if existing:
                if json.loads(existing[0]) != body:
                    raise StateConflict('Historical revision is immutable; provide a newer revision')
                return
            # Same bar interval, monotone revision AND availability: old as-of results must stay unchanged.
            previous = self.db.market_rows(*prefix[:4], open_time=bar.open_time)
            if previous:
                latest = max(previous, key=lambda row: row['revision'])
                if (bar.revision <= latest['revision'] or instant(bar.available_at) <= instant(latest['available_at'])
                    or bar.close_time != latest['close_time'] or bar.origin.value != latest['origin']):
                    raise StateConflict('Correction must advance revision and availability without rebinding the bar')
            elif bar.revision != 1:
                raise StateConflict('First historical revision must be 1')
            self.db.write(conn, 'bar', key, body)
        self.emit('BAR.FINAL', 'BAR_AND_QUOTE_CACHE', body, Priority.P1, market_key(*prefix[:4]))

    def set_quote(self, quote: Quote) -> None:
        quote = self._bind(quote)
        key = market_key(quote.scope_id, quote.account_id, quote.symbol)
        previous = self.db.get('quote', key)
        # Ordering/sequence belongs to one connection epoch. A broker's first
        # market-closed snapshot can predate the prior connection's last tick.
        # Preserve its old provider time; never refresh it with reconnect time.
        if previous and previous['source_epoch'] != quote.source_epoch:
            previous = None
        if previous and instant(previous['available_at']) > instant(quote.available_at):
            raise ValueError('Out-of-order quote rejected')
        if previous and instant(previous['available_at']) == instant(quote.available_at):
            if quote.sequence and quote.sequence > previous.get('sequence', 0):
                pass # One-sided updates retain the older opposite-side freshness.
            elif previous != record(quote):
                raise ValueError('Conflicting quote at the same availability timestamp')
            else:
                return
        self.db.put('quote', key, record(quote))
        self.emit('QUOTE.LKV', 'BAR_AND_QUOTE_CACHE', record(quote), Priority.P1, market_key(quote.scope_id, quote.symbol))

    def invalidate_quote(self, account_id: str, symbol: str, source_epoch: str, observed_at: str, reason: str) -> None:
        """Withdraw an incoherent current quote without inventing replacement prices."""
        symbol_check(symbol);instant(observed_at)
        account=self.account();authority=self.authority(symbol)
        if not account or account.account_id!=account_id or not authority or authority['source_epoch']!=source_epoch:
            raise ValueError('Matching selected quote source required for invalidation')
        key=market_key(account.scope_id,account_id,symbol)
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM records WHERE kind='quote' AND id=?",(key,))
        self.emit('QUOTE.LKV','BAR_AND_QUOTE_CACHE',{'account_id':account_id,'scope_id':account.scope_id,
            'symbol':symbol,'source_epoch':source_epoch,'available_at':observed_at,'available':False,'reason':reason},
            Priority.P1,market_key(account.scope_id,symbol))

    def quote(self, account_id: str, symbol: str) -> Quote | None:
        if symbol not in PAIRS:
            return None
        row = self.db.get('quote', market_key(self.scope_id, account_id, symbol))
        return None if row is None else Quote(**row)

    def bars(self, symbol: str, timeframe: str, cutoff: str, source_epoch: str) -> tuple[Bar, ...]:
        symbol_check(symbol)
        versions: dict[str, Bar] = {}
        for row in self.db.market_rows(self.scope_id, symbol, timeframe, source_epoch):
            if (row['symbol'] != symbol or row['timeframe'] != timeframe or row['source_epoch'] != source_epoch
                or instant(row['available_at']) > instant(cutoff)):
                continue
            bar = Bar(**row)
            if bar.open_time not in versions or bar.revision > versions[bar.open_time].revision:
                versions[bar.open_time] = bar
        return tuple(sorted(versions.values(), key=lambda item: instant(item.open_time)))

    def context(self, symbol: str, cutoff: str, source_epoch: str, *, include_h1: bool = False) -> dict[str, Any]:
        frames = ('W1', 'D1', 'H4', 'H1') if include_h1 else ('W1', 'D1', 'H4')
        series = {frame: self.bars(symbol, frame, cutoff, source_epoch) for frame in frames}
        missing = [frame for frame, bars in series.items() if not bars and frame != 'H1']
        weekly = series['W1']
        atr = self.completed_atr(weekly)
        origins = {bar.origin.value for bars in series.values() for bar in bars}
        if len(origins) > 1:
            raise ValueError('Mixed-origin market context rejected')
        return {'symbol': symbol, 'cutoff': cutoff, 'source_epoch': source_epoch, 'scope_id': self.scope_id,
            'origin': next(iter(origins), 'UNKNOWN'),
            'bars': {frame: record(bars[-1]) if bars else None for frame, bars in series.items()},
            'w1_atr14': None if atr is None else str(atr),
            'missing': missing + ([] if atr is not None else ['W1_ATR14_WARMUP']),
            'optional_missing': ['H1'] if include_h1 and not series.get('H1') else []}

    def completed_atr(self, bars: tuple[Bar, ...], period: int = 14) -> Decimal | None:
        if not bars:
            return None
        # The actual as-of revision set, not display cutoff time, owns this checkpoint.
        fingerprint = hashlib.sha256(json.dumps([period, [record(bar) for bar in bars]],
                                                sort_keys=True).encode()).hexdigest()
        cached = self.db.get('atr_checkpoint', fingerprint)
        if cached is None:
            value = self.wilder_atr(bars, period)
            self.atr_calculations += 1
            cached = {'id': fingerprint, 'scope_id': bars[0].scope_id, 'symbol': bars[0].symbol,
                'source_epoch': bars[0].source_epoch, 'period': period,
                'last_bar': bars[-1].open_time, 'revision': bars[-1].revision,
                'value': None if value is None else str(value)}
            self.db.put('atr_checkpoint', fingerprint, cached)
        return None if cached['value'] is None else Decimal(cached['value'])

    @staticmethod
    def wilder_atr(bars: tuple[Bar, ...], period: int = 14) -> Decimal | None:
        if period < 1:
            raise ValueError('Positive ATR period required')
        if len(bars) < period + 1:
            return None
        ranges = [max(bar.high - bar.low, abs(bar.high - previous.close), abs(bar.low - previous.close))
                  for previous, bar in zip(bars, bars[1:])]
        atr = sum(ranges[:period], Decimal(0)) / Decimal(period)
        for value in ranges[period:]:
            atr = (atr * (period - 1) + value) / period
        return atr
