"""Native clarity controls on unchanged original observations; no networking."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import json,os,sys,traceback
sys.path.insert(0,str(Path(__file__).resolve().parent))
import tab3_checkbox_projection_checks as original
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QApplication,QDialog
from PySide6.QtTest import QTest
from sfm_fx_new_age.contracts.domain import PAIRS,FRAMES
from sfm_fx_new_age.contracts.public_strategies import METHODS


def run():
    app=QApplication.instance() or QApplication([]);assert app.platformName()=='xcb'
    r=None;w=None;out=original.OUT;proof=dict(result='FAIL',original_observations=True,synthetic_observations=0,broker_mutations=0,network_started=False)
    try:
        r,source=original.runtime();proof['source']=source
        for m in METHODS:r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True))
        r.pump();w=original.window(r,app);p=original.catalogue(r,w,app);saved=deepcopy(r.database.list('recipe_state'))
        # All family/readiness filters are evaluated against actual admitted rows.
        filter_checks=[]
        def visible():return {m.key for i,m in enumerate(METHODS) if not p.table.isRowHidden(i)}
        for i in range(p.family_filter.count()):
            p.family_filter.setCurrentIndex(i);app.processEvents();wanted={m.key for m in METHODS if i==0 or m.family==p.family_filter.currentText()};assert visible()==wanted
            filter_checks.append(dict(kind='family',value=p.family_filter.currentText(),visible=len(wanted)))
        p.family_filter.setCurrentIndex(0)
        state_keys={'Ready':'READY','No setup':'NO_SETUP','Data needed':'DATA_UNAVAILABLE','Errors':'ERROR','Off':'OFF'}
        for i in range(p.state_filter.count()):
            p.state_filter.setCurrentIndex(i);app.processEvents();name=p.state_filter.currentText()
            wanted={m.key for m in METHODS if name=='All states' or (name=='Waiting' and p._rows[m.key]['evaluation']['state'] not in {'READY','NO_SETUP','DATA_UNAVAILABLE','ERROR','OFF'}) or p._rows[m.key]['evaluation']['state']==state_keys.get(name)}
            assert visible()==wanted;filter_checks.append(dict(kind='state',value=name,visible=len(wanted)))
        p._reset_filters();original.click(p,'sma_cross',app,False);p.selected_only.setChecked(True);assert visible()=={m.key for m in METHODS if m.key!='sma_cross'}
        p.search.setText('NO MATCH ORIGINAL TEST');assert not visible() and 'No strategies match' in p.details.toPlainText()
        QTest.mouseClick(p.reset_filters,Qt.LeftButton);app.processEvents();assert len(visible())==83
        original.click(p,'sma_cross',app,True);r.pump();p.refresh();assert r.database.list('recipe_state')==saved
        for size in ((960,640),(1440,900)):
            w.resize(*size);app.processEvents();assert w.grab().save(str(out/f'library-{size[0]}.png'))
            scroll=w.main_tabs.widget(2).currentWidget();assert scroll.verticalScrollBar().maximum()==0
            for control in (p.family_filter,p.state_filter,p.selected_only,p.reset_filters,p.chart_button):assert control.isVisible() and p.rect().contains(control.geometry())
        # Real chart handoff and every focus choice, without changing any recipe.
        p=original.catalogue(r,w,app,'EURUSD','H4');QTest.mouseClick(p.chart_button,Qt.LeftButton);app.processEvents();w.refresh_current(force=True);p=w._active_panel();c=p.canvas;c.grab();bar=p.projection_bar;bar.sync()
        assert bar.focus.count()==84
        focus_checks=[]
        for method in METHODS:
            index=bar.focus.findData(method.key);assert index>=0
            bar.focus.setCurrentIndex(index);app.processEvents();c.grab();assert c.projection_focus==method.key
            assert all(v[1]['strategy_id']==method.key for v in c.public_strategy_geometry())
            assert len(c.public_strategy_layers())==83 and r.database.list('recipe_state')==saved
            focus_checks.append(method.key)
        bar.focus.setCurrentIndex(0);app.processEvents();c.grab()
        # Compact/full size: captions outside the candle/price axes and complete
        # original source rows in the inspector, even when labels are elided.
        compact_checks=[]
        for size in ((960,640),(1440,900)):
            w.resize(*size);app.processEvents();c.grab();bar.sync();items=c.projection_badge_layout();rail=c.projection_caption_rect()
            assert items and rail
            for v in items:
                assert rail.contains(v['rect']) and not v['rect'].intersects(c.plot_rect()) and not v['rect'].intersects(c.price_axis_rect())
            scroll=w.main_tabs.widget(0).currentWidget();assert scroll.verticalScrollBar().maximum()==0
            assert c.height()>=120 and all(control.isVisible() for control in (bar.focus,bar.captions,bar.previous,bar.next,bar.details))
            assert w.grab().save(str(out/f'chart-side-rail-{size[0]}.png'))
            compact_checks.append(dict(size=size,captions=len(items),plot_width=c.plot_rect().width(),canvas_height=c.height()))
        w.resize(960,640);app.processEvents();before_height=c.height();QTest.mouseClick(bar.chart_only,Qt.LeftButton);app.processEvents();c.grab()
        assert c.height()>before_height and p.health.isVisible() and bar.isVisible() and not p.settings.isVisible()
        bar.focus.setCurrentIndex(bar.focus.findData('profile_tpo'));app.processEvents();c.grab();assert w.grab().save(str(out/'chart-focus-compact.png'))
        QTest.mouseClick(bar.chart_only,Qt.LeftButton);app.processEvents();assert p.settings.isVisible();bar.focus.setCurrentIndex(0);w.resize(1440,900);app.processEvents();c.grab();bar.sync()
        # Walk actual next/previous page buttons. Compare complete multisets,
        # including distinct records sharing label/price, not just a row count.
        c.set_projection_page(0);c.grab();bar.sync();area=c.plot_rect()
        expected=Counter((v[1],v[3]) for v in c._projection_badge_entries() if area.top()<=v[0]<=area.bottom())
        seen=Counter();status=c.projection_caption_status();pages=status['pages'];assert pages>1
        for i in range(pages):
            c.grab();bar.sync();status=c.projection_caption_status();assert status['page']==i
            seen.update((v['price'],v['label']) for v in c.projection_badge_layout())
            if i+1<pages:assert bar.next.isEnabled();QTest.mouseClick(bar.next,Qt.LeftButton);app.processEvents()
        assert seen==expected and not bar.next.isEnabled();QTest.mouseClick(bar.previous,Qt.LeftButton);app.processEvents();assert c.projection_caption_status()['page']==pages-2
        # Hide captions, never geometry, and restore. Persist placement only.
        layers=deepcopy(c.strategy_layers);bar.captions.setCurrentText('Hidden');app.processEvents();c.grab();bar.sync()
        assert c.public_strategy_geometry() and not c.projection_badge_layout() and c.strategy_layers==layers
        bar.captions.setCurrentText('Side rail');app.processEvents();c.grab();bar.sync()
        bar.focus.setCurrentIndex(bar.focus.findData('profile_tpo'));app.processEvents();c.grab();assert w.grab().save(str(out/'chart-focused-tpo.png'))
        dialogs=[];errors=[]
        def inspect_details(attempt=0):
            d=app.activeModalWidget()
            if d is None and attempt<60:QTimer.singleShot(10,lambda:inspect_details(attempt+1));return
            try:
                assert isinstance(d,QDialog) and d.objectName()=='publicProjectionDetails'
                assert d.picker.count()==83 and d.values.isReadOnly()
                for key in ('profile_tpo','volume_profile','vwap_bands','footprint_delta','dom_imbalance'):
                    d.picker.setCurrentIndex(d.picker.findData(key));text=d.values.toPlainText();assert key in text and 'LIVE_OBSERVED' in text
                assert d.grab().save(str(out/'projection-details.png'));dialogs.append(True)
            except Exception as e:errors.append(type(e).__name__)
            finally:
                if d:d.reject()
        QTimer.singleShot(0,inspect_details);QTest.mouseClick(bar.details,Qt.LeftButton);assert dialogs==[True] and not errors
        # Source/frame transitions cannot retain a different chart's focus.
        contexts=[]
        for symbol in PAIRS:
            for frame in FRAMES:
                r.api(1).navigate(original.VIEWS[frame],r.api(1).inspect(symbol=symbol,timeframe=frame));app.processEvents();w.refresh_current(force=True);p=w._active_panel();c=p.canvas;c.grab();p.projection_bar.sync()
                assert c.data_identity[2:]==(symbol,frame) and c.projection_focus is None
                assert len(c.strategy_layers)==83;contexts.append([symbol,frame])
        assert r.database.list('recipe_state')==saved
        proof.update(result='PASS_NATIVE_CLARITY_ORIGINAL_REPLAY',filter_checks=filter_checks,focus_strategies=focus_checks,compact_checks=compact_checks,paged_levels=sum(seen.values()),caption_pages=pages,chart_contexts=contexts,all_original_layers_preserved=True,fixture_imports=[])
        assert not r.connector.workers and not r.connector.requests and not r.database.list('order')
    except Exception as exc:
        proof.update(error_type=type(exc).__name__,error=str(exc));traceback.print_exc();raise
    finally:
        if w:w.close()
        if r:r.close()
        app.processEvents();proof['runtime_closed']=not r or r.closed
        origins={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)}
        assert all(Path(v).is_relative_to(original.PACKAGE) for v in origins.values());proof['product_origins']=origins
        proof['fixture_imports']=[v for v in origins if v.startswith('sfm_fx_new_age.testing')];assert not proof['fixture_imports']
        (out/'clarity-receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps({k:v for k,v in proof.items() if k not in {'product_origins','filter_checks','focus_strategies','chart_contexts'}},indent=2))


if __name__=='__main__':run()
