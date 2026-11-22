"""Every Tab3 switch -> chart query -> native chart/inspector, on originals only.

Recorded-clock native replay, not a new connected-feed acceptance or trade test.
The normal application database and its saved switches are never opened writable.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from time import monotonic
import hashlib,json,os,sqlite3,sys,traceback
from typing import Any
PACKAGE=Path(os.environ['SFM_TAB3_PACKAGE']).resolve(strict=True);sys.path.insert(0,str(PACKAGE))
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QAbstractItemView
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.domain import AccountContext,PAIRS,FRAMES,instant
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.tabs.tab3.public_activity_alternatives import ACTIVITY_NAMES
from sfm_fx_new_age.ui.chart_projection_details import PublicProjectionDetails
from sfm_fx_new_age.ui.chart_canvas import CandleCanvas
CAPTURE=Path(os.environ['SFM_TAB3_CAPTURE']).resolve(strict=True)
OUT=Path(os.environ['SFM_TAB3_OUT']);OUT.mkdir(parents=True,mode=0o700,exist_ok=False)
DEPTH=json.loads((CAPTURE/'broker-depth-envelopes.json').read_bytes())
CUTOFF=max((v['available_at'] for v in DEPTH.values()),key=instant)
assert all(instant(CUTOFF)<instant(v['valid_until']) for v in DEPTH.values())
SOURCE=CAPTURE/'state.sqlite3';ROSTER={m.key for m in METHODS}
VIEWS={'W1':'1.2','D1':'1.3','H4':'1.4','H1':'1.5'}
START=int(os.environ.get('SFM_TAB3_START','0'));STOP=int(os.environ.get('SFM_TAB3_STOP','83'))
assert 0<=START<STOP<=83


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def append(name,value):
    with (OUT/name).open('a') as f:f.write(canon(value)+'\n');f.flush()
def query(r,symbol,frame,historical=False):
    return thaw(r.api(1).query(VIEWS[frame],DataRequest('chart',symbol=symbol,timeframe=frame,limit=5000,as_of=CUTOFF if historical else None)))
def runtime(existing=False):
    r=ApplicationRuntime(OUT/'state.sqlite3',clock=lambda:CUTOFF,activity_alternatives=True)
    c=sqlite3.connect(SOURCE.as_uri()+'?mode=ro',uri=True)
    try:
        c.execute('PRAGMA query_only=ON')
        rows=c.execute("SELECT kind,id,body FROM records WHERE kind IN ('account_metadata','authority','spec','bar','quote')").fetchall()
        optional=[json.loads(b) for b, in c.execute("SELECT body FROM records WHERE kind='supplemental_evidence' AND json_extract(body,'$.kind')!='BROKER_DEPTH'")]
    finally:c.close()
    if not existing:
        with r.database.transaction() as c:c.executemany('INSERT INTO records VALUES(?,?,?)',rows)
    metadata=r.database.get('account_metadata',DEPTH['EURUSD']['scope_id']);assert metadata
    r.accounts.select(AccountContext(**{k:v for k,v in metadata.items() if k!='scope_id'}))
    admitted=[]
    for data in [*optional,*DEPTH.values()]:
        if instant(data['available_at'])>instant(CUTOFF):continue
        provider=data['provider_id']
        if provider not in r.analytics.supplemental.providers:r.analytics.supplemental.register_provider(provider,kinds=[data['kind']],origin='LIVE_OBSERVED')
        r.analytics.supplemental.accept(SupplementalEvidence(**dict(data,records=tuple(data['records']))));admitted.append(provider)
    # H1 is an existing optional chart; enable it in the isolated test state.
    r.consumers.set_enabled('display.1.5',True)
    return r,dict(input_rows=len(rows),source_rows_sha256=hashlib.sha256(canon(rows).encode()).hexdigest(),admitted_envelopes=len(admitted),cutoff=CUTOFF)
def window(r,app):
    w=create_main_window(r);w.resize(1360,960);w.show();w.core_timer.stop();w.poll_timer.stop();app.processEvents();return w
def catalogue(r,w,app,symbol='EURUSD',frame='H4'):
    r.api(3).navigate('3.1',r.api(3).inspect(symbol=symbol,timeframe=frame));w.refresh_current(force=True);app.processEvents();p=w._active_panel()
    assert p.objectName()=='subtab_3_1' and len(p.checkboxes)==len(ROSTER)==83
    assert p.table.rowCount()==83 and set(p.checkboxes)==ROSTER
    return p
def click(p,key,app,wanted):
    index=next(i for i,m in enumerate(METHODS) if m.key==key)
    p.table.scrollToItem(p.table.item(index,1),QAbstractItemView.PositionAtCenter);p.table.selectRow(index);app.processEvents();box=p.checkboxes[key]
    assert box.isEnabled() and box.isVisible() and box.objectName()=='standardStrategy_'+key
    assert box.isChecked()!=wanted
    QTest.mouseClick(box,Qt.LeftButton,pos=QPoint(8,box.height()//2));app.processEvents();assert box.isChecked()==wanted

def searches(p,app):
    checks=[]
    for i,m in enumerate(METHODS):
        for label in {m.name,p.table.item(i,1).text()}:
            p.search.setText(label);app.processEvents();visible=[METHODS[j].key for j in range(83) if not p.table.isRowHidden(j)]
            assert m.key in visible,dict(key=m.key,search=label,visible=visible)
            checks.append(dict(key=m.key,label=label,found=True))
    p.search.clear();app.processEvents();assert not any(p.table.isRowHidden(i) for i in range(83));return checks

def matrix(r,w,app,baseline):
    results=[];lanes=0
    # Reuse the actual renderer, not 2,324 repeated whole-window navigations.
    # Normal ChartPanel/button integration is independently exercised on all 28
    # charts in the mixed-selection phase below; no data/geometry is modelled.
    canvas=CandleCanvas();canvas.resize(1100,650);canvas.show();app.processEvents()
    # Start with an actual native OFF transition for every row, then exercise
    # each row alone so any unrelated projected strategy is a hard failure.
    p=catalogue(r,w,app)
    for m in METHODS:click(p,m.key,app,False)
    r.pump();p.refresh();assert not any(v.isChecked() for v in p.checkboxes.values())
    for m in METHODS[START:STOP]:
        started=monotonic();p=catalogue(r,w,app);click(p,m.key,app,True);r.pump();p.refresh()
        stored=r.database.get('recipe_state',m.recipe_id);assert stored and stored['enabled'] is True
        method=[]
        for symbol in PAIRS:
            authority=r.market.authority(symbol);assert authority
            for frame in FRAMES:
                data=query(r,symbol,frame);past=query(r,symbol,frame,True)
                assert len(data['strategy_layers'])==len(past['strategy_layers'])==1
                layer=data['strategy_layers'][0];assert layer['strategy_id']==m.key and layer==past['strategy_layers'][0]
                assert canon(layer)==canon(baseline[(symbol,frame)][m.key])
                expected=(r.market.scope_id,authority['source_epoch'],symbol,frame)
                assert (layer['scope_id'],layer['source_epoch'],layer['symbol'],layer['timeframe'])==expected
                canvas.set_data(data['rows'],symbol+' / '+frame,expected,levels=data.get('levels',[])+data.get('overlays',[]),studies=data.get('studies'))
                canvas.offset=0;canvas.price_range=None;canvas.strategy_layers=data['strategy_layers'];canvas.public_filters_applied=True
                assert canvas.grab().width()>0 and canvas.data_identity==expected
                assert [v['strategy_id'] for v in canvas.public_strategy_layers()]==[m.key]
                geometry=canvas.public_strategy_geometry();assert all(v[1]['strategy_id']==m.key for v in geometry)
                if layer['state'] not in {'READY','NO_SETUP'}:assert not geometry
                # The original order-block profile has its own typed region path.
                regions=canvas.research_regions()
                own_regions=[v for v in regions if v[0].get('lineage',{}).get('method_version')=='SFM_OB_CLOSED_PIVOT_RESEARCH_V1']
                if m.key!='order_block':assert not own_regions
                # Wrong-pair originals must be rejected even if a consumer hands
                # them to the canvas. They are not new or retimed observations.
                other=next(s for s in PAIRS if s!=symbol)
                canvas.strategy_layers=[layer,baseline[(other,frame)][m.key]]
                assert canvas.public_strategy_layers()==[layer]
                canvas.strategy_layers=[layer]
                dialog=PublicProjectionDetails(canvas,canvas)
                try:
                    assert dialog.picker.count()==1 and dialog.picker.currentData()==m.key and dialog.values.isReadOnly()
                    text=dialog.values.toPlainText();assert m.key in text and layer['source_epoch'] in text and layer['name'] in text
                    if m.key in ACTIVITY_NAMES and layer['metrics'].get('alternative'):assert ACTIVITY_NAMES[m.key] in text
                finally:dialog.reject()
                checked=dict(strategy=m.key,symbol=symbol,timeframe=frame,state=layer['state'],exact_identity=True,projection_hash=hashlib.sha256(canon(layer).encode()).hexdigest(),painted_geometry=len(geometry),typed_order_block_regions=len(own_regions),inspector=True)
                append('lanes.jsonl',checked);method.append(checked);lanes+=1
        p=catalogue(r,w,app);click(p,m.key,app,False)
        assert r.database.get('recipe_state',m.recipe_id)['enabled'] is False
        for symbol in PAIRS:
            for frame in FRAMES:
                assert query(r,symbol,frame)['strategy_layers']==[] and query(r,symbol,frame,True)['strategy_layers']==[]
        # Feed the actual withdrawn chart payload back through the renderer.
        canvas.strategy_layers=query(r,'NZDUSD','H1')['strategy_layers'];canvas.grab()
        assert not canvas.strategy_layers and not canvas.public_strategy_layers() and not canvas.public_strategy_geometry()
        assert not [v for v in canvas.research_regions() if v[0].get('lineage',{}).get('method_version')=='SFM_OB_CLOSED_PIVOT_RESEARCH_V1']
        r.pump();result=dict(key=m.key,lanes=len(method),on_off=True,off_chart_layers=0,states=dict(Counter(v['state'] for v in method)),seconds=round(monotonic()-started,3));append('methods.jsonl',result);results.append(result)
        if len(results)%10==0:print(json.dumps(dict(completed_methods=len(results),completed_lanes=lanes)),flush=True)
    canvas.close()
    assert len(results)==len({v['key'] for v in results})==STOP-START and lanes==(STOP-START)*len(PAIRS)*len(FRAMES)
    return results

def main():
    app=QApplication.instance() or QApplication([]);assert app.platformName()=='xcb'
    r=None;w=None;proof:dict[str,Any]=dict(result='FAIL',scope='RECORDED_ORIGINAL_X11_SWITCH_TO_CHART_CHECK_NOT_NEW_FEED_OR_SETUP',normal_database_written=False,network_started=False,broker_mutations=0)
    try:
        r,source=runtime();proof['source']=source
        for m in METHODS:assert r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True)).status.value=='ACCEPTED'
        r.pump();baseline={}
        for symbol in PAIRS:
            for frame in FRAMES:
                rows=query(r,symbol,frame)['strategy_layers'];assert len(rows)==83 and not any(v['state']=='ERROR' for v in rows)
                baseline[(symbol,frame)]={v['strategy_id']:v for v in rows}
        w=window(r,app);p=catalogue(r,w,app)
        assert all(box.isChecked() for box in p.checkboxes.values())
        proof['search_checks']=searches(p,app)
        assert w.grab().save(str(OUT/'all-83-tab3.png'))
        if os.environ.get('SFM_TAB3_SEARCH_ONLY')=='1':proof['result']='PASS_ALL_DISPLAYED_AND_ORIGINAL_NAME_SEARCHES';return
        proof['methods']=matrix(r,w,app,baseline)
        # Mixed selection, chart-button navigation and exact frame handoff.
        p=catalogue(r,w,app);selected={m.key for i,m in enumerate(METHODS) if i%2==0}
        for m in METHODS:
            if m.key in selected:click(p,m.key,app,True)
        r.pump();p.refresh();assert w.grab().save(str(OUT/'mixed-tab3-selection.png'))
        for symbol in PAIRS:
            for frame in FRAMES:
                p=catalogue(r,w,app,symbol,frame);QTest.mouseClick(p.chart_button,Qt.LeftButton);w.refresh_current(force=True);app.processEvents();c=w._active_panel().canvas;c.grab()
                assert c.data_identity[2:]==(symbol,frame) and {v['strategy_id'] for v in c.strategy_layers}==selected
        assert w.grab().save(str(OUT/'mixed-forex-chart.png'))
        # Persist a nontrivial subset and verify construction after close/reopen.
        w.close();w=None;r.close();r=None
        r,source=runtime(existing=True);w=window(r,app);p=catalogue(r,w,app)
        assert {key for key,box in p.checkboxes.items() if box.isChecked()}==selected
        proof.update(result='PASS_DECLARED_NATIVE_CHECKBOX_CHART_BATCH',catalogue_strategies=83,tested_strategies=len(proof['methods']),method_range=[START,STOP],pair_frame_lanes=len(proof['methods'])*28,mixed_selection=len(selected),mixed_chart_button_handoffs=28,restart_selection_preserved=True,synthetic_observations=0)
        assert not r.connector.workers and r.connector.analytical_feed is None
        assert not r.database.list('order') and not r.connector.requests
    except Exception as exc:
        proof.update(error_type=type(exc).__name__,error=str(exc));traceback.print_exc();raise
    finally:
        if w:w.close()
        if r:r.close()
        app.processEvents();proof['runtime_closed']=not r or r.closed
        origins={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)}
        proof['fixture_imports']=[k for k in origins if k.startswith('sfm_fx_new_age.testing')];proof['product_origins']=origins
        assert origins and all(Path(v).is_relative_to(PACKAGE) for v in origins.values()) and not proof['fixture_imports']
        with (OUT/'receipt.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
        print(json.dumps({k:v for k,v in proof.items() if k not in {'product_origins','methods','search_checks'}},indent=2))


if __name__=='__main__':main()
