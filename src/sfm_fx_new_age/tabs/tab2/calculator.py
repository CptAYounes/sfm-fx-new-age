"""Embeddable SFM calculator. Never launches the Tk/.deb app or submits trades."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QComboBox,QLineEdit,QLabel,QPushButton,QFrame,QMenu
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.services.tool_calculator import GROUPS,calculate,convert_pnl


class CalculatorWidget(QWidget):
    def __init__(self,parent=None,api=None):
        super().__init__(parent);self.setObjectName('embeddedForexCalculator');self.memory={};self.active_pair='EURUSD'
        self.api=api;self.pending_context=None;self.context_data=None
        layout=QVBoxLayout(self);layout.setContentsMargins(10,8,10,8);layout.setSpacing(5)
        self.pair=QComboBox();self.pair.setObjectName('calculatorPair');self.pair.setEditable(True);self.pair.setInsertPolicy(QComboBox.NoInsert)
        for group,names in GROUPS.items():
            for pair in names.split():self.pair.addItem(pair,group)
        self.side=QComboBox();self.side.addItems(['BUY','SELL']);self.side.setObjectName('calculatorSide')
        row=QHBoxLayout();row.addWidget(self.pair,1);row.addWidget(self.side);reset=QPushButton('Reset');reset.clicked.connect(self.reset);row.addWidget(reset);layout.addLayout(row)
        form=QFormLayout();form.setVerticalSpacing(8);self.inputs={}
        for key,name,placeholder in [('entry','Entry price','Manual price'),('exit','Exit price','Manual price'),('lots','Lots','0.01–1.00')]:
            edit=QLineEdit('0.10' if key=='lots' else '');edit.setObjectName('calculator_'+key);edit.setPlaceholderText(placeholder)
            form.addRow(name,edit);self.inputs[key]=edit;edit.textChanged.connect(self.refresh)
        self.account=QComboBox();self.account.addItems(['Quote currency','USD','EUR','GBP','JPY','CHF','CAD','AUD','NZD'])
        self.rate=QLineEdit();self.rate.setPlaceholderText('Manual quote → account rate');self.rate.setObjectName('calculatorRate')
        right=QFormLayout();right.setVerticalSpacing(8)
        right.addRow('Display currency',self.account);right.addRow('Conversion rate',self.rate)
        self.contract=QLineEdit('100000');self.contract.setObjectName('calculatorContract');self.contract.setToolTip('Editable units per lot')
        self.pip_size=QLineEdit('.0001');self.pip_size.setObjectName('calculatorPip');self.pip_size.setToolTip('Editable pip size')
        specrow=QHBoxLayout();specrow.addWidget(self.contract);specrow.addWidget(self.pip_size);right.addRow('Lot / pip',specrow)
        self.contract.textChanged.connect(self.refresh);self.pip_size.textChanged.connect(self.refresh)

        columns=QHBoxLayout();columns.setSpacing(18);columns.addLayout(form,1);columns.addLayout(right,1);layout.addLayout(columns)
        handoff=QHBoxLayout();self.use_chart=QPushButton('Use chart context');self.use_chart.setObjectName('calculatorUseChart');self.use_chart.clicked.connect(lambda:self.use_context());handoff.addWidget(self.use_chart)
        self.replace_prices=QPushButton('Replace scenario prices');self.replace_prices.setObjectName('calculatorReplaceScenario');self.replace_prices.clicked.connect(lambda:self.use_context(replace=True));handoff.addWidget(self.replace_prices)
        self.use_specs=QPushButton('Use broker spec');self.use_specs.clicked.connect(self._use_specs);handoff.addWidget(self.use_specs)
        self.use_conversion=QPushButton('Use observed conversion');self.use_conversion.clicked.connect(self._use_conversion);handoff.addWidget(self.use_conversion);layout.addLayout(handoff)
        self.show_chart=QPushButton('Show scenario on Chart');self.show_chart.setObjectName('calculatorShowChart');self.show_chart.setToolTip('Project these manual estimates on the source chart; not risk sizing or an order');self.show_chart.clicked.connect(self.project_scenario);row.addWidget(self.show_chart)
        self.provenance=QLabel('Manual / offline estimate · no chart handoff selected');self.provenance.setWordWrap(True);self.provenance.setObjectName('calculatorProvenance');layout.addWidget(self.provenance)
        for b in (self.use_chart,self.replace_prices,self.use_specs,self.use_conversion,self.show_chart):b.setEnabled(False)
        card=QFrame();card.setObjectName('card');card_layout=QVBoxLayout(card)
        self.result=QLabel('—');self.result.setObjectName('calculatorResult');self.result.setProperty('role','heading');self.result.setWordWrap(True)
        self.detail=QLabel('Enter entry and exit prices.');self.detail.setWordWrap(True);self.detail.setTextFormat(Qt.PlainText)
        card_layout.addWidget(self.result);card_layout.addWidget(self.detail);layout.addWidget(card)

        note=QLabel('Gross estimate only · no fees, swaps or broker orders. Handoffs preserve manual edits.')
        note.setProperty('role','muted');note.setWordWrap(True);layout.addWidget(note);layout.addStretch()
        self.side.currentIndexChanged.connect(self.refresh);self.account.currentIndexChanged.connect(self.refresh);self.rate.textChanged.connect(self.refresh)
        self.pair.currentTextChanged.connect(self.change_pair);self.refresh()

    def apply_inspection(self,context):
        if not self.api:return
        self.pending_context=thaw(self.api.validate_inspection(context));self.context_data=thaw(self.api.calculator_context(context))
        self.provenance.setText('Received '+context['symbol']+' / '+context['timeframe']+' · adopt or replace prices explicitly; manual edits are retained.')
        self.provenance.setToolTip('Source-bound handoff. Use chart context fills empty fields only. Replace scenario prices explicitly replaces prices and direction. Show scenario on Chart projects manual estimates without changing the source signal or creating orders.')
        for b in (self.use_chart,self.replace_prices,self.use_specs,self.use_conversion,self.show_chart):b.setEnabled(True)
    def project_scenario(self):
        if not self.api or not self.pending_context:return
        try:
            self.api.validate_inspection(self.pending_context)
            if self.pair.currentText()!=self.pending_context['symbol']:raise ValueError('Matching source/pair required; obtain a new chart handoff for this pair')
            s={k:self.inputs[k].text() for k in ('entry','exit','lots')}
            s.update(side=self.side.currentText(),contract=self.contract.text(),pip_size=self.pip_size.text())
            calculate(self.pair.currentText(),s['side'],s['entry'],s['exit'],s['lots'],s['contract'],s['pip_size'])
            self.api.navigate('1.8',self.api.scenario_context(self.pending_context,s))
        except ValueError as exc:self.provenance.setText('Projection refused: '+str(exc)+' · manual values retained')
    def inspection_context(self):return self.pending_context
    def use_context(self,replace=False):
        if not self.api or not self.pending_context:return
        try:
            self.context_data=thaw(self.api.calculator_context(self.pending_context));ctx=self.context_data['context'];self.pair.setCurrentText(ctx['symbol'])
            scenario=ctx.get('scenario') or {};quote=self.context_data.get('quote') or {}
            # Empty-field adoption preserves the operator's direction too. Only
            # the separate replacement action adopts the scenario direction.
            side=scenario.get('side',self.side.currentText()) if replace else self.side.currentText()
            values={'entry':scenario.get('entry') or quote.get('ask' if side=='BUY' else 'bid'),'exit':scenario.get('exit')}
            for key,value in values.items():
                if value is not None and (replace or not self.inputs[key].text()):self.inputs[key].setText(str(value))
            if replace:self.side.setCurrentText(side)
            self.provenance.setText(ctx['origin']+' · '+ctx['symbol']+' · source-bound scenario · quote observation '+str(quote.get('available_at','not used'))+' · provider snapshot, not refreshed by handoff; lot/pip remain editable')
            self.refresh()
        except ValueError as exc:self.provenance.setText('Handoff refused: '+str(exc)+' · manual values retained')
    def _use_specs(self):
        if not self.api or not self.pending_context:return
        try:
            data=thaw(self.api.calculator_context(self.pending_context));spec=data['specification']
            if not spec or data['context']['symbol']!=self.pair.currentText():raise ValueError('Matching source/pair broker specification unavailable')
            self.contract.setText(spec['units_per_lot']);self.pip_size.setText(spec['pip_size'])
            self.provenance.setText('Broker specification '+spec['symbol']+' · volume '+spec['volume_min']+'–'+spec['volume_max']+' units, step '+spec['volume_step']+' · estimate only; no order rounding or sending')
        except ValueError as exc:self.provenance.setText(str(exc))
    def _use_conversion(self):
        from decimal import Decimal
        if not self.api or not self.pending_context:return
        try:
            data=thaw(self.api.calculator_context(self.pending_context));quote=self.pair.currentText()[3:];account=self.account.currentText()
            if account in {'Quote currency',quote}:self.rate.setText('1');return
            found=next((q for q in data['quotes'] if q['symbol'] in {quote+account,account+quote}),None)
            if not found:raise ValueError('No observed direct/inverse conversion pair; supply a manual rate')
            rate=Decimal(found['bid']) if found['symbol']==quote+account else 1/Decimal(found['ask'])
            self.rate.setText(str(rate));self.provenance.setText('Estimated conversion '+found['symbol']+' · '+found['state']+' · provider time '+found['available_at']+' · gross scenario, not an executable currency conversion')
        except ValueError as exc:self.provenance.setText(str(exc))
    def fields(self):return {key:edit.text() for key,edit in self.inputs.items()}|{'side':self.side.currentText(),'account':self.account.currentText(),'rate':self.rate.text(),'contract':self.contract.text(),'pip_size':self.pip_size.text()}
    def change_pair(self,pair):
        self.memory[self.active_pair]=self.fields();self.active_pair=pair
        data=self.memory.get(pair,{'entry':'','exit':'','lots':'.10','side':'BUY','account':'Quote currency','rate':''})
        for key,edit in self.inputs.items():edit.blockSignals(True);edit.setText(data[key]);edit.blockSignals(False)
        for widget,value in ((self.side,data['side']),(self.account,data['account'])):
            widget.blockSignals(True);widget.setCurrentText(value);widget.blockSignals(False)
        self.rate.blockSignals(True);self.rate.setText(data['rate']);self.rate.blockSignals(False)
        self.contract.setText(data.get('contract','100000'));self.pip_size.setText(data.get('pip_size','.01' if pair.endswith('JPY') else '.0001'));self.refresh()
    def reset(self):
        self.memory.pop(self.active_pair,None)
        # Do not save the current values back into the pair being reset.
        for key,edit in self.inputs.items():edit.setText('.10' if key=='lots' else '')
        self.side.setCurrentIndex(0);self.account.setCurrentIndex(0);self.rate.clear();self.contract.setText('100000');self.pip_size.setText('.01' if self.active_pair.endswith('JPY') else '.0001');self.refresh()
    def refresh(self,*args):
        if not hasattr(self,'pip_size') or not hasattr(self,'result'):return
        required=self.account.currentText() not in ('Quote currency',self.pair.currentText()[3:])
        self.rate.setEnabled(required)
        try:
            result=calculate(self.pair.currentText(),self.side.currentText(),self.inputs['entry'].text(),self.inputs['exit'].text(),self.inputs['lots'].text(),self.contract.text(),self.pip_size.text())
            converted=convert_pnl(result['pnl'],result['quote'],self.account.currentText(),self.rate.text())
        except ValueError as exc:
            self.result.setText('—');self.detail.setText(str(exc));return
        currency=result['quote'] if self.account.currentText()=='Quote currency' else self.account.currentText()
        self.result.setText(f"{converted:+,.2f} {currency}")
        self.detail.setText(f"{result['pips']:+,.1f} pips  ·  {result['units']:,.0f} units\nPip value: {result['pip_value']:,.4f} {result['quote']}  ·  gross estimate")
