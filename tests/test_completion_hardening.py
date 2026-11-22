"""Boundary/recovery acceptance for finished cross-workspace journeys; no real broker."""
from dataclasses import replace
import pytest
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,FIXTURE_EPOCH
from test_workspace_ui_workflows import shell,drain


def test_inspector_recovers_identical_rows_after_transient_query_failure(shell,runtime,monkeypatch):
    app,w=shell;w.main_tabs.setCurrentIndex(2);w.main_tabs.widget(2).setCurrentIndex(12);drain(app,runtime);p=w._active_panel();p.dataset.setCurrentIndex(p.dataset.findData('signals'));p.refresh();original=p.api.query
    assert p._rows
    monkeypatch.setattr(p.api,'query',lambda *a:(_ for _ in ()).throw(ValueError('temporary unavailable')))
    p.refresh();assert not p._rows and p.table.rowCount()==0
    monkeypatch.setattr(p.api,'query',original);p.refresh()
    assert p._rows and p.table.rowCount()==len(p._rows)


def test_handoff_frame_is_used_by_research_bar_query(shell,runtime):
    app,w=shell;ctx=runtime.api(1).inspect(symbol='EURUSD',timeframe='W1')
    runtime.api(1).navigate('3.2',ctx);drain(app,runtime);p=w._active_panel()
    p.dataset.setCurrentIndex(p.dataset.findData('bars'));p.refresh()
    assert p._rows and all(row['timeframe']=='W1' for row in p._rows)


def test_historical_chart_never_labels_current_scanner_state_as_past(runtime):
    data=runtime.api(1).query('1.3',DataRequest('chart',as_of='2026-10-01T00:00:00Z'))
    assert data['readiness']['classification']=='HISTORICAL_CONTEXT_ONLY'
    assert 'position_observation' not in data
    assert not data['readiness']['unavailable_methods']


def test_future_signal_cannot_be_captured_under_earlier_inspection(runtime):
    with pytest.raises(ValueError,match='not available'):
        runtime.api(1).inspect(symbol='EURUSD',as_of='2026-10-01T00:00:00Z',object_kind='signal',object_id='FIXTURE-SIGNAL-1')


def test_failed_navigation_is_visible_and_keeps_current_view_and_return_stack(shell,runtime):
    app,w=shell;ctx=thaw(runtime.api(1).inspect(symbol='EURUSD'));runtime.market.activate_source('EURUSD','NEW', 'SYNTHETIC_FIXTURE')
    before=list(w._navigation_history);page=w._active_panel();w._navigate('3.5',ctx)
    assert w._active_panel() is page and w._navigation_history==before
    assert w.inspection_label.isVisible() and 'refused' in w.inspection_label.text()


def test_calculator_side_remains_consistent_with_opt_in_quote(shell,runtime):
    app,w=shell;c=w._active_panel();ctx=runtime.api(1).inspect(symbol='EURUSD',scenario={'side':'BUY'})
    runtime.api(1).navigate('calculator',ctx);drain(app,runtime);tool=w.tools.windows['forex-calculator'].widget().widget()
    tool.side.setCurrentText('SELL');tool.use_chart.click()
    assert tool.side.currentText()=='SELL'
    assert tool.inputs['entry'].text()==str(runtime.market.quote(runtime.accounts.current.account_id,'EURUSD').bid)


def test_current_only_inspector_explicitly_labels_reference_not_historical(shell,runtime):
    app,w=shell;ctx=runtime.api(1).inspect(symbol='EURUSD',as_of='2026-10-01T00:00:00Z')
    runtime.api(1).navigate('3.5',ctx);drain(app,runtime);p=w._active_panel()
    assert p.dataset.currentData()=='analytics'
    assert 'CURRENT' in p.context_label.text() and 'reference' in p.context_label.text().lower()
    p.dataset.setCurrentIndex(p.dataset.findData('levels'));p.refresh()
    assert 'as of' in p.context_label.text() and '2026-10-01' in p.context_label.text()


def test_refused_pagination_recovers_and_previous_goes_one_page(shell,runtime):
    app,w=shell;w.main_tabs.setCurrentIndex(2);drain(app,runtime);p=w._active_panel()
    # Multi-page explicit offline input via declared shared parameter catalogue.
    for i in range(450):runtime.database.put('parameter_definition','test:'+str(i),{'key':'test:'+str(i)})
    nested=w.main_tabs.widget(2);nested.setCurrentIndex(10);editor=w._active_panel();editor.inspect_registry.click();p=editor._inspector.panel;p.dataset.setCurrentIndex(p.dataset.findData('parameter_definitions'));p.refresh()
    p.next.click();p.next.click();assert p._cursor==400
    p.previous.click();assert p._cursor==200


def test_disappeared_selection_does_not_leave_stale_detail_buttons(shell,runtime):
    app,w=shell;w.main_tabs.setCurrentIndex(2);nested=w.main_tabs.widget(2);nested.setCurrentIndex(12);drain(app,runtime);p=w._active_panel()
    p.dataset.setCurrentIndex(p.dataset.findData('signals'));p.table.selectRow(0);p.refresh();assert p.selected()
    query=p.api.query
    def unavailable(*args):raise ValueError('source unavailable')
    p.api.query=unavailable;p.refresh();assert not p.show_chart.isEnabled() and not p.review.isEnabled()
    p.api.query=query;p.refresh();assert p._rows and p.table.rowCount()>0


def test_calculator_explicit_replacement_adopts_direction_and_matching_side(shell,runtime):
    app,w=shell;ctx=runtime.api(1).inspect(symbol='EURUSD',scenario={'side':'BUY'})
    runtime.api(1).navigate('calculator',ctx);drain(app,runtime);tool=w.tools.windows['forex-calculator'].widget().widget()
    tool.side.setCurrentText('SELL');tool.inputs['entry'].setText('1.9');tool.replace_prices.click()
    assert tool.side.currentText()=='BUY' and tool.inputs['entry'].text()==str(runtime.market.quote(runtime.accounts.current.account_id,'EURUSD').ask)
    assert not runtime.orders.transport.submissions


def test_broken_pagination_never_uses_new_rows_under_old_page_hash(shell,runtime):
    app,w=shell
    for i in range(225):runtime.database.put('parameter_definition','test:'+str(i),{'key':'test:'+str(i)})
    w.main_tabs.setCurrentIndex(2);w.main_tabs.widget(2).setCurrentIndex(10);editor=w._active_panel();editor.inspect_registry.click();p=editor._inspector.panel
    p.dataset.setCurrentIndex(p.dataset.findData('parameter_definitions'));p.refresh();p.next.click();assert p._cursor==200
    runtime.database.put('parameter_definition','test:new',{'key':'test:new'})
    p.refresh();assert 'Dataset changed' in p.status.text() and not p._rows and not p.next.isEnabled()
    p.previous.click();assert p._cursor==0 and p._rows and p.next.isEnabled()


def test_successful_return_clears_visible_navigation_error(shell,runtime):
    app,w=shell;ctx=runtime.api(1).inspect(symbol='EURUSD',timeframe='W1');bad=thaw(ctx);bad['symbol']='GBPUSD'
    w._navigate('3.5',bad);assert w.inspection_label.isVisible()
    runtime.api(1).navigate('3.2',ctx);drain(app,runtime)
    assert w._active_panel().context['timeframe']=='W1' and not w.inspection_label.isVisible()
    w.return_button.click();drain(app,runtime);assert w.main_tabs.currentIndex()==0


def test_signal_calculator_scenario_keeps_original_record_identity(shell,runtime):
    app,w=shell;ctx=runtime.api(4).inspect(symbol='EURUSD',object_kind='signal',object_id='FIXTURE-SIGNAL-1')
    runtime.api(4).navigate('4.2',ctx);drain(app,runtime);panel=w._active_panel();assert panel.selected()
    panel.calculate.click();drain(app,runtime);tool=w.tools.windows['forex-calculator'].widget().widget()
    assert tool.pending_context['object_kind']=='signal' and tool.pending_context['object_id']=='FIXTURE-SIGNAL-1'
    assert tool.pending_context['object_hash']==ctx['object_hash'] and tool.pending_context['scenario']['entry']


def test_broker_inspector_cannot_drop_identity_to_bypass_calculator_boundary(shell,runtime):
    app,w=shell
    runtime.positions.replace_snapshot(runtime.market.scope_id,[{'position_id':'HARDEN-P','symbol':'EURUSD','side':'BUY','units':'1000','entry_price':'1.1'}],observed_at=FIXTURE_NOW,origin='SYNTHETIC_FIXTURE',complete=True)
    runtime.api(4).navigate('4.6',runtime.api(4).inspect(symbol='EURUSD',object_kind='position',object_id='HARDEN-P'));drain(app,runtime);p=w._active_panel()
    assert p.selected() and not p.calculate.isEnabled()
    p.open_selected('calculator');drain(app,runtime)
    assert w._active_panel() is p and 'Broker' in p.feedback.text()
