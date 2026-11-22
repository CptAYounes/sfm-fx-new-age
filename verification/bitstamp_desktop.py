"""Normal native main(), original public L3, read-only SDK and isolated state.

No fixture inputs, original-time retiming, broker mutations or private API.
Focused acceptance of the two genuinely listed native-chain fiat books only.
"""
from pathlib import Path
from decimal import Decimal
from datetime import timedelta
from time import monotonic
import hashlib, json, os, sqlite3, sys, traceback

PACKAGE = Path(os.environ['SFM_BITSTAMP_PACKAGE']).resolve(strict=True)
sys.path.insert(0, str(PACKAGE))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from sfm_fx_new_age.__main__ import main
from sfm_fx_new_age.app import MainWindow
from sfm_fx_new_age.connector.original_capture import ReadOnlyCaptureSdk
from sfm_fx_new_age.connector.bitstamp_book import PROVIDER, KIND, PAIRS
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import FRAMES, instant
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.tab_data import DataRequest


def run():
    out=Path(os.environ['SFM_BITSTAMP_OUT']).resolve()
    out.mkdir(mode=0o700,parents=True,exist_ok=False)
    state=out/'state';state.mkdir(mode=0o700)
    source=Path.home()/'.local/share/sfm-fx-new-age/state.sqlite3'
    reader=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    target=sqlite3.connect(state/'state.sqlite3')
    try:
        reader.execute('PRAGMA query_only=ON');reader.backup(target)
    finally:target.close();reader.close()
    app=QApplication.instance() or QApplication([])
    assert app.platformName()=='xcb'
    proof=dict(result='FAIL',broker_mutations=0,normal_database_opened_for_write=False,
               entrypoint='normal main() saved-session',synthetic_observations=0)
    runtime=None;workers=[];phase=0;started=monotonic();first_epoch=None
    observed={};envelopes={};archive=[];last_log=0.;base_publications=0
    timer=QTimer();timer.setInterval(200)
    def save(name,body):
        (out/name).write_text(json.dumps(body,indent=2,default=str)+'\n')
    def inspect():
        nonlocal runtime,phase,first_epoch,last_log,base_publications
        window=None
        try:
            if monotonic()-started>210:raise TimeoutError('Native L3 startup/reconnect deadline')
            window=next((w for w in app.topLevelWidgets() if isinstance(w,MainWindow)),None)
            if window is None:return
            if runtime is None:
                runtime=window.runtime
                assert not runtime.connector.workers
                def factory(config):
                    worker=ReadOnlyCaptureSdk(config);workers.append(worker);return worker
                runtime.connector.worker_factory=factory
                def deny(*a,**kw):
                    proof['broker_mutations']+=1;raise PermissionError('Read-only qualification')
                runtime.connector.submit=deny;runtime.connector.cancel=deny
                definition=next(v for v in METHODS if v.key=='dom_imbalance')
                result=runtime.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=definition.recipe_id,version=definition.version,enabled=True))
                assert result.status.value=='ACCEPTED'
                original_refresh=runtime.analytics.refresh
                def refresh(symbol):
                    values=runtime.analytics.supplemental.snapshot(symbol,runtime.clock())
                    result=original_refresh(symbol)
                    evidence=values.get(KIND)
                    if evidence is not None and evidence['provider_id']==PROVIDER:
                        for frame in FRAMES:
                            for row in runtime.analytics.projections.read(symbol,frame):
                                if (row['strategy_id']=='dom_imbalance' and row['state']=='READY'
                                    and row.get('metrics',{}).get('source_evidence_hash')==digest(evidence)):
                                    metrics=row['metrics'];book=evidence['records'][-1]
                                    buy=sum(Decimal(v[1]) for v in book['bids'][:5]);sell=sum(Decimal(v[1]) for v in book['asks'][:5])
                                    assert Decimal(metrics['imbalance'])==(buy-sell)/(buy+sell)
                                    assert metrics['native_sequence'] and metrics['full_book_complete'] and metrics['checkpoint_verified']
                                    assert metrics['sequence_model']=='NATIVE_UUID_PREDECESSOR_CHAIN'
                                    assert metrics['native_event_id']==book['event_id'] and not metrics['executed_volume']
                                    observed[(symbol,frame)]=row;envelopes[symbol]=evidence
                    return result
                runtime.analytics.refresh=refresh
            feed=runtime.connector.analytical_feed.native_book
            if monotonic()-last_log>5:
                last_log=monotonic()
                with (out/'phases.jsonl').open('a') as log:
                    log.write(json.dumps(dict(phase=phase,elapsed=round(monotonic()-started,3),status=feed.status(),lanes=len(observed)))+'\n')
            if runtime.connector.state in {'LOGIN_REQUIRED','APPLICATION_AUTH_FAILED','CONNECTION_FAILED'}:
                raise RuntimeError('Native broker read source unavailable')
            if phase==2 and not runtime.connector.feed_intents:
                scope=runtime.connector.preferences.get('scope_id');context=runtime.accounts.sessions.get(scope)
                if context and runtime.connector.native.get((context.endpoint_class,context.account_id),{}).get('connected'):
                    assert runtime.api(4).command('4.5','SELECT_ACCOUNT',dict(scope_id=scope)).status.value=='ACCEPTED'
                    assert runtime.api(2).command('2.3','START_MARKET_FEED',{}).status.value=='ACCEPTED'
            authority=runtime.market.authority('EURUSD')
            if authority is None:return
            required={(s,f) for s in PAIRS for f in FRAMES}
            if not required<=set(observed):return
            if phase==0:
                first_epoch=authority['source_epoch'];base_publications=feed.publications;phase=1;return
            if phase==1:
                if set(feed.status()['fresh_pairs'])!=set(PAIRS):return
                if feed.publications<base_publications+4:return
                archive.extend(envelopes.values());save('first-layers.json',list(observed.values()))
                # Analytical refresh may legitimately trail a newer admitted
                # public event. Test expiry of the actual latest admission,
                # not an older input retained for calculation-math proof.
                expiry=max(instant(e['valid_until']) for e in feed.current.values())+timedelta(seconds=1)
                assert KIND not in runtime.analytics.supplemental.snapshot('EURUSD',expiry.isoformat())
                proof['original_expiry_refused']=True
                runtime.connector.disconnect()
                assert PROVIDER not in runtime.analytics.supplemental.providers and feed.worker is None
                proof['disconnect_withdrawn_and_joined']=True
                observed.clear();envelopes.clear();phase=2
                assert runtime.api(2).command('2.3','CONNECT',{}).status.value=='ACCEPTED'
                return
            if phase==2:
                if authority['source_epoch']==first_epoch:return
                assert all(e['source_epoch']==authority['source_epoch'] for e in envelopes.values())
                current=runtime.api(1).query('1.5',DataRequest('chart',symbol='EURUSD',timeframe='H1',as_of=runtime.clock()))
                layers=[v for v in current.get('strategy_layers',[]) if v['strategy_id']=='dom_imbalance' and v.get('metrics',{}).get('source_venue')=='BITSTAMP_SPOT_FIAT']
                if not layers:return
                archive.extend(envelopes.values());save('second-layers.json',list(observed.values()))
                runtime.api(1).navigate('1.5',runtime.api(1).inspect(symbol='EURUSD',timeframe='H1'))
                window.refresh_current(force=True);phase=3;return
            if phase==3:
                if set(feed.status()['fresh_pairs'])!=set(PAIRS):return
                panel=window._active_panel();panel.refresh()
                canvas=getattr(panel,'canvas',None)
                if canvas is None:return
                layers=[v for v in canvas.strategy_layers if v['strategy_id']=='dom_imbalance' and v.get('metrics',{}).get('source_venue')=='BITSTAMP_SPOT_FIAT']
                if not layers:return
                canvas.set_projection_focus('dom_imbalance');window.resize(1440,960);app.processEvents()
                assert window.grab().save(str(out/'native-chain-chart.png'))
                window.feed_card.button.click();app.processEvents()
                dialog=window.feed_dialog
                if dialog is None:return
                dialog.refresh()
                if 'Bitstamp full public order book:' not in dialog.analytical_status.text():return
                if 'Bitstamp full public order book: 2/7 fresh' not in dialog.analytical_status.text():return
                if set(feed.status()['fresh_pairs'])!=set(PAIRS):return
                dialog.layout().activate();dialog.adjustSize();app.processEvents()
                assert dialog.grab().save(str(out/'native-chain-status.png'));dialog.close()
                proof.update(result='PASS_BITSTAMP_NATIVE_CHAIN_DESKTOP_LIFECYCLE',
                    qualified_pairs=list(PAIRS),pair_frame_lanes=len(required),reconnect_new_epoch=True,
                    independent_imbalance_math=True,recurring_publications=feed.publications,
                    native_chart_layers=len(layers),status_label_verified=True,
                    unsupported_full_book_pairs=['USDJPY','USDCHF','USDCAD','AUDUSD','NZDUSD'],
                    nzdusd_execution_qualified=False,ctrader_fix_qualified=False,
                    source_status=feed.status(),elapsed_seconds=round(monotonic()-started,3))
                timer.stop();window.close()
        except Exception as exc:
            proof.update(error_type=type(exc).__name__,phase_at_failure=phase,
                locations=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(exc.__traceback__)])
            try:
                save('primary-failure.json',proof)
                if runtime is not None:save('failed-source-status.json',runtime.connector.analytical_feed.native_book.status())
            finally:timer.stop();app.quit()
    QTimer.singleShot(0,inspect);timer.timeout.connect(inspect);timer.start()
    sys.argv=['sfm-fx-new-age','--state-dir',str(state)]
    try:code=main()
    finally:
        timer.stop()
        if runtime is not None:
            try:runtime.close()
            except Exception as exc:proof.update(result='FAIL',cleanup_error_type=type(exc).__name__)
            feed=runtime.connector.analytical_feed
            proof.update(runtime_closed=runtime.closed,bitstamp_worker_joined=feed.native_book.worker is None,
                kraken_worker_joined=feed.venue.worker is None,weekly_worker_joined=feed.venue.weekly.worker is None,
                sdk_processes_stopped=all(not w.process.is_alive() for w in workers),
                denied_broker_writes=sum(w.denied_writes for w in workers),
                fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
        save('original-envelopes.json',archive);save('acceptance.json',proof)
    origins={k:str(Path(v.__file__).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)}
    assert origins and all(Path(v).is_relative_to(PACKAGE) for v in origins.values())
    save('module-origins.json',origins)
    print(json.dumps(proof,indent=2))
    assert code==0 and proof['result'].startswith('PASS_')
    assert proof['bitstamp_worker_joined'] and proof['kraken_worker_joined'] and proof['weekly_worker_joined'] and proof['sdk_processes_stopped']
    assert not proof['broker_mutations'] and not proof['denied_broker_writes'] and not proof['fixture_imports']


if __name__=='__main__':run()
