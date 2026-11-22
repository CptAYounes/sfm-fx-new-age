"""Explicit offline acceptance of cross-workspace user journeys, not strategy/broker proof."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.contracts.analytics import Level,Lineage
from sfm_fx_new_age.contracts.domain import Origin,instant
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,FIXTURE_EPOCH
from sfm_fx_new_age.ui.inspection_panels import row_context,identity
from test_cross_lane_candidate_binding import pipeline


def drain(app,r,n=5):
    for _ in range(n):r.pump();app.processEvents()


@pytest.fixture
def shell(runtime):
    app=QApplication.instance() or QApplication([]);w=create_main_window(runtime);w.resize(960,640);w.show();drain(app,runtime)
    w.core_timer.stop();w.poll_timer.stop()
    yield app,w
    w.close();app.processEvents()


def test_navigation_return_and_manual_pair_change_preserve_four_workspaces(shell,runtime):
    app,w=shell;chart=w._active_panel();chart._open_in('3.5');drain(app,runtime)
    assert w.main_tabs.currentIndex()==2 and w._active_panel().context['symbol']=='EURUSD'
    assert w.return_button.isEnabled();w.return_button.click();drain(app,runtime)
    assert w.main_tabs.currentIndex()==0 and w._active_panel().context['symbol']=='EURUSD'
    w.subtab_picker.setCurrentIndex(1);drain(app,runtime)
    assert runtime.selected_pair=='GBPUSD' and 'GBPUSD' in w._active_panel().heading.text() and w._active_panel().context is None
    assert w.main_tabs.count()==4 and [len(runtime.api(i).definitions) for i in (1,2,3,4)]==[10,10,13,9]
    assert not runtime.orders.transport.submissions


def test_chart_measurement_to_calculator_is_opt_in_and_never_overwrites_edits(shell,runtime):
    app,w=shell;c=w._active_panel();c.canvas.ruler=((FIXTURE_NOW,1.1),(FIXTURE_NOW,1.101))
    c._open_in('calculator');drain(app,runtime)
    tool=w.tools.windows['forex-calculator'].widget().widget()
    assert not tool.inputs['entry'].text() and not tool.inputs['exit'].text()
    tool.inputs['entry'].setText('1.2');tool.use_chart.click()
    assert tool.inputs['entry'].text()=='1.2' and tool.inputs['exit'].text()=='1.101'
    tool.replace_prices.click();assert tool.inputs['entry'].text()=='1.1'
    tool.use_specs.click();assert tool.contract.text()=='100000' and tool.pip_size.text()=='0.0001'
    assert 'Broker specification' in tool.provenance.text()
    assert not runtime.orders.transport.submissions and not runtime.database.orders()


def test_stale_handoff_keeps_calculator_manual_prices(shell,runtime):
    app,w=shell;c=w._active_panel();c._open_in('calculator');drain(app,runtime)
    tool=w.tools.windows['forex-calculator'].widget().widget();tool.inputs['entry'].setText('1.2')
    runtime.market.activate_source('EURUSD','RECONNECTED',Origin.SYNTHETIC_FIXTURE.value)
    tool.replace_prices.click();assert tool.inputs['entry'].text()=='1.2' and 'refused' in tool.provenance.text()


def test_calculator_historical_context_has_no_future_quote(runtime):
    ctx=runtime.api(1).inspect(symbol='EURUSD',as_of='2026-10-01T00:00:00Z')
    data=runtime.api(2).calculator_context(ctx)
    assert data['quote'] is None and not data['quotes']


def test_causal_replay_create_step_seek_play_and_research_share_one_clock(shell,runtime):
    app,w=shell;w.chart_tabs.setCurrentIndex(8);drain(app,runtime);p=w._active_panel();p.frame_picker.setCurrentIndex(0)
    p.replay_create.click();drain(app,runtime);run=p.run_id
    assert run and not p.canvas.bars and 'REPLAY' in p.origin.text() and not p.canvas._quotes
    p.replay_buttons['STEP'].click();drain(app,runtime)
    assert len(p.canvas.bars)==1 and p.canvas.bars[0]['scope_id']=='REPLAY:'+run
    p.replay_seek.setValue(4);p._replay_control('SEEK');drain(app,runtime)
    assert len(p.canvas.bars)==5
    ctx=p.inspection_context();p.api.navigate('3.12',ctx);drain(app,runtime)
    research=w._active_panel();research.dataset.setCurrentIndex(research.dataset.findData('replay_runs'));research.refresh()
    for i,row in enumerate(research._rows):
        if row['run_id']==run:research.table.selectRow(i);break
    research.controls['PLAY'].click();drain(app,runtime)
    research.controls['PAUSE'].click();drain(app,runtime)
    value=runtime.replay.snapshot(run)
    assert value['cursor']>4 and value['state']=='PAUSED'
    research.show_run();drain(app,runtime)
    assert w._active_panel().run_id==run and len(w._active_panel().canvas.bars)==value['cursor']+1
    assert not runtime.orders.transport.submissions


def test_saved_drawing_and_preferences_reload_in_a_second_chart_view(shell,runtime):
    app,w=shell;p=w._active_panel();p.style.setCurrentText('Line');p.canvas.drawings.add('Level',[(p.canvas.bars[-1]['open_time'],1.1)]);p._save_workspace()
    w.chart_tabs.setCurrentIndex(2);drain(app,runtime);other=w._active_panel()
    assert other.canvas.style=='Line' and other.canvas.drawings.items[0]['anchors'][0][1]==1.1
    other.canvas.drawings.modify(other.canvas.drawings.items[0]['id'],color='#AABBCC');other._save_workspace()
    p.canvas.drawings.modify(p.canvas.drawings.items[0]['id'],color='#ABCDEF');p._save_workspace()
    assert p._workspace_blocked and 'version conflict' in p.workflow_status.text()
    p._reload_workspace();assert not p._workspace_blocked and p.canvas.drawings.items[0]['color']=='#AABBCC'
    assert not runtime.api(3).query('3.5',DataRequest('levels'))['rows']


def test_history_button_is_explicit_bounded_and_deduplicated(shell,runtime):
    app,w=shell;p=w._active_panel();before=runtime.database.list('backfill');assert not before
    p._older_history(30);jobs=runtime.database.list('backfill');assert len(jobs)==1
    p._older_history(30);assert len(runtime.database.list('backfill'))==1
    assert 'QUEUED' in p.workflow_status.text() and 'bounded' in p.workflow_status.text()
    with pytest.raises(ValueError):p.api.request_older_history(p.inspection_context(),367)
    assert not runtime.orders.transport.submissions


def test_refresh_subscriptions_do_not_reread_idle_hidden_pages(shell,runtime,monkeypatch):
    app,w=shell;calls=[];query=runtime.tab_data.query
    monkeypatch.setattr(runtime.tab_data,'query',lambda view,q:(calls.append((view,q.dataset)),query(view,q))[1])
    w.refresh_current(force=True);first=len(calls);assert first>0
    calls.clear()
    for _ in range(10):w.refresh_current()
    assert not calls
    quote=runtime.market.quote(runtime.accounts.current.account_id,'EURUSD')
    runtime.market.set_quote(replace(quote,sequence=quote.sequence+1));runtime.flush_if_owner();w.refresh_current()
    assert calls and all(view.startswith('1.') for view,ds in calls)


def test_candidate_bind_preview_and_ack_reset_through_real_widgets(pipeline):
    r,payload,_=pipeline;app=QApplication.instance() or QApplication([]);w=create_main_window(r);w.resize(960,640);w.show()
    try:
        ctx=r.api(3).inspect(symbol='EURUSD',timeframe='D1',object_kind='market_candidate',object_id=payload['candidate_id'],revision=1)
        r.api(3).navigate('4.2',ctx);drain(app,r);p=w._active_panel()
        assert p.selected()['candidate_id']==payload['candidate_id'] and p.variant.count()>0
        assert not p.acknowledge.isChecked();p.units.setText('1000');p.bind.click();drain(app,r)
        assert p.selected()['market_candidate_id']==payload['candidate_id']
        assert 'acknowledgement' in p.preview_text.toPlainText() and not r.database.orders()
        p.acknowledge.setChecked(True);p.preflight.click();drain(app,r)
        assert 'PREFLIGHT_VALID' in p.preview_text.toPlainText() and not r.orders.transport.submissions
        p.queue.click();drain(app,r);queue=w._active_panel()
        assert queue.pages.currentIndex()==1
        queue=queue.queue
        assert queue.model.subtab_id=='4.1' and not queue.acknowledge.isChecked()
        queue.acknowledge.setChecked(True);queue.refresh();idx=next(i for i,row in enumerate(queue._rows) if row['signal_id']=='FIXTURE-SIGNAL-1');queue.table.selectRow(idx)
        assert not queue.acknowledge.isChecked() and not queue.buttons['ISSUE'].isEnabled()
        assert not r.orders.transport.submissions
    finally:w.close();app.processEvents()


def test_evidence_identity_cannot_be_confused_with_its_parent_level(pipeline):
    r,_,_=pipeline;e=r.api(3).query('3.5',DataRequest('evidence'))['rows'][0]
    ctx=row_context(r.api(3),thaw(e))
    assert ctx['object_kind']=='evidence' and ctx['object_id']==e['evidence_id'] and identity(e)==e['evidence_id']
    assert r.api(3).inspection_object(ctx)['evidence_id']==e['evidence_id']


def test_research_regions_start_at_availability_not_at_historical_left_edge(shell,runtime):
    app,w=shell;w.chart_tabs.setCurrentIndex(1);drain(app,runtime);p=w._active_panel();bars=p.canvas.bars;line=Lineage(runtime.market.scope_id,FIXTURE_EPOCH,'EURUSD','W1',bars[-2]['close_time'],Origin.SYNTHETIC_FIXTURE,'TEST','PROFILE')
    from sfm_fx_new_age.contracts.domain import record
    level=record(Level('late-zone',1,'SYNTHETIC_TEST_ZONE',Decimal('1.09'),Decimal('1.11'),'BUY','CONFIRMED',('root',),line))
    p.canvas.levels=[level];p.canvas.grab();regions=p.canvas.research_regions();assert len(regions)==1
    assert regions[0][1].left()>p.canvas.plot_rect().left()+p.canvas.plot_rect().width()/2
    p.canvas.levels=[dict(level,lineage=dict(level['lineage'],source_epoch='OTHER'))];assert not p.canvas.research_regions()


def test_native_position_and_local_order_are_visually_and_semantically_distinct(shell,runtime):
    app,w=shell;runtime.positions.replace_snapshot(runtime.market.scope_id,[{'position_id':'NATIVE-P','symbol':'EURUSD','side':'BUY','units':'1000','entry_price':'1.1'}],observed_at=FIXTURE_NOW,origin='SYNTHETIC_FIXTURE',complete=True)
    w.chart_tabs.setCurrentIndex(9);drain(app,runtime);p=w._active_panel();p.refresh()
    assert p.canvas.broker_visuals[0]['category']=='Broker position · last observed'
    assert p.canvas.broker_visuals[0]['position_id']=='NATIVE-P' and not runtime.database.orders()
    p._select_evidence('NATIVE-P');p._open_in('4.3');drain(app,runtime)
    assert w._active_panel().model.subtab_id=='4.6' and w._active_panel().selected()['position_id']=='NATIVE-P'
    with pytest.raises(ValueError):runtime.api(3).inspection_object(p.inspection_context() if not p._selected_record() else row_context(p.api,p._selected_record()))
    w._active_panel().show_chart.click();drain(app,runtime)
    assert w._active_panel().model.subtab_id=='1.10' and w._active_panel().canvas.broker_visuals[0]['position_id']=='NATIVE-P'


def test_acknowledgement_resets_for_same_signal_new_revision(shell,runtime):
    from sfm_fx_new_age.contracts.domain import Candidate
    app,w=shell;w.main_tabs.setCurrentIndex(3);drain(app,runtime);workspace=w._active_panel();workspace.pages.setCurrentIndex(1);drain(app,runtime)
    p=workspace.queue;p.table.selectRow(0);p.acknowledge.setChecked(True)
    original=runtime.signals.get('FIXTURE-SIGNAL-1');fields={k:original[k] for k in Candidate.__dataclass_fields__ if k in original}
    runtime.signals.propose(Candidate(**(fields|{'revision':2})));p.refresh()
    assert p._selection()['revision']==2 and not p.acknowledge.isChecked() and not p.buttons['ISSUE'].isEnabled()


def test_closed_tool_does_not_retain_runtime_authority(shell,runtime):
    app,w=shell;w.main_tabs.setCurrentIndex(1);f=w.tools.open_tool('forex-calculator');api=f.api
    f.close();app.sendPostedEvents(None,0);app.processEvents()
    with pytest.raises(RuntimeError):api.inspect(symbol='EURUSD')
    assert not runtime.closed


def test_broker_inventory_is_not_implicitly_selected_for_research(shell,runtime):
    app,w=shell
    runtime.positions.replace_snapshot(runtime.market.scope_id,[{'position_id':'NATIVE-P','symbol':'EURUSD','side':'BUY','units':'1000','entry_price':'1.1'}],observed_at=FIXTURE_NOW,origin='SYNTHETIC_FIXTURE',complete=True)
    p=w._active_panel();p.refresh()
    assert p._objects and p._selected_record() is None and not p.inspect_button.isEnabled()
    p._open_in('3.5');drain(app,runtime)
    assert w._active_panel().model.subtab_id=='3.5' and w._active_panel().context['object_kind'] is None
    w.return_button.click();drain(app,runtime);p=w._active_panel();p.clear_inspection();p._select_evidence('NATIVE-P')
    p._open_in('3.5');drain(app,runtime)
    assert w._active_panel() is p and 'Broker' in p.workflow_status.text()
