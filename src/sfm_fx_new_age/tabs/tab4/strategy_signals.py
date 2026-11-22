"""Tab 4: source-bound research signals, separate from the explicit Issue queue."""
from collections import Counter
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QLineEdit,
    QPushButton,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView,QTextEdit,QSizePolicy,QTabWidget,QCheckBox)
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.domain import PAIRS


class StrategySignalsPanel(QWidget):
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self.context=None;self._rows=[];self._fingerprint=None
        self.setObjectName('strategySignalsPanel');outer=QVBoxLayout(self);outer.setContentsMargins(12,8,12,8);outer.setSpacing(6)
        title=QLabel('Strategy signals · 83 source-bound research pipelines');title.setProperty('role','heading');outer.addWidget(title)
        note=QLabel('Enable strategies in Tab 3. Qualifying research signals appear here automatically. Context studies need their disclosed price trigger. Binding sends no order; Issue remains separate.');note.setWordWrap(True);outer.addWidget(note)
        controls=QHBoxLayout();self.pair=QComboBox();self.pair.setObjectName('signalPair');self.pair.addItems(PAIRS)
        self.frame=QComboBox();self.frame.setObjectName('signalFrame');self.frame.addItems(('W1','D1','H4','H1'));self.frame.setCurrentText('H4')
        self.filter=QComboBox();self.filter.setObjectName('signalStateFilter');self.filter.addItems(('All strategies','Enabled only','Signals only','Ready to bind','Data needed'))
        self.search=QLineEdit();self.search.setObjectName('signalStrategySearch');self.search.setPlaceholderText('Find strategy…')
        for w in (self.pair,self.frame,self.filter):controls.addWidget(w);w.currentIndexChanged.connect(self.refresh)
        controls.addWidget(self.search,1);self.search.textChanged.connect(self._filter);outer.addLayout(controls)
        self.summary=QLabel();self.summary.setObjectName('strategySignalSummary');self.summary.setWordWrap(True);outer.addWidget(self.summary)
        self.table=QTableWidget(0,6);self.table.setObjectName('strategySignalTable');self.table.setHorizontalHeaderLabels(('Strategy','State','Side','Limit','Invalidation','Objective'))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide();self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        for i,width in enumerate((0,120,55,95,95,95)):
            if i:self.table.setColumnWidth(i,width)
        self.table.setMinimumHeight(90);self.table.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Ignored);self.table.itemSelectionChanged.connect(self._selected);outer.addWidget(self.table,3)
        self.details=QTextEdit();self.details.setReadOnly(True);self.details.setObjectName('strategySignalDetails');self.details.setMinimumHeight(65);self.details.setMaximumHeight(150);self.details.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Ignored);outer.addWidget(self.details,1)
        row=QHBoxLayout();self.units=QLineEdit();self.units.setObjectName('strategySignalUnits');self.units.setPlaceholderText('Explicit units · native min/max/step')
        self.ack=QCheckBox('Research policy reviewed');self.ack.setObjectName('strategySignalAcknowledgement')
        self.bind=QPushButton('Bind local proposal');self.bind.setObjectName('bindStrategySignal');self.bind.clicked.connect(self._bind)
        self.chart=QPushButton('Show pair chart');self.chart.setObjectName('strategySignalChart');self.chart.clicked.connect(self._chart)
        row.addWidget(self.units,2);row.addWidget(self.ack);row.addWidget(self.bind);row.addWidget(self.chart);outer.addLayout(row)
        self.ack.toggled.connect(self._actions);self.units.textChanged.connect(self._actions)
        self.feedback=QLabel('No automatic orders. Research readiness is not profitability or account-level risk approval.');self.feedback.setWordWrap(True);self.feedback.setObjectName('strategySignalFeedback');outer.addWidget(self.feedback)
        self.bind.setEnabled(False)

    def selected(self):
        i=self.table.currentRow();return self._rows[i] if 0<=i<len(self._rows) and not self.table.isRowHidden(i) else None

    def _selected(self,*_,reset_review=True):
        row=self.selected()
        if reset_review:self.ack.setChecked(False)
        if not row:self.details.setPlainText('Select a strategy to see its signal policy and the exact wait/blocker.');self._actions();return
        trigger=row.get('trigger')
        text=row['name']+' · '+row['timeframe']+' · '+row['state']+'\n'+row['reason']+'\n\nSignal policy: '+row['policy']
        if trigger:text+='\n\nTrigger known at '+row['available_at']+'; expires '+str(row['expires_at'])+'\nSource: '+row['origin']+' / '+str(row['source_epoch'])
        if row.get('blockers'):text+='\n\nBinding blockers: '+', '.join(row['blockers'])
        if row.get('source_metrics',{}).get('semantic_warning'):text+='\n\n'+row['source_metrics']['semantic_warning']
        text+='\n\nUNCALIBRATED RESEARCH POLICY · not original OB-MTF qualification, independent consensus, a success probability or permission to order.'
        self.details.setPlainText(text);self._actions()

    def _actions(self,*_):
        row=self.selected();self.bind.setEnabled(bool(row and row.get('opportunity_id') and row['state']=='SIGNAL' and self.ack.isChecked() and self.units.text().strip()))

    def _filter(self,*_):
        terms=self.search.text().casefold().split();mode=self.filter.currentText()
        for i,row in enumerate(self._rows):
            show=all(t in row['name'].casefold() for t in terms)
            if mode=='Enabled only':show &= row['enabled']
            elif mode=='Signals only':show &= bool(row.get('opportunity_id'))
            elif mode=='Ready to bind':show &= row['state']=='SIGNAL'
            elif mode=='Data needed':show &= row['state'] in {'WARMUP','DATA_UNAVAILABLE','UNAVAILABLE','WAITING'}
            self.table.setRowHidden(i,not show)
        if not self.selected():self.table.clearSelection();self._selected()

    def refresh(self,*_):
        symbol=self.pair.currentText();frame=self.frame.currentText()
        data=thaw(self.api.query('4.1',DataRequest('strategy_signals',symbol=symbol,timeframe=frame,limit=5000)))
        counts=Counter(r['state'] for r in data['rows']);enabled=sum(r['enabled'] for r in data['rows'])
        signals=sum(bool(r.get('opportunity_id')) for r in data['rows'])
        self.summary.setText(f'{symbol} · {frame} · {enabled}/83 enabled · {signals} research triggers · {counts["SIGNAL"]} ready to bind\n'+
            ' · '.join(state.replace('_',' ').title()+': '+str(n) for state,n in sorted(counts.items())))
        if data['data_hash']!=self._fingerprint:
            selected=self.selected() or {};identity=selected.get('strategy_id');self._fingerprint=data['data_hash'];self._rows=data['rows']
            self.table.blockSignals(True);self.table.setRowCount(len(self._rows))
            for i,row in enumerate(self._rows):
                for j,value in enumerate((row['name'],row['state'].replace('_',' ').title(),row.get('side'),row.get('entry'),row.get('stop'),row.get('target'))):
                    cell=QTableWidgetItem(str(value) if value is not None else '—');cell.setToolTip(row['reason']);self.table.setItem(i,j,cell)
                self.table.setRowHeight(i,27)
                if row['strategy_id']==identity:self.table.selectRow(i)
            self.table.blockSignals(False)
            def review_identity(row):
                return tuple(row.get(k) for k in ('strategy_id','scope_id','source_epoch','timeframe','side','entry','stop','target','policy_hash','state'))
            self._selected(reset_review=review_identity(selected)!=review_identity(self.selected() or {}))
        self._filter()

    def _bind(self):
        row=self.selected()
        if not row or not row.get('opportunity_id') or not self.ack.isChecked():return
        result=self.api.command('4.2','BIND_RESEARCH_CANDIDATE',dict(candidate_id=row['opportunity_id'],candidate_revision=row['revision'],
            variant_id='native-stop',units=self.units.text().strip(),expected_version=row.get('bound_revision',0),user_initiated=True))
        self.feedback.setText(result.status.value+': '+result.message+' · No broker request sent.')
        self.refresh()
        if result.status.value=='ACCEPTED' and hasattr(self,'bound_callback'):self.bound_callback()

    def _chart(self):
        symbol=self.pair.currentText();frame=self.frame.currentText()
        try:self.api.navigate({'W1':'1.2','D1':'1.3','H4':'1.4','H1':'1.5'}[frame],self.api.inspect(symbol=symbol,timeframe=frame))
        except ValueError as exc:self.feedback.setText(str(exc))

    def apply_inspection(self,context):
        self.context=thaw(self.api.validate_inspection(context))
        if context.get('mode')=='REPLAY':raise ValueError('Strategy signals use current market source only')
        self.pair.setCurrentText(context['symbol']);self.frame.setCurrentText(context['timeframe']);self.refresh()

    def inspection_context(self):return self.context


class SignalQueueWorkspace(QWidget):
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self.setObjectName('subtab_4_1')
        from sfm_fx_new_age.app import SubtabPanel
        self.pages=QTabWidget();self.pages.setObjectName('signalQueuePages')
        self.research_signals=StrategySignalsPanel(api,model,self);self.queue=SubtabPanel(api,model,self)
        self.pages.addTab(self.research_signals,'Strategy signals');self.pages.addTab(self.queue,'Issue queue')
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.addWidget(self.pages)
        self.pages.currentChanged.connect(self.refresh)
        self.research_signals.bound_callback=lambda:self.pages.setCurrentIndex(1)
        # Real Issue-queue controls remain available to existing integrations;
        # they are not copied or given new execution behavior.
        self.table=self.queue.table;self.buttons=self.queue.buttons;self.acknowledge=self.queue.acknowledge;self.result_label=self.queue.result_label

    def refresh(self,*_):
        if self.pages.currentIndex()==0:self.research_signals.refresh()
        else:self.queue.refresh()

    def inspection_context(self):return self.queue.inspection_context() if self.pages.currentIndex()==1 else self.research_signals.inspection_context()

    def apply_inspection(self,context):
        if context.get('object_kind')=='signal':self.pages.setCurrentIndex(1);self.queue.apply_inspection(context)
        else:self.pages.setCurrentIndex(0);self.research_signals.apply_inspection(context)
