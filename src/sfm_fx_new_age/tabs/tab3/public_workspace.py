"""Simple public-method projection switches; all computation stays in core."""
import json
from collections import Counter
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QCheckBox,QTextEdit,QPushButton,QSizePolicy)
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.public_strategies import METHODS,BY_KEY


class PublicStrategiesPanel(QWidget):
    signalsRequested=Signal(str,str)
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self.context=None;self._rows={};self.checkboxes={};self._input_sources={}
        self._readiness_counts={}
        self.setObjectName('subtab_3_1');outer=QVBoxLayout(self);outer.setContentsMargins(14,10,14,10)
        heading=QLabel('Public forex strategies · charts and research signals');heading.setProperty('role','heading');head=QHBoxLayout();head.addWidget(heading,1)
        self.details_toggle=QPushButton('Method details');self.details_toggle.setObjectName('strategyDetailsToggle');self.details_toggle.setCheckable(True);self.details_toggle.setToolTip('Show or hide the selected method’s exact rules, sources and evaluation. This does not change Project selections.');head.addWidget(self.details_toggle);outer.addLayout(head)
        note=QLabel('Enable methods for Tab 1 projections and Tab 4 research signal policies. Saved switches; exact source / pair / frame. Context alone is not an entry. No automatic orders.');note.setWordWrap(True);outer.addWidget(note)
        bar=QHBoxLayout();self.search=QLineEdit();self.search.setObjectName('strategySearch');self.search.setPlaceholderText('Find a strategy or family…');self.search.textChanged.connect(self._filter);bar.addWidget(self.search,1)
        self.frame_picker=QComboBox();self.frame_picker.setObjectName('strategyTimeframe');self.frame_picker.addItems(('W1','D1','H4','H1'));self.frame_picker.setCurrentText('H4');self.frame_picker.currentTextChanged.connect(self.refresh);bar.addWidget(self.frame_picker)
        self.chart_button=QPushButton('Open pair chart');self.chart_button.setObjectName('strategyOpenChart');self.chart_button.clicked.connect(self._chart);bar.addWidget(self.chart_button);outer.addLayout(bar)
        self.signals_button=QPushButton('View signals in Tab 4');self.signals_button.setObjectName('strategyOpenSignals');self.signals_button.clicked.connect(self._signals);bar.addWidget(self.signals_button)
        filters=QHBoxLayout()
        self.family_filter=QComboBox();self.family_filter.setObjectName('strategyFamilyFilter');self.family_filter.setAccessibleName('Strategy family filter');self.family_filter.addItem('All families');self.family_filter.addItems(sorted({m.family for m in METHODS}));self.family_filter.currentTextChanged.connect(self._filter);filters.addWidget(self.family_filter)
        self.state_filter=QComboBox();self.state_filter.setObjectName('strategyStateFilter');self.state_filter.setAccessibleName('Strategy evaluation filter');self.state_filter.addItems(('All states','Ready','No setup','Data needed','Waiting','Errors','Off'));self.state_filter.currentTextChanged.connect(self._filter);filters.addWidget(self.state_filter)
        self.selected_only=QCheckBox('Selected only');self.selected_only.setObjectName('strategySelectedOnly');self.selected_only.setToolTip('Filter the list only; never change Project switches');self.selected_only.toggled.connect(self._filter);filters.addWidget(self.selected_only)
        self.filter_count=QLabel();self.filter_count.setObjectName('strategyFilterCount');filters.addWidget(self.filter_count,1)
        self.reset_filters=QPushButton('Reset filters');self.reset_filters.setObjectName('strategyResetFilters');self.reset_filters.clicked.connect(self._reset_filters);filters.addWidget(self.reset_filters);outer.addLayout(filters)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setObjectName('publicStrategyStatus');outer.addWidget(self.status)
        self.table=QTableWidget(len(METHODS),4);self.table.setObjectName('publicStrategyCatalogue');self.table.setHorizontalHeaderLabels(('Enable','Strategy','Family','Current frame'))
        self.table.setMinimumHeight(105);self.table.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Ignored)
        self.table.verticalHeader().hide();self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.table.setColumnWidth(0,64);self.table.setColumnWidth(2,112);self.table.setColumnWidth(3,125);outer.addWidget(self.table,3)
        for i,m in enumerate(METHODS):
            box=QCheckBox();box.setObjectName('standardStrategy_'+m.key);box.setAccessibleName(m.name+' chart and signal policy');box.setToolTip(m.rules)
            box.clicked.connect(lambda checked,key=m.key:self._switch(key,checked));self.checkboxes[m.key]=box;self.table.setCellWidget(i,0,box)
            self.table.setItem(i,1,QTableWidgetItem(m.name));self.table.setItem(i,2,QTableWidgetItem(m.family));self.table.setItem(i,3,QTableWidgetItem('Off'));self.table.setRowHeight(i,29)
        # Stable alias retained for previously accepted Order Block widget journeys.
        self.strategy_enabled=self.checkboxes['order_block']
        self.table.itemSelectionChanged.connect(self._details)
        self.details=QTextEdit();self.details.setReadOnly(True);self.details.setObjectName('publicStrategyDetails');self.details.setMinimumHeight(78);self.details.setMaximumHeight(160);self.details.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Ignored);outer.addWidget(self.details,1)
        self.details.hide();self.details_toggle.toggled.connect(self.details.setVisible)
        self.feedback=QLabel('Public documentation establishes method identity, not profitability. Exact bounded profiles and sources are shown when a row is selected.');self.feedback.setWordWrap(True);outer.addWidget(self.feedback)
        # Hidden workspaces must not query snapshots during shell construction.
        self.table.selectRow(0)
    def _switch(self,key,enabled):
        m=BY_KEY[key];result=self.api.command('3.1','ENABLE_RECIPE',{'recipe_id':m.recipe_id,'version':m.version,'enabled':enabled})
        self.feedback.setText(result.message);self.refresh()
    def _filter(self,*_):
        from .public_activity_alternatives import ACTIVITY_NAMES
        terms=self.search.text().casefold().split();visible=[]
        family=self.family_filter.currentText();wanted=self.state_filter.currentText()
        states={'Ready':'READY','No setup':'NO_SETUP','Data needed':'DATA_UNAVAILABLE','Errors':'ERROR','Off':'OFF'}
        for i,m in enumerate(METHODS):
            names=' '.join((m.name,m.family,self.table.item(i,1).text(),ACTIVITY_NAMES.get(m.key,'')))
            row=self._rows.get(m.key,{});enabled=row.get('enabled',False);state=row.get('evaluation',{}).get('state','WAITING_SOURCE') if enabled else 'OFF'
            match=all(term in names.casefold() for term in terms) and (family=='All families' or family==m.family) and (not self.selected_only.isChecked() or enabled)
            if wanted=='Waiting':match=match and state not in {'READY','NO_SETUP','DATA_UNAVAILABLE','ERROR','OFF'}
            elif wanted in states:match=match and state==states[wanted]
            self.table.setRowHidden(i,not match)
            if match:visible.append(i)
        self.filter_count.setText(str(len(visible))+' / '+str(len(METHODS))+' shown')
        if not visible:
            self.table.clearSelection();self.table.setCurrentCell(-1,-1);self.details.setPlainText('No strategies match these filters. Reset filters to show all strategies. Project selections are unchanged.')
        elif self.table.currentRow() not in visible:self.table.selectRow(visible[0])

    def _reset_filters(self):
        for widget in (self.search,self.family_filter,self.state_filter,self.selected_only):widget.blockSignals(True)
        self.search.clear();self.family_filter.setCurrentIndex(0);self.state_filter.setCurrentIndex(0);self.selected_only.setChecked(False)
        for widget in (self.search,self.family_filter,self.state_filter,self.selected_only):widget.blockSignals(False)
        self._filter()
    def _details(self):
        i=self.table.currentRow()
        if i<0 or self.table.isRowHidden(i):return
        m=METHODS[i];row=self._rows.get(m.key,{})
        from .public_activity_alternatives import ACTIVITY_NAMES
        warmup='21 (automatic close-only) / 1 plus explicit intrabar count' if m.key=='cause_effect' else str(m.warmup)
        data_label='Native completed closes / tick grid; optional POINT_FIGURE_TICKS override' if m.key=='cause_effect' else 'Genuine broker-scoped displayed depth or validated venue book; scopes remain distinct' if m.key=='dom_imbalance' else (m.data_kind or 'Closed price bars / native symbol facts')
        self.details.setPlainText(m.name+'\n\nExact coded profile: '+m.rules+'\n\nMinimum own-frame completed bars: '+warmup+'\nSupporting frames: '+(', '.join(m.input_frames) or 'Own frame')+'\nAdditional data: '+data_label+'\nDocument recipes (projection coverage only): '+(', '.join(m.document_recipes) or 'Public method / supporting sensor')+'\nSource definitions:\n'+'\n'.join(m.sources)+'\n\nCurrent evaluation:\n'+json.dumps(row.get('evaluation',{}),indent=2)+'\n\nUNCALIBRATED PROJECTION ONLY · not historical SFM acceptance, trade qualification, a win probability or execution authority. Missing genuine data is not a working projection.')
        if m.key=='cause_effect':
            self.details.append('\nDefault input: original completed own-frame closes and native tick grid. Automatic frozen ATR20 / 3-box / 5-column triple-break profile; no external count request or manual direction is needed. A configured POINT_FIGURE_TICKS source instead selects the explicit intrabar-count mode. These are distinct disclosed research interpretations, not operator-supplied discretionary settings.')
        elif m.key=='dom_imbalance':
            self.details.append('\nDOM_BOOK in the supplied scanner specification permits broker- or venue-scoped displayed depth. Genuine acknowledged cTrader BROKER_DEPTH is eligible in normal AND --strict-genuine-data modes, not a tick/quote-activity proxy. The top-five displayed-size calculation retains its original 15-second broker receipt expiry, with no native event clock, sequence, full venue-book, execution or aggressor claim. Explicit venue evidence takes precedence; a bad supplied venue source is refused rather than hidden by fallback. Native-chain full books and checksum L2 keep their own scopes and qualification. Current metrics disclose the actual source, units, clock basis and full-book limitations.')
        elif m.key in ACTIVITY_NAMES:
            self.details.append('\nNormal Desktop also connects read-only to Kraken public fiat markets for original executions, documented taker sides and native closed executed-hour totals. These are visibly labelled Kraken venue context, never cTrader fills or market-wide FX volume. Quantity methods require complete exact chart-bar coverage; absent coverage remains warmup, not synthetic zero volume. No API credentials or Kraken trading account are used.')
            self.details.append('\nNormal Desktop permits this separately named interpretation when strict inputs are absent: '+ACTIVITY_NAMES[m.key]+'. Tick counts / observed quote samples are not executed currency units. Quote UP/DOWN changes are not aggressors. Broker DOM is observed displayed liquidity using a local receive clock, not a sequenced global/full venue book.\nThe active interpretation and units are in Current evaluation → metrics and on chart labels. --strict-genuine-data disables these alternatives. An available valid strict source takes precedence. No fake weights, aggressors or native sequence are generated.')
        elif m.data_kind and m.data_kind!='LIVE_QUOTE':
            providers=[p for p in self._input_sources.get('providers',[]) if m.data_kind in p['kinds']]
            self.details.append('\nLocal input status (publisher declaration, not vendor authentication):\n'+json.dumps(providers,indent=2)+'\nConfigure sources explicitly at startup with --supplemental-config. No source is enabled merely by ticking this row. No OHLC proxy is substituted.')
            requirement={
                'TRADED_PRINTS':'Original matching venue executions with executed prices and quantities. Quote counts, tick-count bar volume and displayed bid/ask sizes are not executed quantity.',
                'AGGRESSOR_PRINTS':'Original matching venue executions with price, quantity and known aggressor side. A quote uptick/downtick does not establish the aggressor.',
                'VENUE_BOOK':'Original two-sided venue book initialized by a full snapshot, followed by uninterrupted vendor-native sequence updates. A local receive ordinal does not establish a complete book.',
            }.get(m.data_kind)
            if requirement:self.details.append('\nRequired evidence: '+requirement+'\nNo source access or successful live qualification is implied by an implemented algorithm or an enabled switch.')
        from sfm_fx_new_age.contracts.strategy_signals import POLICIES
        self.details.append('\n\nTab 4 signal policy (new, uncalibrated research composition): '+POLICIES[m.key].description+'\nAll source / freshness / target / native geometry gates remain enforced at binding and again at Issue. This is separate from the legacy Order Block D1/H4 14-gate evaluator.')
    def refresh(self,*_):
        snapshot=self.api.snapshot('3.1');symbol=(self.context or {}).get('symbol',snapshot.data['symbol']);frame=self.frame_picker.currentText()
        result=thaw(self.api.query('3.1',DataRequest('strategy_catalogue',symbol=symbol,timeframe=frame,limit=500)))
        self._input_sources=result.get('input_sources',{})
        self._rows={r['key']:r for r in result['rows']};enabled=0;states=Counter()
        for i,m in enumerate(METHODS):
            row=self._rows.get(m.key,{});checked=row.get('enabled',False);enabled+=checked
            box=self.checkboxes[m.key];box.blockSignals(True);box.setChecked(checked);box.setEnabled(bool(row));box.blockSignals(False)
            box.setText('On' if checked else 'Off')
            state=row.get('evaluation',{}).get('state','WAITING_SOURCE') if checked else 'OFF'
            states[state]+=1
            self.table.item(i,3).setText('Data needed' if state=='DATA_UNAVAILABLE' else state.replace('_',' ').title())
            self.table.item(i,3).setToolTip(row.get('evaluation',{}).get('reason',''))
            metrics=row.get('evaluation',{}).get('metrics',{})
            self.table.item(i,1).setText(metrics.get('interpretation_name',m.name))
            self.table.item(i,1).setToolTip(metrics.get('semantic_warning',m.rules))
            box.setAccessibleName(self.table.item(i,1).text()+' chart and signal policy')
            box.setToolTip(m.rules+'\n\n'+row.get('evaluation',{}).get('reason',''))
        self._readiness_counts=dict(states)
        waiting=sum(value for state,value in states.items() if state not in {'READY','NO_SETUP','DATA_UNAVAILABLE','ERROR','OFF'})
        summary=' · '.join(label+' '+str(value) for label,value in (
            ('Ready',states['READY']),('No setup',states['NO_SETUP']),('Data needed',states['DATA_UNAVAILABLE']),
            ('Waiting',waiting),('Errors',states['ERROR']),('Off',states['OFF'])))
        self.status.setText(symbol+' · '+frame+' · '+str(enabled)+' / '+str(len(METHODS))+' chart / signal policies on\n'+summary)
        self.status.setToolTip('Counts cover the exact displayed pair / source / frame, including search-hidden rows. Ready means recorded analytical geometry, not live connection health, trade qualification or profitability. No setup is a completed evaluation without a qualifying pattern.\n'+json.dumps(self._readiness_counts,sort_keys=True))
        self._filter();self._details()
    def apply_inspection(self,context):
        if context.get('mode')=='REPLAY':raise ValueError('Live strategy switches do not relabel replay data')
        self.context=thaw(self.api.validate_inspection(context));self.frame_picker.setCurrentText(context['timeframe']);self.refresh()
    def inspection_context(self):return self.context
    def _chart(self):
        symbol=(self.context or {}).get('symbol',self.api.snapshot('3.1').data['symbol']);frame=self.frame_picker.currentText()
        self.api.navigate({'W1':'1.2','D1':'1.3','H4':'1.4','H1':'1.5'}[frame],self.api.inspect(symbol=symbol,timeframe=frame))
    def _signals(self):
        symbol=(self.context or {}).get('symbol',self.api.snapshot('3.1').data['symbol'])
        # The research list is useful before a source is connected as well.
        # Carry a validated inspection when available; never fabricate one.
        try:context=self.api.inspect(symbol=symbol,timeframe=self.frame_picker.currentText())
        except ValueError:
            self.signalsRequested.emit(symbol,self.frame_picker.currentText());return
        self.api.navigate('4.1',context)
