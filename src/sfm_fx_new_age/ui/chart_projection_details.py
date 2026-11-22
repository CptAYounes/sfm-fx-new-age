"""Read-only values from the chart's own projection snapshot, never an API handle."""
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QComboBox,QTextEdit,QDialogButtonBox


class PublicProjectionDetails(QDialog):
    def __init__(self,canvas,parent=None):
        super().__init__(parent if parent is not None else canvas)
        self.canvas=canvas;self.identity=canvas.data_identity;self.layers=[];self.signature=None
        self.setObjectName('publicProjectionDetails');self.setWindowTitle('Public projection details · read-only');self.resize(660,490)
        outer=QVBoxLayout(self)
        notice=QLabel('Exact source-bound analytical values, including off-screen levels. This view does not create signals or orders. Synthetic inputs remain labelled; a configured publisher is not independent vendor authentication.');notice.setWordWrap(True);outer.addWidget(notice)
        self.picker=QComboBox();self.picker.setObjectName('publicProjectionPicker');self.picker.setAccessibleName('Public strategy projection');outer.addWidget(self.picker)
        self.values=QTextEdit();self.values.setReadOnly(True);self.values.setObjectName('publicProjectionValues');outer.addWidget(self.values,1)
        self.picker.currentIndexChanged.connect(self._render)
        buttons=QDialogButtonBox(QDialogButtonBox.Close);buttons.rejected.connect(self.reject);outer.addWidget(buttons)
        self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self.check_source);self.finished.connect(self.timer.stop)
        if self.check_source():self.timer.start()

    def check_source(self):
        layers=self.canvas.public_strategy_layers() if self.canvas.data_identity==self.identity else []
        if not layers:
            self.values.clear();self.picker.clear();self.reject();return False
        signature=json.dumps(layers,sort_keys=True)
        if signature!=self.signature:
            selected=self.picker.currentData();self.layers=layers;self.signature=signature;self.picker.blockSignals(True);self.picker.clear()
            for layer in layers:self.picker.addItem(layer['name']+' · '+layer['state'],layer['strategy_id'])
            index=self.picker.findData(selected);self.picker.setCurrentIndex(max(0,index));self.picker.blockSignals(False);self._render()
        return True

    def _render(self,*_):
        index=self.picker.currentIndex()
        if not 0<=index<len(self.layers):self.values.clear();return
        layer=self.layers[index];lines=[layer['name'],layer['symbol']+' · '+layer['timeframe']+' · '+layer['origin'],
            'State: '+layer['state'],'Available at: '+layer['available_at'],'Source epoch: '+layer['source_epoch'],layer.get('reason',''),'', 'Levels / regions']
        for row in layer['zones']:
            value=row['low'] if row['low']==row['high'] else row['low']+' → '+row['high']
            lines.append(row['label']+': '+value+' · '+row['state']+' · known '+row['available_at'])
        if not layer['zones']:lines.append('None in this evaluation.')
        lines+=['','Markers']
        for row in layer['markers']:lines.append(row['label']+': '+row['price']+' · '+row['side']+' · known '+row['available_at'])
        if not layer['markers']:lines.append('None in this evaluation.')
        lines+=['','Full source-bound record (original values, not chart-rounded prices)',json.dumps(layer,indent=2)]
        self.values.setPlainText('\n'.join(lines))
