"""Read-only chart integration mechanics shared by the ten stable chart views."""
from copy import deepcopy
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .chart_canvas import CandleCanvas
    from sfm_fx_new_age.core.tab_api import TabApi
from uuid import uuid4
import json
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QHBoxLayout,QPushButton,QMenu,QComboBox,QLabel,QDialog,QVBoxLayout,QTextEdit,QDialogButtonBox,QSpinBox
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.analytics import digest
from .inspection_panels import row_context,describe


class ChartWorkflowMixin:
    canvas:'CandleCanvas'
    api:'TabApi'
    def _setup_workflow(self,outer):
        self.context=None;self._inspected_stamp=None;self._workspace_context=None;self._workspace_version=0;self._workspace_hash=None;self._workspace_blocked=False;self._restoring=False
        self.run_id=None;self._objects=[];self._save_timer=QTimer(self);self._save_timer.setSingleShot(True);self._save_timer.setInterval(600);self._save_timer.timeout.connect(self._save_workspace)
        self.canvas.viewChanged.connect(self._schedule_save);self.canvas.optionsChanged.connect(self._schedule_save)
        self.canvas.inspected.connect(self._inspect_candle);self.canvas.evidenceSelected.connect(self._select_evidence)
        bar=QHBoxLayout();self.workflow_bar=bar;self.open_button=QPushButton('Open in…');self.open_button.setObjectName('chartOpenIn');menu=QMenu(self.open_button)
        for text,target in (('Inspect in Research','3.5'),('Replay in Research','3.12'),('Calculate this scenario','calculator'),('Review selected signal / candidate','4.2'),('Inspect orders / positions','4.3')):
            menu.addAction(text,lambda target=target:self._open_in(target))
        self.open_button.setMenu(menu);bar.addWidget(self.open_button)
        self.layers_button=QPushButton('Layers');self.layers_button.setObjectName('chartLayers');self.layers_menu=QMenu(self.layers_button);self.layers_button.setMenu(self.layers_menu);bar.addWidget(self.layers_button)
        self.public_details_action=self.layers_menu.addAction('Public projection details…',self._public_projection_dialog);self.public_details_action.setObjectName('publicProjectionDetailsAction')
        self.layers_menu.addSeparator();self.canvas.publicDetailsRequested.connect(self._public_projection_dialog)
        self.layer_actions={};self.layer_frame_actions={}
        for key,text in (('show_research','Research levels / regions'),('show_setups','Candidate / local signal geometry'),('show_broker','Last-observed broker / local inventory'),('show_scenarios','Manual calculator scenario')):
            action=self.layers_menu.addAction(text);action.setCheckable(True);action.setChecked(self.canvas.display[key]);action.toggled.connect(lambda checked,k=key:self.canvas.set_display({k:checked}));self.layer_actions[key]=action
        frames=self.layers_menu.addMenu('Research / setup source timeframes')
        for frame in ('W1','D1','H4','H1'):
            action=frames.addAction(frame);action.setCheckable(True);action.setChecked(True);action.toggled.connect(lambda checked,f=frame:self._projection_frame(f,checked));self.layer_frame_actions[frame]=action
        note=self.layers_menu.addAction('Source frame labels remain unchanged on other chart frames');note.setEnabled(False)
        self.evidence_picker=QComboBox();self.evidence_picker.setObjectName('chartEvidencePicker');self.evidence_picker.setMinimumContentsLength(12);self.evidence_picker.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.evidence_picker.setToolTip('Select a source-bound level, evidence record, candidate, signal or read-only order/position');bar.addWidget(self.evidence_picker,1)
        self.evidence_picker.setPlaceholderText('Select source record (optional)')
        self.inspect_button=QPushButton('Evidence…');self.inspect_button.setObjectName('chartEvidenceInspector');self.inspect_button.clicked.connect(self._evidence_dialog);bar.addWidget(self.inspect_button)
        self.evidence_picker.currentIndexChanged.connect(lambda index:self.inspect_button.setEnabled(index>=0))
        self.current_context=QPushButton('Current source');self.current_context.setObjectName('chartCurrentSource');self.current_context.clicked.connect(self.clear_inspection);bar.addWidget(self.current_context)
        self.history_button=QPushButton('Older history…');self.history_button.setObjectName('chartOlderHistory');history=QMenu(self.history_button)
        for days in (30,90,366):history.addAction(str(days)+' earlier days',lambda days=days:self._older_history(days))
        self.history_button.setMenu(history);bar.addWidget(self.history_button)
        self.notes=QPushButton('Notes');self.notes.setObjectName('chartNotes');notes=QMenu(self.notes);notes.addAction('Save workspace now',self._save_workspace);notes.addAction('Reload saved notes / discard local edits',self._reload_workspace);notes.addAction('Archived source notes…',self._archives);self.notes.setMenu(notes);bar.addWidget(self.notes)
        outer.insertLayout(4,bar)
        self.readiness=QLabel();self.readiness.setObjectName('chartAnalyticalReadiness');outer.itemAt(0).layout().insertWidget(1,self.readiness,1)
        self.workflow_status=WorkflowStatus();self.workflow_status.setWordWrap(True);self.workflow_status.setObjectName('chartWorkflowStatus');self.workflow_status.hide();outer.addWidget(self.workflow_status)
        if self.model.subtab_id!='1.9':return
        self.replay_bar=QHBoxLayout();self.replay_picker=QComboBox();self.replay_picker.setObjectName('chartReplayRun');self.replay_picker.currentIndexChanged.connect(self._select_run);self.replay_bar.addWidget(self.replay_picker,1)
        self.replay_create=QPushButton('New run');self.replay_create.setToolTip('Create an isolated causal replay from the observed history for this pair/timeframe');self.replay_create.setObjectName('chartCreateReplay');self.replay_create.clicked.connect(self._create_replay);self.replay_bar.addWidget(self.replay_create)
        self.replay_buttons={}
        for action in ('PLAY','PAUSE','STEP'):
            b=QPushButton(action.title());b.setObjectName('chartReplay'+action);b.clicked.connect(lambda checked=False,a=action:self._replay_control(a));self.replay_bar.addWidget(b);self.replay_buttons[action]=b
        self.replay_seek=QSpinBox();self.replay_seek.setMinimum(-1);self.replay_seek.setObjectName('chartReplaySeek');self.replay_bar.addWidget(self.replay_seek)
        b=QPushButton('Seek');b.clicked.connect(lambda:self._replay_control('SEEK'));self.replay_bar.addWidget(b)
        for widget in (self.evidence_picker,self.inspect_button,self.history_button,self.notes):widget.hide()
        bar.addLayout(self.replay_bar)
    def _inspect_candle(self,row):
        self._inspected_stamp=row['available_at'];self.workflow_status.setText('Inspected candle: '+row['open_time']+' · known by '+row['available_at']+' · navigation is not an order instruction')
    def inspection_context(self):
        if self.run_id:return thaw(self.api.inspect(symbol=self._data.get('symbol'),timeframe=self.frame,run_id=self.run_id))
        if self.context:return self.context
        scenario=None
        if self.canvas.ruler and self.canvas.ruler_mode!='time':
            (_,a),(_,b)=self.canvas.ruler;scenario={'entry':str(a),'exit':str(b),'side':'BUY' if b>=a else 'SELL'}
        return thaw(self.api.inspect(symbol=self._data.get('symbol'),timeframe=self.frame,as_of=self._inspected_stamp,scenario=scenario))
    def apply_inspection(self,context):
        if context.get('mode')=='REPLAY' and self.model.subtab_id!='1.9':raise ValueError('Replay rendering belongs to Chart Replay')
        context=thaw(self.api.validate_inspection(context));self._save_workspace()
        self.canvas.set_projection_focus(None);self.canvas.projection_page=0
        self.context=context;self.run_id=context['run_id'];self.frame=context['timeframe'];self.frame_picker.blockSignals(True);self.frame_picker.setCurrentIndex(('W1','D1','H4','H1').index(self.frame));self.frame_picker.blockSignals(False)
        self._inspected_stamp=None;self._fingerprint=None;self.refresh()
        if context['object_id']:self._select_evidence(context['object_id'])
        if self.canvas.bars:self.canvas.go_to(context['as_of'])
    def clear_inspection(self):
        self.context=None;self.run_id=None;self._inspected_stamp=None;self._fingerprint=None;self.workflow_status.setText('');self.refresh()
    def _selected_record(self):
        i=self.evidence_picker.currentIndex();return self._objects[i] if 0<=i<len(self._objects) else None
    def _open_in(self,target):
        try:
            row=self._selected_record()
            if row and target!='3.12':
                context=row_context(self.api,row,as_of=(self.context or {}).get('as_of'),frame=self.frame)
                if context['object_kind']=='position' and target=='4.3':target='4.6'
                elif context['object_kind']=='order' and target=='4.3':target='4.4'
            else:context=self.inspection_context()
            if target=='calculator' and row and row.get('entry',row.get('entry_price')):
                context=thaw(self.api.scenario_context(context,{'entry':str(row.get('entry',row.get('entry_price'))),'side':row.get('side','BUY'),**({'exit':str(row['target'])} if row.get('target') else {})}))
            if target=='4.2' and context['object_kind'] not in {'signal','market_candidate'}:raise ValueError('Select a candidate or signal in the inspector first; chart prices are not signals')
            self._save_workspace();self.api.navigate(target,context)
        except ValueError as exc:self.workflow_status.setText(str(exc))
    def _projection_frame(self,frame,checked):
        frames=set(self.canvas.display['projection_frames'])
        if checked:frames.add(frame)
        else:frames.discard(frame)
        self.canvas.set_display({'projection_frames':[f for f in ('W1','D1','H4','H1') if f in frames]})
    def _sync_layers(self):
        for key,action in self.layer_actions.items():
            action.blockSignals(True);action.setChecked(self.canvas.display[key]);action.blockSignals(False)
        for frame,action in self.layer_frame_actions.items():
            action.blockSignals(True);action.setChecked(frame in self.canvas.display['projection_frames']);action.blockSignals(False)
    def _public_projection_dialog(self):
        from .chart_projection_details import PublicProjectionDetails
        if self.canvas.public_strategy_layers():
            dialog=PublicProjectionDetails(self.canvas,self);dialog.exec();dialog.deleteLater()
    def _update_objects(self,data):
        rows=[]
        for key in ('levels','evidence','market_candidates','overlays','signals','orders','broker_pending','positions'):
            for row in data.get(key,[]):rows.append(row)
        if self.context and self.context['object_id']:
            selected=thaw(self.api.inspection_object(self.context))
            from .inspection_panels import identity
            if selected and not any(identity(v)==identity(selected) for v in rows):rows.append(selected)
        old=self.evidence_picker.currentData();signature=digest(rows)
        if getattr(self,'_object_signature',None)==signature:return
        self._object_signature=signature;self._objects=rows;self.evidence_picker.clear()
        for row in rows:
            from .inspection_panels import identity
            kind=row.get('kind') or ('Broker position' if row.get('position_id') else 'Local signal' if row.get('signal_id') and not row.get('broker_order_id') else 'Broker order' if row.get('broker_order_id') else 'Evidence' if row.get('evidence_id') else 'Candidate')
            self.evidence_picker.addItem(kind+' · '+identity(row)[:28],identity(row))
        index=self.evidence_picker.findData(old)
        self.evidence_picker.setCurrentIndex(index)
        self.inspect_button.setEnabled(index>=0)
    def _select_evidence(self,identity):
        i=self.evidence_picker.findData(identity)
        if i>=0:self.evidence_picker.setCurrentIndex(i)
    def _evidence_dialog(self):
        row=self._selected_record()
        if not row:return
        dialog=QDialog(self);dialog.setWindowTitle('Source-bound evidence / broker observation');dialog.resize(670,490);layout=QVBoxLayout(dialog)
        text=QTextEdit();text.setReadOnly(True);text.setPlainText(describe(row));layout.addWidget(text)
        b=QPushButton('Open owning record');b.clicked.connect(lambda:(self._open_in('4.3' if row.get('position_id') or row.get('broker_order_id') else '4.2' if row.get('signal_id') or row.get('candidate_id') else '3.5'),dialog.accept()));layout.addWidget(b)
        buttons=QDialogButtonBox(QDialogButtonBox.Close);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons);dialog.exec();dialog.deleteLater()
    def _settings(self):
        c=self.canvas
        return {'style':c.style,'volume':c.volume,'grid':c.grid,'crosshair':c.crosshair,'show_bid':c.show_bid,'show_ask':c.show_ask,'wheel_mode':c.wheel_mode,'window':c.window,'studies':sorted(c.studies),'drawings':deepcopy(c.drawings.items),'display':deepcopy(c.display)}
    def _schedule_save(self):
        if not self._restoring and self._workspace_context and not self.run_id and not self._workspace_blocked:self._save_timer.start()
    def _save_workspace(self):
        self._save_timer.stop()
        if not self._workspace_context or self._restoring or self.run_id or self._workspace_blocked:return
        if self.canvas.drag and self.canvas.drag[0] in {'draw','object'}:
            self._save_timer.start(100);return # Never persist a half-finished edit.
        value=self._settings();signature=digest(value)
        if self._workspace_hash==signature:return
        try:
            saved=self.api.save_workspace(self._workspace_context,value,self._workspace_version);self._workspace_version=saved['version'];self._workspace_hash=signature
            self.notes.setToolTip('Saved locally · source-scoped human notes, never research evidence')
        except ValueError as exc:
            self._workspace_blocked=True;self.workflow_status.setText('Local notes not saved: '+str(exc)+' · edits retained in this view; reload explicitly')
    def _restore_workspace(self,data):
        if self.run_id:return
        identity=(data['scope_id'],data['source_epoch'],data['symbol'],self.frame)
        if not identity[1]:return
        if getattr(self,'_workspace_identity',None)==identity:return
        self._workspace_identity=identity;self._workspace_blocked=False;self._restoring=True
        try:
            ctx=thaw(self.api.inspect(symbol=data['symbol'],timeframe=self.frame));saved=thaw(self.api.workspace(ctx));settings=saved['settings']
            c=self.canvas
            from sfm_fx_new_age.contracts.chart_display import DISPLAY_DEFAULTS
            c.display=deepcopy(DISPLAY_DEFAULTS);c.display.update(deepcopy(settings.get('display',{})))
            # Migrate the old shipped 8 px default once. Nondefault custom
            # tolerances, and any workspace already saved with this palette, stay.
            old_display=settings.get('display',{})
            if 'selection_color' not in old_display and old_display.get('hit_distance')==8:c.display['hit_distance']=14
            for key in ('style','volume','grid','crosshair','show_bid','show_ask','wheel_mode','window'):
                if key in settings:setattr(c,key,settings[key])
            c.studies=set(settings.get('studies',[]));c.drawings.items=deepcopy(settings.get('drawings',[]));c.drawings.selected=None
            c.drawings._undo=[];c.drawings._redo=[];c.drawings._gesture=None
            self._workspace_context=ctx;self._workspace_version=saved['version'];self._workspace_hash=digest(self._settings());self._sync_options()
            for name,a in self.study_actions.items():a.blockSignals(True);a.setChecked(name in c.studies);a.blockSignals(False)
            self.notes.setText('Notes'+(' · archives '+str(len(saved['archives'])) if saved['archives'] else ''))
        except ValueError as exc:self.workflow_status.setText(str(exc))
        finally:self._restoring=False
    def _reload_workspace(self):self._workspace_identity=None;self._restore_workspace(self._data);self.canvas.update()
    def _archives(self):
        if not self._workspace_context:return
        try:archives=thaw(self.api.workspace(self._workspace_context))['archives']
        except ValueError as exc:self.workflow_status.setText(str(exc));return
        d=QDialog(self);d.setWindowTitle('Archived source notes · not active evidence');d.resize(620,420);layout=QVBoxLayout(d)
        text=QTextEdit();text.setReadOnly(True);text.setPlainText(json.dumps(archives,indent=2) if archives else 'No archived source notes.');layout.addWidget(text)
        b=QDialogButtonBox(QDialogButtonBox.Close);b.rejected.connect(d.reject);layout.addWidget(b);d.exec();d.deleteLater()
    def _older_history(self,days):
        try:
            context=thaw(self.api.inspect(symbol=self._data['symbol'],timeframe=self.frame));job=self.api.request_older_history(context,days)
            self.workflow_status.setText('Shared history job '+job['status']+' · '+job['from']+' → '+job['to']+' · bounded; failures require explicit action')
        except ValueError as exc:self.workflow_status.setText(str(exc))
    def _sync_runs(self):
        if self.model.subtab_id!='1.9':return
        rows=thaw(self.api.query('1.9',DataRequest('replay',limit=5000)))['rows'];self.replay_picker.blockSignals(True);self.replay_picker.clear();self.replay_picker.addItem('Select an isolated replay run',None)
        for run in rows:self.replay_picker.addItem(run['run_id']+' · '+run['state'],run['run_id'])
        index=self.replay_picker.findData(self.run_id);self.replay_picker.setCurrentIndex(max(0,index));self.replay_picker.blockSignals(False)
        for b in self.replay_buttons.values():b.setEnabled(bool(self.run_id))
    def _select_run(self,index):
        self._save_workspace();self.run_id=self.replay_picker.itemData(index);self.context=None;self._fingerprint=None;self.refresh()
    def _create_replay(self):
        try:
            self._save_workspace()
            ctx=thaw(self.api.inspect(symbol=self._data.get('symbol'),timeframe=self.frame,as_of=self._inspected_stamp))
            run=self.api.create_inspection_replay(ctx,'chart-'+uuid4().hex);self.run_id=run['run_id'];self.context=None;self._fingerprint=None;self.refresh()
        except ValueError as exc:self.workflow_status.setText(str(exc))
    def _replay_control(self,action):
        if not self.run_id:return
        try:self.api.control_replay(self.run_id,action,cursor=self.replay_seek.value() if action=='SEEK' else None);self.refresh()
        except ValueError as exc:self.workflow_status.setText(str(exc))
    def dispose(self):
        self._save_workspace();self._save_timer.stop()
        if hasattr(self,'projection_bar'):self.projection_bar.dispose()


class WorkflowStatus(QLabel):
    def setText(self,text):super().setText(text);self.setToolTip(text);self.setVisible(bool(text))
