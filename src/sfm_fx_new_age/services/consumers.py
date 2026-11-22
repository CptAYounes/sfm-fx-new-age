"""Registered, owner-bound consumer control. Physical/P0 sources are never switch targets."""
from __future__ import annotations
from typing import Any, Callable

from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.storage.database import Database


class ConsumerService:
    def __init__(self, db: Database, emit: Callable) -> None:
        self.db, self.emit = db, emit
        self.owners: dict[str, dict[str, Any]] = {}

    def register(self, identity: str, owner: str, *, enabled: bool = True) -> None:
        if not identity.startswith(('analysis.', 'display.')) or identity in self.owners:
            raise ValueError('Unique analysis/display consumer required')
        saved = self.db.get('consumer', identity)
        self.owners[identity] = {'id': identity, 'owner': owner,
            'enabled': saved['enabled'] if saved else enabled, 'processed': 0, 'suppressed': 0}

    def enabled(self, identity: str) -> bool:
        if identity not in self.owners:
            raise ValueError('Unknown consumer owner')
        return self.owners[identity]['enabled']

    def set_enabled(self, identity: str, enabled: bool) -> dict[str, Any]:
        if type(enabled) is not bool or identity not in self.owners:
            raise ValueError('Registered consumer and boolean state required; required sources cannot be switched')
        self.owners[identity]['enabled'] = enabled
        body = dict(self.owners[identity])
        self.db.put('consumer', identity, body)
        self.emit('CONFIG.VERSION', 'LOCAL_CONFIG_STORE', {'consumer_id': identity, 'enabled': enabled}, Priority.P2)
        return body

    def consume(self, identity: str, callback: Callable, *args, **kwargs) -> Any:
        state = self.owners[identity]
        if not state['enabled']:
            state['suppressed'] += 1
            return None
        state['processed'] += 1
        return callback(*args, **kwargs)

    def rows(self) -> list[dict[str, Any]]:
        return [dict(self.owners[key]) for key in sorted(self.owners)]
