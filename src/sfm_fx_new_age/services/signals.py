from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from sfm_fx_new_age.contracts.domain import Candidate, SignalState, instant, record
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.storage.database import Database, StateConflict


class SignalService:
    def __init__(self, db: Database, emit: Any, scope: Any, clock=None) -> None:
        self.db, self.emit, self.scope = db, emit, scope
        from sfm_fx_new_age.contracts.models import utc_now
        self.clock = clock or utc_now

    def key(self, signal_id: str) -> str:
        return json.dumps([self.scope(), signal_id], separators=(',', ':'))

    def propose(self, candidate: Candidate) -> dict[str, Any]:
        if self.scope() == 'UNBOUND' or candidate.scope_id not in {'UNBOUND', self.scope()}:
            raise ValueError('Candidate requires the selected account/source namespace')
        candidate = replace(candidate, scope_id=self.scope())
        key = self.key(candidate.signal_id)
        body = record(candidate); body['state'] = SignalState.QUEUED.value
        with self.db.transaction() as conn:
            row = conn.execute("SELECT body FROM records WHERE kind='signal' AND id=?", (key,)).fetchone()
            if row:
                previous = json.loads(row[0])
                if previous['state'] != 'QUEUED' or candidate.revision <= previous['revision']:
                    raise StateConflict('Only queued signals may receive a strictly newer revision')
                if any(previous[k] != body[k] for k in ('setup_id', 'symbol', 'origin')):
                    raise StateConflict('Stable signal identity cannot be rebound')
            self.db.write(conn, 'signal', key, body)
            self.db.write(conn, 'signal_revision', json.dumps([key, candidate.revision]), body)
        self.emit('CANDIDATE.PROPOSED', 'STRATEGY_RECIPE_HOST', body, Priority.P2, candidate.symbol)
        self._changed(body)
        return body

    def _changed(self, body: dict[str, Any]) -> None:
        from sfm_fx_new_age.contracts.analytics import digest
        self.db.put('signal_state_history', digest(body), dict(body,changed_at=self.clock()))
        self.emit('SIGNAL.SNAPSHOT', 'SIGNAL_VIEW_STORE', body, Priority.P2, body['signal_id'])
        self.emit('SIGNAL.QUEUE_SNAPSHOT', 'SIGNAL_QUEUE', {'signals': self.all(), 'scope_id': self.scope()}, Priority.P2, self.scope())

    def all(self) -> list[dict[str, Any]]:
        return [row for row in self.db.list('signal') if row.get('scope_id') == self.scope()]

    def get(self, signal_id: str) -> dict[str, Any] | None:
        return self.db.get('signal', self.key(signal_id))

    def cancel(self, signal_id: str) -> dict[str, Any]:
        return self._terminal(signal_id, 'CANCELED')

    def _terminal(self, signal_id: str, state: str) -> dict[str, Any]:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT body FROM records WHERE kind='signal' AND id=?", (self.key(signal_id),)).fetchone()
            if row is None:
                raise StateConflict('Signal not found')
            body = json.loads(row[0])
            if body['state'] != 'QUEUED':
                raise StateConflict('Only unissued queued signals may be cancelled or expired')
            body['state'] = state
            self.db.write(conn, 'signal', self.key(signal_id), body)
        self._changed(body)
        return body

    def cancel_all(self) -> int:
        count = 0
        for body in self.all():
            if body['state'] == 'QUEUED':
                self.cancel(body['signal_id']); count += 1
        return count

    def expire(self, now: str) -> int:
        count = 0
        for body in self.all():
            if body['state'] == 'QUEUED' and instant(body['expires_at']) <= instant(now):
                self._terminal(body['signal_id'], 'EXPIRED'); count += 1
        return count
