"""Strategy control consumes shared contracts only; never owns calculations or feed."""
from PySide6.QtWidgets import QCheckBox,QLabel,QPushButton,QHBoxLayout
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.ui.inspection_panels import InspectionPanel
from .order_blocks import RECIPE_ID
from .candidates import CANDIDATE_RECIPE


class StrategyPanel(InspectionPanel):
    def __init__(self,*args):
        super().__init__(*args)
        row=QHBoxLayout()
        self.strategy_enabled=QCheckBox('Order Block · project confirmed research zones')
        self.strategy_enabled.setObjectName('orderBlockStrategyEnabled')
        self.strategy_enabled.setToolTip('Enables the source-backed pivot-break/displacement research profile. No automatic signal or order; incomplete qualification remains blocked.')
        self.strategy_enabled.clicked.connect(self._switch);row.addWidget(self.strategy_enabled,1)
        self.inspect_zones=QPushButton('Inspect zones');self.inspect_zones.setObjectName('inspectOrderBlockZones')
        self.inspect_zones.clicked.connect(self._inspect_zones);row.addWidget(self.inspect_zones)
        self.layout().insertLayout(1,row)
        self.candidates_enabled=QCheckBox('Evaluate D1 / H4 research candidates · all 14 gates remain enforced')
        self.candidates_enabled.setObjectName('orderBlockCandidatesEnabled')
        self.candidates_enabled.clicked.connect(self._candidate_switch);self.layout().insertWidget(2,self.candidates_enabled)
        self.strategy_status=QLabel();self.strategy_status.setObjectName('orderBlockStatus');self.strategy_status.setWordWrap(True)
        self.layout().insertWidget(2,self.strategy_status)
        self.refresh()
    def _switch(self,enabled):
        result=self.api.command('3.1','ENABLE_RECIPE',{'recipe_id':RECIPE_ID,'version':1,'enabled':enabled})
        self.feedback.setText(result.status.value+': '+result.message);self.refresh()
    def _candidate_switch(self,enabled):
        result=self.api.command('3.1','ENABLE_RECIPE',{'recipe_id':CANDIDATE_RECIPE,'version':1,'enabled':enabled})
        self.feedback.setText(result.status.value+': '+result.message);self.refresh()
    def _inspect_zones(self):
        if self.model.subtab_id=='3.5':
            self.dataset.setCurrentIndex(self.dataset.findData('levels'));self.refresh();return
        rows=thaw(self.api.query('3.5',DataRequest('levels',symbol=(self.context or {}).get('symbol'))))['rows']
        zones=[v for v in rows if v.get('kind')=='ORDER_BLOCK' and v['state'] in {'CONFIRMED','TOUCHED'}]
        if not zones:
            self.feedback.setText('No confirmed order-block zone in this source yet. Missing history or no qualifying setup is a valid state.');return
        row=zones[-1];ctx=self.api.inspect(symbol=row['lineage']['symbol'],timeframe=(self.context or {}).get('timeframe','H4'),object_kind='level',object_id=row['level_id'])
        self.api.navigate('3.5',ctx)
    def refresh(self):
        super().refresh()
        if not hasattr(self,'strategy_enabled'):return
        rows=thaw(self.api.query('3.1',DataRequest('recipes')))['rows']
        recipe=next((r for r in rows if r['recipe_id']==RECIPE_ID),None)
        enabled=bool(recipe and (recipe.get('requested') or {}).get('enabled'))
        self.strategy_enabled.blockSignals(True);self.strategy_enabled.setChecked(enabled);self.strategy_enabled.setEnabled(bool(recipe));self.strategy_enabled.blockSignals(False)
        state=(recipe or {}).get('evaluation',{}).get('state','NOT_INSTALLED')
        candidate=next((r for r in rows if r['recipe_id']==CANDIDATE_RECIPE),None)
        self.candidates_enabled.blockSignals(True);self.candidates_enabled.setChecked(bool(candidate and (candidate.get('requested') or {}).get('enabled')));self.candidates_enabled.blockSignals(False)
        cstate=(candidate or {}).get('evaluation',{}).get('state','NOT_EVALUATED')
        self.strategy_status.setText(('Zones enabled' if enabled else 'Zones off')+' · '+state.replace('_',' ')+' · candidate evaluation '+cstate+' · research only; no automatic order or capital approval')

