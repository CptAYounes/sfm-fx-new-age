"""Actual normal main()/Desktop, saved session, DOM and reconnect; zero orders."""
from pathlib import Path
from time import monotonic
import json,os,sys
from typing import Any
PACKAGE=Path(os.environ['SFM_NATIVE_PACKAGE']).resolve(strict=True);sys.path.insert(0,str(PACKAGE))
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from sfm_fx_new_age.__main__ import main
from sfm_fx_new_age.app import MainWindow
from sfm_fx_new_age.connector.original_capture import ReadOnlyCaptureSdk
from sfm_fx_new_age.contracts.domain import PAIRS


def run():
    out=Path(os.environ['SFM_NATIVE_OUT']);out.mkdir(parents=True,mode=0o700,exist_ok=False)
    state=Path(os.environ['SFM_NATIVE_STATE']).resolve(strict=True)
    app=QApplication.instance() or QApplication([]);assert app.platformName()=='xcb'
    proof:dict[str,Any]=dict(result='FAIL',entrypoint='sfm_fx_new_age.__main__.main',normal_database=True,synthetic_observations=0,broker_mutations=0)
    started=monotonic();runtime=None;workers=[];before_settings=None;timer=QTimer();timer.setInterval(300);first_binding=None;before_publications=0
    def inspect():
        nonlocal runtime,before_settings,first_binding,before_publications
        window=next((w for w in app.topLevelWidgets() if isinstance(w,MainWindow)),None)
        try:
            if window is None:return
            if runtime is None:
                runtime=window.runtime;assert not runtime.connector.workers and runtime.analytics.activity_alternatives
                before_settings={kind:runtime.database.list(kind) for kind in ('recipe_state','recipe','setting')}
                def factory(config):
                    worker=ReadOnlyCaptureSdk(config);workers.append(worker);return worker
                runtime.connector.worker_factory=factory
                def deny(*a,**kw):raise PermissionError('Desktop verification refuses broker writes')
                runtime.connector.submit=deny;runtime.connector.cancel=deny
            status=runtime.connector.status();feed=status['analytical_feed'];depth=feed.get('broker_depth',{})
            if feed.get('official_context')=='ADMITTED' and len(feed.get('tpo',{}))==7 and all(v=='ADMITTED' for v in feed['tpo'].values()) and depth.get('publications',0)>=before_publications+14:
                assert status['feed']['completed_history_jobs']==28
                account=runtime.accounts.current;assert account and account.authenticated
                actual={s:sorted(runtime.analytics.supplemental.snapshot(s,runtime.clock())) for s in PAIRS}
                if not all(v==['BROKER_DEPTH','CFTC_REPORT','INTRABAR_PRICES','OFFICIAL_CALENDAR'] for v in actual.values()):return
                authorities={s:runtime.market.authority(s) for s in PAIRS};assert all(authorities.values())
                binding=tuple((s,(authorities[s] or {})['source_epoch']) for s in PAIRS)
                if first_binding is None:
                    first_binding=binding;before_publications=depth['publications'];proof['first_connection']=dict(feed=feed,store_input_kinds=actual)
                    runtime.connector.disconnect();assert not runtime.analytics.supplemental.providers
                    runtime.connector._startup_attempted=False;runtime.connector.resume_saved_session();return
                assert first_binding!=binding
                assert before_settings is not None
                window.resize(1360,960);window.refresh_current(force=True);app.processEvents()
                QTest.mouseClick(window.feed_card.button,Qt.LeftButton);app.processEvents()
                dialog=window.feed_dialog;assert dialog is not None and dialog.isVisible()
                dialog.refresh();app.processEvents();assert 'broker DOM: 7/7' in dialog.analytical_status.text() and 'activity alternatives enabled' in dialog.analytical_status.text()
                assert dialog.grab().save(str(out/'normal-launch-reconnected-feed.png'))
                proof.update(result='PASS_NORMAL_DESKTOP_AND_SECOND_CONNECTED_DOM_BINDING',analytical_feed=feed,feed=status['feed'],store_input_kinds=actual,
                    native_dialog_text=dialog.analytical_status.text(),saved_switches_unchanged=runtime.database.list('recipe_state')==before_settings['recipe_state'],
                    recipe_records_unchanged=runtime.database.list('recipe')==before_settings['recipe'],new_source_epoch_after_reconnect=True,elapsed_seconds=round(monotonic()-started,3))
                assert proof['saved_switches_unchanged'] and proof['recipe_records_unchanged']
                dialog.close();timer.stop();window.close();app.quit()
            elif monotonic()-started>270:raise TimeoutError('Normal desktop reconnect startup deadline')
        except Exception as exc:
            proof.update(error_type=type(exc).__name__);timer.stop()
            if window:window.close()
            app.exit(1)
    QTimer.singleShot(0,inspect);timer.timeout.connect(inspect);timer.start()
    sys.argv=['sfm-fx-new-age','--state-dir',str(state)];exit_code=main()
    if runtime is not None:
        auth=runtime.connector.auth_worker;runtime.close()
        if auth and auth.is_alive():auth.join(timeout=35)
        proof.update(runtime_closed=runtime.closed,auth_thread_stopped=not(auth and auth.is_alive()),official_thread_stopped=not(runtime.connector.analytical_feed and runtime.connector.analytical_feed.worker))
    proof.update(process_exit=exit_code,sdk_processes_stopped=all(not w.process.is_alive() for w in workers),denied_broker_mutations=sum(w.denied_writes for w in workers),fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')],product_module_origins={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)})
    assert all(Path(p).is_relative_to(PACKAGE) for p in proof['product_module_origins'].values())
    with (out/'desktop-receipt.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in proof.items() if k!='product_module_origins'},indent=2))
    assert proof['result']=='PASS_NORMAL_DESKTOP_AND_SECOND_CONNECTED_DOM_BINDING' and proof['sdk_processes_stopped'] and proof['official_thread_stopped'] and not proof['fixture_imports']
    return exit_code


if __name__=='__main__':raise SystemExit(run())
