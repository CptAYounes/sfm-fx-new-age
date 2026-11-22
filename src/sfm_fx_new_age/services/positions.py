"""Connector-fed read-only positions; order acceptance is never position evidence."""
from __future__ import annotations

from typing import Any, Callable

from sfm_fx_new_age.contracts.domain import AccountContext, instant, decimal, symbol_check
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.storage.database import Database


class PositionService:
    def __init__(self, db: Database, emit: Callable, account: Callable[[], AccountContext | None]) -> None:
        self.db, self.emit, self.account = db, emit, account

    def replace_snapshot(self, scope_id: str, rows: list[dict[str, Any]], *,
                         observed_at: str, origin: str, complete: bool,
                         sequence: int = 0, excluded_native_positions: int = 0) -> None:
        account = self.account()
        if account is None or account.scope_id != scope_id or account.origin.value != origin:
            raise ValueError('Position snapshot account/source mismatch')
        instant(observed_at)
        if type(complete) is not bool:
            raise ValueError('Explicit complete/incomplete snapshot state required')
        identities: set[str] = set()
        validated = []
        for row in rows:
            identity = row.get('position_id')
            if not isinstance(identity, str) or not identity or identity in identities:
                raise ValueError('Unique native position identities required')
            identities.add(identity)
            symbol_check(row.get('symbol', ''))
            if row.get('side') not in {'BUY', 'SELL'}:
                raise ValueError('Native position side required')
            validated.append({'position_id': identity, 'symbol': row['symbol'], 'side': row['side'],
                'units': str(decimal(row.get('units'), positive=True)),
                'entry_price': str(decimal(row.get('entry_price'), positive=True)),
                'scope_id': scope_id, 'origin': origin, 'observed_at': observed_at})
        body = {'scope_id': scope_id, 'rows': validated, 'observed_at': observed_at,
                'origin': origin, 'complete': complete}
        if type(sequence) is not int or sequence < 0 or type(excluded_native_positions) is not int or excluded_native_positions < 0:
            raise ValueError('Nonnegative native snapshot sequence/count required')
        if sequence: body['sequence'] = sequence
        if excluded_native_positions:
            body['excluded_native_positions'] = excluded_native_positions
            body['complete'] = False
        old = self.db.get('position_snapshot', scope_id)
        if old and instant(old['observed_at']) >= instant(observed_at):
            if old == body:
                return
            if not (instant(old['observed_at']) == instant(observed_at) and sequence > old.get('sequence', 0)):
                raise ValueError('Position snapshots cannot rewind or contradict the same observation')
        self.db.put('position_snapshot', scope_id, body)
        self.emit('POSITION.UPDATED', 'READONLY_POSITION_MONITOR', body, Priority.P1, scope_id)

    def snapshot(self) -> dict[str, Any] | None:
        account = self.account()
        return None if account is None else self.db.get('position_snapshot', account.scope_id)
