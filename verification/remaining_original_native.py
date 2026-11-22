"""Native P&F original quote check using explicit non-user-adopted research settings."""
from pathlib import Path
import json,sys
from typing import Any
from PySide6.QtWidgets import QApplication,QAbstractItemView,QDialog,QTextEdit
from PySide6.QtCore import Qt,QTimer,QPoint
from PySide6.QtTest import QTest
from remaining_original_checks import OUT,PACKAGE,REQUEST,BODY,request_file,create_runtime
from sfm_fx_new_age.services.point_figure_preparation import prepare_original_point_figure
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.app import create_main_window


def main():
    app=QApplication([]);assert app.platformName()=='xcb';p=request_file('prepared-research');receipt=prepare_original_point_figure(p);r,_=create_runtime(OUT/'prepared-research');w=None
    proof:dict[str,Any]=dict(result='FAIL',scope='RECORDED_ORIGINAL_QUOTES_EXPLICIT_SOFTWARE_CHECK_SETTINGS_NOT_USER_ADOPTED',synthetic_market_observations=0,package_root=str(PACKAGE))
    try:
        w=create_main_window(r);w.resize(1280,850);w.show();w.core_timer.stop();w.poll_timer.stop();app.processEvents()
        r.api(3).navigate('3.1',r.api(3).inspect(symbol='EURUSD',timeframe='H4'));w.refresh_current(force=True);app.processEvents();panel=w._active_panel();assert panel is not None;index=next(i for i,m in enumerate(METHODS) if m.key=='cause_effect');panel.table.scrollToItem(panel.table.item(index,1),QAbstractItemView.PositionAtCenter);panel.table.selectRow(index);app.processEvents()
        box=panel.checkboxes['cause_effect'];assert not box.isChecked();QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));assert box.isChecked();r.pump();panel.refresh();app.processEvents()
        QTest.mouseClick(panel.chart_button,Qt.LeftButton);app.processEvents();w.refresh_current(force=True);panel=w._active_panel();assert panel is not None;c=panel.canvas;c.grab();assert len(c.strategy_layers)==1;layer=c.strategy_layers[0];assert layer['strategy_id']=='cause_effect' and layer['state']=='READY' and len(layer['zones'])==2
        assert layer['metrics']['count_parameters']==REQUEST['parameters'] and 'EXPLICIT_SOFTWARE_VERIFICATION_SETTINGS_NOT_USER_ADOPTED' in layer['metrics']['source_reference']
        prices=[float(b[k]) for b in c.bars[-c.window:] for k in ('low','high')]+[float(z[k]) for z in layer['zones'] for k in ('low','high')];lo,hi=min(prices),max(prices);pad=max((hi-lo)*.08,.0001);c.price_range=(lo-pad,hi+pad);c.update();app.processEvents();c.grab();layout=c.projection_badge_layout();assert len(layout)==2 and layout[0]['rect'].bottom()+1<=layout[1]['rect'].top();assert w.grab().save(str(OUT/'original-point-figure-chart.png'))
        captured=[];errors=[]
        def inspect():
            d=app.activeModalWidget()
            try:
                assert isinstance(d,QDialog);text=d.findChild(QTextEdit,'publicProjectionValues');assert text and text.isReadOnly();value=text.toPlainText()
                for z in layer['zones']:assert z['low'] in value and z['high'] in value
                assert 'count_parameters' in value and 'SOURCE_DECLARED_RESEARCH_SETTINGS_NOT_INDEPENDENT_OPERATOR_APPROVAL' in value and BODY['source_epoch'] in value
                assert d.grab().save(str(OUT/'original-point-figure-details.png'));captured.append(True)
            except Exception as exc:errors.append(repr(exc))
            finally:
                if isinstance(d,QDialog):d.reject()
        QTimer.singleShot(100,app,inspect);panel.public_details_action.trigger();assert captured and not errors,errors
        proof.update(result='PASS',actual_checkbox=True,actual_chart_handoff=True,complete_readonly_count_settings_and_prices=True,caption_counts=c.projection_badge_counts(),completed_columns=receipt['completed_count_columns'],source_epoch_unchanged=layer['source_epoch']==BODY['source_epoch'],sdk_workers_started=bool(r.connector.workers),fixture_imports=[name for name in sys.modules if name.startswith('sfm_fx_new_age.testing')])
        assert not proof['sdk_workers_started'] and not proof['fixture_imports']
    finally:
        if w:w.close()
        r.close();app.processEvents();proof['runtime_closed']=r.closed
        with (OUT/'native-receipt.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
        print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
