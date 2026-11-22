"""Read-only Forex workspace using shared source-scoped data, never broker calls."""
from __future__ import annotations
import csv,io,json
from datetime import datetime,timezone
from PySide6.QtCore import Qt,Signal,QDateTime,QTimeZone,QSaveFile,QIODevice
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QMenu,QDialog,QDateTimeEdit,QDialogButtonBox,QFileDialog
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.models import thaw
from .chart_canvas import CandleCanvas
from .chart_objects import KINDS
from .chart_object_manager import DrawingManager
from .chart_workflow import ChartWorkflowMixin

CHART_LABELS=('Overview','W1','D1','H4','H1','Structure','ATR / Fib','Signals','Replay','Orders')


def chart_csv(rows):
    """Exact broker observations, not pixels or interpolated/renormalized prices."""
    buffer=io.StringIO(newline='');columns=('symbol','timeframe','open_time','close_time','available_at','open','high','low','close','tick_volume','quote_basis','construction','origin','source_epoch')
    writer=csv.DictWriter(buffer,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    return buffer.getvalue()


class ChartPanel(ChartWorkflowMixin,QWidget):
    connectRequested=Signal()
    frameRequested=Signal(str)
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self.setObjectName('subtab_'+model.subtab_id.replace('.','_'))
        self.frame={'1.2':'W1','1.3':'D1','1.4':'H4','1.5':'H1'}.get(model.subtab_id,'D1');self._fingerprint=None;self._data={}
        outer=QVBoxLayout(self);outer.setContentsMargins(12,8,12,8);outer.setSpacing(4)
        row=QHBoxLayout();self.heading=QLabel();self.heading.setObjectName('chartHeading');row.addWidget(self.heading)
        row.addStretch();self.origin=QLabel();self.origin.setObjectName('chartOrigin');row.addWidget(self.origin);outer.addLayout(row)
        controls=QHBoxLayout();self.frame_picker=QComboBox();self.frame_picker.setObjectName('chartContextFrame');self.frame_picker.setAccessibleName('Chart context timeframe')
        for frame,name in (('W1','Weekly'),('D1','Daily'),('H4','4 hours'),('H1','1 hour')):self.frame_picker.addItem(name,frame)
        self.frame_picker.setCurrentIndex(('W1','D1','H4','H1').index(self.frame));self.frame_picker.currentIndexChanged.connect(lambda index:self.set_frame(self.frame_picker.itemData(index)))
        self.frame_picker.setToolTip('Overview context; the dedicated W1/D1/H4/H1 views stay fixed')
        self.frame_picker.setVisible(model.subtab_id not in {'1.2','1.3','1.4','1.5'});controls.addWidget(self.frame_picker)
        self.quote=QLabel('Bid —    Ask —    Spread —');self.quote.setObjectName('chartQuote');controls.addWidget(self.quote,1)
        self.enable_h1=QPushButton('Enable H1');self.enable_h1.clicked.connect(self._enable_h1);controls.addWidget(self.enable_h1);self.enable_h1.hide();outer.addLayout(controls)
        health=QHBoxLayout();self.health=QLabel();self.health.setObjectName('chartHealth');self.health.setWordWrap(True);health.addWidget(self.health,1)
        self.connection=QPushButton('Connection…');self.connection.setObjectName('chartConnection');self.connection.setToolTip('Manage authentication, select an account and start the shared data feed');self.connection.clicked.connect(self.connectRequested);health.addWidget(self.connection);outer.addLayout(health)
        self.canvas=CandleCanvas();toolbar=QHBoxLayout();toolbar.setSpacing(6);self.chart_toolbar=toolbar
        def button(text,name,tip,callback):
            b=QPushButton(text);b.setObjectName(name);b.setToolTip(tip);b.clicked.connect(callback);toolbar.addWidget(b);return b
        self.zoom_out=button('−','chartZoomOut','Zoom out time axis (−)',lambda:self.canvas.zoom(1.25))
        self.zoom_in=button('+','chartZoomIn','Zoom in time axis (+)',lambda:self.canvas.zoom(.8))
        for b in (self.zoom_in,self.zoom_out):b.setFixedWidth(32)
        self.latest=button('Latest','chartLatest','Return to latest and follow new candles (End)',self.canvas.latest)
        self.fit=button('Fit','chartFit','Reset price scale and return to the latest candles',self.canvas.fit)
        self.style=QComboBox();self.style.setObjectName('chartStyle');self.style.setAccessibleName('Chart type');self.style.addItems(('Candles','OHLC','Line','Dot'));self.style.currentTextChanged.connect(self._style);toolbar.addWidget(self.style)
        self.study_button=QPushButton('Studies');self.study_button.setObjectName('chartStudies');self.study_menu=QMenu(self.study_button)
        self.study_actions={}
        for name in ('SMA 20','EMA 50'):
            action=self.study_menu.addAction(name+' · close');action.setCheckable(True);action.setToolTip('Shared closed-bar display study; not a strategy signal');action.toggled.connect(lambda checked,name=name:self._study(name,checked));self.study_actions[name]=action
        self.study_button.setMenu(self.study_menu);toolbar.addWidget(self.study_button)
        self.tools_button=QPushButton('Tools');self.tools_button.setObjectName('chartTools');self.tools_menu=QMenu(self.tools_button);self.tool_actions={}
        draw_menu=self.tools_menu.addMenu('Draw lines / text');shape_menu=self.tools_menu.addMenu('Draw shapes')
        for name in ('Pan','Select','Ruler','Time ruler','Price ruler',*KINDS):
            owner=shape_menu if name in {'Rectangle','Ellipse','Triangle'} else draw_menu if name in KINDS else self.tools_menu
            action=owner.addAction({'Pan':'Pan / inspect','Select':'Select objects (drag a selection box)','Ruler':'Range ruler · pips + time (Shift+drag)','Time ruler':'Time ruler · observed intervals / elapsed time','Price ruler':'Price ruler · pips / percentage','Level':'Horizontal level','Vertical':'Vertical time marker'}.get(name,name));action.setCheckable(True);action.setChecked(name=='Pan');action.triggered.connect(lambda checked,name=name:self._tool(name));self.tool_actions[name]=action
        self.measure_button=QPushButton('Measure');self.measure_button.setObjectName('chartMeasure');self.measure_button.setToolTip('Time, price or range ruler · drag in chart or directly on the axis · Escape clears')
        self.measure_menu=QMenu(self.measure_button)
        for name in ('Ruler','Time ruler','Price ruler'):self.measure_menu.addAction(self.tool_actions[name])
        self.measure_menu.addSeparator();self.clear_measure=self.measure_menu.addAction('Clear measurement (Esc)',self.canvas.clear_ruler)
        self.measure_menu.addAction('Return to Pan',lambda:self._tool('Pan'));self.measure_button.setMenu(self.measure_menu);toolbar.addWidget(self.measure_button)
        self.edit_menu=self.tools_menu.addMenu('Object actions');self.edit_menu.aboutToShow.connect(self._object_menu)
        visibility_menu=self.tools_menu.addMenu('Viewing options')
        self.grid_action=self._toggle(visibility_menu,'Grid',True,'grid');self.crosshair_action=self._toggle(visibility_menu,'Crosshair',True,'crosshair');self.volume_action=self._toggle(visibility_menu,'Tick volume',False,'volume')
        self.bid_action=self._toggle(visibility_menu,'Bid price line (Ctrl+B)',False,'show_bid');self.ask_action=self._toggle(visibility_menu,'Ask price line',False,'show_ask')
        self.tools_menu.addSeparator();self.tools_menu.addAction('Auto price scale',self._auto_scale);self.tools_menu.addAction('Go to date…',self._go_to);self.tools_menu.addAction('Clear view drawings',self._clear_drawings)
        self.tools_menu.addAction('Drawing defaults…',self._drawing_defaults)
        self.tools_button.setMenu(self.tools_menu);toolbar.addWidget(self.tools_button)
        self.objects=button('Objects','chartObjects','Manage local drawings (Ctrl+D); select/drag handles, Del removes, Ctrl+Z undoes',self._manage_objects)
        self.settings=button('Settings','chartSettings','Chart appearance, interaction, snapping, visibility and shortcut help',self._preferences)
        self.export_button=QPushButton('Export');self.export_button.setObjectName('chartExport');menu=QMenu(self.export_button);menu.addAction('Closed candles CSV…',self._export_csv);menu.addAction('Chart image PNG…',self._export_image);self.export_button.setMenu(menu);toolbar.addWidget(self.export_button);toolbar.addStretch()
        self.view_state=QLabel();self.view_state.setObjectName('chartViewState');toolbar.addWidget(self.view_state);outer.addLayout(toolbar)
        outer.addWidget(self.canvas,1);self.canvas.viewChanged.connect(self._view_state)
        self.canvas.toolChanged.connect(self._tool)
        self.canvas.optionsChanged.connect(self._sync_options);self.canvas.manageDrawings.connect(self._manage_objects);self.canvas.periodStepped.connect(self._step_period)
        self.canvas.editDrawing.connect(self._properties);self.canvas.settingsRequested.connect(self._preferences)
        self.canvas.editSelection.connect(self._bulk_properties)
        self.canvas.axisSettingsRequested.connect(self._axis_preferences)
        self.canvas.colourSettingsRequested.connect(self._colour_preferences)
        self.canvas.selectionSettingsRequested.connect(self._selection_preferences)
        self.ohlc=QLabel('');self.ohlc.setObjectName('chartOhlc');self.ohlc.setMinimumHeight(16);self.canvas.hovered.connect(self._hover);outer.addWidget(self.ohlc)
        self.detail=QLabel();self.detail.setObjectName('chartDetail');self.detail.setWordWrap(True);outer.addWidget(self.detail)
        self.setMinimumHeight(300)
        self._setup_workflow(outer)
        from .chart_projection_bar import ProjectionBar
        self.projection_bar=ProjectionBar(self.canvas,self._public_projection_dialog,self)
        outer.insertWidget(outer.indexOf(self.canvas),self.projection_bar)

    def _chart_focus_mode(self,checked):
        if checked:
            widgets=[layout.itemAt(i).widget() for layout in (self.chart_toolbar,self.workflow_bar) for i in range(layout.count())]
            self._focus_hidden=[v for v in [*widgets,self.ohlc,self.detail] if v is not None and not v.isHidden()]
            for widget in self._focus_hidden:widget.hide()
        else:
            for widget in getattr(self,'_focus_hidden',[]):widget.show()
            self._focus_hidden=[]
        self.projection_bar.chart_only.setText('Restore tools' if checked else 'Chart focus')

    def _toggle(self,menu,label,default,attribute):
        action=menu.addAction(label);action.setCheckable(True);action.setChecked(default)
        action.toggled.connect(lambda checked:(setattr(self.canvas,attribute,checked),self.canvas.update(),self._schedule_save()));return action
    def _style(self,value):self.canvas.style=value;self.canvas.update();self._schedule_save()
    def _study(self,name,checked):
        if checked:self.canvas.studies.add(name)
        else:self.canvas.studies.discard(name)
        self.study_button.setText('Studies'+(f' ({len(self.canvas.studies)})' if self.canvas.studies else ''));self.canvas.update();self._schedule_save()
    def _tool(self,name):
        self.canvas.tool=name
        if name in KINDS and (not self.canvas.display['show_drawings'] or self.canvas.drawings.hidden):
            self.canvas.drawings.hidden=False;self.canvas.set_display({'show_drawings':True})
        for key,action in self.tool_actions.items():action.setChecked(key==name)
        measuring=name in {'Ruler','Time ruler','Price ruler'}
        self.tools_button.setText('Tools' if name=='Pan' or measuring else name);self.canvas.setCursor(Qt.CrossCursor if name!='Pan' else Qt.ArrowCursor)
        self.measure_button.setText('Time ruler' if name=='Time ruler' else 'Price ruler' if name=='Price ruler' else 'Range ruler' if name=='Ruler' else 'Measure')
    def _object_menu(self):
        self.edit_menu.clear();self.canvas.populate_object_menu(self.edit_menu)
    def _auto_scale(self):self.canvas.price_range=None;self.canvas.update()
    def _clear_drawings(self):self.canvas.drawings.clear();self.canvas.ruler=None;self.canvas.update()
    def _manage_objects(self):
        dialog=DrawingManager(self.canvas,self);dialog.exec();dialog.deleteLater()
    def _properties(self,identity):
        from .chart_properties import ObjectProperties
        if self.canvas.drawings.get(identity):
            d=ObjectProperties(self.canvas,identity,self);d.exec();d.deleteLater()
    def _bulk_properties(self):
        from .chart_properties import BulkAppearance
        if self.canvas.drawings.selection:
            d=BulkAppearance(self.canvas,self.canvas.drawings.selection,self);d.exec();d.deleteLater()
    def _preferences(self):
        from .chart_preferences import ChartPreferences
        d=ChartPreferences(self.canvas,self);d.exec();d.deleteLater()
    def _axis_preferences(self):
        from .chart_preferences import ChartPreferences
        d=ChartPreferences(self.canvas,self);d.tabs.setCurrentIndex(1);d.exec();d.deleteLater()
    def _colour_preferences(self):
        from .chart_preferences import ChartPreferences
        d=ChartPreferences(self.canvas,self);d.tabs.setCurrentWidget(d.colour_page);d.exec();d.deleteLater()
    def _selection_preferences(self):
        from .chart_preferences import ChartPreferences
        d=ChartPreferences(self.canvas,self);d.tabs.setCurrentIndex(2);d.exec();d.deleteLater()
    def _drawing_defaults(self):
        from .chart_properties import DrawingDefaults
        d=DrawingDefaults(self.canvas,self);d.exec();d.deleteLater()
    def _sync_options(self):
        self.style.blockSignals(True);self.style.setCurrentText(self.canvas.style);self.style.blockSignals(False)
        for action,attribute in ((self.grid_action,'grid'),(self.crosshair_action,'crosshair'),(self.volume_action,'volume'),(self.bid_action,'show_bid'),(self.ask_action,'show_ask')):
            action.blockSignals(True);action.setChecked(getattr(self.canvas,attribute));action.blockSignals(False)
        if hasattr(self,'layer_actions'):self._sync_layers()
    def _step_period(self,delta):
        frames=('W1','D1','H4','H1');index=(frames.index(self.frame)+delta)%len(frames)
        if self.model.subtab_id in {'1.2','1.3','1.4','1.5'}:self.frameRequested.emit(frames[index])
        else:self.frame_picker.setCurrentIndex(index)
    def _view_state(self):
        pinned=bool(getattr(self,'context',None) or getattr(self,'run_id',None))
        current=bool(self._data.get('health',{}).get('authenticated')) and not pinned
        self.view_state.setText(('Historical' if pinned else 'Following' if current else 'Loaded end') if self.canvas.offset==0 else f'−{self.canvas.offset} bars')
        self.view_state.setToolTip(('Latest loaded completed candle; this label does not establish a fresh quote or active connection.' if self.canvas.offset==0 else 'History inspection; new candles will not move this view. Click Latest to return to the loaded endpoint.')+'\n'+str(len(self.canvas.drawings.selection))+' selected objects · Tools → Object actions or right-click to edit')
        self.objects.setText('Objects'+(f' ({len(self.canvas.drawings.items)})' if self.canvas.drawings.items else ''))
    def _hover(self,text):self.ohlc.setText(text);self.ohlc.setToolTip(text)
    def _go_to(self):
        if not self.canvas.bars:return
        d=QDialog(self);d.setWindowTitle('Go to candle · UTC');box=QVBoxLayout(d);box.addWidget(QLabel('Choose a time within the loaded broker history (UTC).'))
        field=QDateTimeEdit();field.setDisplayFormat('yyyy-MM-dd HH:mm');field.setCalendarPopup(True);field.setTimeZone(QTimeZone(b'UTC'))
        field.setMinimumDateTime(QDateTime.fromString(self.canvas.bars[0]['open_time'],Qt.ISODate));field.setMaximumDateTime(QDateTime.fromString(self.canvas.bars[-1]['open_time'],Qt.ISODate));field.setDateTime(field.maximumDateTime());box.addWidget(field)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(d.accept);buttons.rejected.connect(d.reject);box.addWidget(buttons)
        if d.exec():self.canvas.go_to(field.dateTime().toUTC().toString(Qt.ISODate))
    def _save_text(self,path,text):
        file=QSaveFile(path)
        if not file.open(QIODevice.WriteOnly):return False
        data=text.encode('utf-8');return file.write(data)==len(data) and file.commit()
    def _export_csv(self):
        if not self.canvas.bars:return
        path,_=QFileDialog.getSaveFileName(self,'Export observed closed candles',self.heading.text().replace('  /  ','-')+'.csv','CSV (*.csv)')
        if path:self.detail.setText('Closed broker candles exported.' if self._save_text(path,chart_csv(self.canvas.bars)) else 'Export failed; choose a writable destination.')
    def _export_image(self):
        path,_=QFileDialog.getSaveFileName(self,'Export chart image','SFM-chart.png','PNG (*.png)')
        if path:self.detail.setText('Chart image exported.' if self.grab().save(path,'PNG') else 'Image export failed; choose a writable destination.')
    def _enable_h1(self):self.api.command('1.5','ENABLE_OPTIONAL_H1',{'enabled':True});self.refresh()
    def set_frame(self,frame):self._save_workspace();self.canvas.set_projection_focus(None);self.canvas.projection_page=0;self.frame=frame;self.context=None;self._inspected_stamp=None;self._fingerprint=None;self.workflow_status.setText('');self.refresh()
    def refresh(self):
        if self.context:
            try:self.api.validate_inspection(self.context)
            except ValueError as exc:
                self.canvas.set_data([],'Inspection unavailable',('STALE',None,None,None),empty=str(exc));self.canvas.setup_projections=[];self.canvas.strategy_layers=[];self.canvas.scenario_projection=None;self.canvas.broker_visuals=[];self.quote.setText('Inspection source changed');self.workflow_status.setText(str(exc));return
        self._sync_runs()
        snapshot=self.api.snapshot(self.model.subtab_id);symbol=(self.context or {}).get('symbol',snapshot.data['symbol'])
        broker_inspection=bool(self.context and self.context['object_kind'] in {'order','broker_pending','position'})
        previous=self._data
        data=thaw(self.api.query(self.model.subtab_id,DataRequest('chart',symbol=symbol,timeframe=self.frame,limit=5000,as_of=(self.context or {}).get('as_of') if not self.run_id and not broker_inspection else None,run_id=self.run_id)));self._data=data
        if previous and (previous['scope_id'],previous['source_epoch'],previous['symbol'])!=(data['scope_id'],data['source_epoch'],symbol):self._save_workspace();self._inspected_stamp=None
        quotes=thaw(self.api.query('1.1',DataRequest('watchlist'))) if not self.run_id and not self.context else {'rows':[]};quote=next((v for v in quotes['rows'] if v['symbol']==symbol),{})
        self.heading.setText(symbol+'  /  '+self.frame);origin=data.get('origin','NO_SOURCE');health=data.get('health',{});closed=health.get('market_open') is False
        self.origin.setText('TEST FIXTURE' if origin=='SYNTHETIC_FIXTURE' else 'BROKER DATA' if origin=='LIVE_OBSERVED' else '')
        self.origin.setToolTip('Data provenance, not quote freshness. Market/session and last quote time are shown separately.')
        if quote.get('bid') and quote.get('ask'):
            from decimal import Decimal
            pip=Decimal('.01') if 'JPY' in symbol else Decimal('.0001');spread=(Decimal(quote['ask'])-Decimal(quote['bid']))/pip
            state='last market snapshot' if closed and quote['state']=='STALE' else quote['state'].replace('_',' ').lower()
            self.quote.setText(f"Bid {quote['bid']}    Ask {quote['ask']}    {spread:.1f} pip · {state}")
            self.quote.setToolTip('Provider quote time: '+quote.get('observed_at','unknown')+' · never refreshed by reconnecting')
        else:self.quote.setText('Bid —    Ask —    Spread —')
        disabled=data['status']=='DISABLED';self.enable_h1.setVisible(disabled and self.model.subtab_id=='1.5')
        account_type=health.get('account_type') or 'No account';session='Market closed' if closed else 'Market open' if health.get('market_open') else 'Session unknown'
        history=health.get('history_state','NOT_STARTED');feed=health.get('feed_state','NOT_STARTED')
        if health.get('authenticated'):
            message=f'Connected · {account_type} · {session} · '+('history complete' if history=='COMPLETE' else 'history failed' if history=='FAILED' else 'loading history' if history in {'QUEUED','PARTIAL'} else 'feed not started')
            if closed and health.get('next_open'):message+=' · scheduled open '+health['next_open'][:16].replace('T',' ')+' UTC'
            if history=='FAILED':message+=' · manage connection to retry explicitly'
        else:message='No authenticated account · open Connection to reconnect or choose a data source'
        subscriptions=health.get('live_bar_subscriptions',{})
        if subscriptions.get('FAILED'):message+=' · closed-bar stream incomplete'
        self.health.setText(message);self.health.setToolTip((health.get('history_detail','') or 'Session comes from this account’s current native symbol schedule. Scheduled reopening can change for broker holidays or maintenance.')+'\nClosed-bar subscriptions: '+str(subscriptions)+' · received native updates: '+str(health.get('native_live_bars_received',0)))
        if disabled:empty='H1 inspection is disabled. Enable H1 to inspect it.'
        elif history=='FAILED':empty='Chart history failed to load. Open Connection for the source status; no automatic retry or substituted data.'
        elif health.get('authenticated') and feed in {'WAITING_METADATA','LOADING_HISTORY'}:empty='Loading broker symbol metadata and chart history…'
        elif health.get('authenticated'):empty='No completed candles received for this interval. Open Connection to start or inspect the shared feed.'
        else:empty='No chart source. Open Connection and choose an authenticated account.'
        levels=data.get('levels',[])+data.get('overlays',[])
        fingerprint=json.dumps([data['data_hash'],levels,data['scope_id'],data['source_epoch'],self.frame,disabled],sort_keys=True)
        if fingerprint!=self._fingerprint:
            self._fingerprint=fingerprint;self.ohlc.clear()
            self.canvas.set_data(data['rows'],symbol+' · '+self.frame+' · '+('SYNTHETIC FIXTURE' if origin=='SYNTHETIC_FIXTURE' else 'Completed bid candles · UTC'),(data['scope_id'],data['source_epoch'],symbol,self.frame),empty=empty,levels=levels,studies=data.get('studies'))
        elif self.canvas.empty!=empty:self.canvas.empty=empty;self.canvas.update()
        self._restore_workspace(data);self._update_objects(data)
        self.canvas.strategy_layers=data.get('strategy_layers',[]);self.canvas.reconcile_projection_focus();self.canvas.public_filters_applied='strategy_layers' in data;self.canvas.update()
        if not self.canvas.public_strategy_layers() and self.projection_bar.chart_only.isChecked():self.projection_bar.chart_only.setChecked(False)
        self.projection_bar.schedule()
        self.canvas.setup_projections=data.get('setup_projections',[])
        if self.context and self.context['object_kind'] in {'market_candidate','signal'}:
            projection=thaw(self.api.inspection_projection(self.context))
            self.canvas.setup_projections=[projection] if projection else []
        from sfm_fx_new_age.services.chart_projection import scenario_projection
        self.canvas.scenario_projection=scenario_projection(self.context) if self.context and not self.run_id else None
        if self.canvas.scenario_projection:
            scenario=self.canvas.scenario_projection
            self.workflow_status.setText('Manual scenario · '+(scenario['lots']+' lots · gross '+scenario['gross_quote_pnl']+' '+scenario['quote_currency']+' · ' if 'lots' in scenario else '')+'not risk sizing, funding, signal evidence or broker instruction')
        ready=data.get('readiness',{});self.readiness.setText('Isolated causal Replay · no live quotes, signals or broker overlays' if self.run_id else
            'Research: '+('disabled' if ready.get('disabled') else ready.get('classification','not evaluated').replace('_',' ').lower())+
            ' · missing frames: '+str(len(ready.get('missing_frames',[])))+' · unavailable methods: '+str(len(ready.get('unavailable_methods',[])))+
            ' · qualified candidates: '+str(ready.get('qualified_candidates',0)))
        self.readiness.setToolTip(json.dumps(ready,indent=2))
        self.canvas.broker_visuals=[]
        if (not self.context or broker_inspection) and not self.run_id:
            for category,rows in (('Local order · not broker proof',data.get('orders',[])),('Broker pending · last observed',data.get('broker_pending',[])),('Broker position · last observed',data.get('positions',[]))):
                for row in rows:
                    if row.get('entry_price'):self.canvas.broker_visuals.append(dict(row,category=category))
        self.canvas.set_quotes(quote)
        forming=next((row for row in data.get('forming_bars',[]) if row.get('timeframe')==self.frame),None)
        self.canvas.set_forming(forming if health.get('market_open') is True else None)
        for name,action in self.study_actions.items():
            period=int(name.split()[1]);action.setText(name+' · close'+(f' (needs {period} bars)' if len(data['rows'])<period else ''))
        for b in (self.fit,self.latest,self.zoom_in,self.zoom_out,self.export_button):b.setEnabled(bool(data['rows']))
        self._view_state()
        detail=f"{data['total']} closed candles · Measure: time / price / range · drag axes: scale · Shift+drag axis: measure · UTC"
        if data['rows']:detail+=' · last close '+data['rows'][-1]['close_time'][:16].replace('T',' ')
        if self.canvas.studies:detail+=' · '+', '.join(sorted(self.canvas.studies))+' (display only)'
        if self.model.subtab_id=='1.9':
            run=data.get('run',{});detail=('Replay '+self.run_id+' · '+run.get('state','')+' · clock '+str(run.get('as_of'))+' · cursor '+str(run.get('cursor'))+' · execution disabled') if self.run_id else 'Select or create an isolated replay run. Current market preview is not a replay.'
            self.replay_seek.setMaximum(run.get('total_items',1)-1)
            if self.run_id:self.health.setText('Historical replay · isolated clock · no broker execution');self.quote.setText('Replay clock: '+str(run.get('as_of')));self.origin.setText('REPLAY')
        if self.context and not self.run_id:self.health.setText(('Read-only broker observation · selected '+self.context['object_id']+' · provider observation is not refreshed by navigation') if broker_inspection else 'Pinned historical inspection · as of '+self.context['as_of']+' · no current quote / order overlay')
        if self.model.subtab_id=='1.10':detail+=' · local orders '+str(len(data.get('orders',[])))+' · positions '+data.get('position_observation',{}).get('status','UNKNOWN')+' · pending '+str(data.get('pending_observation',{}).get('observed_at','UNKNOWN'))+' · no chart order entry'
        self.detail.setText(detail)
