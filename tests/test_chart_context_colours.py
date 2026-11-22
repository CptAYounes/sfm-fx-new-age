"""Local chart colour menus and forgiving selection: synthetic input, no broker."""
from copy import deepcopy
import pytest
from PySide6.QtCore import QPoint,QPointF,Qt
from PySide6.QtTest import QTest
from test_chart_workstation import canvas,rows
from sfm_fx_new_age.contracts.chart_display import COLOR_GROUPS,DISPLAY_DEFAULTS,validate_display,validate_style,style_for,KINDS
from sfm_fx_new_age.ui.chart_preferences import ChartPreferences
from sfm_fx_new_age.ui.chart_properties import ObjectProperties,BulkAppearance


def test_every_chart_palette_role_is_editable_staged_and_validated(canvas):
    _,c=canvas;d=ChartPreferences(c);keys=[key for _,items in COLOR_GROUPS for key,_ in items]
    assert len(keys)==len(set(keys)) and set(keys)=={k for k in DISPLAY_DEFAULTS if k.endswith('_color') or k in {'background','foreground'}}
    before=deepcopy(c.display)
    for key in keys:d.fields[key].set_value('#123456')
    assert c.display==before and d.apply()
    assert all(c.display[k]=='#123456' for k in keys)
    d.fields['background'].set_value('#654321');d.reject();assert c.display['background']=='#123456'
    for key in keys:
        with pytest.raises(ValueError):validate_display({key:'bad'})


@pytest.mark.parametrize('kind',KINDS)
def test_any_local_object_colour_parts_apply_without_geometry_or_flag_changes(canvas,kind):
    _,c=canvas;a=c._anchor(QPointF(220,120));b=c._anchor(QPointF(400,220))
    o=c.drawings.add(kind,[a] if kind in {'Level','Vertical','Text'} else [a,b],name='Keep');c.drawings.modify(o['id'],locked=True)
    before=deepcopy(o);d=ObjectProperties(c,o['id']);d.color.set_value('#11AA22');d.linked_colours['text_color'][0].setChecked(False);d.linked_colours['text_color'][1].set_value('#AB12CD')
    d.linked_colours['fill_color'][0].setChecked(False);d.linked_colours['fill_color'][1].set_value('#123ABC')
    assert d.apply();assert o['anchors']==before['anchors'] and o['locked'] and o['name']=='Keep'
    assert o['color']=='#11AA22' and o['text_color']=='#AB12CD' and o['fill_color']=='#123ABC'
    d.color.set_value('#777777');d.reject();assert o['color']=='#11AA22'
    assert not c.grab().isNull()
    c.drawings.undo();assert c.drawings.get(o['id'])==before


@pytest.mark.parametrize('kind',KINDS)
def test_wide_hit_region_selects_all_types_with_a_real_left_click(canvas,kind):
    _,c=canvas;a=c._anchor(QPointF(180,110));b=c._anchor(QPointF(400,230))
    o=c.drawings.add(kind,[a] if kind in {'Level','Vertical','Text'} else [a,b]);c.drawings.selected=None;c.grab()
    _,segments,_,_=c._shape(o)
    if kind=='Text':pos=c._text_rect(o).bottomRight()+QPointF(8,0)
    else:
        u,v=max(segments,key=lambda seg:(seg[1]-seg[0]).manhattanLength());mid=(u+v)/2;dx,dy=v.x()-u.x(),v.y()-u.y();length=max(.001,(dx*dx+dy*dy)**.5)
        pos=mid+QPointF(-dy/length*11,dx/length*11)
    before=deepcopy(o);QTest.mouseClick(c,Qt.LeftButton,pos=pos.toPoint())
    assert c.drawings.selected==o['id'] and o==before


def test_nearest_outline_wins_over_topmost_filled_shape(canvas):
    _,c=canvas;a=c.drawings.add('Level',[c._anchor(QPointF(200,155))]);b=c.drawings.add('Level',[c._anchor(QPointF(200,175))])
    box=c.drawings.add('Rectangle',[c._anchor(QPointF(120,80)),c._anchor(QPointF(550,280))]);c.drawings.selected=None;c.grab()
    assert c._hit_drawing(QPointF(300,158))[0]['id']==a['id']
    assert c._hit_drawing(QPointF(300,172))[0]['id']==b['id']
    assert c._hit_drawing(QPointF(300,250))[0]['id']==box['id']
    c.drawings.modify(box['id'],hidden=True);assert c._hit_drawing(QPointF(300,250)) is None
    c.drawings.modify(a['id'],hidden=True);assert c._hit_drawing(QPointF(300,155)) is None


def test_label_pick_and_select_tool_click_are_not_precision_marquees(canvas):
    _,c=canvas;o=c.drawings.add('Level',[c._anchor(QPointF(240,150))],name='Long readable horizontal annotation')
    c.drawings.selected=None;c.tool='Select';c.grab();label=c._label_rects(o)[0][1]
    QTest.mouseClick(c,Qt.LeftButton,pos=(label.center()+QPointF(0,0)).toPoint());assert c.drawings.selected==o['id']
    c.drawings.selected=None;c.display['show_labels']=False;c.grab()
    assert c._hit_drawing(QPointF(label.center().x(),label.top()-12)) is None


def test_context_menu_exposes_chart_and_selected_object_settings_without_broker_authority(canvas):
    _,c=canvas;o=c.drawings.add('Level',[c._anchor(QPointF(200,150))]);menu=c.build_context_menu();settings=next(a.menu() for a in menu.actions() if a.text()=='Settings')
    assert {'Chart colours…','Chart settings…','Axes / rulers…','Object selection…'}<=set(a.text() for a in settings.actions())
    object_action=next(a for a in menu.actions() if a.objectName()=='selectedObjectSettings');calls=[];c.editDrawing.connect(calls.append);object_action.trigger();QTest.qWait(10);assert calls==[o['id']]
    captured=[];c.colourSettingsRequested.connect(lambda:captured.append('colours'));next(a for a in settings.actions() if a.text()=='Chart colours…').trigger();QTest.qWait(10);assert captured==['colours']
    c.drawings.modify(o['id'],locked=True);menu.deleteLater();assert not c.grab().isNull()


def test_linked_object_colours_and_bulk_edits_preserve_independence(canvas):
    _,c=canvas;o=c.drawings.add('Rectangle',[c._anchor(QPointF(180,100)),c._anchor(QPointF(400,230))]);before=deepcopy(o)
    d=ObjectProperties(c,o['id']);assert all(pair[0].isChecked() for pair in d.linked_colours.values());assert d.apply() and o==before;d.reject()
    bulk=BulkAppearance(c,[o['id']]);bulk.enabled['fill_color'].setChecked(True);bulk.fields['fill_color'].set_value('#77CCAA');assert bulk.apply()
    assert o['fill_color']=='#77CCAA' and o['anchors']==before['anchors'] and o['color']==before['color'];bulk.reject()
    assert validate_style({'fill_color':None,'text_color':None,'label_background':None})
    for key in ('fill_color','text_color','label_background'):
        with pytest.raises(ValueError):validate_style({key:'nonsense'})


def test_colour_settings_reject_source_change_and_forgiving_pick_is_bounded(canvas):
    _,c=canvas;d=ChartPreferences(c);d.fields['crosshair_color'].set_value('#ABCDEF');c.set_data(rows(),'Other',('scope','new','EURUSD','H1'));assert not d.apply()
    with pytest.raises(ValueError):validate_display({'hit_distance':1000})
    assert validate_display({'hit_distance':32})
