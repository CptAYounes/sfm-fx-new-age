"""Normal native Desktop, read-only broker SDK, genuine public NZDUSD source.

All four quantity methods, actual broker frames, recurring source acquisition,
new-epoch reconnect, first-observation preservation, expiry/withdrawal and joins.
No fixture observations, inferred aggressors, broker orders or source retiming.
"""
from pathlib import Path
from decimal import Decimal
from datetime import timedelta
from time import monotonic
import json, os, sqlite3, sys, traceback

PACKAGE = Path(os.environ['SFM_FXOPEN_PACKAGE']).resolve(strict=True)
sys.path.insert(0, str(PACKAGE))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from sfm_fx_new_age.__main__ import main
from sfm_fx_new_age.app import MainWindow
from sfm_fx_new_age.connector.original_capture import ReadOnlyCaptureSdk
from sfm_fx_new_age.connector.fxopen_reported import PROVIDER, VENUE, KINDS, SYMBOL
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import FRAMES, instant
from sfm_fx_new_age.contracts.public_projection_inputs import optional_projection_source
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.tab_data import DataRequest

KEYS = ('volume_displacement', 'effort_result', 'volume_profile', 'vwap_bands')


def run():
    out = Path(os.environ['SFM_FXOPEN_OUT']).resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    state = out / 'state'
    state.mkdir(mode=0o700)
    source = Path.home() / '.local/share/sfm-fx-new-age/state.sqlite3'
    reader = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    target = sqlite3.connect(state / 'state.sqlite3')
    try:
        reader.execute('PRAGMA query_only=ON')
        reader.backup(target)
    finally:
        target.close()
        reader.close()
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == 'xcb'
    proof = dict(result='FAIL', broker_mutations=0, normal_database_opened_for_write=False,
                 entrypoint='normal main() saved-session', synthetic_observations=0)
    runtime = None
    workers = []
    phase = 0
    started = monotonic()
    first_epoch = None
    first_seen = {}
    observed = {}
    envelopes = {}
    archive = []
    last_log = 0.
    base_publications = 0
    timer = QTimer()
    timer.setInterval(200)
    def save(name, body):
        (out / name).write_text(json.dumps(body, indent=2, default=str) + '\n')
    def inspect():
        nonlocal runtime, phase, first_epoch, last_log, base_publications, first_seen
        window = None
        try:
            if monotonic() - started > 300:
                raise TimeoutError('Native NZDUSD source/reconnect deadline')
            window = next((w for w in app.topLevelWidgets() if isinstance(w, MainWindow)), None)
            if window is None:
                return
            if runtime is None:
                runtime = window.runtime
                assert not runtime.connector.workers
                def factory(config):
                    worker = ReadOnlyCaptureSdk(config)
                    workers.append(worker)
                    return worker
                runtime.connector.worker_factory = factory
                def deny(*args, **kwargs):
                    proof['broker_mutations'] += 1
                    raise PermissionError('Read-only qualification')
                runtime.connector.submit = deny
                runtime.connector.cancel = deny
                for key in KEYS:
                    definition = next(v for v in METHODS if v.key == key)
                    result = runtime.api(3).command('3.1', 'ENABLE_RECIPE',
                        dict(recipe_id=definition.recipe_id, version=definition.version, enabled=True))
                    assert result.status.value == 'ACCEPTED'
                original_refresh = runtime.analytics.refresh
                def refresh(symbol):
                    values = runtime.analytics.supplemental.snapshot(symbol, runtime.clock())
                    result = original_refresh(symbol)
                    if symbol != SYMBOL:
                        return result
                    for frame in FRAMES:
                        for row in runtime.analytics.projections.read(symbol, frame):
                            key = row['strategy_id']
                            if key not in KEYS or row['state'] not in {'READY', 'NO_SETUP'} or row.get('metrics', {}).get('source_venue') != VENUE:
                                continue
                            kind = 'TRADED_PRINTS'
                            evidence = optional_projection_source(key, kind, values, frame)
                            if evidence is None or evidence['provider_id'] != PROVIDER or row['metrics']['source_evidence_hash'] != digest(evidence):
                                continue
                            metrics = row['metrics']
                            if row['state'] == 'NO_SETUP':
                                assert row['reason'] == 'Evaluated; no qualifying closed-bar pattern'
                                assert not any(row.get(geometry) for geometry in ('markers', 'zones', 'series'))
                            assert metrics['executed_volume'] and not metrics['known_aggressors']
                            assert not metrics['market_wide_volume'] and not metrics['broker_fill_claim']
                            assert metrics['interpretation_name'].startswith('FXOpen reported · ')
                            if key in {'volume_displacement', 'effort_result'}:
                                assert metrics['latest_bar_quantity_covered'] and metrics['latest_lookback_complete']
                                assert metrics['eligible_volume_bars'] > 0
                                if frame == 'W1':
                                    assert evidence['kind'] == 'EXECUTED_WEEK_QUANTITIES' and len(evidence['records']) == 21
                            elif key == 'vwap_bands':
                                total = sum((Decimal(v['quantity']) for v in evidence['records']), Decimal(0))
                                numerator = sum((Decimal(v['price']) * Decimal(v['quantity']) for v in evidence['records']), Decimal(0))
                                assert Decimal(metrics['quantity']) == total
                                assert abs(Decimal(metrics['vwap']) - numerator / total) < Decimal('1e-24')
                            else:
                                assert metrics['measurement'] == 'ACTUAL_EXECUTED_QUANTITY' and metrics['observed_bins'] > 0
                            observed[(key, frame)] = row
                            envelopes[evidence['kind']] = evidence
                    # Buy/Sell execution side is never promoted to taker evidence.
                    assert values.get('AGGRESSOR_PRINTS', {}).get('provider_id') != PROVIDER
                    assert values.get('VENUE_BOOK', {}).get('provider_id') != PROVIDER
                    return result
                runtime.analytics.refresh = refresh
            feed = runtime.connector.analytical_feed.reported_fx
            if monotonic() - last_log > 5:
                last_log = monotonic()
                with (out / 'phases.jsonl').open('a') as log:
                    log.write(json.dumps(dict(phase=phase, elapsed=round(monotonic() - started, 3),
                        status=feed.status(), lanes=len(observed))) + '\n')
            if runtime.connector.state in {'LOGIN_REQUIRED', 'APPLICATION_AUTH_FAILED', 'CONNECTION_FAILED'}:
                raise RuntimeError('Native broker read source unavailable')
            if phase == 2 and not runtime.connector.feed_intents:
                scope = runtime.connector.preferences.get('scope_id')
                context = runtime.accounts.sessions.get(scope)
                if context and runtime.connector.native.get((context.endpoint_class, context.account_id), {}).get('connected'):
                    assert runtime.api(4).command('4.5', 'SELECT_ACCOUNT', dict(scope_id=scope)).status.value == 'ACCEPTED'
                    assert runtime.api(2).command('2.3', 'START_MARKET_FEED', {}).status.value == 'ACCEPTED'
            authority = runtime.market.authority(SYMBOL)
            if authority is None:
                return
            required = {(key, frame) for key in KEYS for frame in FRAMES}
            if not required <= set(observed):
                return
            if phase == 0:
                first_epoch = authority['source_epoch']
                base_publications = feed.publications
                first_seen = {row['id']: row['available_at'] for row in envelopes['TRADED_PRINTS']['records']}
                phase = 1
                return
            if phase == 1:
                if feed.publications <= base_publications or set(feed.status()['fresh_kinds']) != KINDS:
                    return
                assert feed.tape is not None
                recurring = {row['id']: row['available_at'] for row in feed.tape.prints()}
                assert first_seen.keys() <= recurring.keys()
                assert all(recurring[key] == at for key, at in first_seen.items())
                proof['recurring_first_observation_clocks_preserved'] = True
                archive.extend(envelopes.values())
                save('first-layers.json', list(observed.values()))
                save('first-native-range-proofs.json', list(feed.audit))
                # Verify every exact broker week against retained actual prints.
                weekly = envelopes['EXECUTED_WEEK_QUANTITIES']
                for week in weekly['records']:
                    members = [row for row in feed.tape.prints() if instant(week['time']) <= instant(row['time']) < instant(week['end_time'])]
                    assert week['trade_count'] == len(members)
                    assert Decimal(week['quantity']) == sum((Decimal(v['quantity']) for v in members), Decimal(0))
                proof['independent_21_exact_broker_week_totals'] = True
                expiry = max(instant(value['valid_until']) for value in feed.current.values()) + timedelta(seconds=1)
                expired = runtime.analytics.supplemental.snapshot(SYMBOL, expiry.isoformat())
                assert all(expired.get(kind, {}).get('provider_id') != PROVIDER for kind in KINDS)
                proof['original_expiry_refused'] = True
                runtime.connector.disconnect()
                assert PROVIDER not in runtime.analytics.supplemental.providers and feed.worker is None
                proof['disconnect_withdrawn_and_joined'] = True
                observed.clear()
                envelopes.clear()
                phase = 2
                assert runtime.api(2).command('2.3', 'CONNECT', {}).status.value == 'ACCEPTED'
                return
            if phase == 2:
                if authority['source_epoch'] == first_epoch:
                    return
                assert all(value['source_epoch'] == authority['source_epoch'] for value in envelopes.values())
                returned = {row['id']: row['available_at'] for row in envelopes['TRADED_PRINTS']['records']}
                assert all(returned[key] == first_seen[key] for key in returned.keys() & first_seen.keys())
                proof['reconnect_first_observation_clocks_preserved'] = True
                current = runtime.api(1).query('1.5', DataRequest('chart', symbol=SYMBOL, timeframe='H1', as_of=runtime.clock()))
                layers = [row for row in current.get('strategy_layers', ()) if row['strategy_id'] in KEYS and row.get('metrics', {}).get('source_venue') == VENUE]
                if not {'volume_profile', 'vwap_bands'} <= {row['strategy_id'] for row in layers}:
                    return
                archive.extend(envelopes.values())
                save('second-layers.json', list(observed.values()))
                save('second-native-range-proofs.json', list(feed.audit))
                runtime.api(1).navigate('1.5', runtime.api(1).inspect(symbol=SYMBOL, timeframe='H1'))
                window.refresh_current(force=True)
                phase = 3
                return
            if phase == 3:
                if set(feed.status()['fresh_kinds']) != KINDS:
                    return
                panel = window._active_panel()
                panel.refresh()
                canvas = getattr(panel, 'canvas', None)
                if canvas is None:
                    return
                layers = [row for row in canvas.strategy_layers if row['strategy_id'] in KEYS and row.get('metrics', {}).get('source_venue') == VENUE]
                if not {'volume_profile', 'vwap_bands'} <= {row['strategy_id'] for row in layers}:
                    return
                canvas.set_projection_focus('vwap_bands')
                window.resize(1440, 960)
                app.processEvents()
                assert window.grab().save(str(out / 'native-nzdusd-chart.png'))
                window.feed_card.button.click()
                app.processEvents()
                dialog = window.feed_dialog
                if dialog is None:
                    return
                dialog.refresh()
                if 'FXOpen reported NZDUSD executions: available' not in dialog.analytical_status.text():
                    return
                dialog.layout().activate()
                dialog.adjustSize()
                app.processEvents()
                assert dialog.grab().save(str(out / 'native-nzdusd-status.png'))
                dialog.close()
                proof.update(result='PASS_FXOPEN_REPORTED_NZDUSD_NATIVE_DESKTOP_LIFECYCLE',
                    qualified_pairs=[SYMBOL], methods=list(KEYS), method_frame_lanes=len(required),
                    method_frame_outcomes=[dict(method=key, frame=frame, state=observed[(key, frame)]['state'])
                        for key, frame in sorted(required)],
                    no_setup_means_evaluated_without_fabricated_signal=True,
                    reconnect_new_epoch=True, recurring_publications=feed.publications,
                    native_chart_layers=len(layers), status_label_verified=True,
                    nzdusd_aggressor_qualified=False, strict_full_book_qualified=False, ctrader_fix_qualified=False,
                    source_status=feed.status(), elapsed_seconds=round(monotonic() - started, 3))
                timer.stop()
                window.close()
        except Exception as exc:
            proof.update(error_type=type(exc).__name__, phase_at_failure=phase,
                locations=[dict(file=Path(f.filename).name, line=f.lineno, function=f.name) for f in traceback.extract_tb(exc.__traceback__)])
            try:
                save('primary-failure.json', proof)
                if runtime is not None:
                    save('failed-source-status.json', runtime.connector.analytical_feed.reported_fx.status())
            finally:
                timer.stop()
                app.quit()
    QTimer.singleShot(0, inspect)
    timer.timeout.connect(inspect)
    timer.start()
    sys.argv = ['sfm-fx-new-age', '--state-dir', str(state)]
    try:
        code = main()
    finally:
        timer.stop()
        if runtime is not None:
            try:
                runtime.close()
            except Exception as exc:
                proof.update(result='FAIL', cleanup_error_type=type(exc).__name__)
            feed = runtime.connector.analytical_feed
            proof.update(runtime_closed=runtime.closed, fxopen_worker_joined=feed.reported_fx.worker is None,
                bitstamp_worker_joined=feed.native_book.worker is None, kraken_worker_joined=feed.venue.worker is None,
                weekly_worker_joined=feed.venue.weekly.worker is None,
                sdk_processes_stopped=all(not worker.process.is_alive() for worker in workers),
                denied_broker_writes=sum(worker.denied_writes for worker in workers),
                fixture_imports=[key for key in sys.modules if key.startswith('sfm_fx_new_age.testing')])
        save('original-envelopes.json', archive)
        save('acceptance.json', proof)
    origins = {key: str(Path(value.__file__).resolve()) for key, value in sys.modules.items()
               if key.startswith('sfm_fx_new_age') and getattr(value, '__file__', None)}
    assert origins and all(Path(value).is_relative_to(PACKAGE) for value in origins.values())
    save('module-origins.json', origins)
    print(json.dumps(proof, indent=2))
    assert code == 0 and proof['result'].startswith('PASS_')
    assert all(proof[key] for key in ('fxopen_worker_joined', 'bitstamp_worker_joined', 'kraken_worker_joined', 'weekly_worker_joined', 'sdk_processes_stopped'))
    assert not proof['broker_mutations'] and not proof['denied_broker_writes'] and not proof['fixture_imports']


if __name__ == '__main__':
    run()
