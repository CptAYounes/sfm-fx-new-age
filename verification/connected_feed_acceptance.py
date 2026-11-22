"""Real connected producer→core→strategy→chart check; no fixture or fake packets."""
from pathlib import Path
from time import monotonic,sleep
from collections import Counter
import hashlib,json,os,sqlite3,sys
from typing import Any
PACKAGE=Path(os.environ['SFM_FEED_PACKAGE']).resolve(strict=True);sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.storage.database import Database
from sfm_fx_new_age.connector.original_capture import ReadOnlyCaptureSdk
from sfm_fx_new_age.connector.native_feed_audit import native_quote_health
from sfm_fx_new_age.contracts.domain import PAIRS,FRAMES,record
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest


def main():
    out=Path(os.environ['SFM_FEED_OUT']);out.mkdir(parents=True,mode=0o700,exist_ok=False)
    source=Path(os.environ.get('SFM_FEED_SOURCE',str(Path.home()/'.local/share/sfm-fx-new-age/state.sqlite3')))
    normal=os.environ.get('SFM_FEED_USE_NORMAL')=='1'
    database=source if normal else out/'state.sqlite3'
    if not normal:
        c=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
        try:
            c.execute('PRAGMA query_only=ON');settings=c.execute("SELECT kind,id,body FROM records WHERE kind='setting' AND id IN ('connector_public_profile','connector_remember')").fetchall()
        finally:c.close()
        db=Database(database)
        try:
            with db.transaction() as c:c.executemany('INSERT INTO records VALUES(?,?,?)',settings)
        finally:db.close()
    r=ApplicationRuntime(database,native_analytical_feed=True);workers=[];proof:dict[str,Any]=dict(result='FAIL',normal_database=normal,synthetic_observations=0,full_requested_completion=False)
    def factory(config):
        w=ReadOnlyCaptureSdk(config);workers.append(w);return w
    r.connector.worker_factory=factory
    def deny(*a,**kw):raise PermissionError('Feed verification refuses broker mutation')
    r.connector.submit=deny;r.connector.cancel=deny
    started=monotonic();window=None
    try:
        assert r.connector.analytical_feed is not None
        r.connector.resume_saved_session()
        s:dict[str,Any]={}
        while monotonic()-started<210:
            r.pump();s=r.connector.analytical_feed.status()
            if len(s['tpo'])==7 and all(v=='ADMITTED' for v in s['tpo'].values()) and s['official_context']=='ADMITTED':break
            if r.connector.state in {'LOGIN_REQUIRED','CONNECTION_FAILED','APPLICATION_AUTH_FAILED'}:raise ValueError('Saved-session connection failed')
            sleep(.07)
        else:raise TimeoutError('Connected input deadline: '+json.dumps(s))
        account=r.accounts.current;assert account and account.authenticated
        # Read the actual store, not the producer's self-report.
        inputs={symbol:r.analytics.supplemental.snapshot(symbol,r.clock()) for symbol in PAIRS}
        assert all(set(value)=={'INTRABAR_PRICES','CFTC_REPORT','OFFICIAL_CALENDAR'} for value in inputs.values())
        for symbol,values in inputs.items():
            authority=r.market.authority(symbol);assert authority is not None
            assert all((e['scope_id'],e['source_epoch'],e['symbol'])==(account.scope_id,authority['source_epoch'],symbol) for e in values.values())
        if not normal:
            for m in METHODS:
                result=r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True));assert result.status.value=='ACCEPTED'
            r.pump()
            layers=[v for symbol in PAIRS for frame in FRAMES for v in r.analytics.projections.read(symbol,frame)]
            assert len(layers)==2324 and all(v['state']!='ERROR' for v in layers)
            for key in ('profile_tpo','cot_macro'):
                assert all(v['state']=='READY' for v in layers if v['strategy_id']==key)
            assert all(v['state'] in {'READY','NO_SETUP'} for v in layers if v['strategy_id']=='calendar_context')
            blocked={'volume_displacement','effort_result','volume_profile','vwap_bands','footprint_delta','dom_imbalance'}
            assert all(v['state']=='DATA_UNAVAILABLE' for v in layers if v['strategy_id'] in blocked)
            chart=thaw(r.api(1).query('1.4',DataRequest('chart',symbol='EURUSD',timeframe='H4',limit=5000)))
            assert {v['strategy_id'] for v in chart['strategy_layers']}=={m.key for m in METHODS}
            raw=(json.dumps(layers,sort_keys=True)+'\n').encode();(out/'matrix.json').write_bytes(raw)
            proof.update(matrix_rows=len(layers),matrix_states=dict(Counter(v['state'] for v in layers)),matrix_sha256=hashlib.sha256(raw).hexdigest(),chart_layers=len(chart['strategy_layers']))
        if os.environ.get('SFM_FEED_NATIVE')=='1':
            from PySide6.QtWidgets import QApplication
            from sfm_fx_new_age.app import create_main_window
            from sfm_fx_new_age.ui.feed_connection import FeedDialog
            app=QApplication.instance() or QApplication([]);assert app.platformName()=='xcb'
            window=create_main_window(r);window.resize(1360,960);window.show();window.core_timer.stop();window.poll_timer.stop();app.processEvents()
            dialog=FeedDialog(r.api(2),r.api(4),window);dialog.show();dialog.timer.stop();dialog.refresh();app.processEvents()
            assert '7/7' in dialog.analytical_status.text() and 'admitted' in dialog.analytical_status.text()
            assert dialog.grab().save(str(out/'connected-feed-dialog.png'));dialog.close()
            r.api(3).navigate('3.1',r.api(3).inspect(symbol='EURUSD',timeframe='H4'));window.refresh_current(force=True);app.processEvents()
            assert window.grab().save(str(out/'connected-strategy-library.png'))
            proof.update(native_feed_status_visible=True,native_dialog_text=dialog.analytical_status.text());window.close();window=None
        proof.update(result='CONNECTED_SUPPORTED_INPUTS_ADMITTED_AND_CHARTED',elapsed_seconds=round(monotonic()-started,3),feed=r.connector.feed_status(),analytical_feed=r.connector.analytical_feed.status(),store_input_kinds={s:sorted(v) for s,v in inputs.items()},original_quote_records=sum(len(v['INTRABAR_PRICES']['records']) for v in inputs.values()),quote_health={s:native_quote_health(record(r.market.quote(account.account_id,s)),r.clock()) for s in PAIRS},fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
        assert not proof['fixture_imports']
    finally:
        auth=r.connector.auth_worker;feed=r.connector.analytical_feed
        if window:window.close()
        r.close()
        if auth and auth.is_alive():auth.join(timeout=35)
        proof.update(sdk_processes_stopped=all(not w.process.is_alive() for w in workers),auth_thread_stopped=not(auth and auth.is_alive()),official_thread_stopped=not(feed and feed.worker),runtime_closed=r.closed,denied_broker_mutations=sum(w.denied_writes for w in workers),read_request_counts={name:sum(w.read_counts.get(name,0) for w in workers) for name in sorted({n for w in workers for n in w.read_counts})})
        with (out/'connected-feed-receipt.json').open('x') as stream:json.dump(proof,stream,indent=2);stream.write('\n')
    assert proof['sdk_processes_stopped'] and proof['auth_thread_stopped'] and proof['official_thread_stopped']
    print(json.dumps({k:v for k,v in proof.items() if k not in {'quote_health'}},indent=2))


if __name__=='__main__':main()
