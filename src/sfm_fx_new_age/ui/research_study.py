"""Reachable research-only study controls; no transport or raw storage access."""
from uuid import uuid4
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QGridLayout,QHBoxLayout,QVBoxLayout,QLabel,QComboBox,QLineEdit,QSpinBox,QPushButton,QDialog,QTextEdit,QTabWidget)
from sfm_fx_new_age.contracts.backtest import StudyRequest,STUDY_METHODS
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.public_strategies import BY_KEY


class StudyControls(QWidget):
    def __init__(self,api,selection,context,parent=None):
        super().__init__(parent);self.api,self.selection,self.context=api,selection,context;self.last_result=None
        self.setObjectName('researchStudyControls');g=QGridLayout(self);g.setContentsMargins(0,0,0,0)
        self.method=QComboBox();self.method.setObjectName('studyMethod')
        for key in STUDY_METHODS:self.method.addItem(BY_KEY[key].name,key)
        self.stop=QLineEdit('10,20');self.stop.setObjectName('studyStopBps');self.stop.setMaximumWidth(100)
        self.reward=QLineEdit('1,2');self.reward.setObjectName('studyRewardR');self.reward.setMaximumWidth(80)
        self.cost=QLineEdit('0');self.cost.setObjectName('studyCostBps');self.cost.setMaximumWidth(60)
        self.clock=QComboBox();self.clock.setObjectName('studyInformationClock')
        self.clock.addItem('As observed','AS_OBSERVED');self.clock.addItem('Historical close assumption','HISTORICAL_CLOSE_ASSUMPTION')
        self.train=QSpinBox();self.train.setRange(2,1500);self.train.setValue(100);self.train.setObjectName('studyTrain')
        self.test=QSpinBox();self.test.setRange(1,500);self.test.setValue(30);self.test.setObjectName('studyTest')
        self.hold=QSpinBox();self.hold.setRange(1,100);self.hold.setValue(5);self.hold.setObjectName('studyHolding')
        first=QHBoxLayout()
        for label,widget in [('Marker',self.method),('Stop bps',self.stop),('Target R',self.reward)]:first.addWidget(QLabel(label));first.addWidget(widget)
        g.addLayout(first,0,0)
        first.addWidget(self.clock)
        second=QHBoxLayout()
        for label,widget in [('Train batches',self.train),('Test',self.test),('Hold bars',self.hold),('Cost bps',self.cost)]:second.addWidget(QLabel(label));second.addWidget(widget)
        self.run=QPushButton('Run backtest + walk-forward');self.run.setObjectName('runResearchStudy');self.run.clicked.connect(self.execute);second.addWidget(self.run)
        self.report=QPushButton('View report');self.report.setObjectName('viewResearchStudy');self.report.clicked.connect(self.show_report);self.report.setEnabled(False);second.addWidget(self.report)
        g.addLayout(second,1,0)
        self.status=QLabel('Select replay history or use a chart inspection. Modelled next-open entries; not strategy execution or broker orders.');self.status.setWordWrap(True);self.status.setObjectName('studyStatus');g.addWidget(self.status,2,0)

    def execute(self):
        self.run.setEnabled(False)
        try:
            row=self.selection() or {};context=self.context();dataset_id=row.get('dataset_id')
            if not dataset_id:
                if not context or context['mode']!='MARKET':raise ValueError('Select a replay run/dataset or inspect market history from a chart')
                run=thaw(self.api.create_inspection_replay(context,'study-history-'+uuid4().hex));dataset_id=run['dataset_id']
            datasets=thaw(self.api.query('3.12',DataRequest('replay_datasets',limit=5000)))['rows']
            meta=next((d for d in datasets if d['dataset_id']==dataset_id),None)
            if not meta or len(meta['series'])!=1:raise ValueError('One pair/timeframe dataset required for a study')
            symbol,frame=meta['series'][0]
            axes=lambda editor:tuple(v.strip() for v in editor.text().split(','))
            request=StudyRequest('study-'+uuid4().hex,dataset_id,symbol,frame,self.method.currentData(),axes(self.stop),axes(self.reward),self.hold.value(),self.train.value(),self.test.value(),self.cost.text().strip(),self.clock.currentData())
            self.last_result=thaw(self.api.run_research_study(request));self.report.setEnabled(True)
            s=self.last_result['backtest']['summary'];w=self.last_result['walk_forward']
            self.status.setText(f"Saved {request.study_id} · {s['trades']} baseline trades / {s['ambiguous']} ambiguous · {len(w['folds'])} OOS folds · {w['summary']['net_r']} resolved OOS R. Unknown outcomes excluded; research only.")
            self.show_report()
        except (ValueError,TypeError) as exc:self.status.setText('Study refused: '+str(exc))
        finally:self.run.setEnabled(True)

    def select_saved(self,row):
        if row and row.get('study_id'):
            self.last_result=thaw(self.api.research_study(row['study_id']));self.report.setEnabled(True)

    def show_report(self):
        if not self.last_result:return
        r=self.last_result;d=QDialog(self);d.setAttribute(Qt.WA_DeleteOnClose)
        d.setObjectName('researchStudyReport');d.setWindowTitle('Historical research report · no execution');d.resize(850,550);layout=QVBoxLayout(d);tabs=QTabWidget();layout.addWidget(tabs)
        def page(name,text):
            view=QTextEdit();view.setReadOnly(True);view.setPlainText(text);tabs.addTab(view,name)
        baseline=r['backtest']['summary'];wf=r['walk_forward'];p=r['configuration']
        page('Summary',f"{BY_KEY[p['method_id']].name} · {p['symbol']} {p['timeframe']}\nDataset: {r['dataset_id']}\nOriginal data: {r['original_origin']}\nInformation clock: {r['information_clock']}\nModel: {r['model_version']}\n\nBaseline (first configuration, not best in hindsight)\n"+json.dumps(baseline,indent=2)+"\n\nOut-of-sample (parameters selected using training only)\n"+json.dumps(wf['summary'],indent=2)+"\n\n"+'\n'.join(r['limitations']))
        page('Walk-forward','\n\n'.join(f"Fold {i+1} · {f['selection_state']}\n{json.dumps(f['window'],indent=2)}\nSelected: {f['selected_parameters']}\nTest: {json.dumps(f['test']['summary'])}" for i,f in enumerate(wf['folds'])) or 'Insufficient distinct availability batches for the requested train/test windows. No OOS claim.')
        page('Trades',json.dumps(r['backtest']['trades'],indent=2));page('Technical result',json.dumps(r,indent=2));d.show()
