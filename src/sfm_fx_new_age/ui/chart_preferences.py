"""Grouped local chart settings. No feed, account or order ownership."""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QTabWidget,QCheckBox,QComboBox,
 QDoubleSpinBox,QSpinBox,QDialogButtonBox,QPushButton,QLabel)
from sfm_fx_new_age.contracts.chart_display import DISPLAY_DEFAULTS,COLOR_GROUPS
from .chart_properties import ColorButton,DrawingDefaults,scroll_form


class ChartPreferences(QDialog):
    def __init__(self,canvas,parent=None):
        super().__init__(parent if parent is not None else canvas);self.canvas=canvas;self.identity=canvas.data_identity;self.setObjectName('chartPreferences');self.setWindowTitle('Chart settings');self.resize(550,530);self.fields={}
        outer=QVBoxLayout(self);notice=QLabel('Local display preferences · scoped to account / symbol / timeframe. Apply saves; Cancel discards only unapplied changes.');notice.setWordWrap(True);outer.addWidget(notice)
        self.tabs=QTabWidget();outer.addWidget(self.tabs,1)
        a=scroll_form(self.tabs,'Appearance');r=scroll_form(self.tabs,'Axes / rulers');n=scroll_form(self.tabs,'Navigation');v=scroll_form(self.tabs,'Visibility');help=scroll_form(self.tabs,'Help')
        colours=scroll_form(self.tabs,'Colours');self.colour_page=self.tabs.widget(self.tabs.count()-1)
        palette_note=QLabel('All chart palette roles · choose any RGB colour. These display colours never change prices, object identity or broker state. Object-specific colours are under the selected object’s settings.');palette_note.setWordWrap(True);colours.addRow(palette_note)
        axis_note=QLabel('Time labels are UTC and use loaded candles only. Plain axis drag scales; Shift+drag measures. Esc clears a measurement. Rulers never create observations or orders.');axis_note.setWordWrap(True);r.addRow(axis_note)
        self.theme=QComboBox();self.theme.addItems(('Custom','SFM navy','Light chart','High contrast'));a.addRow('Colour preset',self.theme);self.theme.currentTextChanged.connect(self.preset)
        for group,items in COLOR_GROUPS:
            heading=QLabel(group);heading.setStyleSheet('font-weight:600; margin-top:8px;');colours.addRow(heading)
            for key,label in items:
                field=ColorButton(canvas.display[key]);field.setObjectName('chartSetting_'+key);field.setAccessibleName(label+' colour');self.fields[key]=field;colours.addRow(label,field)
        shortcut=QPushButton('Chart colours…');shortcut.clicked.connect(lambda:self.tabs.setCurrentWidget(self.colour_page));a.addRow(shortcut)
        shortcut=QPushButton('Measurement colour…');shortcut.clicked.connect(lambda:self.tabs.setCurrentWidget(self.colour_page));r.addRow(shortcut)
        for f,key,label,lo,hi,step in ((a,'wick_width','Wick width',.5,4,.5),(a,'candle_width','Candle width (%)',15,90,1),
          (a,'line_width','Price line width',.5,6,.5),(a,'dot_radius','Dot radius (px)',1,6,.5),(r,'axis_font_size','Axis text size (pt)',8,16,1),
          (r,'price_tick_spacing','Price tick spacing (px)',28,100,4),(r,'time_tick_spacing','Time label spacing (px)',70,240,5),
          (a,'crosshair_width','Crosshair width',.5,3,.5),(n,'right_margin','Right margin (bar spaces)',0,20,1),(n,'price_padding','Auto-scale padding (%)',2,40,1),
          (n,'snap_distance','Nearby snap distance (px)',2,20,1),(n,'hit_distance','Object pick radius (px)',4,32,1),
          (n,'nudge_pips','Nudge price (pips)',.1,100,.1),(a,'volume_height','Volume height (px)',35,120,1)):
            field=QDoubleSpinBox();field.setRange(lo,hi);field.setSingleStep(step);field.setValue(canvas.display[key]);field.setObjectName('chartSetting_'+key);self.fields[key]=field;f.addRow(label,field)
        field=QSpinBox();field.setRange(1,20);field.setValue(canvas.display['nudge_bars']);field.setObjectName('chartSetting_nudge_bars');self.fields['nudge_bars']=field;n.addRow('Nudge time (bar spaces)',field)
        for form,key,label,choices in ((n,'snap_mode','Chart object snapping',('Nearby','Always','Off')),(n,'pan_mode','Drag behavior',('Time and price','Time only')),
          (a,'grid_style','Grid line style',('Solid','Dash','Dot','Dash dot')),(a,'crosshair_style','Crosshair line style',('Solid','Dash','Dot','Dash dot')),
          (r,'time_label_format','Time labels (UTC)',('Adaptive UTC','ISO date + time','Date only')),
          (r,'ruler_position','Measurement readout position',('Top left','Top right','Bottom left','Bottom right'))):
            field=QComboBox();field.addItems(choices);field.setCurrentText(canvas.display[key]);field.setObjectName('chartSetting_'+key);self.fields[key]=field;form.addRow(label,field)
        self.wheel=QComboBox();self.wheel.addItems(('Zoom','Scroll'));self.wheel.setCurrentText(canvas.wheel_mode);n.addRow('Mouse wheel',self.wheel)
        pick_note=QLabel('Object picking uses a generous invisible halo (default 14 px), chooses the nearest edge or label and shows a hand cursor on hover. Filled interiors are a fallback. Increase the radius here if needed; existing saved custom values are retained.');pick_note.setWordWrap(True);n.addRow(pick_note)
        for form,key,label in ((r,'axis_panel','Shaded time / price axis rails'),(r,'axis_minor_ticks','Minor axis ticks'),(r,'show_axis_highlight','Highlight hovered axis'),
          (r,'show_ruler_card','Persistent measurement readout'),(r,'show_ruler_guides','Measurement endpoint guides'),
          (n,'one_shot','Return to Pan after drawing'),(n,'select_filled','Select filled shapes by interior'),
          (a,'bull_filled','Fill bullish candle bodies'),(a,'bear_filled','Fill bearish candle bodies'),(v,'grid_horizontal','Horizontal grid lines'),(v,'grid_vertical','Vertical grid lines'),
          (v,'show_close','Last completed close line'),(v,'show_forming','Partial forming candle'),(v,'show_research','Research regions'),(v,'show_broker','Read-only broker / local inventory'),
          (v,'show_setups','Candidate / local signal geometry'),(v,'show_scenarios','Manual calculator scenario'),
          (v,'show_labels','Drawing labels / text'),(v,'show_drawings','Local chart drawings'),(v,'show_title','Chart title'),(v,'show_study_legend','Study legend')):
            field=QCheckBox(label);field.setChecked(canvas.display[key]);field.setObjectName('chartSetting_'+key);self.fields[key]=field;form.addRow(field)
        self.simple={}
        for key,label in (('grid','Grid (master switch)'),('crosshair','Crosshair'),('volume','Native tick volume'),('show_bid','Bid line'),('show_ask','Ask line')):
            field=QCheckBox(label);field.setChecked(getattr(canvas,key));field.setObjectName('chartSetting_'+key);self.simple[key]=field;v.addRow(field)
        text=QLabel('Drawing actions\nTools → Select: drag a selection box; Ctrl adds to selection\nDouble-click / Enter: selected object properties\nCtrl+click: toggle selection · Ctrl+drag: duplicate\nCtrl+C / X / V: chart-local copy / cut / paste\nCtrl+Shift+D: duplicate · Ctrl+Z: undo\nCtrl+Y / Ctrl+Shift+Z: redo\nAlt+arrow: nudge by configured bars / pips\nShift+Alt+arrow: ten nudge steps\nDel: delete selection · Escape: cancel gesture\nCtrl+D: Objects · Ctrl+H: hide / show drawings\nShift or Alt while drawing: bypass price snapping\n\nChart navigation\nWheel: chosen mode · Ctrl+wheel: zoom\nDrag right price scale / bottom time scale: rescale\nHome / End: oldest / latest · Page Up/Down: history\nUp / Down: timeframe · Shift+drag in Pan: measure\n\nDrawings in blank space are local annotations, not observations. Outside loaded bars, time coordinates use nominal W1/D1/H4/H1 spacing; no candles or trading sessions are fabricated. Snaps only use observed OHLC.\n\nNo setting, drawing, paste or property edit places or modifies broker orders. Copy/paste and undo remain bound to the exact source / epoch / symbol / frame.');text.setWordWrap(True);help.addRow(text)
        row=QHBoxLayout();defaults=QPushButton('Drawing defaults…');defaults.setObjectName('chartDrawingDefaultsButton');defaults.clicked.connect(self.drawing_defaults);row.addWidget(defaults)
        reset=QPushButton('Reset display defaults');reset.clicked.connect(self.reset);row.addWidget(reset);outer.addLayout(row)
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Apply|QDialogButtonBox.Cancel);b.accepted.connect(self.ok);b.rejected.connect(self.reject);b.button(QDialogButtonBox.Apply).clicked.connect(self.apply);outer.addWidget(b)
        self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self.check_source);self.finished.connect(self.timer.stop);self.timer.start()
    def check_source(self):
        valid=self.canvas.data_identity==self.identity
        if not valid:self.reject()
        return valid
    def drawing_defaults(self):
        if self.check_source():
            d=DrawingDefaults(self.canvas,self);d.exec();d.deleteLater()
    def preset(self,name):
        palettes={'SFM navy':{k:DISPLAY_DEFAULTS[k] for k in ('background','foreground','grid_color','bull_color','bear_color','line_color')},
          'Light chart':dict(background='#F5F7FB',foreground='#18212F',grid_color='#D5DBE5',bull_color='#087F5B',bear_color='#BE123C',line_color='#1D4ED8'),
          'High contrast':dict(background='#080C14',foreground='#FFFFFF',grid_color='#46536A',bull_color='#5DE1A6',bear_color='#FF8C9B',line_color='#F4C66B')}
        if name not in palettes:return
        base=palettes[name];extended={key:DISPLAY_DEFAULTS[key] for _,items in COLOR_GROUPS for key,_ in items};extended.update(base)
        for key,source in {'axis_color':'foreground','title_color':'foreground','crosshair_color':'foreground','selection_color':'foreground',
            'axis_border_color':'grid_color','bull_wick_color':'bull_color','bull_border_color':'bull_color','volume_bull_color':'bull_color',
            'bear_wick_color':'bear_color','bear_border_color':'bear_color','volume_bear_color':'bear_color','close_color':'line_color',
            'forming_color':'line_color','research_color':'line_color','ask_color':'bull_color','broker_color':'bull_color'}.items():extended[key]=base[source]
        if name=='Light chart':extended.update(axis_background_color='#EDF1F7',bid_color='#8A5B00',ruler_color='#8A5B00',sma_color='#8A5B00',ema_color='#7254B8',setup_color='#7254B8',scenario_color='#8A5B00',local_order_color='#7254B8')
        for key,value in extended.items():self.fields[key].set_value(value)
    def values(self):
        return {k:f.value if isinstance(f,ColorButton) else f.isChecked() if isinstance(f,QCheckBox) else f.currentText() if isinstance(f,QComboBox) else f.value() for k,f in self.fields.items()}
    def reset(self):
        for k,f in self.fields.items():
            value=DISPLAY_DEFAULTS[k]
            if isinstance(f,ColorButton):f.set_value(value)
            elif isinstance(f,QCheckBox):f.setChecked(value)
            elif isinstance(f,QComboBox):f.setCurrentText(value)
            else:f.setValue(value)
        for k,f in self.simple.items():f.setChecked(k in {'grid','crosshair'})
        self.wheel.setCurrentText('Zoom');self.theme.setCurrentText('Custom');self.status.setText('Defaults staged; Apply to save. Objects and per-tool drawing styles are unchanged.')
    def apply(self):
        if not self.check_source():return False
        try:
            self.canvas.set_display(self.values())
            for k,f in self.simple.items():setattr(self.canvas,k,f.isChecked())
            self.canvas.wheel_mode=self.wheel.currentText();self.canvas.optionsChanged.emit();self.canvas.update();self.status.setText('Applied locally');return True
        except ValueError as exc:self.status.setText(str(exc));return False
    def ok(self):
        if self.apply():self.accept()
