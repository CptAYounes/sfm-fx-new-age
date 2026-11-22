"""Native original-bar automatic P&F checkbox, chart, inspector and withdrawal."""
from pathlib import Path
from typing import Any
import os,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
# Importing this helper does not execute its unittest entry point or seed fixtures.
from original_source_checks import original_runtime,RUN,PACKAGE
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.app import create_main_window
from PySide6.QtWidgets import QApplication,QAbstractItemView,QDialog,QTextEdit
from PySide6.QtCore import Qt,QPoint,QTimer
from PySide6.QtTest import QTest


def main():
    app=QApplication([]);assert app.platformName()=='xcb';r,_,_,replay=original_runtime();w=None
    proof:dict[str,Any]=dict(result='FAIL',scope='ORIGINAL_BAR_REPLAY_AUTOMATIC_PNF_NO_MANUAL_SETTINGS',synthetic_market_observations=0,package_root=str(PACKAGE))
    try:
        for m in METHODS:r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=False))
        w=create_main_window(r);w.resize(1280,850);w.show();w.core_timer.stop();w.poll_timer.stop();app.processEvents()
        r.api(3).navigate('3.1',r.api(3).inspect(symbol='GBPUSD',timeframe='H4'));w.refresh_current(force=True);app.processEvents();panel=w._active_panel();index=next(i for i,m in enumerate(METHODS) if m.key=='cause_effect');panel.table.scrollToItem(panel.table.item(index,1),QAbstractItemView.PositionAtCenter);panel.table.selectRow(index);app.processEvents()
        self_text=panel.details.toPlainText();assert 'Default input: original completed own-frame closes' in self_text
        box=panel.checkboxes['cause_effect'];assert not box.isChecked();QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));assert box.isChecked();r.pump();panel.refresh();app.processEvents();assert 'manual direction is needed' in panel.details.toPlainText()
        QTest.mouseClick(panel.chart_button,Qt.LeftButton);app.processEvents();w.refresh_current(force=True);chart=w._active_panel();c=chart.canvas;c.grab();assert len(c.strategy_layers)==1;layer=c.strategy_layers[0]
        assert layer['strategy_id']=='cause_effect' and layer['state']=='READY' and layer['origin']=='LIVE_OBSERVED' and layer['symbol']=='GBPUSD' and layer['timeframe']=='H4';assert layer['zones'];assert layer['metrics']['profile']=='PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1';assert layer['metrics']['intrabar_sequence_inferred'] is False
        prices=[float(b[k]) for b in c.bars[-c.window:] for k in ('low','high')]+[float(z[k]) for z in layer['zones'] for k in ('low','high')];lo,hi=min(prices),max(prices);pad=max((hi-lo)*.08,.0001);c.price_range=(lo-pad,hi+pad);c.update();app.processEvents();c.grab();counts=c.projection_badge_counts();assert counts['shown']>0 and counts['shown']<=counts['eligible'];assert w.grab().save(str(RUN/'automatic-pnf-chart.png'))
        captured=[];errors=[];attempts=[0]
        def inspect():
            d=app.activeModalWidget();attempts[0]+=1
            if not isinstance(d,QDialog):
                if attempts[0]<30:QTimer.singleShot(50,app,inspect);return
                errors.append('Inspector did not become ready');return
            try:
                text=d.findChild(QTextEdit,'publicProjectionValues');assert text and text.isReadOnly();value=text.toPlainText()
                for token in ('PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1','ORIGINAL_COMPLETED_CLOSE_ONLY','box_size','box_frozen','count_columns',layer['source_epoch']):assert token in value,token
                for z in layer['zones']:assert z['low'] in value
                assert d.grab().save(str(RUN/'automatic-pnf-inspector.png'));captured.append(True)
            except Exception as exc:errors.append(repr(exc))
            finally:d.reject()
        QTimer.singleShot(50,app,inspect);chart.public_details_action.trigger();assert captured and not errors,errors
        # Off via the real checkbox removes only this analytical chart layer.
        r.api(3).navigate('3.1',r.api(3).inspect(symbol='GBPUSD',timeframe='H4'));w.refresh_current(force=True);app.processEvents();panel=w._active_panel();panel.table.scrollToItem(panel.table.item(index,1),QAbstractItemView.PositionAtCenter);box=panel.checkboxes['cause_effect'];assert box.isChecked();QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));r.pump();assert not r.analytics.projections.read('GBPUSD','H4')
        modules={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)};assert all(Path(v).is_relative_to(PACKAGE) for v in modules.values())
        proof.update(result='PASS',actual_checkbox_on_off=True,actual_chart_handoff=True,readonly_inspector_values=True,source_bound=True,source_epoch=layer['source_epoch'],caption_counts=counts,active_objectives=len(layer['zones']),manual_count_request_used=False,viewport_expanded_to_actual_objective_values_only=True,fixture_imports=[n for n in sys.modules if n.startswith('sfm_fx_new_age.testing')],sdk_workers_started=bool(r.connector.workers),product_modules=len(modules))
        assert not proof['fixture_imports'] and not proof['sdk_workers_started']
    finally:
        if w:w.close()
        r.close();app.processEvents();proof['runtime_closed']=r.closed
        (RUN/'native-receipt.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k!='source_epoch'},indent=2))
if __name__=='__main__':main()
