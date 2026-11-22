"""Synthetic lifecycle controls only: recording transports, no broker contact.

Terminal history failures must remain failures without becoming cross-pair locks.
These tests do not qualify original market data or strict execution/book inputs.
"""
from copy import deepcopy
from queue import Full

import pytest

from test_connector_boundary import connected
from sfm_fx_new_age.connector.analytical_feed import ConnectedAnalyticalFeed
from sfm_fx_new_age.connector.broker_depth import PROVIDER
from sfm_fx_new_age.contracts.domain import PAIRS

FRAMES = ('W1', 'D1', 'H4', 'H1')
KINDS = {'BROKER_DEPTH', 'INTRABAR_PRICES', 'CFTC_REPORT', 'OFFICIAL_CALENDAR'}


def full_feed(connected, *, include=()):
    r, event = connected
    c = r.connector
    account = r.accounts.current
    state = c.native[(account.endpoint_class, account.account_id)]
    template = deepcopy(state['specs'][1])
    event('ProtoOASymbolsListRes', {
        'ctidTraderAccountId': account.account_id,
        'symbol': [dict(symbolId=i, symbolName=s, enabled=True)
                   for i, s in enumerate(PAIRS, 1)],
    })
    event('ProtoOASymbolByIdRes', {
        'ctidTraderAccountId': account.account_id,
        'symbol': [dict(template, symbolId=i) for i, _ in enumerate(PAIRS, 1)],
    })
    c.analytical_feed = ConnectedAnalyticalFeed(c, excluded_kinds=KINDS - set(include))
    c.start_market_feed()
    assert c.feed_status()['history_jobs'] == len(PAIRS) * len(FRAMES)
    return r, c, event


def history_states(r, c, *, overrides=None, default='COMPLETE'):
    intent = c.feed_intents[r.market.scope_id]
    for key, identity in intent['jobs'].items():
        job = r.database.get('backfill', identity)
        symbol, frame = key.split(':')
        job['status'] = (overrides or {}).get((symbol, frame), default)
        r.database.put('backfill', identity, job)


def history_reads(c):
    return [m for w in c.workers.values() for m in w.sent
            if m.get('name') == 'ProtoOAGetTrendbarsReq']


@pytest.mark.parametrize('pending', ['QUEUED', 'PARTIAL'])
def test_core_retains_only_pending_pair_dirty_work(connected, monkeypatch, pending):
    r, c, _ = full_feed(connected)
    history_states(r, c, overrides={('GBPUSD', f): pending for f in FRAMES})
    seen = []
    monkeypatch.setattr(r.analytics, 'refresh', seen.append)
    r._analytics_dirty = {'EURUSD', 'GBPUSD'}
    r.pump()
    assert seen == ['EURUSD']
    assert r._analytics_dirty == {'GBPUSD'}
    before = history_reads(c)
    history_states(r, c, overrides={('GBPUSD', f): 'FAILED' for f in FRAMES})
    r.pump()
    assert seen == ['EURUSD', 'GBPUSD']
    assert not r._analytics_dirty
    assert history_reads(c) == before  # Terminal failures are never blindly retried.
    assert c.feed_status()['failed_history_jobs'] == len(FRAMES)
    assert not r.database.orders()


def test_all_terminal_failures_release_analysis_without_claiming_history_success(connected, monkeypatch):
    r, c, _ = full_feed(connected)
    history_states(r, c, default='FAILED')
    seen = []
    monkeypatch.setattr(r.analytics, 'refresh', seen.append)
    r._analytics_dirty = set(PAIRS)
    for _ in PAIRS:
        r.pump()
    assert len(seen) == len(PAIRS) and set(seen) == set(PAIRS)
    status = c.feed_status()
    assert status['state'] == 'HISTORY_INCOMPLETE'
    assert status['completed_history_jobs'] == 0
    assert status['failed_history_jobs'] == len(PAIRS) * len(FRAMES)
    assert not status['pending_history_symbols'] and not status['pending_history_jobs']
    assert not r.database.orders()


@pytest.mark.parametrize('status', ['QUEUED', 'PARTIAL', 'COMPLETE', 'FAILED'])
def test_history_status_reports_actual_pair_local_work(connected, status):
    r, c, _ = full_feed(connected)
    history_states(r, c, overrides={('EURUSD', 'H1'): status})
    feed = c.feed_status()
    assert feed['history_by_pair']['EURUSD']['H1'] == status
    assert feed['pending_history_symbols'] == (['EURUSD'] if status in {'QUEUED', 'PARTIAL'} else [])
    assert feed['pending_history_jobs'] == (1 if status in {'QUEUED', 'PARTIAL'} else 0)


def test_tpo_schedules_independent_pairs_after_terminal_failure(connected):
    r, c, _ = full_feed(connected, include={'INTRABAR_PRICES'})
    history_states(r, c, overrides={('GBPUSD', f): 'PARTIAL' for f in FRAMES}
                   | {('EURUSD', 'H1'): 'FAILED'})
    feed = c.analytical_feed
    feed.poll()
    assert set(feed.jobs) == set(PAIRS) - {'GBPUSD'}
    first = dict(feed.jobs)
    assert all(r.database.get('native_quote_history_job', identity)['state'] == 'RUNNING'
               for identity in first.values())
    feed.poll()
    assert feed.jobs == first
    history_states(r, c, overrides={('EURUSD', 'H1'): 'FAILED'})
    feed.poll()
    assert set(feed.jobs) == set(PAIRS)
    assert all(feed.jobs[s] == identity for s, identity in first.items())
    assert c.feed_status()['failed_history_jobs'] == 1
    assert not r.database.orders()


def test_broker_depth_does_not_require_completed_candle_history(connected):
    r, c, event = full_feed(connected, include={'BROKER_DEPTH'})
    assert c.feed_status()['completed_history_jobs'] == 0
    feed = c.analytical_feed
    feed.poll()
    requests = [(key, v) for key, v in c.requests.items()
                if (v.get('context') or {}).get('broker_depth') == 'SUBSCRIBE']
    assert len(requests) == 1
    identity, request = requests[0]
    account = r.accounts.current
    event('ProtoOASubscribeDepthQuotesRes', {'ctidTraderAccountId': account.account_id}, request_id=identity)
    sid = r.market.spec(account.account_id, 'EURUSD').broker_symbol_id
    event('ProtoOADepthEvent', dict(ctidTraderAccountId=account.account_id, symbolId=sid,
          newQuotes=[dict(id='SYNTHETIC_BID', size='100000', bid='110100'),
                     dict(id='SYNTHETIC_ASK', size='200000', ask='110120')]))
    r.clock = lambda: '2026-11-05T12:00:00.001000Z'
    # The fixture injected a fixed clock into both owners; advance both.
    r.analytics.supplemental.clock = r.clock
    feed.poll()
    assert feed.depth.ack and feed.depth.publications == 1
    assert 'BROKER_DEPTH' in r.analytics.supplemental.snapshot('EURUSD', r.clock())
    assert 'VENUE_BOOK' not in r.analytics.supplemental.snapshot('EURUSD', r.clock())
    assert c.feed_status()['completed_history_jobs'] == 0
    c.disconnect()
    assert PROVIDER not in r.analytics.supplemental.providers
    assert not r.database.orders()


def test_depth_backpressure_defers_unsent_subscription_without_crashing(connected, monkeypatch):
    r, c, _ = full_feed(connected, include={'BROKER_DEPTH'})
    feed = c.analytical_feed
    identity = feed._identity()
    original = c.request
    calls = []

    def busy(endpoint, name, payload, **kwargs):
        if name == 'ProtoOASubscribeDepthQuotesReq':
            calls.append(name)
            raise Full('Synthetic read-only queue capacity')
        return original(endpoint, name, payload, **kwargs)

    monkeypatch.setattr(c, 'request', busy)
    feed.depth.poll(identity)
    assert not feed.depth.attempted and not feed.depth.ack
    assert set(feed.depth.states.values()) == {'WAITING_READ_CAPACITY'}
    monkeypatch.setattr(c, 'request', original)
    feed.depth.poll(identity)
    assert feed.depth.attempted
    requests = [v for v in c.requests.values()
                if (v.get('context') or {}).get('broker_depth') == 'SUBSCRIBE']
    assert len(requests) == 1 and len(calls) == 1
    feed.depth.fail(requests[0])
    feed.depth.poll(identity)
    assert len([v for v in c.requests.values()
                if (v.get('context') or {}).get('broker_depth') == 'SUBSCRIBE']) == 1
    assert set(feed.depth.states.values()) == {'SUBSCRIPTION_FAILED'}
    assert not r.database.orders()


def test_unauthenticated_feed_never_schedules_independent_inputs(connected):
    r, c, _ = full_feed(connected, include={'BROKER_DEPTH', 'INTRABAR_PRICES'})
    c.native[(r.accounts.current.endpoint_class, r.accounts.current.account_id)]['connected'] = False
    c.analytical_feed.poll()
    assert c.analytical_feed.binding is None and not c.analytical_feed.jobs
    assert not any((v.get('context') or {}).get('broker_depth') for v in c.requests.values())
    assert not r.analytics.supplemental.providers


@pytest.mark.parametrize('context', [None, {}, {'broker_depth': 'SUBSCRIBE', 'binding': 'OLD_SOURCE'}])
def test_depth_failure_ignores_unowned_requests_and_old_source(context, connected):
    r, c, _ = full_feed(connected, include={'BROKER_DEPTH'})
    depth = c.analytical_feed.depth
    depth.poll(c.analytical_feed._identity())
    depth.ack = True  # Synthetic lifecycle state only, not original-source proof.
    before = dict(depth.states)
    depth.fail(dict(context=context))
    assert depth.ack and depth.states == before


def test_native_pump_rotates_dirty_pairs_instead_of_starving_read_handling(connected, monkeypatch):
    r, c, _ = full_feed(connected)
    history_states(r, c)
    seen = []
    def busy_refresh(symbol):
        seen.append(symbol)
        r._analytics_dirty.update(PAIRS)
    monkeypatch.setattr(r.analytics, 'refresh', busy_refresh)
    r._analytics_dirty = set(PAIRS)
    for _ in PAIRS:
        before = len(seen)
        r.pump()
        assert len(seen) == before + 1
    assert set(seen) == set(PAIRS)
    assert r._analytics_dirty == set(PAIRS)


def test_failed_refresh_retains_its_pending_invalidation(connected, monkeypatch):
    r, c, _ = full_feed(connected)
    history_states(r, c)
    def failure(symbol):
        raise RuntimeError('Synthetic analytical failure')
    monkeypatch.setattr(r.analytics, 'refresh', failure)
    r._analytics_dirty = {'EURUSD'}
    with pytest.raises(RuntimeError, match='Synthetic analytical failure'):
        r.pump()
    assert r._analytics_dirty == {'EURUSD'}


def test_native_read_queue_wait_and_response_time_are_separate(connected):
    from time import monotonic
    r, event = connected
    c = r.connector
    account = r.accounts.current
    c.workers[account.endpoint_class].reports_sdk_admission = True
    identity = c.request(account.endpoint_class, 'ProtoOATraderReq',
                         dict(ctidTraderAccountId=account.account_id))
    c.requests[identity]['sent'] = monotonic() - 31
    c.poll()
    assert identity in c.requests  # Queued, not a thirty-second vendor timeout.
    c.handle(account.endpoint_class, dict(kind='READ_SDK_ACCEPTED', request_id=identity,
                                         accepted_monotonic=monotonic() - 31))
    c.poll()
    assert identity not in c.requests  # The original response budget is unchanged.
    assert not r.database.orders()


def test_unsent_native_read_wait_is_still_bounded(connected):
    from time import monotonic
    r, _ = connected
    c = r.connector
    account = r.accounts.current
    c.workers[account.endpoint_class].reports_sdk_admission = True
    identity = c.request(account.endpoint_class, 'ProtoOATraderReq',
                         dict(ctidTraderAccountId=account.account_id))
    c.requests[identity]['sent'] = monotonic() - 121
    c.poll()
    assert identity not in c.requests
    assert 'no blind retry' in c.reason.lower()


def test_wrong_endpoint_sdk_admission_cannot_restart_a_read_clock(connected):
    from time import monotonic
    r, _ = connected
    c = r.connector
    account = r.accounts.current
    c.workers[account.endpoint_class].reports_sdk_admission = True
    identity = c.request(account.endpoint_class, 'ProtoOATraderReq',
                         dict(ctidTraderAccountId=account.account_id))
    before = dict(c.requests[identity])
    c.handle('DEMO', dict(kind='READ_SDK_ACCEPTED', request_id=identity,
                          accepted_monotonic=monotonic()))
    assert c.requests[identity] == before
