"""Projection caption regressions; every observation is a labelled test fixture."""
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt,QPoint,QTimer,QEvent
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication,QToolTip,QDialog
from test_chart_workstation import canvas


@pytest.fixture(autouse=True)
def explicit_legacy_overlay(request):
    # These invariants target the retained Overlay mode. Side-rail/no-candle-
    # occlusion and paging are independently covered in test_chart_clarity.
    if 'canvas' in request.fixturenames:
        _,c=request.getfixturevalue('canvas');c.set_display({'projection_captions':'Overlay'})


def layer(c,*,zones=None,name='LABELLED TEST TPO'):
    t=c.bars[-1]['close_time']
    zones=zones if zones is not None else [dict(low='1.11001',high='1.11001',label=label,state='CONFIRMED',available_at=t) for label in ('POC','Value-area low 70%','Value-area high 70%','Initial-balance low','Initial-balance high')]
    return dict(scope_id=c.data_identity[0],source_epoch=c.data_identity[1],symbol=c.data_identity[2],timeframe=c.data_identity[3],strategy_id='profile_tpo',name=name,state='READY',available_at=t,origin='SYNTHETIC_FIXTURE',series=[],markers=[],zones=zones,metrics={},fingerprint='LABELLED_TEST_FINGERPRINT')


@pytest.mark.parametrize('font',[8,12,16])
@pytest.mark.parametrize('size',[(480,360),(820,420)])
def test_equal_price_level_identities_and_prices_have_font_sized_separate_captions(canvas,font,size):
    app,c=canvas;c.resize(*size);c.set_display({'axis_font_size':font});body=layer(c);c.strategy_layers=[body];before=deepcopy(body);c.grab()
    captions=c.projection_badge_layout();assert len(captions)==5
    assert all(v['rect'].height()>=c.axis_metrics().height()+4 for v in captions)
    assert all(c.plot_rect().contains(v['rect']) for v in captions)
    assert all(a['rect'].bottom()+1<=b['rect'].top() for a,b in zip(captions,captions[1:]))
    assert {v['label'].split(' · ')[0] for v in captions}=={z['label'] for z in body['zones']}
    assert {v['price_text'] for v in captions}=={'1.11001'}
    assert all(v['price_rect'].width()>=c.axis_metrics().horizontalAdvance(v['price_text']) for v in captions)
    assert all(not v['label_rect'].intersects(v['price_rect']) for v in captions)
    assert c.strategy_layers==[before] and not c.drawings.items


def test_nonzero_projection_band_has_both_explicit_bound_prices(canvas):
    _,c=canvas;t=c.bars[-1]['close_time'];c.strategy_layers=[layer(c,zones=[dict(low='1.11001',high='1.11234',label='LABELLED TEST BAND',state='CONFIRMED',available_at=t)])];c.grab()
    items=c.projection_badge_layout();assert {v['price_text'] for v in items}=={'1.11001','1.11234'}
    assert {v['label'].split(' · ')[0] for v in items}=={'LABELLED TEST BAND high','LABELLED TEST BAND low'}


@pytest.mark.parametrize('corner',['Top left','Top right','Bottom left','Bottom right'])
def test_captions_do_not_cover_public_legend_or_ruler_readout(canvas,corner):
    _,c=canvas;c.strategy_layers=[layer(c)];c.set_display({'ruler_position':corner});stamp=c.bars[-1]['open_time'];c.ruler=((stamp,1.11001),(stamp,1.11234));c.ruler_mode='price';c.grab()
    legend=c.public_strategy_legend_rect();card=c.ruler_card_rect();items=c.projection_badge_layout();assert items
    assert all(not v['rect'].intersects(legend) and not v['rect'].intersects(card) for v in items)


def test_tooltip_retains_full_elided_identity_and_price_without_html_injection(canvas):
    app,c=canvas;c.strategy_layers=[layer(c,name='<b>LABELLED & TEST</b> '*15)];c.grab();item=c.projection_badge_layout()[0]
    point=item['label_rect'].center().toPoint();QApplication.sendEvent(c,QHelpEvent(QEvent.ToolTip,point,c.mapToGlobal(point)))
    text=QToolTip.text();assert '1.11001' in text and '&lt;b&gt;' in text and '&amp;' in text
    assert 'projection' in text.lower();QToolTip.hideText()


def test_legend_and_captions_obey_source_frame_visibility_and_historical_cutoff(canvas):
    _,c=canvas;original=layer(c);c.strategy_layers=[original];c.grab();assert c.public_strategy_legend_rect()
    for key,value in [('scope_id','OTHER'),('source_epoch','OTHER'),('symbol','GBPUSD'),('timeframe','H4')]:
        c.strategy_layers=[dict(original,**{key:value})];assert not c.public_strategy_geometry() and c.public_strategy_legend_rect() is None and not c.projection_badge_layout()
    c.strategy_layers=[original];c.set_display({'show_research':False});c.grab();assert not c.projection_badge_layout() and c.public_strategy_legend_rect() is None
    c.set_display({'show_research':True,'projection_frames':['H4']});c.grab();assert not c.public_strategy_geometry() and c.public_strategy_legend_rect() is None
    c.set_display({'projection_frames':['H1']});c.pan(20);c.grab();assert not c.public_strategy_geometry()
    assert not c.projection_badge_layout() # Later evaluation must not be rendered in old history.


def test_caption_capacity_is_explicit_and_does_not_move_level_coordinates(canvas):
    _,c=canvas;c.resize(480,240);body=layer(c);body['zones']=[dict(body['zones'][0],label=f'LABELLED LEVEL {i}') for i in range(80)];c.strategy_layers=[body];c.grab()
    count=c.projection_badge_counts();items=c.projection_badge_layout();assert count['eligible']==80 and count['shown']==len(items)<80
    assert all(v['actual_y']==items[0]['actual_y'] and v['price']==1.11001 for v in items)
    assert all(v['rect'].bottom()<c.public_strategy_legend_rect().top() for v in items)
    assert c.public_strategy_caption_text().find(f"{count['shown']}/80")>=0


def test_large_font_in_short_plot_discloses_capacity_without_shrinking_font_or_losing_source_rows(canvas):
    _,c=canvas;c.resize(480,300);c.set_display({'axis_font_size':16});c.strategy_layers=[layer(c)];c.grab()
    counts=c.projection_badge_counts();items=c.projection_badge_layout()
    assert counts['eligible']==5 and counts['shown']==len(items) and 0<counts['shown']<=5
    assert c.axis_font().pointSizeF()==16 and len(c.public_strategy_layers()[0]['zones'])==5
    assert all(v['rect'].height()>=c.axis_metrics().height()+4 for v in items)
    assert all(not v['rect'].intersects(c.public_strategy_legend_rect()) for v in items)
    assert all(a['rect'].bottom()+1<=b['rect'].top() for a,b in zip(items,items[1:]))
    assert f"{counts['shown']}/5" in c.public_strategy_caption_text()


def test_label_allocator_retains_default_equal_price_axis_coalescing():
    from sfm_fx_new_age.ui.chart_axis import price_badges
    values=[(50,1.1,'#FFFFFF','A'),(50,1.1,'#FFFFFF','B')]
    assert len(price_badges(values,10,110,5))==1
    separate=price_badges(values,10,110,5,coalesce=False,label_height=25)
    assert len(separate)==2 and separate[1]['label_y']>=separate[0]['label_y']+27
    assert len(price_badges([(108,1.1,'#FFFFFF','A')],10,90,5,coalesce=False,anchor_range=(0,110)))==1


def test_actual_layers_action_opens_readonly_projection_details_and_invalidates_on_source_change():
    from test_public_strategies import seed,enable
    from sfm_fx_new_age.app import create_main_window
    app=QApplication.instance() or QApplication([]);r=seed();w=None;observed=[]
    try:
        enable(r,'ema_cross');w=create_main_window(r);w.resize(960,640);w.show();w.core_timer.stop();w.poll_timer.stop();app.processEvents()
        r.api(1).navigate('1.4',r.api(1).inspect(symbol='EURUSD',timeframe='H4'));r.pump();app.processEvents();w.refresh_current(force=True);app.processEvents();p=w._active_panel();c=p.canvas;c.grab()
        action=next(a for a in p.layers_menu.actions() if a.objectName()=='publicProjectionDetailsAction');assert action.isEnabled()
        def inspect():
            d=app.activeModalWidget();assert isinstance(d,QDialog) and d.objectName()=='publicProjectionDetails'
            text=d.findChild(__import__('PySide6.QtWidgets',fromlist=['QTextEdit']).QTextEdit,'publicProjectionValues')
            assert text.isReadOnly() and 'ema_cross' in text.toPlainText() and 'SYNTHETIC_FIXTURE' in text.toPlainText()
            assert 'zones' in text.toPlainText() and 'available_at' in text.toPlainText();observed.append(True)
            c.data_identity=('OTHER','OTHER','EURUSD','H4');d.check_source();assert not text.toPlainText() and not d.isVisible()
        QTimer.singleShot(25,inspect);action.trigger();assert observed==[True]
        menu=c.build_context_menu();assert any(a.objectName()=='publicProjectionDetailsContext' for a in menu.actions());menu.deleteLater()
        assert not r.connector.workers and not r.orders.transport.submissions and not r.orders.transport.cancellations
    finally:
        if w:w.close()
        r.close();app.processEvents()
