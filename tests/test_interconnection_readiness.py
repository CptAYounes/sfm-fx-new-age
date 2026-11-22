"""Offline workspace acceptance, never strategy qualification or broker permission."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import pytest
from sfm_fx_new_age.contracts.analytics import Level, Lineage
from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES, Origin, record, instant
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW, FIXTURE_EPOCH
from test_workspace_ui_workflows import shell, drain
from test_cross_lane_candidate_binding import pipeline


def test_selected_chart_signal_keeps_identity_into_calculator(shell, runtime):
    app, w = shell
    p = w._active_panel()
    p._select_evidence('FIXTURE-SIGNAL-1')
    assert p._selected_record()
    p._open_in('calculator'); drain(app, runtime)
    tool = w.tools.windows['forex-calculator'].widget().widget()
    assert tool.pending_context['object_kind'] == 'signal'
    assert tool.pending_context['object_id'] == 'FIXTURE-SIGNAL-1'
    assert tool.pending_context['object_hash']
    assert tool.pending_context['scenario']['entry']
    assert not runtime.orders.transport.submissions


def test_selected_chart_broker_record_cannot_be_laundered_into_tool(shell, runtime):
    app, w = shell
    runtime.positions.replace_snapshot(runtime.market.scope_id, [dict(position_id='NO-TOOL', symbol='EURUSD', side='BUY', units='1000', entry_price='1.1')], observed_at=FIXTURE_NOW, origin='SYNTHETIC_FIXTURE', complete=True)
    p = w._active_panel(); p.refresh(); p._select_evidence('NO-TOOL')
    p._open_in('calculator'); drain(app, runtime)
    assert w._active_panel() is p and w.main_tabs.currentIndex() == 0
    assert 'Broker' in p.workflow_status.text()


def test_scenario_derivation_preserves_exact_original_context(runtime):
    api = runtime.api(2)
    ctx = thaw(api.inspect(symbol='EURUSD', timeframe='H4', object_kind='signal', object_id='FIXTURE-SIGNAL-1'))
    scenario = {'entry':'1.1', 'exit':'1.11', 'side':'BUY', 'lots':'.1', 'contract':'100000', 'pip_size':'.0001'}
    derived = thaw(api.scenario_context(ctx, scenario))
    assert {k:v for k,v in derived.items() if k not in {'context_id','scenario'}} == {k:v for k,v in ctx.items() if k not in {'context_id','scenario'}}
    assert derived['scenario'] == scenario and derived['context_id'] != ctx['context_id']
    runtime.market.activate_source('EURUSD','NEW',Origin.SYNTHETIC_FIXTURE)
    with pytest.raises(ValueError): api.scenario_context(ctx, scenario)


@pytest.mark.parametrize('scenario', [dict(lots='0'),dict(contract='NaN'),dict(pip_size='-1'),dict(units='1'),dict(side='FLAT')])
def test_scenario_contract_rejects_unqualified_values(runtime, scenario):
    api = runtime.api(2); ctx = api.inspect(symbol='EURUSD')
    with pytest.raises(ValueError):api.scenario_context(ctx, scenario)


def test_calculator_chart_roundtrip_is_explicit_and_preserves_source(shell, runtime):
    app, w = shell
    ctx = runtime.api(1).inspect(symbol='EURUSD', timeframe='H4', object_kind='signal', object_id='FIXTURE-SIGNAL-1')
    runtime.api(1).navigate('calculator',ctx); drain(app,runtime)
    tool = w.tools.windows['forex-calculator'].widget().widget()
    tool.inputs['entry'].setText('1.1');tool.inputs['exit'].setText('1.11');tool.inputs['lots'].setText('.10')
    tool.show_chart.click();drain(app,runtime)
    chart = w._active_panel()
    assert chart.model.subtab_id == '1.8' and chart.frame == 'H4'
    assert chart.context['object_hash'] == ctx['object_hash']
    assert chart.canvas.scenario_projection['category'] == 'MANUAL_SCENARIO'
    assert chart.canvas.scenario_projection['lots'] == '.10'
    assert chart.canvas.scenario_projection['gross_quote_pnl'] == '100.0000'
    assert 'not risk sizing' in chart.workflow_status.text()
    w.return_button.click();drain(app,runtime)
    assert w.main_tabs.currentIndex() == 1 and tool.inputs['lots'].text() == '.10'
    assert not runtime.database.orders() and not runtime.orders.transport.submissions


def test_calculator_wrong_pair_and_stale_source_refuse_projection(shell,runtime):
    app,w=shell;runtime.api(1).navigate('calculator',runtime.api(1).inspect(symbol='EURUSD'));drain(app,runtime)
    tool=w.tools.windows['forex-calculator'].widget().widget()
    tool.pair.setCurrentText('GBPUSD');tool.show_chart.click();drain(app,runtime)
    assert w.main_tabs.currentIndex()==1 and 'Matching' in tool.provenance.text()
    tool.pair.setCurrentText('EURUSD');runtime.market.activate_source('EURUSD','NEW',Origin.SYNTHETIC_FIXTURE)
    tool.show_chart.click();drain(app,runtime)
    assert w.main_tabs.currentIndex()==1 and 'refused' in tool.provenance.text()


def test_pinned_chart_retains_selected_signal_geometry_without_current_inventory(shell,runtime):
    app,w=shell;ctx=runtime.api(4).inspect(symbol='EURUSD',timeframe='H1',object_kind='signal',object_id='FIXTURE-SIGNAL-1')
    runtime.api(4).navigate('1.8',ctx);drain(app,runtime);p=w._active_panel()
    assert len(p.canvas.setup_projections)==1
    projection=p.canvas.setup_projections[0]
    assert projection['object_id']=='FIXTURE-SIGNAL-1' and projection['object_kind']=='signal'
    assert projection['source_timeframe'] is None
    assert {line['role'] for line in projection['lines']}=={'entry','internal invalidation'}
    assert p._selected_record()['signal_id']=='FIXTURE-SIGNAL-1'
    assert not p.canvas.broker_visuals and not p.canvas._quotes


def test_candidate_geometry_keeps_variant_identity_and_not_broker_stop(pipeline):
    r,payload,_=pipeline
    ctx=r.api(3).inspect(symbol='EURUSD',timeframe='H4',object_kind='market_candidate',object_id=payload['candidate_id'])
    projection=thaw(r.api(1).inspection_projection(ctx))
    assert projection['source_timeframe']=='D1'
    assert projection['object_hash']==ctx['object_hash']
    assert any(line.get('variant_id')==payload['variant_id'] for line in projection['lines'])
    assert 'broker_stop_loss' not in projection
    assert not r.orders.transport.submissions


def test_all_pair_frame_projection_filters_and_causal_cutoffs(runtime):
    for pair in PAIRS:
        for frame in FRAMES:
            line=Lineage(runtime.market.scope_id,FIXTURE_EPOCH,pair,frame,'2026-11-01T00:00:00Z',Origin.SYNTHETIC_FIXTURE,'SYNTHETIC_TEST','TEST')
            runtime.research.publish(Level(pair+frame,1,'TEST_ZONE',Decimal('1.09'),Decimal('1.11'),'BUY','CONFIRMED',('test',),line))
    lanes=set()
    for pair in PAIRS:
        for frame in FRAMES:
            d=thaw(runtime.api(1).query('1.3',DataRequest('chart',symbol=pair,timeframe=frame)))
            assert {row['lineage']['symbol'] for row in d['levels']}=={pair}
            assert {row['lineage']['timeframe'] for row in d['levels']}==set(FRAMES)
            assert not runtime.api(1).query('1.3',DataRequest('chart',symbol=pair,timeframe=frame,as_of='2026-10-31T00:00:00Z'))['levels']
            lanes.add((pair,frame))
    assert lanes=={(p,f) for p in PAIRS for f in FRAMES}
    assert not runtime.orders.transport.submissions


def test_chart_layers_available_on_fixed_timeframes_and_persist(shell,runtime):
    app,w=shell;w.chart_tabs.setCurrentIndex(2);drain(app,runtime);p=w._active_panel()
    line=Lineage(runtime.market.scope_id,FIXTURE_EPOCH,'EURUSD','W1','2026-11-01T00:00:00Z',Origin.SYNTHETIC_FIXTURE,'SYNTHETIC_TEST','TEST')
    runtime.research.publish(Level('macro',1,'TEST_ZONE',Decimal('1.09'),Decimal('1.11'),'BUY','CONFIRMED',('test',),line))
    p.refresh();p.canvas.grab()
    assert p.canvas.research_regions() and 'W1' in p.layer_frame_actions
    p.layer_frame_actions['W1'].setChecked(False);p.canvas.grab()
    assert not p.canvas.research_regions()
    p._save_workspace();stored=runtime.api(1).workspace(p._workspace_context)
    assert 'W1' not in stored['settings']['display']['projection_frames']
    p.layer_actions['show_broker'].setChecked(False)
    assert not p.canvas.display['show_broker']


def test_research_handoff_keeps_pinned_target_frame_separate_from_source(shell,runtime):
    app,w=shell
    line=Lineage(runtime.market.scope_id,FIXTURE_EPOCH,'EURUSD','D1','2026-11-01T00:00:00Z',Origin.SYNTHETIC_FIXTURE,'SYNTHETIC_TEST','TEST')
    runtime.research.publish(Level('daily',1,'TEST_ZONE',Decimal('1.09'),Decimal('1.11'),'BUY','CONFIRMED',('test',),line))
    runtime.api(1).navigate('3.5',runtime.api(1).inspect(symbol='EURUSD',timeframe='H4'));drain(app,runtime)
    p=w._active_panel();p.dataset.setCurrentIndex(p.dataset.findData('levels'));p.table.selectRow(0);p.show_chart.click();drain(app,runtime)
    assert w._active_panel().frame=='H4'
    assert runtime.api(1).inspection_object(w._active_panel().context)['lineage']['timeframe']=='D1'


def test_calculator_handoff_fits_after_hidden_tab_geometry_settles(shell,runtime):
    app,w=shell
    runtime.api(1).navigate('calculator',runtime.api(1).inspect(symbol='EURUSD',timeframe='H4'));drain(app,runtime)
    frame=w.tools.windows['forex-calculator'];tool=frame.widget().widget()
    tool.inputs['entry'].setText('1.1');tool.inputs['exit'].setText('1.11');drain(app,runtime)
    assert frame.widget().verticalScrollBar().maximum()==frame.widget().horizontalScrollBar().maximum()==0
    frame.resize(550,300);drain(app,runtime)
    assert frame.size().toTuple()==(550,300)


def test_projection_has_no_retroactive_or_wrong_source_lines(shell,runtime):
    app,w=shell
    base=runtime.market.bars('EURUSD','H4',FIXTURE_NOW,FIXTURE_EPOCH)[0]
    for n in range(1,14):
        delta=timedelta(hours=4*n)
        runtime.market.ingest(replace(base,open_time=(instant(base.open_time)-delta).isoformat(),close_time=(instant(base.close_time)-delta).isoformat(),available_at=(instant(base.available_at)-delta).isoformat()))
    ctx=runtime.api(1).inspect(symbol='EURUSD',timeframe='H4',object_kind='signal',object_id='FIXTURE-SIGNAL-1')
    runtime.api(1).navigate('1.8',ctx);drain(app,runtime);c=w._active_panel().canvas;c.grab()
    assert c.projection_lines()
    good=deepcopy(c.setup_projections)
    for field,value in (('scope_id','OTHER'),('source_epoch','OTHER'),('symbol','GBPUSD')):
        c.setup_projections=deepcopy(good);c.setup_projections[0][field]=value
        assert not c.projection_lines()
    c.setup_projections=good;c.window=8;c.pan(10);c.grab()
    assert not c.projection_lines()


def test_scenario_projection_clears_without_changing_signal_or_evidence(shell,runtime):
    app,w=shell;api=runtime.api(1)
    ctx=api.scenario_context(api.inspect(symbol='EURUSD'),dict(entry='1.1',exit='1.11',side='BUY',lots='.10',contract='100000',pip_size='.0001'))
    before=thaw(runtime.api(4).query('4.2',DataRequest('signals')))['rows']
    api.navigate('1.8',ctx);drain(app,runtime);p=w._active_panel();assert p.canvas.scenario_projection
    p.current_context.click();drain(app,runtime)
    assert p.canvas.scenario_projection is None and not p.workflow_status.text()
    assert thaw(runtime.api(4).query('4.2',DataRequest('signals')))['rows']==before
    assert not runtime.api(3).query('3.5',DataRequest('evidence'))['rows']
    assert not runtime.database.orders()


@pytest.mark.parametrize('frames', [['W1','W1'],['M15'],[{}],None])
def test_projection_frame_setting_rejects_malformed_values(frames):
    from sfm_fx_new_age.contracts.chart_display import validate_display
    with pytest.raises(ValueError):validate_display({'projection_frames':frames})


def test_direct_tool_context_rejects_broker_identity(runtime):
    runtime.positions.replace_snapshot(runtime.market.scope_id,[dict(position_id='DIRECT-P',symbol='EURUSD',side='BUY',units='1000',entry_price='1.1')],observed_at=FIXTURE_NOW,origin='SYNTHETIC_FIXTURE',complete=True)
    ctx=runtime.api(4).inspect(symbol='EURUSD',object_kind='position',object_id='DIRECT-P')
    with pytest.raises(ValueError):runtime.api(2).calculator_context(ctx)
    with pytest.raises(ValueError):runtime.api(2).scenario_context(ctx,{'entry':'1.1'})


def test_research_setup_and_scenario_labels_share_collision_rail(shell,runtime):
    app,w=shell;api=runtime.api(1)
    ctx=api.scenario_context(api.inspect(symbol='EURUSD',timeframe='H4',object_kind='signal',object_id='FIXTURE-SIGNAL-1'),dict(entry='1.1000',exit='1.1001',side='BUY'))
    api.navigate('1.8',ctx);drain(app,runtime);c=w._active_panel().canvas;c.grab()
    badges=c.projection_badges()
    assert len(badges)>1
    assert all(b['label_y']+20<=a['label_y'] for b,a in zip(badges,badges[1:]))
    assert any('Manual Scenario' in b['label'] for b in badges)
    assert all('actual_y' in b and 'price' in b for b in badges)


def test_signal_future_expiry_remains_visible_on_sparse_observed_chart(shell,runtime):
    app,w=shell;ctx=runtime.api(1).inspect(symbol='EURUSD',timeframe='H4',object_kind='signal',object_id='FIXTURE-SIGNAL-1')
    runtime.api(1).navigate('1.8',ctx);drain(app,runtime);c=w._active_panel().canvas;c.grab()
    assert len(c.bars)==1
    assert any(line[1]['role']=='entry' for line in c.projection_lines())
    assert c.region_end_x('2026-11-07T12:00:00Z')==c.plot_rect().right()
