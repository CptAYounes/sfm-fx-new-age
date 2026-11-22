"""Executable offline acceptance, explicitly not real broker integration proof."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from sfm_fx_new_age.contracts.domain import BrokerOutcome, OrderState
from sfm_fx_new_age.contracts.enums import CommandStatus
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.services.orders import FixtureBroker
from .fixtures import FIXTURE_NOW, fixture_runtime


def run_checkpoint() -> dict[str, Any]:
    broker = FixtureBroker(OrderState.UNKNOWN)
    # Use project-independent ephemeral SQLite; no operator settings or credentials are touched.
    import os
    scratch = Path(os.environ.get('TMPDIR', str(Path.home()/'.hermes/cache/scratch')))
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='sfm-offline-check-', dir=scratch) as directory:
        path = Path(directory)/'state.sqlite3'
        runtime = fixture_runtime(path, broker=broker)
        account = runtime.accounts.current
        assert account is not None
        try:
            snapshots = [runtime.api(tab.tab_id).snapshot(sub.definition.subtab_id)
                         for tab in runtime.tabs for sub in tab.subtabs]
            assert len(snapshots) == 42
            payload = {'signal_id': 'FIXTURE-SIGNAL-1', 'revision': 1,
                       'user_initiated': True, 'acknowledge_research': True}
            first = runtime.api(4).command('4.1', 'ISSUE', payload)
            assert first.status is CommandStatus.ACCEPTED
            order = runtime.database.orders()[0]
            assert order['state'] == 'UNKNOWN'
            duplicate = runtime.api(4).command('4.1', 'ISSUE', payload)
            assert duplicate.status is CommandStatus.REJECTED
            assert len(broker.submissions) == 1
            assert not runtime.router.errors
            bar_count = len(runtime.database.list('bar'))
        finally:
            runtime.close()
        recovered = ApplicationRuntime(path, clock=lambda: FIXTURE_NOW, transport=broker)
        try:
            assert recovered.accounts.current is None
            recovered.accounts.select(account)
            broker.native[order['id']] = BrokerOutcome(OrderState.ACCEPTED_PENDING, 'FIXTURE-RECONCILED-1')
            final = recovered.orders.reconcile(order['id'])
            assert final['state'] == 'ACCEPTED_PENDING'
            assert len(broker.submissions) == 1
            assert recovered.api(1).snapshot('1.10').data['rows'][0]['id'] == final['id']
            assert recovered.api(4).snapshot('4.4').data['rows'][0]['id'] == final['id']
            assert recovered.api(4).command('4.1','CANCEL_ALL_UNISSUED').status is CommandStatus.ACCEPTED
            assert recovered.database.order(final['id'])['state'] == 'ACCEPTED_PENDING'
            assert not recovered.router.errors
            return {'ok': True, 'scope': 'OFFLINE_SYNTHETIC_FIXTURE_ONLY', 'tab_api_version': 1,
                    'main_tabs': 4, 'subtabs': len(snapshots), 'fixture_bars': bar_count,
                    'fixture_submissions': len(broker.submissions), 'duplicate_rejected': True,
                    'restart_reconciled': True, 'cross_tab_order_identity': True,
                    'local_cancel_preserves_broker_order': True, 'network_calls': 0,
                    'real_broker_orders': 0}
        finally:
            recovered.close()
