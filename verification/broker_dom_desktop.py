"""Native original cTrader DOM qualification; no fixtures or broker mutations.

Normal main()/saved-session startup, strict genuine-data mode, unfiltered
normal producers. Seven-pair broker calculations and actual mixed-source chart
projections are distinguished; no full native-book/aggressor promotion.
"""
from pathlib import Path
from decimal import Decimal
from datetime import timedelta
from time import monotonic
from typing import Any
import json, os, sqlite3, sys, traceback

PACKAGE = Path(os.environ['SFM_DOM_PACKAGE']).resolve(strict=True)
sys.path.insert(0, str(PACKAGE))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from sfm_fx_new_age.__main__ import main
from sfm_fx_new_age.app import MainWindow
from sfm_fx_new_age.connector.original_capture import ReadOnlyCaptureSdk
from sfm_fx_new_age.connector.broker_depth import PROVIDER
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES, instant
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.public_projection_inputs import optional_projection_source
from sfm_fx_new_age.contracts.public_strategies import BY_KEY
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.tabs.tab3.public_algorithms import evaluate
from sfm_fx_new_age.tabs.tab3.public_features import Features


def run():
    out = Path(os.environ['SFM_DOM_OUT']).resolve()
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
    proof: dict[str, Any] = dict(result='FAIL', broker_mutations=0, normal_database_opened_for_write=False,
        entrypoint='normal main() saved-session --strict-genuine-data',
        public_producers_filtered=False, synthetic_observations=0,
        strict_native_full_book_qualified=False, nzdusd_aggressor_qualified=False, ctrader_fix_qualified=False)
    runtime = None
    workers = []
    observed, broker_witnesses, originals, source_inputs = {}, {}, {}, {}
    native_events = []
    phase, first_epoch, base_publications = 0, None, 0
    first_receipts = {}
    started, last_log = monotonic(), 0.
    required = {(s, f) for s in PAIRS for f in FRAMES}
    timer = QTimer()
    timer.setInterval(200)

    def save(name, body):
        (out / name).write_text(json.dumps(body, indent=2, default=str) + '\n')

    def finish_native(window):
        assert runtime is not None and runtime.connector.analytical_feed is not None
        if proof['result'].startswith('PASS_'):
            return
        panel = window._active_panel()
        if getattr(panel, 'frame', None) != 'H1':
            return
        # An inspection pins a historical cutoff. Use the normal Current-source
        # control before testing live DOM, never retime that old cutoff/data.
        if panel.context:
            panel.clear_inspection()
        panel.refresh()
        canvas = getattr(panel, 'canvas', None)
        if canvas is None or canvas.data_identity[2:] != ('NZDUSD', 'H1'):
            return
        layers = [row for row in canvas.strategy_layers if row['strategy_id'] == 'dom_imbalance']
        if len(layers) != 1 or not layers[0].get('metrics', {}).get('genuine_displayed_depth'):
            return
        pair_status = runtime.connector.analytical_feed.depth.status()['pairs']
        assert isinstance(pair_status, dict)
        if not all(v == 'OBSERVED_BROKER_DEPTH' for v in pair_status.values()):
            return
        canvas.set_projection_focus('dom_imbalance')
        window.resize(1440, 960)
        window.layout().activate()
        assert window.grab().save(str(out / 'native-nzdusd-broker-dom.png'))
        window.feed_card.button.click()
        dialog = window.feed_dialog
        dialog.refresh()
        if 'strict genuine-data mode' not in dialog.analytical_status.text() or 'broker DOM: 7/7 fresh receipts' not in dialog.analytical_status.text():
            dialog.close()
            return
        dialog.adjustSize()
        dialog.layout().activate()
        assert dialog.grab().save(str(out / 'native-broker-dom-status.png'))
        dialog.close()
        proof.update(result='PASS_GENUINE_BROKER_DOM_STRICT_MODE_NATIVE_LIFECYCLE',
            qualified_pairs=list(PAIRS), actual_chart_lanes_per_epoch=len(required),
            pure_broker_calculation_lanes_per_epoch=len(required), reconnect_new_epoch=True,
            native_nzdusd_broker_chart=True, native_status_all_seven_fresh=True,
            chart_cutoff_mode='CURRENT_SOURCE_AT_REAL_PROJECTION_COMPLETION_NOT_PINNED_STALE_CUTOFF',
            selected_chart_kinds={s: observed[(s,'H1')]['metrics']['source_kind'] for s in PAIRS},
            elapsed_seconds=round(monotonic()-started, 3))
        timer.stop()
        # Let the synchronous core calculation return before its owner closes.
        QTimer.singleShot(0, window.close)

    def inspect():
        nonlocal runtime, phase, first_epoch, base_publications, first_receipts, last_log
        window = None
        try:
            if monotonic() - started > 300:
                raise TimeoutError('Native original broker-DOM lifecycle deadline')
            window = next((w for w in app.topLevelWidgets() if isinstance(w, MainWindow)), None)
            if window is None:
                return
            if runtime is None:
                runtime = window.runtime
                assert not runtime.connector.workers
                assert runtime.analytics.activity_alternatives is False
                def factory(config):
                    worker = ReadOnlyCaptureSdk(config)
                    workers.append(worker)
                    return worker
                runtime.connector.worker_factory = factory
                def deny(*args, **kwargs):
                    proof['broker_mutations'] += 1
                    raise PermissionError('Read-only DOM qualification')
                runtime.connector.submit = deny
                runtime.connector.cancel = deny
                definition = BY_KEY['dom_imbalance']
                result = runtime.api(3).command('3.1', 'ENABLE_RECIPE',
                    dict(recipe_id=definition.recipe_id, version=definition.version, enabled=True))
                assert result.status.value == 'ACCEPTED'
                depth = runtime.connector.analytical_feed.depth
                original_handle = depth.handle
                def handle(endpoint, name, body, request):
                    before = depth.events
                    answer = original_handle(endpoint, name, body, request)
                    if depth.events != before:
                        assert len(native_events) < 5000
                        symbol = depth.ids[int(body['symbolId'])]
                        native_events.append(dict(session=depth.session, symbol=symbol,
                            received_at=depth.received[symbol], payload=dict(body)))
                    return answer
                depth.handle = handle
                projection = runtime.analytics.projections
                original_refresh = projection.refresh
                def refresh(inputs, results):
                    answer = original_refresh(inputs, results)
                    symbol, epoch = inputs['symbol'], inputs['authority']['source_epoch']
                    if not all(inputs['bars'][frame] for frame in FRAMES):
                        return answer
                    values = inputs.get('optional_evidence', {})
                    for frame in FRAMES:
                        selected = optional_projection_source('dom_imbalance', 'VENUE_BOOK', values, frame)
                        for row in projection.read(symbol, frame):
                            if row['strategy_id'] != 'dom_imbalance' or row['state'] != 'READY':
                                continue
                            m = row['metrics']
                            if selected is None or m.get('source_evidence_hash') != digest(selected):
                                continue
                            assert row['source_epoch'] == epoch and row['scope_id'] == inputs['scope_id']
                            assert not m.get('alternative') and not m['executed_volume']
                            if selected['kind'] == 'BROKER_DEPTH':
                                assert m['genuine_displayed_depth'] and not m['strict_native_full_book_qualified']
                                assert row['classification'] == 'BROKER_SCOPED_DISPLAYED_DEPTH_NOT_EXECUTED_VOLUME'
                            observed[(symbol, frame)] = row
                            originals[digest(selected)] = thaw(selected)
                    broker = values.get('BROKER_DEPTH')
                    if broker is not None:
                        assert broker['provider_id'] == PROVIDER and broker['origin'] == 'LIVE_OBSERVED'
                        for frame in FRAMES:
                            minimal = {k: thaw(inputs[k]) for k in ('scope_id', 'authority', 'symbol', '_evaluation_at', 'spec')}
                            minimal.update(frame=frame, activity_alternatives=False, optional_evidence={'BROKER_DEPTH': thaw(broker)})
                            bar = thaw(inputs['bars'][frame][-1])
                            output = evaluate('dom_imbalance', Features([bar], ()), minimal, {})
                            m = output['metrics']
                            assert m['genuine_displayed_depth'] and m['alternative'] is False
                            assert m['source_evidence_hash'] == digest(broker)
                            bids, asks = broker['records'][-1]['bids'][:5], broker['records'][-1]['asks'][:5]
                            buy = sum((Decimal(q) for p, q in bids), Decimal(0))
                            sell = sum((Decimal(q) for p, q in asks), Decimal(0))
                            assert Decimal(m['imbalance']) == (buy-sell)/(buy+sell)
                            broker_witnesses[(symbol, frame)] = dict(inputs=minimal, bar=bar, output=output)
                        originals[digest(broker)] = thaw(broker)
                    if phase == 3 and symbol == 'NZDUSD':
                        finish_native(window)
                    return answer
                projection.refresh = refresh
            feed = runtime.connector.analytical_feed
            depth = feed.depth
            if monotonic() - last_log > 5:
                last_log = monotonic()
                with (out / 'phases.jsonl').open('a') as log:
                    log.write(json.dumps(dict(phase=phase, elapsed=round(monotonic()-started, 3),
                        dom=depth.status(), chart_lanes=len(observed), broker_lanes=len(broker_witnesses)))+'\n')
            if runtime.connector.state in {'LOGIN_REQUIRED', 'APPLICATION_AUTH_FAILED', 'CONNECTION_FAILED'}:
                raise RuntimeError('Native broker read source unavailable')
            if phase == 2 and not runtime.connector.feed_intents:
                scope = runtime.connector.preferences.get('scope_id')
                context = runtime.accounts.sessions.get(scope)
                if context and runtime.connector.native.get((context.endpoint_class, context.account_id), {}).get('connected'):
                    assert runtime.api(4).command('4.5', 'SELECT_ACCOUNT', dict(scope_id=scope)).status.value == 'ACCEPTED'
                    assert runtime.api(2).command('2.3', 'START_MARKET_FEED', {}).status.value == 'ACCEPTED'
            authority = runtime.market.authority('NZDUSD')
            if authority is None or set(observed) != required or set(broker_witnesses) != required:
                return
            if phase == 0:
                first_epoch = authority['source_epoch']
                base_publications = depth.publications
                first_receipts = dict(depth.received)
                phase = 1
                return
            if phase == 1:
                if depth.publications <= base_publications or any(instant(depth.received.get(s, first_receipts[s])) <= instant(first_receipts[s]) for s in PAIRS):
                    return
                latest = {s: runtime.analytics.supplemental.snapshot(s, runtime.clock()).get('BROKER_DEPTH') for s in PAIRS}
                if not all(latest.values()):
                    return
                for symbol, evidence in latest.items():
                    cutoff = (instant(evidence['valid_until']) + timedelta(microseconds=1)).isoformat()
                    assert 'BROKER_DEPTH' not in runtime.analytics.supplemental.snapshot(symbol, cutoff)
                proof['original_receipt_expiry_refused'] = True
                proof['all_seven_recurring_native_receipts'] = True
                save('first-chart-layers.json', list(observed.values()))
                save('first-broker-witnesses.json', list(broker_witnesses.values()))
                runtime.connector.disconnect()
                assert PROVIDER not in runtime.analytics.supplemental.providers and not depth.books
                assert all('BROKER_DEPTH' not in runtime.analytics.supplemental.snapshot(s, runtime.clock()) for s in PAIRS)
                proof['disconnect_withdraws_broker_authority'] = True
                observed.clear()
                broker_witnesses.clear()
                phase = 2
                assert runtime.api(2).command('2.3', 'CONNECT', {}).status.value == 'ACCEPTED'
                return
            if phase == 2:
                if authority['source_epoch'] == first_epoch:
                    return
                assert all(row['source_epoch'] == authority['source_epoch'] for row in observed.values())
                assert all(value['inputs']['authority']['source_epoch'] == authority['source_epoch'] for value in broker_witnesses.values())
                save('second-chart-layers.json', list(observed.values()))
                save('second-broker-witnesses.json', list(broker_witnesses.values()))
                runtime.api(1).navigate('1.5', runtime.api(1).inspect(symbol='NZDUSD', timeframe='H1'))
                window.refresh_current(force=True)
                phase = 3
                return
            if phase == 3:
                finish_native(window)
        except Exception as exc:
            proof.update(error_type=type(exc).__name__, phase_at_failure=phase,
                locations=[dict(file=Path(f.filename).name, line=f.lineno, function=f.name) for f in traceback.extract_tb(exc.__traceback__)])
            try:
                save('primary-failure.json', proof)
            finally:
                timer.stop()
                app.quit()
    QTimer.singleShot(0, inspect)
    timer.timeout.connect(inspect)
    timer.start()
    sys.argv = ['sfm-fx-new-age', '--state-dir', str(state), '--strict-genuine-data']
    code = None
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
            proof.update(runtime_closed=runtime.closed,
                owned_workers_joined=all(worker is None for worker in (feed.worker,feed.reported_fx.worker,
                    feed.native_book.worker,feed.venue.worker,feed.venue.weekly.worker)),
                sdk_processes_stopped=all(not w.process.is_alive() for w in workers),
                denied_broker_writes=sum(w.denied_writes for w in workers),
                fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
        save('native-depth-events.json', native_events)
        save('original-envelopes.json', list(originals.values()))
        save('acceptance.json', proof)
    origins = {key: str(Path(value.__file__).resolve()) for key,value in sys.modules.items()
        if key.startswith('sfm_fx_new_age') and getattr(value, '__file__', None)}
    assert origins and all(Path(p).is_relative_to(PACKAGE) for p in origins.values())
    save('module-origins.json', origins)
    print(json.dumps(proof, indent=2))
    assert code == 0 and proof['result'].startswith('PASS_')
    assert proof['owned_workers_joined'] and proof['sdk_processes_stopped']
    assert not proof['broker_mutations'] and not proof['denied_broker_writes'] and not proof['fixture_imports']


if __name__ == '__main__':
    run()
