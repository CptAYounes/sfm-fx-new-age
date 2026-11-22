"""Display-only clarity controls. Market values here are labelled fixtures, not feed proof."""
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from test_chart_workstation import canvas
from test_projection_legibility import layer


@pytest.mark.parametrize('size',[(480,360),(820,420),(1360,700)])
@pytest.mark.parametrize('font',[8,12,16])
def test_default_caption_rail_never_obscures_candles_or_price_axis(canvas,size,font):
    app,c=canvas;c.resize(*size);c.set_display({'axis_font_size':font});body=layer(c);c.strategy_layers=[body];before=deepcopy(body);c.grab()
    assert c.display['projection_captions']=='Side rail'
    items=c.projection_badge_layout();rail=c.projection_caption_rect();assert items and rail
    for item in items:
        assert rail.contains(item['rect'])
        assert not item['rect'].intersects(c.plot_rect()) and not item['rect'].intersects(c.price_axis_rect())
        assert item['price_rect'].width()>=c.axis_metrics().horizontalAdvance(item['price_text'])
    assert c.plot_rect().width()>=180 and c.strategy_layers==[before]


def test_caption_pages_reach_every_identity_without_moving_or_dropping_originals(canvas):
    _,c=canvas;c.resize(820,420);body=layer(c);body['zones']=[dict(body['zones'][0],label=f'LEVEL {i:03}') for i in range(83)];c.strategy_layers=[body];before=deepcopy(body);c.grab()
    counts=c.projection_caption_status();assert counts['pages']>1 and counts['eligible']==83
    seen=[]
    for page in range(counts['pages']):
        c.set_projection_page(page);c.grab();seen.extend(v['label'] for v in c.projection_badge_layout())
    assert len(seen)==len(set(seen))==83 and c.strategy_layers==[before]
    assert all(v['price']==1.11001 for v in c.projection_badge_layout())
    c.set_projection_page(10000);assert c.projection_caption_status()['page']==counts['pages']-1
    c.set_projection_page(-1);assert c.projection_caption_status()['page']==0


def test_first_caption_page_prioritizes_nearby_completed_close_not_highest_price(canvas):
    _,c=canvas;close=float(c.bars[-1]['close']);stamp=c.bars[-1]['close_time']
    zones=[dict(low=str(close+i*.0001),high=str(close+i*.0001),label=f'DISTANCE {i}',state='CONFIRMED',available_at=stamp) for i in range(-20,21)]
    c.price_range=(close-.003,close+.003);c.strategy_layers=[layer(c,zones=zones)];c.grab()
    items=c.projection_badge_layout();assert any(v['label'].startswith('DISTANCE 0 ·') for v in items)
    assert max(abs(v['price']-close) for v in items)<.002


def test_hidden_captions_do_not_hide_geometry_or_change_source_layers(canvas):
    _,c=canvas;c.strategy_layers=[layer(c)];c.grab();before=deepcopy(c.strategy_layers)
    geometry=c.public_strategy_geometry();c.set_display({'projection_captions':'Hidden'});c.grab()
    # Hiding the rail returns its width to the candles; pixel x coordinates
    # intentionally reflow while source identities/prices/topology stay exact.
    assert not c.projection_badge_layout()
    assert [v[:3] for v in c.public_strategy_geometry()]==[v[:3] for v in geometry]
    assert c.projection_caption_status()['eligible']==5 and c.projection_caption_status()['shown']==0
    assert c.strategy_layers==before and c.public_strategy_layers()==before
    c.set_display({'projection_captions':'Overlay'});c.grab();assert c.projection_badge_layout()
    with pytest.raises(ValueError):c.set_display({'projection_captions':'Fake prices'})


def test_public_focus_is_chart_local_and_source_changes_clear_it(canvas):
    _,c=canvas;one=layer(c);two=dict(layer(c,name='SECOND FIXTURE'),strategy_id='vwap_bands');c.strategy_layers=[one,two];before=deepcopy(c.strategy_layers)
    c.set_projection_focus('vwap_bands');c.grab();assert {v[1]['strategy_id'] for v in c.public_strategy_geometry()}=={'vwap_bands'}
    assert c.public_strategy_layers()==before and len(c.strategy_layers)==2
    c.set_projection_focus(None);c.grab();assert {v[1]['strategy_id'] for v in c.public_strategy_geometry()}=={'profile_tpo','vwap_bands'}
    c.set_projection_focus('vwap_bands');c.set_data(c.bars,'GBPUSD',('scope','epoch','GBPUSD','H1'))
    assert c.projection_focus is None and c.projection_page==0


def test_focus_unknown_or_withdrawn_cannot_resurrect_layers(canvas):
    _,c=canvas;c.strategy_layers=[layer(c)];c.grab()
    with pytest.raises(ValueError):c.set_projection_focus('unknown')
    c.set_projection_focus('profile_tpo');c.strategy_layers=[];c.reconcile_projection_focus()
    assert c.projection_focus is None and not c.public_strategy_geometry() and not c.projection_badge_layout()


def test_chart_projection_bar_actions_are_local_and_caption_preference_persists(tmp_path):
    from test_public_strategies import seed,enable
    from sfm_fx_new_age.app import create_main_window
    from sfm_fx_new_age.contracts.models import thaw
    app=QApplication.instance() or QApplication([]);r=seed(tmp_path/'state.sqlite3');w=None
    try:
        enable(r,'ema_cross');enable(r,'fvg');w=create_main_window(r);w.resize(960,640);w.show();w.core_timer.stop();w.poll_timer.stop();app.processEvents()
        r.api(1).navigate('1.4',r.api(1).inspect(symbol='EURUSD',timeframe='H4'));w.refresh_current(force=True);app.processEvents();p=w._active_panel();p.canvas.grab();bar=p.projection_bar;bar.sync()
        states=deepcopy(r.database.list('recipe_state'));bar.focus.setCurrentIndex(bar.focus.findData('ema_cross'));app.processEvents()
        assert p.canvas.projection_focus=='ema_cross' and r.database.list('recipe_state')==states
        bar.captions.setCurrentText('Hidden');p._save_workspace();ctx=p._workspace_context
        assert thaw(p.api.workspace(ctx))['settings']['display']['projection_captions']=='Hidden'
        assert 'projection_focus' not in thaw(p.api.workspace(ctx))['settings']
        p.canvas.set_display({'projection_captions':'Side rail'});p._reload_workspace();assert p.canvas.display['projection_captions']=='Hidden'
        assert bar.isVisible() and p.canvas.height()>=120
        before_height=p.canvas.height();QTest.mouseClick(bar.chart_only,Qt.LeftButton);app.processEvents()
        assert p.canvas.height()>before_height and p.health.isVisible() and bar.isVisible() and not p.settings.isVisible()
        QTest.mouseClick(bar.chart_only,Qt.LeftButton);app.processEvents();assert p.settings.isVisible()
        assert not r.connector.workers and not r.orders.transport.submissions
    finally:
        if w:
            w.close();assert bar._disposed and not bar.timer.isActive()
        r.close();app.processEvents()


def test_strategy_library_combined_filters_reset_and_empty_state_never_switch_methods():
    from test_public_strategies import seed,enable
    from sfm_fx_new_age.app import create_main_window
    from sfm_fx_new_age.contracts.public_strategies import METHODS,BY_KEY
    app=QApplication.instance() or QApplication([]);r=seed();w=None
    try:
        enable(r,'ema_cross');enable(r,'fvg');w=create_main_window(r);w.resize(960,640);w.show();w.core_timer.stop();w.poll_timer.stop();app.processEvents()
        r.api(3).navigate('3.1',r.api(3).inspect(symbol='EURUSD',timeframe='H4'));w.refresh_current(force=True);app.processEvents();p=w._active_panel();before=deepcopy(r.database.list('recipe_state'))
        p.selected_only.setChecked(True);app.processEvents()
        visible=lambda:{m.key for i,m in enumerate(METHODS) if not p.table.isRowHidden(i)}
        assert visible()=={'ema_cross','fvg'}
        p.family_filter.setCurrentText(BY_KEY['ema_cross'].family);assert visible()=={'ema_cross'}
        p.search.setText('NOT A REAL STRATEGY');assert not visible() and p.table.currentRow()==-1
        assert 'No strategies match' in p.details.toPlainText()
        QTest.mouseClick(p.reset_filters,Qt.LeftButton);app.processEvents();assert visible()=={m.key for m in METHODS}
        assert not p.selected_only.isChecked() and p.search.text()=='' and r.database.list('recipe_state')==before
        assert '83 / 83' in p.filter_count.text()
        assert not p.details.isVisible();QTest.mouseClick(p.details_toggle,Qt.LeftButton);app.processEvents();assert p.details.isVisible()
        p.state_filter.setCurrentText('Off');assert len(visible())==81
        assert not r.connector.workers and not r.orders.transport.submissions
    finally:
        if w:w.close()
        r.close();app.processEvents()
