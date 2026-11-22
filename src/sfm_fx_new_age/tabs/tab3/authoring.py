"""Actual authoring widgets use only TabApi; one shared evaluator/config owner."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,QPushButton,
    QPlainTextEdit,QTreeWidget,QTreeWidgetItem,QSplitter,QSpinBox,QFormLayout,QMessageBox,QDialog)
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.analytics import digest


def rows(api,view,dataset,**kwargs):return thaw(api.query(view,DataRequest(dataset,limit=5000,**kwargs)))['rows']


class RuleBuilderPanel(QWidget):
    """Tree + typed condition composer, with full bounded declarative JSON access.
    Preview is pure; saving never activates, and activation pins a saved revision.
    Polling never overwrites an in-progress edit or updates its CAS baseline.
    """
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self.context=None;self._version=0;self._saved_hash=None;self._saved_rule=None
        self.setObjectName('subtab_3_10');layout=QVBoxLayout(self);layout.setContentsMargins(14,10,14,10);layout.setSpacing(6)
        heading=QLabel(model.title);heading.setProperty('role','heading');layout.addWidget(heading)
        note=QLabel('Analytical rules only · TRUE / FALSE / UNKNOWN · Preview writes nothing · Save does not activate · No broker outputs');note.setWordWrap(True);layout.addWidget(note)
        row=QHBoxLayout();self.rule_id=QLineEdit();self.rule_id.setObjectName('ruleIdentity');self.rule_id.setPlaceholderText('Rule ID')
        row.addWidget(self.rule_id,2);self.saved=QComboBox();self.saved.setObjectName('savedRules');row.addWidget(self.saved,2)
        self.load=QPushButton('Load saved');self.load.clicked.connect(self.load_rule);row.addWidget(self.load)
        self.new=QPushButton('New');self.new.clicked.connect(self.new_rule);row.addWidget(self.new);layout.addLayout(row)
        row=QHBoxLayout();self.variable=QComboBox();self.variable.setObjectName('ruleVariable');row.addWidget(self.variable,3)
        self.operator=QComboBox();self.operator.addItems(['GT','GE','LT','LE','EQ','NE']);row.addWidget(self.operator)
        self.literal=QLineEdit();self.literal.setObjectName('ruleLiteral');self.literal.setPlaceholderText('Typed value');row.addWidget(self.literal,1)
        self.history=QSpinBox();self.history.setRange(0,128);self.history.setPrefix('Bars back ');row.addWidget(self.history)
        self.add=QPushButton('Add condition');self.add.setObjectName('addRuleCondition');self.add.clicked.connect(self.add_condition);row.addWidget(self.add);layout.addLayout(row)
        split=QSplitter();self.tree=QTreeWidget();self.tree.setHeaderLabels(['Logic tile','Value / unit']);self.tree.setObjectName('ruleTree')
        split.addWidget(self.tree);self.editor=QPlainTextEdit();self.editor.setObjectName('ruleJson');self.editor.setPlaceholderText('Declarative rule JSON; no executable expressions')
        self.editor.textChanged.connect(self.render_tree);split.addWidget(self.editor);layout.addWidget(split,1)
        row=QHBoxLayout();self.combine=QComboBox();self.combine.addItems(['AND','OR']);row.addWidget(self.combine)
        for title,callback in [('Wrap selected group',self.wrap_group),('Negate selection',self.negate),('Remove tile',self.remove_tile)]:
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        self.output=QComboBox();self.output.addItems(['DISPLAY','OBSERVATION','NOTIFICATION','PARAMETER_PROPOSAL']);self.output.setToolTip('Analytical output type. Broker operations are never permitted.');row.addWidget(QLabel('Output'));row.addWidget(self.output,1);layout.addLayout(row)
        row=QHBoxLayout();self.actions={}
        for action,title in [('preview','Preview only'),('save','Save draft'),('activate','Activate saved'),('suspend','Suspend'),('rollback','Use prior saved')]:
            b=QPushButton(title);b.setObjectName('rule'+action.title());b.clicked.connect(lambda checked=False,a=action:self.perform(a));self.actions[action]=b;row.addWidget(b)
        self.revision=QSpinBox();self.revision.setRange(1,1000000);self.revision.setPrefix('Version ');row.addWidget(self.revision);layout.addLayout(row)
        self.feedback=QLabel();self.feedback.setWordWrap(True);self.feedback.setObjectName('ruleFeedback');layout.addWidget(self.feedback)
        self.new_rule();self.refresh()
    def new_rule(self):
        self._version=0;self._loaded_id=None;self._saved_hash=None;self._saved_rule=None;self.rule_id.clear()
        self.editor.setPlainText(json.dumps({'op':'AND','children':[]},indent=2));self.feedback.setText('New unsaved draft · add a typed condition or edit the bounded declarative JSON.')
    def _rule(self):
        text=self.editor.toPlainText()
        if len(text)>100000:raise ValueError('Rule JSON exceeds editor budget')
        return json.loads(text)
    def _path(self):
        item=self.tree.currentItem();return item.data(0,Qt.UserRole) if item else ()
    @staticmethod
    def at(rule,path):
        value=rule
        for key in path:value=value[key]
        return value
    def change(self,rule):self.editor.setPlainText(json.dumps(rule,indent=2,allow_nan=False))
    def add_condition(self):
        try:
            definition=self.variable.currentData()
            if not definition:raise ValueError('Select a registered typed variable first')
            value=json.loads(self.literal.text()) if definition['data_type'] in {'number','integer','boolean'} else self.literal.text()
            if definition['data_type']=='boolean' and type(value) is not bool:raise ValueError('Boolean literal must be true or false')
            if definition['data_type']=='integer' and type(value) is not int:raise ValueError('Integer literal required')
            if definition['data_type']=='number' and (isinstance(value,bool) or not isinstance(value,(int,float))):raise ValueError('Numeric JSON literal required')
            left={'op':'HISTORY','variable':definition['key'],'bars':self.history.value()} if self.history.value() else {'op':'VAR','variable':definition['key']}
            condition={'op':self.operator.currentText(),'left':left,'right':{'op':'CONST','value':value,'unit':definition['unit']}}
            rule=self._rule();path=self._path();parent=self.at(rule,path)
            if parent.get('op') in {'AND','OR'}:parent['children'].append(condition)
            elif not path:rule={'op':self.combine.currentText(),'children':[rule,condition]}
            else:raise ValueError('Select an AND/OR group or the root to add a condition')
            self.change(rule)
        except (ValueError,KeyError,TypeError) as exc:self.feedback.setText(str(exc))
    def wrap_group(self):self._wrap(False)
    def negate(self):self._wrap(True)
    def _wrap(self,negate):
        try:
            rule=self._rule();path=self._path();node=self.at(rule,path)
            wrapped={'op':'NOT','child':node} if negate else {'op':self.combine.currentText(),'children':[node]}
            if path:self.at(rule,path[:-1])[path[-1]]=wrapped
            else:rule=wrapped
            self.change(rule)
        except (ValueError,KeyError,TypeError) as exc:self.feedback.setText(str(exc))
    def remove_tile(self):
        try:
            rule=self._rule();path=self._path()
            if not path:raise ValueError('Replace the root JSON or start New to clear the entire rule')
            parent=self.at(rule,path[:-1]);key=path[-1]
            if not isinstance(parent,list):raise ValueError('Remove conditions from a group; edit required operands in JSON')
            del parent[key];self.change(rule)
        except (ValueError,KeyError,TypeError) as exc:self.feedback.setText(str(exc))
    def render_tree(self):
        self.tree.clear()
        try:rule=self._rule()
        except ValueError:return
        count=[0]
        def add(parent,node,path=(),depth=0):
            count[0]+=1
            if count[0]>256 or depth>16:return
            if not isinstance(node,dict):return
            text=str(node.get('variable',node.get('value','')))+' '+str(node.get('unit',''))
            item=QTreeWidgetItem([str(node.get('op','invalid')),text]);item.setData(0,Qt.UserRole,path)
            (parent.addChild if isinstance(parent,QTreeWidgetItem) else parent.addTopLevelItem)(item)
            for key in ['left','right','child','low','high','value']:
                if isinstance(node.get(key),dict):add(item,node[key],path+(key,),depth+1)
            children=node.get('children',[])
            for i,child in enumerate(children[:64] if isinstance(children,list) else []):add(item,child,path+('children',i),depth+1)
        add(self.tree,rule);self.tree.expandToDepth(3);self.tree.resizeColumnToContents(0)
    def refresh(self):
        current=self.saved.currentData();self.saved.blockSignals(True);self.saved.clear()
        for row in rows(self.api,'3.10','rules'):self.saved.addItem(row['rule_id']+' · '+row['state']+' · draft '+str(row['version'])+' / active '+str(row.get('active_version')),row['rule_id'])
        if self.saved.findData(current)>=0:self.saved.setCurrentIndex(self.saved.findData(current))
        self.saved.blockSignals(False)
        current=self.variable.currentData();key=current.get('key') if current else None;self.variable.blockSignals(True);self.variable.clear()
        for d in rows(self.api,'3.10','variable_definitions'):self.variable.addItem(d['key']+' ['+d['unit']+']',d)
        for i in range(self.variable.count()):
            if self.variable.itemData(i)['key']==key:self.variable.setCurrentIndex(i);break
        self.variable.blockSignals(False)
    def load_rule(self):
        identity=self.saved.currentData()
        if not identity:return
        if self.editor.document().isModified():
            if QMessageBox.question(self,'Discard unsaved rule edits?','Load the saved rule and discard current unapplied edits?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        found=rows(self.api,'3.10','rules',object_id=identity)
        if not found:return
        row=found[0];self.rule_id.setText(identity);self._loaded_id=identity;self._version=row['version'];self._saved_rule=row['rule'];self._saved_hash=digest(row['rule'])
        self.change(row['rule']);self.editor.document().setModified(False);self.output.setCurrentText(row['output']);self.revision.setValue(row['version'])
        self.feedback.setText('Loaded draft '+str(self._version)+' · active '+str(row.get('active_version'))+' · '+row['state'])
    def perform(self,action):
        try:
            identity=self.rule_id.text().strip()
            if not identity or len(identity)>200:raise ValueError('Rule ID must be 1–200 characters')
            rule=self._rule();payload={'rule_id':identity,'rule':rule,'action':action}
            if action!='preview':payload['expected_version']=self._version if identity==self._loaded_id else 0
            if action=='save':payload['output']=self.output.currentText()
            if action=='activate':
                if self._saved_hash!=digest(rule):raise ValueError('Save these edits before activating; only an exact saved revision can be activated')
                payload['version']=self._version
            if action=='rollback':payload['version']=self.revision.value()
            result=self.api.command('3.10','SAVE_PREVIEW_ACTIVATE_RULE',payload)
            self.feedback.setText(result.status.value+': '+result.message)
            if result.status.value=='ACCEPTED' and action=='save':
                row=rows(self.api,'3.10','rules',object_id=identity)[0];self._loaded_id=identity;self._version=row['version'];self._saved_rule=rule;self._saved_hash=digest(rule)
                self.editor.document().setModified(False);self.revision.setValue(self._version)
            self.refresh()
            if self.saved.findData(identity)>=0:self.saved.setCurrentIndex(self.saved.findData(identity))
        except (ValueError,KeyError,TypeError) as exc:self.feedback.setText('Refused: '+str(exc))
    def apply_inspection(self,context):self.context=thaw(self.api.validate_inspection(context))
    def inspection_context(self):return self.context


class ParameterEditorPanel(QWidget):
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self.context=None;self._version=0;self._key=None;self._definitions={}
        self.setObjectName('subtab_3_11');layout=QVBoxLayout(self);heading=QLabel(model.title);heading.setProperty('role','heading');layout.addWidget(heading)
        note=QLabel('Versioned research parameters · editing does not activate a strategy or submit an order · defaults are not calibrated policy');note.setWordWrap(True);layout.addWidget(note)
        self.profile=QComboBox();self.profile.setObjectName('parameterPairProfile');self.profile.addItem('Global research defaults',None)
        from sfm_fx_new_age.contracts.domain import PAIRS
        for pair in PAIRS:self.profile.addItem(pair+' · selected account override',pair)
        self.profile.currentIndexChanged.connect(self.load_parameter);layout.addWidget(self.profile)
        self.choose=QComboBox();self.choose.setObjectName('researchParameter');self.choose.currentIndexChanged.connect(self.load_parameter);layout.addWidget(self.choose)
        self.description=QLabel();self.description.setWordWrap(True);layout.addWidget(self.description)
        self.value=QLineEdit();self.value.setObjectName('researchParameterValue');layout.addWidget(self.value)
        row=QHBoxLayout();self.apply=QPushButton('Apply versioned change');self.apply.setObjectName('applyResearchParameter');self.apply.clicked.connect(self.apply_change);row.addWidget(self.apply)
        self.reload=QPushButton('Reload current');self.reload.clicked.connect(self.load_parameter);row.addWidget(self.reload);layout.addLayout(row)
        self.history=QPlainTextEdit();self.history.setReadOnly(True);layout.addWidget(self.history,1)
        self.feedback=QLabel('');self.feedback.setWordWrap(True);layout.addWidget(self.feedback)
        self._inspector=None;self.inspect_registry=QPushButton('Inspect definitions / history…');self.inspect_registry.setObjectName('inspectParameterRegistry');self.inspect_registry.clicked.connect(self.open_registry);layout.addWidget(self.inspect_registry)
        self.refresh()
    def open_registry(self):
        if self._inspector:self._inspector.show();self._inspector.raise_();return
        from sfm_fx_new_age.ui.inspection_panels import InspectionPanel
        dialog=QDialog(self);dialog.setWindowTitle('Research parameter registry');dialog.setObjectName('parameterRegistryDialog');dialog.resize(840,600)
        layout=QVBoxLayout(dialog);dialog.panel=InspectionPanel(self.api,self.model,dialog);layout.addWidget(dialog.panel)
        dialog.finished.connect(lambda code:setattr(self,'_inspector',None));dialog.setAttribute(Qt.WA_DeleteOnClose);self._inspector=dialog;dialog.show()
    def refresh(self):
        definitions=rows(self.api,'3.11','parameter_definitions');self._definitions={d['key']:d for d in definitions if d.get('owner')=='STRATEGY_RECIPE_HOST'}
        if [self.choose.itemData(i) for i in range(self.choose.count())]!=list(self._definitions):
            self.choose.blockSignals(True);self.choose.clear()
            for key in self._definitions:self.choose.addItem(key,key)
            self.choose.blockSignals(False);self.load_parameter()
    def load_parameter(self):
        key=self.choose.currentData()
        if not key:return
        d=self._definitions[key];pair=self.profile.currentData()
        query=thaw(self.api.query('3.11',DataRequest('pair_parameters' if pair else 'parameters',object_id=key,symbol=pair)))
        self._scope=query['scope_id'];found=query['rows'];global_rows=rows(self.api,'3.11','parameters',object_id=key)
        inherited=global_rows[0]['value'] if global_rows else d['default'];body=found[0] if found else {'version':0,'value':inherited}
        self._key=key;self._version=body['version'];self.value.setText(json.dumps(body['value']))
        self.description.setText(d['data_type']+' · '+d['unit']+' · range '+str(d['minimum'])+'…'+str(d['maximum'])+' · current version '+str(self._version)+' · '+d['activation_boundary'])
        self.history.setPlainText(('Inherited global value; saving creates a selected-account pair override.\n' if pair and not found else '')+json.dumps(rows(self.api,'3.11','pair_parameter_history' if pair else 'parameter_history',object_id=key,symbol=pair),indent=2))
    def apply_change(self):
        try:
            if self._key!=self.choose.currentData():raise ValueError('Reload the selected parameter')
            value=json.loads(self.value.text());payload={'key':self._key,'value':value,'expected_version':self._version}
            if self.profile.currentData():payload.update(symbol=self.profile.currentData(),expected_scope_id=self._scope)
            result=self.api.command('3.11','PROPOSE_VERSIONED_PARAM_CHANGE',payload)
            self.feedback.setText(result.status.value+': '+result.message)
            if result.status.value=='ACCEPTED':self.load_parameter()
        except ValueError as exc:self.feedback.setText('Refused: '+str(exc))
    def apply_inspection(self,context):self.context=thaw(self.api.validate_inspection(context))
    def inspection_context(self):return self.context
