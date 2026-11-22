"""Shared-data inspectors. Navigation and binding are never order submission."""
from uuid import uuid4
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QTableWidget,QTableWidgetItem,
    QAbstractItemView,QHeaderView,QTextEdit,QLineEdit,QCheckBox,QSpinBox,QSizePolicy,QTabWidget)
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DATASETS,DataRequest
from sfm_fx_new_age.contracts.analytics import digest

OBJECTS={'level_id':('level','levels'),'evidence_id':('evidence','evidence'),'candidate_id':('market_candidate','market_candidates'),
         'overlay_id':('overlay','overlays'),'signal_id':('signal','signals'),'position_id':('position','positions')}


def identity(row):
    if row.get('client_order_id') and row.get('id'):return str(row['id'])
    if row.get('broker_order_id'):return str(row.get('id') or row['broker_order_id'])
    if row.get('position_id'):return str(row['position_id'])
    for key in ('candidate_id','evidence_id','overlay_id','level_id','signal_id','id','run_id','study_id','dataset_id','recipe_id'):
        if row.get(key):return str(row[key])
    return digest(row)


def row_context(api,row,*,as_of=None,frame=None):
    line=row.get('lineage',{});kind=None;key=None
    for field in ('position_id','candidate_id','evidence_id','overlay_id','level_id','signal_id'):
        if row.get(field):kind=OBJECTS[field][0];key=str(row[field]);break
    if row.get('id') and (row.get('broker_order_id') or row.get('client_order_id')):kind='order';key=str(row['id'])
    elif not kind and row.get('broker_order_id'):kind='broker_pending';key=str(row['broker_order_id'])
    return thaw(api.inspect(symbol=line.get('symbol') or row.get('symbol'),timeframe=frame or line.get('timeframe') or 'D1',
                            as_of=as_of,object_kind=kind,object_id=key,revision=row.get('revision')))


def describe(row):
    line=row.get('lineage',{});text=[]
    for key in ('kind','state','research_state','symbol','side','entry','entry_price','invalidation_price','units','profile','confidence','quality','expires_at'):
        if key in row:text.append(key.replace('_',' ').capitalize()+': '+str(row[key]))
    if line:
        text+=['Timeframe: '+line['timeframe'],'Known from: '+line['available_at'],'Method: '+line['method_version'],
               'Source: '+line['origin'],'Scope: '+line['source_scope'],'Epoch: '+line['source_epoch'],'Profile: '+line['profile_hash']]
    if 'confirmed' in row:text.append('Confirmed: '+str(row['confirmed']))
    if row.get('blockers'):text.append('Blockers: '+', '.join(row['blockers']))
    if row.get('gates'):text.append('Qualification: '+', '.join(k+'='+str(v) for k,v in row['gates']))
    for key in ('root_ids','root_id','evidence_ids','zone_id','source_candidate_hash','variant_id','revision','observed_at','broker_order_id','position_id'):
        if key in row:text.append(key.replace('_',' ').capitalize()+': '+str(row[key]))
    if not text:
        import json
        text=[json.dumps(row,indent=2,default=str)]
    return '\n'.join(text)


class InspectionPanel(QWidget):
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self.setObjectName('subtab_'+model.subtab_id.replace('.','_'))
        self._rows=[];self.context=None;self._selection_signature=None;self._cursor=0;self._expected=None;self._next=None
        layout=QVBoxLayout(self);layout.setContentsMargins(14,10,14,10);layout.setSpacing(7)
        self.heading=QLabel(model.title);self.heading.setProperty('role','heading');layout.addWidget(self.heading)
        self.context_label=QLabel('Current selected market source · no inspection pinned');self.context_label.setWordWrap(True);layout.addWidget(self.context_label)
        self.origin=self.context_label
        bar=QHBoxLayout();self.dataset=QComboBox();self.dataset.setObjectName('inspectionDataset')
        for ds in DATASETS[model.subtab_id]:self.dataset.addItem(ds.replace('_',' ').title(),ds)
        self.dataset.currentIndexChanged.connect(self._dataset_changed);bar.addWidget(self.dataset,1)
        self.current_button=QPushButton('Current source');self.current_button.clicked.connect(self.clear_inspection);bar.addWidget(self.current_button)
        self.previous=QPushButton('Previous page');self.previous.clicked.connect(lambda:self._page(max(0,self._cursor-200)));bar.addWidget(self.previous)
        self.next=QPushButton('Next page');self.next.clicked.connect(lambda:self._page(self._next));bar.addWidget(self.next);layout.addLayout(bar)
        self.status=QLabel();self.status.setObjectName('inspectionStatus');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.table=QTableWidget();self.table.setObjectName('inspectionTable');self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True);self.table.verticalHeader().hide();self.table.setMinimumHeight(65)
        self.table.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Ignored);self.table.itemSelectionChanged.connect(self._selected);layout.addWidget(self.table,2)
        self.details=QTextEdit();self.details.setReadOnly(True);self.details.setObjectName('evidenceInspector');self.details.setMinimumHeight(80);layout.addWidget(self.details,2)
        actions=QHBoxLayout();self.show_chart=QPushButton('Show on Chart');self.show_chart.setObjectName('showOnChart');self.show_chart.clicked.connect(lambda:self.open_selected('chart'));actions.addWidget(self.show_chart)
        self.review=QPushButton('Review signal');self.review.setObjectName('reviewSignal');self.review.clicked.connect(lambda:self.open_selected('4.2'));actions.addWidget(self.review)
        self.research=QPushButton('Inspect in Research');self.research.clicked.connect(lambda:self.open_selected('3.5'));actions.addWidget(self.research)
        self.calculate=QPushButton('Calculate scenario');self.calculate.clicked.connect(lambda:self.open_selected('calculator'));actions.addWidget(self.calculate);layout.addLayout(actions)
        self.feedback=QLabel('Inspection and navigation do not acknowledge or submit orders.');self.feedback.setWordWrap(True);self.feedback.setObjectName('inspectionFeedback');layout.addWidget(self.feedback)
        self._selected()
    def _dataset_changed(self):self._cursor=0;self._expected=None;self.refresh()
    def _page(self,cursor):
        if cursor is None:return
        self._cursor=cursor
        if cursor==0:self._expected=None
        self.refresh()
    def clear_inspection(self):self.context=None;self._dataset_changed()
    def apply_inspection(self,context):
        if context.get('mode')=='REPLAY' and self.model.subtab_id!='3.12':raise ValueError('Replay inspection cannot read current market datasets')
        self.context=thaw(self.api.validate_inspection(context));self._cursor=0;self._expected=None
        field=next((ds for _,(kind,ds) in OBJECTS.items() if kind==self.context['object_kind']),None)
        if self.context['object_kind']=='order':field='orders'
        if self.context['object_kind']=='broker_pending':field='broker_pending'
        index=self.dataset.findData(field)
        if index>=0:self.dataset.blockSignals(True);self.dataset.setCurrentIndex(index);self.dataset.blockSignals(False)
        self.refresh()
        for i,row in enumerate(self._rows):
            if identity(row)==self.context.get('object_id'):self.table.selectRow(i);break
    def inspection_context(self):
        if self.selected():return row_context(self.api,self.selected(),as_of=(self.context or {}).get('as_of'),frame=(self.context or {}).get('timeframe'))
        return self.context
    def selected(self):
        i=self.table.currentRow();return self._rows[i] if 0<=i<len(self._rows) else None
    def _selected(self):
        row=self.selected();signature=digest(row) if row else None
        if signature!=self._selection_signature:
            self._selection_signature=signature
            if hasattr(self,'acknowledge'):self.acknowledge.setChecked(False)
        self.details.setPlainText(describe(row) if row else 'Select one record to inspect its source, method, confirmation, expiry and blockers.')
        valid=bool(row and (row.get('lineage') or row.get('symbol')))
        for b in (self.show_chart,self.research,self.calculate):b.setEnabled(valid)
        self.review.setEnabled(valid and bool(row and (row.get('candidate_id') or row.get('signal_id'))))
        broker=bool(row and (row.get('broker_order_id') or row.get('position_id') or row.get('client_order_id')))
        self.research.setEnabled(valid and not broker);self.calculate.setEnabled(valid and not broker)
    def refresh(self):
        try:
            if self.context:self.api.validate_inspection(self.context)
            ds=self.dataset.currentData();ctx=self.context or {}
            historical=ds in {'levels','evidence','market_candidates','overlays','geometry','signal_history','bars','chart'}
            result=thaw(self.api.query(self.model.subtab_id,DataRequest(ds,symbol=ctx.get('symbol'),timeframe=ctx.get('timeframe'),as_of=ctx.get('as_of') if historical else None,
                cursor=self._cursor,expected_hash=self._expected if self._cursor else None,limit=200)))
        except ValueError as exc:
            self._rows=[];self._rows_hash=None;self._next=None;self.table.setRowCount(0)
            self.next.setEnabled(False);self.previous.setEnabled(bool(self._cursor));self._selected()
            self.status.setText('Selection unavailable: '+str(exc)+' · use Current source or Previous page to recover');return
        self._expected=result['data_hash'];self._next=result['next_cursor'];selected=identity(self.selected()) if self.selected() else None
        self.previous.setEnabled(bool(self._cursor));self.next.setEnabled(self._next is not None)
        self.status.setText(result['status'].replace('_',' ')+' · '+str(result['total'])+(' record' if result['total']==1 else ' records')+(' · more pages available' if self._next is not None else '')+(' · '+result['detail'] if result.get('detail') else ''))
        if result.get('observation'):self.status.setText(self.status.text()+' · '+str(result['observation'].get('observed_at','observation unavailable'))+' · last known, not proof of current freshness')
        if ctx and historical:
            self.context_label.setText(ctx.get('mode','MARKET')+' · '+result['symbol']+' · '+ctx.get('timeframe','all frames')+' · as of '+ctx.get('as_of',result['as_of']))
        elif ctx:
            self.context_label.setText('CURRENT dataset · '+result['symbol']+' · inspection reference '+ctx['as_of']+' · not a historical reconstruction')
            if self.context_label.isHidden():self.status.setText(self.status.text()+' · CURRENT records; pinned time is a reference only')
        else:self.context_label.setText('Current source · '+result['symbol']+' · no inspection pinned')
        rows=result['rows'];fingerprint=digest(rows)
        if getattr(self,'_rows_hash',None)==fingerprint:return
        self._rows_hash=fingerprint;self._rows=rows;self.table.blockSignals(True);self.table.clearSelection();self.table.setCurrentCell(-1,-1)
        columns=['identity','type / state','frame','known / observed']
        self.table.setColumnCount(4);self.table.setHorizontalHeaderLabels(columns);self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            line=row.get('lineage',{});values=[identity(row),row.get('kind') or row.get('state') or row.get('status') or row.get('domain') or row.get('side') or '',line.get('timeframe',row.get('timeframe','')),line.get('available_at',row.get('observed_at',''))]
            for j,value in enumerate(values):item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.table.setItem(i,j,item)
            if identity(row)==selected:self.table.selectRow(i)
        self.table.setColumnWidth(0,230);self.table.setColumnWidth(1,150);self.table.setColumnWidth(2,65);self.table.blockSignals(False);self._selected()
    def open_selected(self,target):
        row=self.selected()
        if not row:return
        try:
            ctx=row_context(self.api,row,as_of=(self.context or {}).get('as_of'),frame=(self.context or {}).get('timeframe'))
            if target=='chart':target='1.10' if ctx['object_kind'] in {'order','position','broker_pending'} else '1.8' if ctx['object_kind'] in {'market_candidate','signal','overlay'} else '1.6'
            if target=='calculator' and ctx['object_kind'] in {'order','position','broker_pending'}:
                raise ValueError('Broker/local order context stays in Chart / Trading Operations; use generic chart context for a calculator scenario')
            if target=='calculator' and row.get('entry',row.get('entry_price')):
                ctx=thaw(self.api.scenario_context(ctx,{'entry':str(row.get('entry',row.get('entry_price'))),
                    **({'exit':str(row['target'])} if row.get('target') else {}),'side':row.get('side','BUY')}))
            self.api.navigate(target,ctx)
        except ValueError as exc:self.feedback.setText(str(exc))


class SignalDetailPanel(InspectionPanel):
    def __init__(self,*args):
        super().__init__(*args);layout=self.layout()
        layout.setSpacing(5);self.context_label.hide();self.table.hide()
        self.record_picker=QComboBox();self.record_picker.setObjectName('reviewRecord');self.record_picker.setMinimumContentsLength(12)
        self.record_picker.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.record_picker.currentIndexChanged.connect(lambda index:self.table.selectRow(index-1) if index>0 else self.table.setCurrentCell(-1,-1))
        layout.itemAt(2).layout().insertWidget(1,self.record_picker,2)
        self.dataset.blockSignals(True);self.dataset.clear();self.dataset.addItem('Candidates','market_candidates');self.dataset.addItem('Signals','signals');self.dataset.blockSignals(False)
        self.current_button.setText('Current')
        for button in (self.show_chart,self.review,self.research,self.calculate):button.hide()
        index=layout.indexOf(self.details);layout.removeWidget(self.details);self.detail_tabs=QTabWidget();self.detail_tabs.setObjectName('signalDetailPages');self.detail_tabs.addTab(self.details,'Evidence and geometry');layout.insertWidget(index,self.detail_tabs,3)
        self.variant=QComboBox();self.variant.setObjectName('candidateVariant');self.variant.currentIndexChanged.connect(self._variant_changed)
        self.units=QLineEdit();self.units.setObjectName('candidateUnits');self.units.setPlaceholderText('Explicit units (broker min/max/step)')
        row=QHBoxLayout();self.variant_label=QLabel('Variant');row.addWidget(self.variant_label);row.addWidget(self.variant,2);row.addWidget(self.units,1)
        self.bind=QPushButton('Bind local proposal');self.bind.setObjectName('bindCandidate');self.bind.clicked.connect(self.bind_candidate);row.addWidget(self.bind);layout.insertLayout(layout.count()-1,row)
        self.acknowledge=QCheckBox('I acknowledge this selected RESEARCH_ONLY proposal is not a validated success probability')
        self.acknowledge.setObjectName('previewResearchAcknowledgement');self.acknowledge.toggled.connect(self.preview);layout.insertWidget(layout.count()-1,self.acknowledge)
        buttons=QHBoxLayout();self.preflight=QPushButton('Validate preview only');self.preflight.setObjectName('validatePreview');self.preflight.clicked.connect(self.confirm_preview);buttons.addWidget(self.preflight)
        self.queue=QPushButton('Open Issue queue');self.queue.setObjectName('openIssueQueue');self.queue.clicked.connect(lambda:self.open_selected('4.1'));buttons.addWidget(self.queue);layout.insertLayout(layout.count()-1,buttons)
        for button in (self.show_chart,self.research,self.calculate):buttons.addWidget(button);button.show()
        self.preview_text=QTextEdit();self.preview_text.setReadOnly(True);self.preview_text.setMinimumHeight(65);self.preview_text.setObjectName('issuePreflight');self.detail_tabs.addTab(self.preview_text,'No-write preflight')
        self.money_text=QTextEdit();self.money_text.setReadOnly(True);self.money_text.setObjectName('candidateMoneyResearch');self.detail_tabs.addTab(self.money_text,'Research money estimates')
        self._rows_hash=None;self.refresh();self._selected()
    def _selected(self):
        super()._selected()
        if not hasattr(self,'variant'):return
        self.record_picker.blockSignals(True);self.record_picker.clear();self.record_picker.addItem('Select a record',None)
        for item in self._rows:self.record_picker.addItem(identity(item)+' · '+item.get('side','')+' '+item.get('state',''),identity(item))
        self.record_picker.setCurrentIndex(self.table.currentRow()+1);self.record_picker.blockSignals(False)
        row=self.selected() or {};old=self.variant.currentData();self.variant.blockSignals(True);self.variant.clear()
        for v in row.get('variants',[]):self.variant.addItem(v['buffer_code']+' · '+v['actual_band']+' · '+v['distance_pips']+' pips',v['variant_id'])
        if self.variant.findData(old)>=0:self.variant.setCurrentIndex(self.variant.findData(old))
        self.variant.blockSignals(False);candidate=bool(row.get('candidate_id'));signal=bool(row.get('signal_id'))
        self.bind.setEnabled(candidate and not row.get('blockers'));self.units.setEnabled(candidate);self.variant.setEnabled(candidate)
        for widget in (self.variant_label,self.variant,self.units,self.bind):widget.setVisible(candidate)
        self.preflight.setEnabled(signal);self.queue.setEnabled(signal);self.acknowledge.setEnabled(signal and row.get('profile')=='RESEARCH_ONLY');self._variant_changed();self.preview()
    def _variant_changed(self):
        if not hasattr(self,'variant'):return
        row=self.selected() or {};v=next((v for v in row.get('variants',[]) if v['variant_id']==self.variant.currentData()),None)
        if v:self.details.setPlainText(describe(row)+'\n\nSelected variant (research geometry):\n'+describe(v)+'\n'+str(v))
        if hasattr(self,'money_text'):
            import json
            data=thaw(self.api.query('4.2',DataRequest('capital_context',symbol=row.get('symbol',(row.get('lineage') or {}).get('symbol')))))
            estimates=[e for e in data.get('candidate_estimates',[]) if e['candidate_id']==row.get('candidate_id') and e['variant_id']==self.variant.currentData()]
            self.money_text.setPlainText(json.dumps({'context':data['rows'][0],'selected_variant_estimate':estimates},indent=2)+'\n\nConfigure explicit research assumptions in Trading Operations → Capital. Units are never auto-filled; research estimates are not risk approval.')
    def preview(self):
        if not hasattr(self,'preview_text'):return
        row=self.selected() or {}
        if not row.get('signal_id'):self.preview_text.setPlainText('Select a signal, or bind one current qualified candidate/variant with explicit units. Binding sends no broker request.');return
        value=thaw(self.api.query('4.2',DataRequest('issue_preview',object_id=row['signal_id'],acknowledge_research=self.acknowledge.isChecked())))
        import json
        self.preview_text.setPlainText(json.dumps(value['rows'][0] if value['rows'] else {'status':value['status'],'detail':value['detail']},indent=2)+'\n\nNo reservation or broker submission occurs during preview. Issue revalidates immediately.')
    def refresh(self):
        super().refresh()
        if hasattr(self,'preview_text'):self.preview()
    def confirm_preview(self):
        row=self.selected() or {}
        if not row.get('signal_id'):return
        result=self.api.command('4.2','CONFIRM_SELECTED_SIGNAL',{'signal_id':row['signal_id'],'revision':row['revision'],'acknowledge_research':self.acknowledge.isChecked()})
        self.feedback.setText('Preview validated · no broker request sent. Use Issue separately.' if result.status.value=='ACCEPTED' else result.status.value+': '+result.message)
        self.feedback.setToolTip(result.message);self.preview();self.detail_tabs.setCurrentIndex(1)
    def bind_candidate(self):
        row=self.selected() or {};variant=self.variant.currentData()
        if not row.get('candidate_id') or not variant:return
        try:context=row_context(self.api,row,as_of=(self.context or {}).get('as_of'));self.api.validate_inspection(context)
        except ValueError as exc:self.feedback.setText(str(exc));return
        signals=thaw(self.api.query('4.2',DataRequest('signals',limit=5000)))['rows']
        previous=next((s for s in signals if s.get('market_candidate_id')==row['candidate_id'] and s.get('variant_id')==variant),None)
        result=self.api.command('4.2','BIND_RESEARCH_CANDIDATE',{'candidate_id':row['candidate_id'],'candidate_revision':row['revision'],'variant_id':variant,
            'units':self.units.text(),'expected_version':previous['revision'] if previous else 0,'user_initiated':True})
        self.feedback.setText(result.status.value+': '+result.message)
        if result.status.value=='ACCEPTED':
            self.context=None;self.dataset.setCurrentIndex(self.dataset.findData('signals'));self.refresh()
            for i,s in enumerate(self._rows):
                if s.get('market_candidate_id')==row['candidate_id'] and s.get('variant_id')==variant:self.table.selectRow(i);break


class ReplayPanel(InspectionPanel):
    def __init__(self,*args):
        super().__init__(*args);self.dataset.setCurrentIndex(self.dataset.findData('replay_runs'))
        row=QHBoxLayout();self.create=QPushButton('Replay inspected history');self.create.clicked.connect(self.create_run);row.addWidget(self.create)
        self.controls={}
        for action in ('PLAY','PAUSE','STEP'):
            b=QPushButton(action.title());b.setObjectName('researchReplay'+action);b.clicked.connect(lambda checked=False,a=action:self.control(a));self.controls[action]=b;row.addWidget(b)
        self.seek=QSpinBox();self.seek.setMinimum(-1);self.seek.setObjectName('researchReplaySeek');row.addWidget(self.seek)
        b=QPushButton('Seek');b.clicked.connect(lambda:self.control('SEEK'));row.addWidget(b)
        self.chart=QPushButton('Show replay on Chart');self.chart.clicked.connect(self.show_run);row.addWidget(self.chart);self.layout().insertLayout(self.layout().count()-1,row)
        from .research_study import StudyControls
        self.study=StudyControls(self.api,self.selected,lambda:self.context,self)
        self.layout().insertWidget(self.layout().count()-1,self.study)
    def apply_inspection(self,context):
        super().apply_inspection(context)
        if context.get('run_id'):
            self.dataset.setCurrentIndex(self.dataset.findData('replay_runs'));self.refresh()
            for i,row in enumerate(self._rows):
                if row.get('run_id')==context['run_id']:self.table.selectRow(i);break
    def _selected(self):
        super()._selected()
        if not hasattr(self,'controls'):return
        if hasattr(self,'study'):self.study.select_saved(self.selected())
        run=(self.selected() or {}).get('run_id')
        for b in self.controls.values():b.setEnabled(bool(run))
        self.chart.setEnabled(bool(run))
        if run:
            value=thaw(self.api.query('3.12',DataRequest('replay',run_id=run)))['rows'][0]
            self.seek.setMaximum(value['total_items']-1);self.seek.setToolTip('Atomic availability-batch cursor; no future bars before seek')
            self.details.setPlainText(describe(value)+'\nReplay clock: '+str(value['as_of'])+'\nExecution disabled')
    def create_run(self):
        try:
            context=self.context
            if not context or context['mode']!='MARKET':raise ValueError('Use Inspect in Research from the market chart first')
            self.api.create_inspection_replay(context,'inspect-'+uuid4().hex);self._rows_hash=None;self.refresh()
        except ValueError as exc:self.feedback.setText(str(exc))
    def control(self,action):
        run=(self.selected() or {}).get('run_id')
        if not run:return
        try:self.api.control_replay(run,action,cursor=self.seek.value() if action=='SEEK' else None);self._rows_hash=None;self.refresh()
        except ValueError as exc:self.feedback.setText(str(exc))
    def show_run(self):
        run=(self.selected() or {}).get('run_id')
        if run:
            ctx=self.context or {};self.api.navigate('1.9',self.api.inspect(symbol=ctx.get('symbol'),timeframe=ctx.get('timeframe','D1'),run_id=run))
