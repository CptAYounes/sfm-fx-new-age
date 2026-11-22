"""Shared-spine release tests: account/source isolation, causal corrections and tab updates."""
from dataclasses import replace
import json
import sqlite3

import pytest

from sfm_fx_new_age.contracts.domain import Bar, Candidate, Origin, record
from sfm_fx_new_age.contracts.enums import CommandStatus
from sfm_fx_new_age.contracts.registry import load_subtabs
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.storage.database import Database, StateConflict
from sfm_fx_new_age.testing.fixtures import FIXTURE_EPOCH, FIXTURE_NOW

P = {'signal_id': 'FIXTURE-SIGNAL-1', 'revision': 1,
     'user_initiated': True, 'acknowledge_research': True}


@pytest.mark.parametrize('definition', load_subtabs(), ids=lambda d: d.subtab_id)
def test_every_tab_receives_selection_notification_and_disposes(runtime, definition):
    if definition.subtab_id == '1.5':
        runtime.api(1).command('1.5', 'ENABLE_OPTIONAL_H1', {'enabled': True})
    api = runtime.api(definition.main_tab)
    snapshots = []
    baseline = runtime.router.metrics()['subscriber_count']
    release = api.subscribe_snapshots(definition.subtab_id, snapshots.append)
    assert len(snapshots) == 1
    assert runtime.api(1).command('1.1', 'SELECT_PAIR', {'symbol': 'GBPUSD'}).status is CommandStatus.ACCEPTED
    assert snapshots[-1].data['symbol'] == 'GBPUSD'
    assert snapshots[-1].version > snapshots[0].version
    release(); release()
    assert runtime.router.metrics()['subscriber_count'] == baseline
    count = len(snapshots)
    runtime.api(1).command('1.1', 'SELECT_PAIR', {'symbol': 'USDJPY'})
    assert len(snapshots) == count
    api.close(); api.close()
    with pytest.raises(RuntimeError): api.snapshot(definition.subtab_id)
    assert not runtime.router.errors


@pytest.mark.parametrize('definition', load_subtabs(), ids=lambda d: d.subtab_id)
def test_every_allowed_command_has_explicit_capability(runtime, definition):
    api = runtime.api(definition.main_tab)
    capabilities = api.capabilities(definition.subtab_id)
    assert tuple(item.name for item in capabilities) == definition.commands
    assert all(item.status in {'IMPLEMENTED', 'PARTIAL', 'SNAPSHOT_ONLY', 'NOT_IMPLEMENTED'} for item in capabilities)
    assert len(api.snapshot(definition.subtab_id).data['capabilities']) == len(capabilities)
    for item in capabilities:
        if item.status == 'NOT_IMPLEMENTED':
            assert api.command(definition.subtab_id, item.name).status is CommandStatus.NOT_IMPLEMENTED


@pytest.mark.parametrize('changes', [
    {'revision': True}, {'revision': '1'}, {'revision': 1.2}, {'user_initiated': 1},
    {'revision': 0}, {'authenticated': True}, {'origin': 'LIVE_OBSERVED'},
])
def test_issue_payload_is_exact_and_cannot_smuggle_authentication(runtime, changes):
    result = runtime.api(4).command('4.1', 'ISSUE', P | changes)
    assert result.status is CommandStatus.REJECTED
    assert runtime.orders.transport.submissions == []


@pytest.mark.parametrize('change', [
    {'account_id': 'OTHER'}, {'endpoint_class': 'OTHER'}, {'broker_id': 'OTHER'},
    {'origin': Origin.HISTORICAL_REPLAY},
])
def test_account_endpoint_and_broker_are_distinct_namespaces(runtime, change):
    original = runtime.accounts.current
    original_candidate = runtime.signals.get(P['signal_id'])
    result = runtime.api(4).command('4.1', 'ISSUE', P)
    assert result.status is CommandStatus.ACCEPTED
    order = runtime.database.orders()[0]
    other = replace(original, **change)
    runtime.accounts.select(other)
    assert runtime.market.bars('EURUSD', 'W1', FIXTURE_NOW, FIXTURE_EPOCH) == ()
    assert runtime.market.quote(other.account_id, 'EURUSD') is None
    assert runtime.market.spec(other.account_id, 'EURUSD') is None
    assert runtime.signals.all() == []
    assert runtime.market.authority('EURUSD') is None
    assert runtime.api(4).snapshot('4.3').data['rows'] == ()
    assert runtime.api(2).snapshot('2.4').data['rows'] == ()
    with pytest.raises(ValueError): runtime.orders.cancel_broker_order(order['id'], user_initiated=True)
    with pytest.raises(ValueError): runtime.orders.reconcile(order['id'])
    body = dict(original_candidate); body.pop('state')
    with pytest.raises(ValueError): runtime.signals.propose(Candidate(**body))
    assert runtime.api(4).command('4.5', 'SELECT_ACCOUNT', {'scope_id': original.scope_id}).status is CommandStatus.ACCEPTED
    assert runtime.market.quote(original.account_id, 'EURUSD') is not None
    assert runtime.api(4).snapshot('4.3').data['rows'][0]['id'] == order['id']


def test_same_signal_identity_in_different_endpoint_has_independent_reservation(runtime):
    original = runtime.accounts.current
    original_signal = dict(runtime.signals.get(P['signal_id'])); original_signal.pop('state')
    spec = runtime.market.spec(original.account_id, 'EURUSD')
    quote = runtime.market.quote(original.account_id, 'EURUSD')
    assert runtime.api(4).command('4.1', 'ISSUE', P).status is CommandStatus.ACCEPTED
    other = replace(original, endpoint_class='OTHER-ENDPOINT')
    runtime.accounts.select(other)
    runtime.market.activate_source('EURUSD', FIXTURE_EPOCH, other.origin.value)
    runtime.market.set_spec(replace(spec, scope_id='UNBOUND'))
    runtime.market.set_quote(replace(quote, scope_id='UNBOUND'))
    runtime.signals.propose(Candidate(**(original_signal | {'scope_id': 'UNBOUND'})))
    assert runtime.api(4).command('4.1', 'ISSUE', P).status is CommandStatus.ACCEPTED
    assert len(runtime.orders.transport.submissions) == 2
    assert len(runtime.database.orders()) == 2
    assert len({row['scope_id'] for row in runtime.database.orders()}) == 2
    assert len(runtime.api(4).snapshot('4.3').data['rows']) == 1


def test_ui_cannot_create_account_session_from_a_payload(runtime):
    assert runtime.api(4).command('4.5', 'SELECT_ACCOUNT', {'scope_id': 'invented'}).status is CommandStatus.REJECTED
    assert runtime.api(4).command('4.5', 'SELECT_ACCOUNT', {'scope_id': runtime.accounts.current.scope_id,
        'authenticated': True}).status is CommandStatus.REJECTED


def test_historical_correction_does_not_rewrite_asof_results(runtime):
    original = runtime.market.bars('EURUSD', 'W1', FIXTURE_NOW, FIXTURE_EPOCH)[-1]
    before = runtime.market.context('EURUSD', FIXTURE_NOW, FIXTURE_EPOCH)
    correction = replace(original, revision=2, available_at='2026-11-05T13:00:00Z', high=original.high + 1)
    runtime.market.ingest(correction)
    runtime.market.ingest(correction)  # exact redelivery is idempotent
    assert runtime.market.context('EURUSD', FIXTURE_NOW, FIXTURE_EPOCH) == before
    after = runtime.market.context('EURUSD', '2026-11-05T14:00:00Z', FIXTURE_EPOCH)
    assert after['w1_atr14'] != before['w1_atr14']
    assert after['bars']['W1']['revision'] == 2
    assert len(runtime.market.bars('EURUSD', 'W1', '2026-11-05T14:00:00Z', FIXTURE_EPOCH)) == 15
    with pytest.raises(StateConflict): runtime.market.ingest(replace(original, high=original.high + 1))
    with pytest.raises(StateConflict): runtime.market.ingest(replace(correction, revision=3))


def test_active_source_switch_revokes_issue_of_old_epoch(runtime):
    runtime.market.activate_source('EURUSD', 'NEW-EPOCH', Origin.SYNTHETIC_FIXTURE.value)
    assert runtime.api(4).command('4.1', 'ISSUE', P).status is CommandStatus.REJECTED
    row = next(row for row in runtime.api(2).snapshot('2.4').data['rows'] if row['symbol'] == 'EURUSD')
    assert row['freshness'] == 'INACTIVE_SOURCE'
    assert runtime.orders.transport.submissions == []


def test_parameter_and_bar_updates_reach_dependent_research_and_system_tabs(runtime):
    listeners = {key: [] for key in ('1.2', '2.8', '3.3', '3.10', '3.11')}
    apis = []
    for key, values in listeners.items():
        api = runtime.api(int(key[0])); apis.append(api)
        api.subscribe_snapshots(key, values.append, initial=False)
    from sfm_fx_new_age.contracts.analytics import ParameterDefinition
    runtime.catalogues.register_parameter(ParameterDefinition('shared.test','TEST_OWNER','string','string'))
    runtime.catalogues.set_parameter('shared.test', 'value', expected_version=0)
    assert all(listeners[key] for key in ('2.8', '3.10', '3.11'))
    original = runtime.market.bars('EURUSD', 'W1', FIXTURE_NOW, FIXTURE_EPOCH)[-1]
    runtime.market.ingest(replace(original, revision=2, available_at='2026-11-05T13:00:00Z'))
    assert listeners['1.2'] and listeners['3.3']
    for api in apis: api.close()
    assert not runtime.router.errors


def test_empty_position_rows_are_unknown_until_explicit_native_snapshot(runtime):
    account = runtime.accounts.current
    assert runtime.api(4).snapshot('4.6').status == 'UNKNOWN'
    runtime.api(4).command('4.1', 'ISSUE', P)
    assert runtime.api(4).snapshot('4.6').status == 'UNKNOWN'  # an order is not a position
    values = []
    release = runtime.api(4).subscribe_snapshots('4.6', values.append, initial=False)
    runtime.positions.replace_snapshot(account.scope_id, [], observed_at=FIXTURE_NOW,
                                       origin=account.origin.value, complete=False)
    assert values[-1].status == 'INCOMPLETE'
    runtime.positions.replace_snapshot(account.scope_id, [], observed_at='2026-11-05T12:01:00Z',
                                       origin=account.origin.value, complete=True)
    assert values[-1].status == 'LAST_KNOWN'
    assert values[-1].data['observation']['complete'] is True
    runtime.accounts.select(replace(account, broker_id='OTHER'))
    assert runtime.api(4).snapshot('4.6').status == 'UNKNOWN'
    release()


def test_native_position_rows_are_readonly_persistent_and_account_scoped(runtime):
    account = runtime.accounts.current
    row = {'position_id': 'FIXTURE-POS-1', 'symbol': 'EURUSD', 'side': 'BUY',
           'units': '1000', 'entry_price': '1.10'}
    runtime.positions.replace_snapshot(account.scope_id, [row], observed_at=FIXTURE_NOW,
        origin=account.origin.value, complete=True)
    snap = runtime.api(4).snapshot('4.6')
    assert snap.data['rows'][0]['position_id'] == row['position_id']
    with pytest.raises(TypeError): snap.data['rows'][0]['units'] = '0'
    with pytest.raises(ValueError):
        runtime.positions.replace_snapshot(account.scope_id, [row, row], observed_at='2026-11-05T12:01:00Z',
            origin=account.origin.value, complete=True)
    with pytest.raises(ValueError):
        runtime.positions.replace_snapshot(account.scope_id, [], observed_at='2026-11-05T11:00:00Z',
            origin=account.origin.value, complete=True)


def test_v1_database_migration_preserves_unbound_evidence_without_authentication(tmp_path):
    path = tmp_path/'v1.sqlite3'
    body = {'id': 'OLD', 'account_id': 'OLD-ACCOUNT', 'signal_id': 'OLD-SIGNAL', 'state': 'SUBMITTING'}
    original = json.dumps(body)
    with sqlite3.connect(path) as conn:
        conn.executescript('''CREATE TABLE orders (id TEXT PRIMARY KEY, account_id TEXT NOT NULL,
            signal_id TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(account_id,signal_id));
            PRAGMA user_version=1;''')
        conn.execute('INSERT INTO orders VALUES(?,?,?,?)', ('OLD', 'OLD-ACCOUNT', 'OLD-SIGNAL', original))
    db = Database(path)
    assert db.connection.execute('PRAGMA user_version').fetchone()[0] == 2
    assert db.order('OLD') == body
    assert db.connection.execute('SELECT body FROM orders').fetchone()[0] == original
    assert db.connection.execute('SELECT scope_id FROM orders').fetchone()[0] == 'LEGACY_UNBOUND:OLD-ACCOUNT'
    db.close()
    runtime = ApplicationRuntime(path)
    try:
        assert runtime.database.order('OLD')['state'] == 'UNKNOWN'
        assert runtime.accounts.current is None
        assert runtime.api(4).snapshot('4.3').data['rows'] == ()
        assert runtime.api(2).snapshot('2.10').data['rows'][0]['unscoped_legacy_orders'] == 1
        with pytest.raises(ValueError): runtime.orders.reconcile('OLD')
    finally: runtime.close()
