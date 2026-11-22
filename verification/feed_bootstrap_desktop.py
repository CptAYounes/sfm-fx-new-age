"""Real saved-session Desktop with one withheld original response, then reconnect.

Uses a private SQLite backup, real original observations, normal main(), and
read-only SDK workers. No synthetic broker replies or market values are injected.
One genuine history response is withheld locally. No broker reply is invented.
"""
from pathlib import Path
from collections import Counter
from time import monotonic
import hashlib
import json
import os
import sqlite3
import sys
import traceback
from typing import Any

PACKAGE = Path(os.environ['SFM_BOOTSTRAP_PACKAGE']).resolve(strict=True)
sys.path.insert(0, str(PACKAGE))
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from sfm_fx_new_age.__main__ import main
from sfm_fx_new_age.app import MainWindow
from sfm_fx_new_age.connector.original_capture import ReadOnlyCaptureSdk
from sfm_fx_new_age.contracts.domain import PAIRS, record
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw


def write_new(path, body):
    with path.open('x') as stream:
        json.dump(body, stream, indent=2)
        stream.write('\n')


def run():
    out = Path(os.environ['SFM_BOOTSTRAP_OUT']).resolve()
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    source = Path(os.environ['SFM_BOOTSTRAP_DATABASE']).resolve(strict=True)
    state = out / 'state'
    state.mkdir(mode=0o700)
    connection = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    target = sqlite3.connect(state / 'state.sqlite3')
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.backup(target)
    finally:
        target.close()
        connection.close()
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == 'xcb'
    started = monotonic()
    proof: dict[str, Any] = dict(result='FAIL', entrypoint='sfm_fx_new_age.__main__.main',
                 private_copy_of_normal_state=True, normal_database_modified=False,
                 synthetic_observations=0, synthetic_broker_replies=0,
                 broker_mutations=0, strict_original_data_obligations_closed=False)
    runtime: Any = None
    workers = []
    withheld = []
    suppressed_responses = []
    first_epoch = None
    first_publications = 0
    partial = False
    partial_navigation = False
    chart_observations: dict[str, Any] = {}
    chart_observation_epoch = None
    timer = QTimer()
    timer.setInterval(250)

    class FaultControlledReadOnlySdk(ReadOnlyCaptureSdk):
        def send(self, body):
            payload = body.get('payload') or {}
            if (not withheld and body.get('kind') == 'READ'
                    and body.get('name') == 'ProtoOAGetTrendbarsReq'
                    and payload.get('period') == 'H1'):
                account = runtime.accounts.current
                assert account is not None
                native = runtime.connector.native[(account.endpoint_class, account.account_id)]
                symbol = native['symbols'].get(int(payload.get('symbolId', -1)))
                if symbol == 'EURUSD':
                    withheld.append(dict(request_id=body['request_id'], symbol=symbol,
                                         timeframe='H1', requested_at=runtime.clock(),
                                         outcome='LOCAL_ORIGINAL_RESPONSE_SUPPRESSION_NO_FAKE_REPLY'))
            return super().send(body)

        def poll(self, limit=128):
            rows = []
            for message in super().poll(limit):
                if (withheld and message.get('kind') == 'MESSAGE'
                        and message.get('name') == 'ProtoOAGetTrendbarsRes'
                        and message.get('request_id') == withheld[0]['request_id']):
                    assert not suppressed_responses
                    suppressed_responses.append(message)
                    write_new(out / 'withheld-original-response.json', message)
                    continue
                rows.append(message)
            return rows

    def source_checks():
        nonlocal chart_observation_epoch
        account = runtime.accounts.current
        assert account and account.authenticated
        current_epoch = runtime.connector.native[(account.endpoint_class, account.account_id)]['epoch']
        if current_epoch != chart_observation_epoch:
            chart_observations.clear()
            chart_observation_epoch = current_epoch
        for symbol in PAIRS:
            authority = runtime.market.authority(symbol)
            # Account auth can precede current-epoch symbol metadata. Ignore
            # that bootstrap interval; only matching new-source reads earn proof.
            if (not authority or authority['scope_id'] != account.scope_id
                    or authority['source_epoch'] != current_epoch
                    or authority['origin'] != 'LIVE_OBSERVED'):
                continue
            snap = runtime.analytics.snapshot(symbol)
            if not snap or snap['source_epoch'] != current_epoch:
                continue
            chart = thaw(runtime.api(1).query('1.3', DataRequest('chart', symbol=symbol, timeframe='H4')))
            layers = chart['strategy_layers']
            if len(layers) != len(METHODS) or not chart['rows']:
                continue
            assert all(r['source_epoch'] == current_epoch for r in chart['rows'])
            assert {r['strategy_id'] for r in layers} == {m.key for m in METHODS}
            assert all((r['scope_id'], r['source_epoch'], r['symbol'], r['timeframe'])
                       == (account.scope_id, current_epoch, symbol, 'H4') for r in layers)
            assert not any(r['state'] == 'ERROR' for r in layers)
            chart_observations[symbol] = dict(bars=len(chart['rows']), states=dict(Counter(r['state'] for r in layers)),
                projected_methods=len(layers), source_epoch=current_epoch, observed_at=runtime.clock())
        # Dirty pairs remain unavailable until their own refresh. Observe each
        # clean chart in turn; never weaken that guard to demand simultaneous
        # completion while a real seven-pair feed is continuously invalidating.
        if set(chart_observations) == set(PAIRS):
            return current_epoch, dict(chart_observations)
        return None

    def inspect():
        nonlocal runtime, first_epoch, first_publications, partial, partial_navigation
        window = next((w for w in app.topLevelWidgets() if isinstance(w, MainWindow)), None)
        try:
            if monotonic() - started > 280:
                raise TimeoutError('Bounded saved-session fault/reconnect verification deadline')
            if window is None:
                return
            if runtime is None:
                runtime = window.runtime
                assert not runtime.connector.workers and runtime.analytics.activity_alternatives
                assert not runtime.fixture_mode
                def factory(config):
                    worker = FaultControlledReadOnlySdk(config)
                    workers.append(worker)
                    return worker
                runtime.connector.worker_factory = factory
                def deny(*args, **kwargs):
                    proof['broker_mutations'] += 1
                    raise PermissionError('Bootstrap verification refuses broker writes')
                runtime.connector.submit = deny
                runtime.connector.cancel = deny
                # Stress the real startup path with every public method enabled,
                # but change only this private backup, never the normal choices.
                for method in METHODS:
                    response = runtime.api(3).command('3.1', 'ENABLE_RECIPE',
                        dict(recipe_id=method.recipe_id, version=method.version, enabled=True))
                    assert response.status.value == 'ACCEPTED'
                proof['enabled_method_count'] = len(METHODS)
                actual_refresh = runtime.analytics.refresh
                def observe_refresh(symbol):
                    result = actual_refresh(symbol)
                    if result is None:
                        return result
                    try:
                        # Observe delivery at the real completion edge, not a
                        # timer that can alias the round-robin scan cadence.
                        source_checks()
                        if partial_navigation and not partial and symbol == 'GBPUSD':
                            panel = window._active_panel()
                            assert panel is not None
                            panel.refresh()
                            if (panel.canvas.data_identity[2:] == ('GBPUSD', 'H4')
                                    and len(panel.canvas.strategy_layers) == len(METHODS)
                                    and not proof.get('partial_chart_captured')):
                                assert window.grab().save(str(out / 'partial-history-healthy-chart.png'))
                                proof['partial_chart_captured'] = dict(methods=len(METHODS), observed_at=runtime.clock())
                    except Exception as exc:
                        proof['delivery_probe_error'] = dict(error_type=type(exc).__name__, locations=[dict(
                            file=Path(f.filename).name, line=f.lineno, function=f.name)
                            for f in traceback.extract_tb(exc.__traceback__)])
                    return result
                runtime.analytics.refresh = observe_refresh
            if proof.get('delivery_probe_error'):
                raise RuntimeError('Original chart delivery probe failed')
            c = runtime.connector
            if c.state in {'LOGIN_REQUIRED', 'CONNECTION_FAILED', 'APPLICATION_AUTH_FAILED'}:
                raise RuntimeError('Saved-session native source unavailable')
            feed = c.feed_status()
            analytical: dict[str, Any] = c.analytical_feed.status()
            depth: dict[str, Any] = analytical['broker_depth']
            if depth['subscription_acknowledged'] and 'depth_ack_history_completed' not in proof:
                proof['depth_ack_history_completed'] = feed['completed_history_jobs']
            condition = ((feed['completed_history_jobs'] == 27 and feed['failed_history_jobs'] == 1)
                         if not partial else
                         (feed['completed_history_jobs'] == 28 and not feed['failed_history_jobs']))
            if not condition or feed['pending_history_jobs']:
                return
            if (len(analytical['tpo']) != len(PAIRS)
                    or any(value != 'ADMITTED' for value in analytical['tpo'].values())):
                return
            # Observe actual recurring fresh publications, not only subscription ACK.
            if depth['publications'] < first_publications + 14:
                return
            if any('BROKER_DEPTH' not in runtime.analytics.supplemental.snapshot(s, runtime.clock()) for s in PAIRS):
                return
            checked = source_checks()
            if checked is None:
                return
            epoch, charts = checked
            if not partial:
                if not partial_navigation:
                    window.resize(1440, 900)
                    envelope = runtime.api(1).inspect(symbol='GBPUSD', timeframe='H4')
                    runtime.api(1).navigate('1.4', envelope)
                    window.refresh_current(force=True)
                    partial_navigation = True
                    return
                if not proof.get('partial_chart_captured'):
                    return
                assert len(withheld) == len(suppressed_responses) == 1
                assert feed['history_by_pair']['EURUSD']['H1'] == 'FAILED'
                assert not runtime.market.bars('EURUSD', 'H1', runtime.clock(), epoch)
                h1 = runtime.analytics.projections.read('EURUSD', 'H1')
                assert len(h1) == len(METHODS)
                assert all(r['bars_used'] == 0 and r['state'] not in {'READY', 'NO_SETUP'} for r in h1)
                assert all(all(v == 'COMPLETE' for v in frames.values())
                           for s, frames in feed['history_by_pair'].items() if s != 'EURUSD')
                proof['partial_history'] = dict(feed=feed, analytical_feed=analytical, charts=charts,
                    absent_frame_projection_states=dict(Counter(r['state'] for r in h1)),
                    withheld_read=dict(withheld[0]), elapsed_seconds=round(monotonic() - started, 3))
                # Preserve original producer outputs before withdrawing the first epoch.
                write_new(out / 'partial-original-observations.json', dict(
                    depth_audit=list(c.analytical_feed.depth.audit),
                    h4_bars={s:[record(b) for b in runtime.market.bars(s, 'H4', runtime.clock(), epoch)] for s in PAIRS},
                    depth_evidence={s:runtime.analytics.supplemental.snapshot(s, runtime.clock())['BROKER_DEPTH'] for s in PAIRS}))
                QTest.mouseClick(window.feed_card.button, Qt.LeftButton)
                app.processEvents()
                dialog = window.feed_dialog
                assert dialog and dialog.isVisible()
                dialog.refresh()
                assert 'history incomplete' in dialog.status.text().lower()
                assert dialog.grab().save(str(out / 'partial-history-feed.png'))
                proof['partial_dialog_text'] = dialog.status.text()
                dialog.close()
                first_epoch = epoch
                first_publications = depth['publications']
                partial = True
                c.disconnect()
                assert not runtime.analytics.supplemental.providers
                c._startup_attempted = False
                c.resume_saved_session()
                return
            assert epoch != first_epoch
            assert len(withheld) == 1
            assert runtime.market.bars('EURUSD', 'H1', runtime.clock(), epoch)
            proof.update(result='PASS_REAL_DESKTOP_PARTIAL_HISTORY_AND_RECONNECT',
                         reconnected_history=dict(feed=feed, analytical_feed=analytical, charts=charts),
                         new_epoch_after_reconnect=True,
                         withheld_history_reads=len(withheld),
                         withheld_original_history_responses=len(suppressed_responses),
                         elapsed_seconds=round(monotonic() - started, 3))
            timer.stop()
            window.close()
            app.quit()
        except Exception as exc:
            if runtime is not None:
                proof['last_feed'] = runtime.connector.feed_status()
                proof['last_analytical_feed'] = runtime.connector.analytical_feed.status()
                proof['last_native_errors'] = list(runtime.connector.errors)
                proof['last_pending_request_types'] = dict(Counter(v['name'] for v in runtime.connector.requests.values()))
            proof.update(error_type=type(exc).__name__, error_locations=[dict(file=Path(f.filename).name, line=f.lineno, function=f.name)
                for f in traceback.extract_tb(exc.__traceback__)])
            timer.stop()
            if window:
                window.close()
            app.exit(1)

    QTimer.singleShot(0, inspect)
    timer.timeout.connect(inspect)
    timer.start()
    sys.argv = ['sfm-fx-new-age', '--state-dir', str(state)]
    code = main()
    timer.stop()
    if runtime is not None:
        auth = runtime.connector.auth_worker
        runtime.close()
        if auth and auth.is_alive():
            auth.join(timeout=35)
        proof.update(runtime_closed=runtime.closed,
                     auth_thread_stopped=not (auth and auth.is_alive()),
                     official_thread_stopped=not runtime.connector.analytical_feed.worker)
        connection = sqlite3.connect(state / 'state.sqlite3')
        try:
            proof['sqlite_quick_check'] = connection.execute('PRAGMA quick_check').fetchone()[0]
        finally:
            connection.close()
    origins = {key:str(Path(module.__file__).resolve()) for key, module in sys.modules.items()
               if key.startswith('sfm_fx_new_age') and getattr(module, '__file__', None)}
    proof.update(process_exit=code,
                 sdk_processes_stopped=all(not worker.process.is_alive() for worker in workers),
                 denied_broker_mutations=sum(worker.denied_writes for worker in workers),
                 fixture_imports=[key for key in sys.modules if key.startswith('sfm_fx_new_age.testing')],
                 product_module_origins=origins)
    assert origins and all(Path(path).is_relative_to(PACKAGE) for path in origins.values())
    write_new(out / 'desktop-receipt.json', proof)
    print(json.dumps({k:v for k,v in proof.items() if k not in {'product_module_origins', 'partial_history', 'reconnected_history'}}, indent=2), flush=True)
    assert code == 0 and proof['result'] == 'PASS_REAL_DESKTOP_PARTIAL_HISTORY_AND_RECONNECT'
    assert proof['sdk_processes_stopped'] and proof['official_thread_stopped'] and proof['auth_thread_stopped']
    assert not proof['broker_mutations'] and not proof['denied_broker_mutations'] and not proof['fixture_imports']
    return code


if __name__ == '__main__':
    raise SystemExit(run())
