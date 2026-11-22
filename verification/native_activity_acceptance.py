"""Actual OpenAPI activity/depth alternatives acceptance; no synthetic data."""
from pathlib import Path
from time import monotonic,sleep
from collections import Counter
import hashlib,json,os,sqlite3,sys
from typing import Any
PACKAGE=Path(os.environ['SFM_NATIVE_PACKAGE']).resolve(strict=True);sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.storage.database import Database
from sfm_fx_new_age.connector.original_capture import ReadOnlyCaptureSdk
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.domain import PAIRS,FRAMES,instant,record
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.tabs.tab3.public_activity_alternatives import ACTIVITY_NAMES


def exercise_gui(r,out):
    from PySide6.QtWidgets import QApplication,QAbstractItemView
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt,QPoint
    from sfm_fx_new_age.app import create_main_window
    app=QApplication.instance() or QApplication([]);assert app.platformName()=='xcb'
    window=create_main_window(r)
    try:
        window.resize(1360,960);window.show();window.core_timer.stop();window.poll_timer.stop();app.processEvents()
        r.api(3).navigate('3.1',r.api(3).inspect(symbol='EURUSD',timeframe='H4'));window.refresh_current(force=True);app.processEvents()
        panel=window._active_panel();assert len(panel.checkboxes)==83;switches=[]
        for index,m in enumerate(METHODS):
            panel.table.scrollToItem(panel.table.item(index,1),QAbstractItemView.PositionAtCenter);panel.table.selectRow(index);app.processEvents()
            box=panel.checkboxes[m.key];assert box.isChecked()
            QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));app.processEvents();assert not box.isChecked()
            QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));app.processEvents();assert box.isChecked();switches.append(m.key)
        r.pump();panel.refresh();panel.search.setText('volume');app.processEvents();assert window.grab().save(str(out/'native-activity-library.png'))
        panel.search.clear();r.api(1).navigate('1.4',r.api(1).inspect(symbol='EURUSD',timeframe='H4'));window.refresh_current(force=True);app.processEvents()
        chart=thaw(r.api(1).query('1.4',DataRequest('chart',symbol='EURUSD',timeframe='H4',limit=5000)));assert len(chart['strategy_layers'])==83
        assert window.grab().save(str(out/'native-activity-chart.png'))
        return switches
    finally:window.close()


def main():
    out=Path(os.environ['SFM_NATIVE_OUT']);out.mkdir(mode=0o700,parents=True,exist_ok=False)
    source=Path.home()/'.local/share/sfm-fx-new-age/state.sqlite3';db=Database(out/'state.sqlite3')
    c=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    try:
        c.execute('PRAGMA query_only=ON');settings=c.execute("SELECT kind,id,body FROM records WHERE kind='setting' AND id IN ('connector_public_profile','connector_remember')").fetchall()
    finally:c.close()
    try:
        with db.transaction() as c:c.executemany('INSERT INTO records VALUES(?,?,?)',settings)
    finally:db.close()
    r=ApplicationRuntime(out/'state.sqlite3',native_analytical_feed=True,activity_alternatives=True);workers=[];proof={'result':'FAIL','broker_mutations':0};started=monotonic();window=None
    def factory(config):
        w=ReadOnlyCaptureSdk(config);workers.append(w);return w
    r.connector.worker_factory=factory
    def deny(*a,**kw):raise PermissionError('Native acceptance forbids broker mutation')
    r.connector.submit=deny;r.connector.cancel=deny
    native_events=[];original_handle=r.connector.handle
    def handle(endpoint,message):
        original_handle(endpoint,message)
        if message.get('name')=='ProtoOADepthEvent' and r.connector.analytical_feed:
            depth=r.connector.analytical_feed.depth
            if depth.audit and len(native_events)<2048:native_events.append(dict(depth.audit[-1]))
    r.connector.handle=handle
    observed={};depth_evidence={};refreshes=[]
    feed=r.connector.analytical_feed;assert feed is not None
    try:
        for m in METHODS:
            result=r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True));assert result.status.value=='ACCEPTED'
        r.connector.resume_saved_session()
        while monotonic()-started<240:
            r.pump();feed=r.connector.analytical_feed;assert feed is not None
            account=r.accounts.current
            if account:
                for symbol in PAIRS:
                    for frame in FRAMES:
                        rows=r.analytics.projections.read(symbol,frame)
                        for row in rows:
                            if row['strategy_id'] in ACTIVITY_NAMES and row['state'] in {'READY','NO_SETUP'}:
                                metrics=row['metrics'];assert isinstance(metrics,dict) and metrics.get('alternative') is True
                                assert metrics['executed_volume'] is False and metrics['known_aggressors'] is False
                                observed[(symbol,frame,row['strategy_id'])]=row
                    values=r.analytics.supplemental.snapshot(symbol,r.clock())
                    if 'BROKER_DEPTH' in values:depth_evidence[symbol]=values['BROKER_DEPTH']
            refreshes.append(dict(elapsed=round(monotonic()-started,3),positive_alternative_lanes=len(observed),depth_events=feed.depth.events,publications=feed.depth.publications))
            if len(observed)==168 and len(depth_evidence)==7 and feed.depth.publications>=14:break
            if r.connector.state in {'LOGIN_REQUIRED','APPLICATION_AUTH_FAILED','CONNECTION_FAILED'}:raise ValueError('Native authentication failed')
            sleep(.08)
        assert len(observed)==168,(len(observed),feed.status(),[(s,fr,k) for s in PAIRS for fr in FRAMES for k in ACTIVITY_NAMES if (s,fr,k) not in observed])
        assert len(depth_evidence)==7 and feed.depth.publications>=14
        account=r.accounts.current;assert account and account.authenticated
        matrix=[v for symbol in PAIRS for frame in FRAMES for v in r.analytics.projections.read(symbol,frame)]
        assert len(matrix)==2324 and not any(v['state']=='ERROR' for v in matrix)
        (out/'all-profile-matrix.json').write_text(json.dumps(matrix,sort_keys=True,indent=2)+'\n')
        # Store actual source snapshots and observed projections with original clocks.
        (out/'observed-alternative-layers.json').write_text(json.dumps(list(observed.values()),sort_keys=True,indent=2)+'\n')
        (out/'broker-depth-envelopes.json').write_text(json.dumps(depth_evidence,indent=2)+'\n')
        (out/'bounded-native-depth-events.json').write_text(json.dumps(list(feed.depth.audit),indent=2)+'\n')
        (out/'original-depth-events.json').write_text(json.dumps(native_events,indent=2)+'\n')
        # Price/weight/direction math is independently checked on original inputs.
        checks=[]
        for symbol in PAIRS:
            values=r.analytics.supplemental.snapshot(symbol,r.clock());data=values['INTRABAR_PRICES'];prices=[__import__('decimal').Decimal(v['price']) for v in data['records']]
            layer=observed[(symbol,'H4','vwap_bands')];mean=sum(prices)/len(prices)
            assert abs(__import__('decimal').Decimal(layer['metrics']['quote_sample_mean'])-mean)<__import__('decimal').Decimal('1e-20')
            directional=observed[(symbol,'H4','footprint_delta')]['metrics'];up=sum(b>a for a,b in zip(prices,prices[1:]));down=sum(b<a for a,b in zip(prices,prices[1:]))
            assert directional['up_quote_changes']==up and directional['down_quote_changes']==down and not directional['aggressor_inferred']
            assert 'sequence' not in depth_evidence[symbol]['records'][0] and depth_evidence[symbol]['parameters']['full_book_complete'] is False
            from sfm_fx_new_age.connector.depth_capture import decode_observed_levels
            original=[dict(payload=v['payload']) for v in native_events if v['symbol']==symbol and instant(v['received_at'])<=instant(depth_evidence[symbol]['records'][0]['time'])]
            decoded:Any=decode_observed_levels(original)['observed_levels']
            assert decoded['bid'][:100]==depth_evidence[symbol]['records'][0]['bids'] and decoded['ask'][:100]==depth_evidence[symbol]['records'][0]['asks']
            checks.append(dict(symbol=symbol,mean_and_direction_verified=True))
        # Strict mode is preserved: removing policy never converts proxy evidence.
        r.analytics.activity_alternatives=False
        for symbol in PAIRS:r._analytics_dirty.add(symbol)
        r.pump()
        strict=[v for symbol in PAIRS for frame in FRAMES for v in r.analytics.projections.read(symbol,frame) if v['strategy_id'] in ACTIVITY_NAMES]
        assert len(strict)==168 and all(v['state']=='DATA_UNAVAILABLE' for v in strict)
        r.analytics.activity_alternatives=True
        for symbol in PAIRS:r._analytics_dirty.add(symbol)
        r.pump()
        if os.environ.get('SFM_NATIVE_GUI')=='1':
            r.pump()
            proof['actual_all_83_switches']=exercise_gui(r,out)
        publications=feed.depth.publications
        r.connector.disconnect()
        assert not r.analytics.supplemental.snapshot('EURUSD',r.clock())
        proof.update(result='PASS_168_NATIVE_ALTERNATIVE_LANES_AND_BROKER_DOM',scope='USER_AUTHORIZED_ALTERNATIVES_NOT_STRICT_EXECUTION_FLOW_ACCEPTANCE',alternative_lanes=len(observed),profile_count=83,matrix_lanes=len(matrix),matrix_states=dict(Counter(v['state'] for v in matrix)),
            alternative_states=dict(Counter(v['state'] for v in observed.values())),strict_mode_still_refuses_all_168=True,depth_envelopes=len(depth_evidence),repeated_depth_publications=publications,
            independent_original_math_checks=checks,disconnect_withdrawn=True,progress=refreshes,elapsed_seconds=round(monotonic()-started,3),fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
    finally:
        auth=r.connector.auth_worker
        if window:window.close()
        r.close()
        if auth and auth.is_alive():auth.join(timeout=35)
        proof.update(runtime_closed=r.closed,sdk_processes_stopped=all(not w.process.is_alive() for w in workers),auth_thread_stopped=not(auth and auth.is_alive()),denied_broker_mutations=sum(w.denied_writes for w in workers))
        with (out/'acceptance.json').open('x') as stream:json.dump(proof,stream,indent=2);stream.write('\n')
    assert proof['sdk_processes_stopped'] and proof['auth_thread_stopped'] and proof['denied_broker_mutations']==0 and not proof['fixture_imports']
    origins={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)}
    assert all(Path(p).is_relative_to(PACKAGE) for p in origins.values())
    with (out/'process-origin.json').open('x') as f:json.dump(dict(all_product_modules_from_declared_root=True,package_root=str(PACKAGE),origins=origins),f,indent=2)
    print(json.dumps({k:v for k,v in proof.items() if k!='progress'},indent=2))


if __name__=='__main__':main()
