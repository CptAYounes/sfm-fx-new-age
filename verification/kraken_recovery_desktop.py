"""Original-only, normal main()/saved-session public-venue acceptance.

The operator database is read-only copied; all writes use an isolated private
state directory. Real cTrader reads and real Kraken reads only. No fake feeds.
"""
from pathlib import Path
from collections import Counter
from decimal import Decimal
from time import monotonic
import hashlib,json,os,sqlite3,sys,traceback

PACKAGE=Path(os.environ['SFM_KRAKEN_PACKAGE']).resolve(strict=True)
sys.path.insert(0,str(PACKAGE))
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from sfm_fx_new_age.__main__ import main
from sfm_fx_new_age.app import MainWindow
from sfm_fx_new_age.connector.original_capture import ReadOnlyCaptureSdk
from sfm_fx_new_age.connector.kraken_public import PROVIDER,KINDS
from sfm_fx_new_age.contracts.domain import PAIRS,FRAMES,instant
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw

TARGETS=('EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD')
METHOD_KEYS=('volume_displacement','effort_result','volume_profile','vwap_bands','footprint_delta','dom_imbalance')


def run():
    out=Path(os.environ['SFM_KRAKEN_OUT']).resolve();out.mkdir(mode=0o700,parents=True,exist_ok=False)
    state=out/'state';state.mkdir(mode=0o700)
    source=Path.home()/'.local/share/sfm-fx-new-age/state.sqlite3'
    c=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);target=sqlite3.connect(state/'state.sqlite3')
    try:c.execute('PRAGMA query_only=ON');c.backup(target)
    finally:target.close();c.close()
    app=QApplication.instance() or QApplication([]);assert app.platformName()=='xcb'
    proof={'result':'FAIL','entrypoint':'normal main() saved-session startup','synthetic_observations':0,'broker_mutations':0,'normal_database_opened_for_write':False}
    workers=[];runtime=None;started=monotonic();phase=0;first_epoch=None;first_publications=0
    observed={};layer_states={};audit={};http={};envelopes={};timer=QTimer();timer.setInterval(150)
    verified_math={};math_originals={};last_checkpoint=0.;last_phase=None;week_audit={}
    def save(name,body):(out/name).write_text(json.dumps(body,indent=2,default=str)+'\n')
    def checkpoint(event,**extra):
        nonlocal last_checkpoint,last_phase
        now=monotonic()
        if event=='poll' and now-last_checkpoint<5 and phase==last_phase:return
        last_checkpoint=now;last_phase=phase
        data=dict(event=event,elapsed_seconds=round(now-started,3),phase=phase,
                  observed_lanes=len(observed),envelopes=len(envelopes),math_by_pair={k:sorted(v) for k,v in verified_math.items()},**extra)
        if runtime is not None:
            venue=runtime.connector.analytical_feed.venue
            data.update(connector_state=runtime.connector.state,venue=venue.status(),
                        dirty_pairs=sorted(runtime._analytics_dirty),
                        venue_queue=venue.results.qsize(),feed_intents=len(runtime.connector.feed_intents))
        with (out/'phases.jsonl').open('a') as stream:
            stream.write(json.dumps(data,default=str)+'\n');stream.flush();os.fsync(stream.fileno())
    def inspect():
        nonlocal runtime,phase,first_epoch,first_publications
        window=None
        try:
            checkpoint('poll')
            if monotonic()-started>380:raise TimeoutError('Native public-venue acceptance deadline')
            window=next((w for w in app.topLevelWidgets() if isinstance(w,MainWindow)),None)
            if window is None:return
            if runtime is None:
                runtime=window.runtime;assert not runtime.connector.workers
                def factory(config):
                    w=ReadOnlyCaptureSdk(config);workers.append(w);return w
                runtime.connector.worker_factory=factory
                def deny(*a,**kw):proof['broker_mutations']+=1;raise PermissionError('No broker mutations in acceptance')
                runtime.connector.submit=deny;runtime.connector.cancel=deny
                for m in METHODS:
                    result=runtime.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True))
                    assert result.status.value=='ACCEPTED'
                original_refresh=runtime.analytics.refresh
                def refresh(symbol):
                    nonlocal phase
                    refresh_start=monotonic()
                    captured=runtime.analytics.supplemental.snapshot(symbol,runtime.clock())
                    result=original_refresh(symbol)
                    if runtime.accounts.current:
                        for frame in FRAMES:
                            for row in runtime.analytics.projections.read(symbol,frame):
                                if row['strategy_id'] in METHOD_KEYS:
                                    layer_states[(symbol,frame,row['strategy_id'])]=row
                                    if row['state'] in {'READY','NO_SETUP'} and row['metrics'].get('source_venue')=='KRAKEN_SPOT_FIAT':
                                        observed[(symbol,frame,row['strategy_id'])]=row
                        if phase in (0,1):
                            from sfm_fx_new_age.contracts.analytics import digest
                            matched={}
                            for key,kind in (('footprint_delta','AGGRESSOR_PRINTS'),('vwap_bands','TRADED_PRINTS'),('dom_imbalance','VENUE_L2_CHECKSUM_BOOK')):
                                ev=captured.get(kind)
                                if not ev or ev['provider_id']!=PROVIDER:continue
                                rows=[v for k,v in observed.items() if k[0]==symbol and k[2]==key and v['metrics'].get('source_evidence_hash')==digest(ev)]
                                if not rows:continue
                                metrics=rows[0]['metrics']
                                if kind=='AGGRESSOR_PRINTS':
                                    delta=sum((Decimal(v['quantity'])*(1 if v['aggressor']=='BUY' else -1) for v in ev['records']),Decimal(0));assert Decimal(metrics['delta'])==delta
                                elif kind=='TRADED_PRINTS':
                                    q=sum(Decimal(v['quantity']) for v in ev['records']);mean=sum(Decimal(v['price'])*Decimal(v['quantity']) for v in ev['records'])/q
                                    assert abs(Decimal(metrics['vwap'])-mean)<Decimal('1e-20')
                                else:
                                    book=ev['records'][-1];buy=sum(Decimal(v[1]) for v in book['bids'][:5]);sell=sum(Decimal(v[1]) for v in book['asks'][:5]);assert Decimal(metrics['imbalance'])==(buy-sell)/(buy+sell)
                                matched[kind]=True;math_originals[(symbol,kind)]=ev
                            prior=verified_math.setdefault(symbol,{})
                            prior.update(matched)
                    if phase==1.5 and symbol=='EURUSD':
                        panel=window._active_panel();panel.refresh()
                        if all(panel._rows.get(k,{}).get('evaluation',{}).get('metrics',{}).get('source_venue')=='KRAKEN_SPOT_FIAT' for k in METHOD_KEYS):
                            assert window.grab().save(str(out/'kraken-library.png'));proof['library_captured_after_actual_refresh']=True
                    authority=runtime.market.authority(symbol)
                    if phase==2 and symbol=='EURUSD' and authority and first_epoch!=authority['source_epoch']:
                        needed={(s,f,k) for s in TARGETS for f in FRAMES for k in ('volume_profile','vwap_bands','footprint_delta','dom_imbalance')}
                        weekly={(s,'W1',k) for s in TARGETS for k in METHOD_KEYS[:2]}
                        weeks_ready=weekly<=set(observed) and all(observed[k]['metrics'].get('latest_lookback_complete') is True and observed[k]['metrics'].get('source_kind')=='EXECUTED_WEEK_QUANTITIES' for k in weekly)
                        if needed<=set(observed) and weeks_ready:
                            current=runtime.api(1).query('1.5',DataRequest('chart',symbol=symbol,timeframe='H1',as_of=runtime.clock()))
                            valid=[v for v in current['strategy_layers'] if v['strategy_id'] in METHOD_KEYS and v.get('metrics',{}).get('source_venue')=='KRAKEN_SPOT_FIAT']
                            if len(valid)==6:
                                runtime.api(1).navigate('1.5',runtime.api(1).inspect(symbol=symbol,timeframe='H1'));window.refresh_current(force=True);phase=3
                    checkpoint('refresh',symbol=symbol,duration_seconds=round(monotonic()-refresh_start,3),
                               positive_by_method=dict(Counter(k[2] for k in observed)))
                    return result
                runtime.analytics.refresh=refresh
            venue=runtime.connector.analytical_feed.venue
            for event in tuple(venue.audit):
                key=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest();audit[key]=event
            for event in tuple(venue.http_audit):http[event['sha256']]=event
            for event in tuple(venue.weekly.audit):week_audit[event['sha256']]=event
            if runtime.connector.state in {'LOGIN_REQUIRED','APPLICATION_AUTH_FAILED','CONNECTION_FAILED'}:raise RuntimeError('Native broker source unavailable')
            if phase==2 and not runtime.connector.feed_intents:
                scope=runtime.connector.preferences.get('scope_id')
                context=runtime.accounts.sessions.get(scope)
                if context and runtime.connector.native.get((context.endpoint_class,context.account_id),{}).get('connected'):
                    result=runtime.api(4).command('4.5','SELECT_ACCOUNT',dict(scope_id=scope));assert result.status.value=='ACCEPTED'
                    result=runtime.api(2).command('2.3','START_MARKET_FEED',{});assert result.status.value=='ACCEPTED'
            if runtime.accounts.current is None:return
            epoch=runtime.market.authority('EURUSD')
            if not epoch:return
            for symbol in TARGETS:
                values=runtime.analytics.supplemental.snapshot(symbol,runtime.clock())
                for kind in KINDS:
                    if kind in values and values[kind]['provider_id']==PROVIDER:
                        envelopes[(symbol,kind)]=values[kind]
            if len(envelopes)<30:return
            assert 'NZDUSD' not in venue.pairs and venue.states['NZDUSD']=='NOT_LISTED_BY_VENUE'
            # All three print-based methods, on every source-bound frame and pair.
            required={(s,f,k) for s in TARGETS for f in FRAMES for k in ('volume_profile','vwap_bands','footprint_delta','dom_imbalance')}
            if not required<=set(observed):return
            weekly={(s,'W1',k) for s in TARGETS for k in METHOD_KEYS[:2]}
            if not weekly<=set(observed) or not all(observed[k]['metrics'].get('latest_lookback_complete') is True and observed[k]['metrics'].get('source_kind')=='EXECUTED_WEEK_QUANTITIES' for k in weekly):return
            if phase==0:
                first_epoch=epoch['source_epoch'];first_publications=venue.publications;phase=1;return
            if phase==1 and venue.publications<first_publications+12:return
            if phase<=1:
                if not all(len(verified_math.get(s,{}))==3 for s in TARGETS):return
                proof['original_math']=[dict(symbol=s,delta_verified=True,vwap_verified=True,checksum_imbalance_verified=True) for s in TARGETS]
                save('math-originals.json',list(math_originals.values()))
                from datetime import timedelta
                expiry=max(instant(e['valid_until']) for e in envelopes.values())+timedelta(seconds=1)
                assert not KINDS.intersection(runtime.analytics.supplemental.snapshot('EURUSD',expiry.isoformat()))
                proof['expiry_query_refused']=True
                proof['first_epoch']=first_epoch
                proof['first_history_metadata']=venue.history_metadata
                proof['first_connection_publications']=venue.publications
                proof['quantity_states']={':'.join(k):v['state'] for k,v in layer_states.items() if k[0] in TARGETS and k[2] in METHOD_KEYS[:2]}
                save('first-connection-layers.json',list(observed.values()));save('first-connection-envelope-originals.json',list(envelopes.values()))
                # Observe the actual widget layer/control; no synthetic GUI data.
                window.resize(1440,960)
                runtime.api(3).navigate('3.1',runtime.api(3).inspect(symbol='EURUSD',timeframe='H1'));window.refresh_current(force=True);app.processEvents()
                panel=window._active_panel();assert len(panel.checkboxes)==83
                for key in METHOD_KEYS:
                    box=panel.checkboxes[key];assert box.isChecked()
                    panel.table.scrollToItem(panel.table.item(next(i for i,m in enumerate(METHODS) if m.key==key),1));app.processEvents()
                    QTest.mouseClick(box,Qt.LeftButton);app.processEvents();assert not box.isChecked()
                    QTest.mouseClick(box,Qt.LeftButton);app.processEvents();assert box.isChecked()
                save('all-frame-layer-states.json',list(layer_states.values()))
                phase=1.5;return
            if phase==1.5:
                if not proof.get('library_captured_after_actual_refresh'):return
                # Reconnect through public commands, not the startup-once helper.
                runtime.connector.disconnect()
                assert PROVIDER not in runtime.analytics.supplemental.providers and not venue.worker
                assert not runtime.analytics.supplemental.snapshot('EURUSD',runtime.clock())
                observed.clear();envelopes.clear();phase=2
                result=runtime.api(2).command('2.3','CONNECT',{});assert result.status.value=='ACCEPTED';return
            if phase==2:
                if epoch['source_epoch']==first_epoch:return
                assert all(v['source_epoch']==epoch['source_epoch'] for v in envelopes.values())
                return
            if phase==3:
                panel=window._active_panel();panel.refresh();app.processEvents()
                if not getattr(panel,'canvas',None):return
                layers=panel.canvas.strategy_layers
                projected=[r for r in layers if r['strategy_id'] in METHOD_KEYS and r.get('metrics',{}).get('source_venue')=='KRAKEN_SPOT_FIAT']
                if len(projected)<6:return
                panel.canvas.set_projection_focus('footprint_delta');app.processEvents()
                assert window.grab().save(str(out/'kraken-chart.png'))
                QTest.mouseClick(window.feed_card.button,Qt.LeftButton);app.processEvents()
                dialog=window.feed_dialog;assert dialog is not None;dialog.refresh()
                assert 'Kraken' in dialog.analytical_status.text() and 'executions 6/7' in dialog.analytical_status.text()
                assert 'Kraken checksum L2:' in dialog.analytical_status.text()
                dialog.layout().activate();dialog.adjustSize();app.processEvents()
                assert dialog.grab().save(str(out/'kraken-feed.png'));dialog.close()
                proof.update(result='PASS_PUBLIC_VENUE_EXACT_WEEKS_NATIVE_LIFECYCLE',source_pairs=list(TARGETS),unsupported_pairs=['NZDUSD'],trade_and_checksum_pair_frame_method_lanes=len(required),
                    observed_genuine_lanes=len(observed),all_83_switches_present=True,five_native_switches_exercised=True,
                    second_epoch=epoch['source_epoch'],reconnect_rebound=True,strict_full_book_qualified=False,all_seven_strict_complete=False,
                    actual_native_chart_layers=len(projected),
                    six_native_switches_exercised=True,latest_complete_weekly_lanes=len(weekly),
                    quantity_positive_lanes=sum(v['state'] in {'READY','NO_SETUP'} for k,v in layer_states.items() if k[0] in TARGETS and k[2] in METHOD_KEYS[:2]),
                    weekly_quantity_states={':'.join(k):dict(state=v['state'],metrics=v.get('metrics',{})) for k,v in layer_states.items() if k[0] in TARGETS and k[1]=='W1' and k[2] in METHOD_KEYS[:2]},
                    public_status=venue.status(),elapsed_seconds=round(monotonic()-started,3))
                timer.stop();window.close()
        except Exception as exc:
            proof['error_type']=type(exc).__name__;proof['locations']=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name) for f in traceback.extract_tb(exc.__traceback__)]
            proof['phase_at_failure']=phase
            proof['observed_keys']=[':'.join(k) for k in observed];proof['envelope_keys']=[':'.join(k) for k in envelopes]
            try:
                save('primary-failure.json',proof)
                for name,read in (
                    ('venue_status',lambda:runtime.connector.analytical_feed.venue.status()),
                    ('feed_state',lambda:runtime.connector.feed_status()),
                    ('active_panel_class',lambda:type(window._active_panel()).__name__),
                    ('chart_layer_sources',lambda:[dict(strategy_id=v['strategy_id'],state=v['state'],source=v.get('metrics',{}).get('source_venue')) for v in window._active_panel().canvas.strategy_layers if v['strategy_id'] in METHOD_KEYS])):
                    try:proof[name]=read()
                    except Exception as diagnostic:proof.setdefault('diagnostic_errors',{})[name]=type(diagnostic).__name__
                save('failure-diagnostics.json',proof)
            finally:
                timer.stop();app.quit()
    QTimer.singleShot(0,inspect);timer.timeout.connect(inspect);timer.start()
    sys.argv=['sfm-fx-new-age','--state-dir',str(state)]
    try:code=main()
    finally:
        timer.stop()
        if runtime is not None:
            auth=runtime.connector.auth_worker
            try:runtime.close()
            except Exception as cleanup:proof['cleanup_error_type']=type(cleanup).__name__;proof['result']='FAIL'
            finally:
                if auth is not None and auth.is_alive():auth.join(timeout=35)
            proof.update(runtime_closed=runtime.closed,public_worker_joined=not runtime.connector.analytical_feed.venue.worker,
                         weekly_worker_joined=not runtime.connector.analytical_feed.venue.weekly.worker,
                         sdk_processes_stopped=all(not w.process.is_alive() for w in workers),denied_broker_writes=sum(w.denied_writes for w in workers),
                         fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
        save('native-ws-originals.json',list(audit.values()));save('native-http-originals.json',list(http.values()));save('week-native-originals.json',list(week_audit.values()));save('acceptance.json',proof)
        c=sqlite3.connect((state/'state.sqlite3').as_uri()+'?mode=ro',uri=True)
        try:
            counts=list(c.execute("SELECT json_extract(body,'$.symbol'),json_extract(body,'$.kind'),COUNT(*) FROM records WHERE kind='supplemental_evidence' AND json_extract(body,'$.provider_id')=? GROUP BY 1,2",(PROVIDER,)))
            assert all(row[2]<=16 for row in counts)
            proof['bounded_publication_counts']=counts
            proof['normalized_original_archive_counts']=dict(c.execute("SELECT kind,COUNT(*) FROM records WHERE kind IN ('kraken_native_execution','kraken_native_hour_quantity') GROUP BY kind"))
        finally:c.close()
        save('acceptance.json',proof)
    origins={k:str(Path(v.__file__).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)}
    assert origins and all(Path(v).is_relative_to(PACKAGE) for v in origins.values());save('module-origins.json',origins)
    print(json.dumps(proof,indent=2))
    assert code==0 and proof['result'].startswith('PASS_') and proof['sdk_processes_stopped'] and proof['public_worker_joined'] and proof['weekly_worker_joined'] and not proof['fixture_imports'] and not proof['broker_mutations'] and not proof['denied_broker_writes']


if __name__=='__main__':run()
