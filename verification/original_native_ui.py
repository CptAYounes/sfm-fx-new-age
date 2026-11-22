"""Native X11 GUI checks using recorded original broker/official observations only."""
from pathlib import Path
import os,sys,json
from PySide6.QtWidgets import QApplication,QAbstractItemView,QDialog,QTextEdit,QComboBox
from PySide6.QtCore import Qt,QTimer,QPoint
from PySide6.QtTest import QTest
from original_source_checks import original_runtime,RUN,PACKAGE
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw


def main():
    app=QApplication.instance() or QApplication([]);assert app.platformName()=='xcb'
    r,layers,raw,source=original_runtime();w=None;proof=dict(scope='NATIVE_X11_RECORDED_ORIGINAL_BROKER_AND_OFFICIAL_DATA_NOT_A_NEW_LIVE_FEED',package_root=str(PACKAGE),synthetic_observations=0,checkboxes=[],screenshots=[],result='FAIL')
    try:
        for m in METHODS:r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=False))
        r.pump();w=create_main_window(r);w.resize(1280,850);w.show();w.core_timer.stop();w.poll_timer.stop();app.processEvents()
        r.api(3).navigate('3.1',r.api(3).inspect(symbol='EURUSD',timeframe='H4'));app.processEvents();w.refresh_current(force=True);p=w._active_panel()
        assert len(p.checkboxes)==83
        for m in METHODS:
            index=next(i for i,v in enumerate(METHODS) if v.key==m.key);p.table.scrollToItem(p.table.item(index,1),QAbstractItemView.PositionAtCenter);p.table.selectRow(index);app.processEvents()
            box=p.checkboxes[m.key];assert not box.isChecked()
            QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));app.processEvents();assert box.isChecked() and r.database.get('recipe_state',m.recipe_id)['enabled'] is True
            QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));app.processEvents();assert not box.isChecked() and r.database.get('recipe_state',m.recipe_id)['enabled'] is False
            proof['checkboxes'].append(m.key)
        for key in ('cot_macro','calendar_context','profile_tpo'):
            index=next(i for i,v in enumerate(METHODS) if v.key==key);p.table.scrollToItem(p.table.item(index,1),QAbstractItemView.PositionAtCenter);app.processEvents();box=p.checkboxes[key];QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));assert box.isChecked()
        r.pump();p.refresh();app.processEvents();screen=RUN/'original-strategy-library.png';assert w.grab().save(str(screen));proof['screenshots'].append(str(screen))
        QTest.mouseClick(p.chart_button,Qt.LeftButton);app.processEvents();w.refresh_current(force=True);p=w._active_panel();c=p.canvas;c.grab()
        assert {v['strategy_id'] for v in c.strategy_layers}=={'cot_macro','calendar_context','profile_tpo'}
        assert all(v['state'] in {'READY','NO_SETUP'} for v in c.strategy_layers)
        all_prices=[float(b[k]) for b in c.bars[-c.window:] for k in ('low','high')]+[float(z[k]) for v in c.strategy_layers for z in v['zones'] for k in ('low','high')]
        lo,hi=min(all_prices),max(all_prices);padding=max((hi-lo)*.08,.0001);c.price_range=(max(.000001,lo-padding),hi+padding);c.update();app.processEvents();c.grab()
        captions=c.projection_badge_layout();counts=c.projection_badge_counts()
        assert counts['shown']==len(captions)<=counts['eligible'] and captions
        assert all(a['rect'].bottom()+1<=b['rect'].top() for a,b in zip(captions,captions[1:]))
        screen=RUN/'original-cot-fed-tpo-chart.png';assert w.grab().save(str(screen));proof['screenshots'].append(str(screen));proof['captions']=counts
        results=[];errors=[]
        def inspect():
            dialog=app.activeModalWidget()
            try:
                assert isinstance(dialog,QDialog) and dialog.objectName()=='publicProjectionDetails'
                text=dialog.findChild(QTextEdit,'publicProjectionValues');assert text and text.isReadOnly()
                picker=dialog.findChild(QComboBox,'publicProjectionPicker');assert picker and picker.count()==len(c.strategy_layers)
                for layer in c.strategy_layers:
                    index=picker.findData(layer['strategy_id']);assert index>=0;picker.setCurrentIndex(index);app.processEvents();value=text.toPlainText()
                    assert 'LIVE_OBSERVED' in value and 'SYNTHETIC_FIXTURE' not in value
                    assert layer['strategy_id'] in value and layer['source_epoch'] in value
                    for zone in layer['zones']:assert zone['low'] in value and zone['high'] in value
                screen=RUN/'original-projection-details.png';assert dialog.grab().save(str(screen));proof['screenshots'].append(str(screen));results.append(True)
            except Exception as exc:errors.append(repr(exc))
            finally:
                if isinstance(dialog,QDialog):dialog.reject()
        QTimer.singleShot(100,app,inspect);p.public_details_action.trigger();proof['inspector_errors']=errors;assert results and not errors
        proof.update(result='PASS',independent_native_checkboxes=len(proof['checkboxes']),original_data_layers=[dict(strategy_id=v['strategy_id'],state=v['state'],symbol=v['symbol'],timeframe=v['timeframe'],source_epoch=v['source_epoch'],origin=v['origin']) for v in c.strategy_layers],details_contains_original_values=True,sdk_workers_started=bool(r.connector.workers),fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
        assert not proof['sdk_workers_started'] and not proof['fixture_imports']
    finally:
        if w:w.close()
        r.close();app.processEvents();proof['runtime_closed']=r.closed
        with (RUN/'native-receipt.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
        print(json.dumps(proof,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
