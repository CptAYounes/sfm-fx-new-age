"""Compact scanner inspection, not a persistent 44-row catalogue in the workspace."""
from collections import Counter
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QFrame
from sfm_fx_new_age.contracts.models import thaw


def _text(value,role='muted'):
    result=QLabel(value);result.setWordWrap(True);result.setTextFormat(Qt.PlainText)
    result.setProperty('role',role)
    return result


class ScannerOverview(QWidget):
    """Keep required diagnostics on demand, without deleting registry/domain capabilities."""
    def __init__(self,api,model,parent=None):
        super().__init__(parent);self.api,self.model=api,model;self._fingerprint=None;self._nodes={}
        self.setObjectName('subtab_2_2')
        layout=QVBoxLayout(self);layout.setContentsMargins(20,20,20,20);layout.setSpacing(16)
        layout.addWidget(_text('Scanner overview','heading'))
        self.summary=_text('No market data — components have not been evaluated.')
        self.summary.setObjectName('scannerSummary');layout.addWidget(self.summary)
        card=QFrame();card.setObjectName('card');body=QVBoxLayout(card);body.setContentsMargins(16,16,16,16);body.setSpacing(12)
        row=QHBoxLayout();caption=_text('Inspect component','caption');row.addWidget(caption)
        self.picker=QComboBox();self.picker.setObjectName('scannerComponentPicker')
        self.picker.setAccessibleName('Scanner component to inspect');caption.setBuddy(self.picker)
        self.picker.setMinimumContentsLength(24)
        row.addWidget(self.picker,1);body.addLayout(row)
        self.detail=_text('Select a component to inspect its current capability.')
        self.detail.setObjectName('scannerComponentDetail');self.detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.addWidget(self.detail);layout.addWidget(card)
        layout.addWidget(_text('This view reads the shared scanner. Selecting a component does not start, stop or duplicate it.','caption'))
        layout.addStretch(1)
        self.picker.currentIndexChanged.connect(self._show_component)

    def refresh(self):
        snapshot=self.api.snapshot('2.2');data=thaw(snapshot.data)
        fingerprint=json.dumps(data,sort_keys=True,default=str)
        if fingerprint==self._fingerprint:return
        self._fingerprint=fingerprint;selected=self.picker.currentData()
        self._nodes={node['id']:node for node in data['rows']}
        counts=Counter(node.get('state',node.get('status','NOT_EVALUATED')) for node in self._nodes.values())
        summary=' · '.join(f'{count} {state.lower().replace("_"," ")}' for state,count in sorted(counts.items()))
        prefix='No market data' if data['origin']=='NO_SOURCE' else f'{data["origin"]} · {data["symbol"]}'
        self.summary.setText(prefix+'\n'+summary)
        self.picker.blockSignals(True);self.picker.clear()
        for identity in self._nodes:self.picker.addItem(identity.replace('_',' ').title(),identity)
        found=self.picker.findData(selected)
        self.picker.setCurrentIndex(max(0,found));self.picker.blockSignals(False)
        self._show_component()

    def _show_component(self,*args):
        node=self._nodes.get(self.picker.currentData())
        if not node:return
        state=node.get('state',node.get('status','NOT_EVALUATED')).replace('_',' ')
        registered=node.get('registered')
        lines=[node['id'],f'Current state: {state}']
        if registered is not None:lines.append('Producer: '+('registered' if registered else 'not implemented'))
        if node.get('reason'):lines.append('Detail: '+node['reason'])
        self.detail.setText('\n'.join(lines))
