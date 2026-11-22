"""Explicit research monetary policy; native observations remain read-only."""
import json
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QComboBox,QLineEdit,QPushButton,QPlainTextEdit,QSizePolicy
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest


class CapitalPanel(QWidget):
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self.context=None;self._scope=None;self._version=0
        self.setObjectName('subtab_4_7');layout=QVBoxLayout(self)
        heading=QLabel(model.title);heading.setProperty('role','heading');layout.addWidget(heading)
        note=QLabel('RESEARCH ONLY — not account-risk approval. The 45% reference is not a per-trade budget. Internal invalidation is not broker SL, guaranteed maximum loss, margin approval or portfolio permission.');note.setWordWrap(True);note.setStyleSheet('QLabel { color: #F4C66B; padding: 6px; background: #1D2A3D; border-radius: 5px; }');layout.addWidget(note)
        form=QFormLayout();self.base=QComboBox();self.base.setObjectName('researchCapitalBase');self.base.addItems(['UNCONFIGURED','BALANCE','EQUITY']);form.addRow('Research capital denominator',self.base)
        self.fraction=QLineEdit('0.45');self.fraction.setObjectName('researchCapitalFraction');form.addRow('Decimal fraction (0 < value ≤ 1)',self.fraction)
        self.budget=QLineEdit();self.budget.setObjectName('researchMoneyBudget');self.budget.setPlaceholderText('Positive amount; blank = unconfigured');self.budget_label=QLabel('Scenario budget (account currency)');form.addRow(self.budget_label,self.budget);layout.addLayout(form)
        row=QHBoxLayout();self.apply=QPushButton('Save research policy');self.apply.setObjectName('saveResearchPolicy');self.apply.clicked.connect(self.save_policy);row.addWidget(self.apply)
        reload=QPushButton('Reload current policy');reload.clicked.connect(self.load_policy);row.addWidget(reload);layout.addLayout(row)
        self.state=QLabel();self.state.setWordWrap(True);self.state.setObjectName('capitalObservationStatus');layout.addWidget(self.state)
        self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.technical=QPushButton('Technical details');self.technical.setCheckable(True);self.technical.toggled.connect(lambda checked:self.details.setVisible(checked));layout.addWidget(self.technical)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setObjectName('researchMoneyContext');self.details.setMinimumHeight(65);self.details.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Ignored);layout.addWidget(self.details,1);self.details.hide()
        self.feedback=QLabel();self.feedback.setWordWrap(True);layout.addWidget(self.feedback);self.load_policy()
    def read(self):
        return thaw(self.api.query('4.7',DataRequest('capital_context',symbol=(self.context or {}).get('symbol'))))
    def load_policy(self):
        q=self.read();c=q['rows'][0];self._scope=c['scope_id'];self._version=c['policy_version'];p=c['policy']
        self.base.setCurrentText(p['capital_base']);self.fraction.setText(p['capital_fraction']);self.budget.setText(p['budget_money'] or '')
        self.refresh()
    def refresh(self):
        q=self.read();c=q['rows'][0]
        self.apply.setEnabled(bool(self._scope and self._scope==c['scope_id']))
        currency=c['account_currency'] or 'unknown currency';self.budget_label.setText('Scenario budget ('+currency+')')
        self.state.setText('Native money: '+('current observation' if c['native_money_current'] else 'missing / stale / wrong epoch')+' · Position inventory: '+c['position_inventory_state'].replace('_',' ').lower()+' · Pending inventory: '+c['pending_inventory_state'].replace('_',' ').lower()+(' · Account changed: reload policy before saving' if self._scope!=c['scope_id'] else ''))
        money=c.get('native_money') or {};self.summary.setText('Selected account policy version: '+str(c['policy_version'])+' · '+currency+'\nLast observed balance: '+str(money.get('balance','unavailable'))+' '+currency+' · '+str(money.get('observed_at','no observation'))+'\nResearch reference amount: '+str(c.get('research_fraction_amount') or 'withheld / denominator unconfigured')+' · Approved account amount: NONE\nNo netting, reserve recycling or account-risk permission is inferred.')
        self.details.setPlainText(json.dumps({'context':c,'candidate_variant_estimates':q.get('candidate_estimates',[]),'estimates_total':q.get('candidate_estimates_total',0),'estimates_truncated':q.get('candidate_estimates_truncated',False)},indent=2))
    def save_policy(self):
        result=self.api.command('4.7','SET_RESEARCH_POLICY',{'policy':{'classification':'RESEARCH_ONLY','capital_base':self.base.currentText(),
            'capital_fraction':self.fraction.text(),'budget_money':self.budget.text() or None},'expected_version':self._version,'expected_scope_id':self._scope})
        self.feedback.setText(result.status.value+': '+result.message)
        if result.status.value=='ACCEPTED':self.load_policy()
    def apply_inspection(self,context):self.context=thaw(self.api.validate_inspection(context));self.refresh()
    def inspection_context(self):return self.context
