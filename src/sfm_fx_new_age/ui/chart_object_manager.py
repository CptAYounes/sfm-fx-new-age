"""Multi-object inventory: exact properties, bulk flags, layering and source guard."""
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QPushButton,QAbstractItemView,QInputDialog,QLineEdit)
from .chart_properties import ObjectProperties,BulkAppearance
from PySide6.QtWidgets import QColorDialog
from PySide6.QtGui import QColor
from sfm_fx_new_age.contracts.chart_display import style_for

class DrawingManager(QDialog):
    def __init__(self,canvas,parent=None):
        super().__init__(parent if parent is not None else canvas);self.canvas=canvas;self.book=canvas.drawings;self.identity=canvas.data_identity
        self.setWindowTitle('Local chart objects');self.resize(750,450);self.setObjectName('chartDrawingManager')
        outer=QVBoxLayout(self);label=QLabel('Local display annotations · source-scoped notes save through the chart workspace · Ctrl/Shift selects multiple objects');label.setWordWrap(True);outer.addWidget(label)
        self.search=QLineEdit();self.search.setPlaceholderText('Filter by name / type');self.search.setObjectName('chartObjectFilter');self.search.textChanged.connect(self.refresh);outer.addWidget(self.search)
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(('Name / type','Anchors · UTC / price','Visibility','Movement'));self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSelectionMode(QAbstractItemView.ExtendedSelection);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.verticalHeader().hide();self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0,170);self.table.setColumnWidth(1,310);self.table.itemSelectionChanged.connect(self.select);self.table.cellDoubleClicked.connect(lambda *_:self.properties());outer.addWidget(self.table,1)
        self.buttons={}
        groups=((('Properties…','properties',self.properties),('Style…','style',self.bulk_style),('Duplicate','duplicate',self.duplicate),('Hide/show','hide',lambda:self.modify('hidden')),('Lock/unlock','lock',lambda:self.modify('locked')),('Find on chart','find',self.find)),
         (('Price…','price',self.price),('Colour…','colour',self.colour),('Back','back',lambda:self.layer(False)),('Front','front',lambda:self.layer(True)),('Delete','delete',self.remove),('Undo','undo',self.undo),('Redo','redo',self.redo)))
        for group in groups:
            row=QHBoxLayout()
            for title,key,callback in group:
                button=QPushButton(title);button.setObjectName('chartObject_'+key);button.clicked.connect(callback);row.addWidget(button);self.buttons[key]=button
            outer.addLayout(row)
        self.message=QLabel();self.message.setWordWrap(True);outer.addWidget(self.message);close=QPushButton('Close');close.clicked.connect(self.accept);outer.addWidget(close)
        self.timer=QTimer(self);self.timer.setInterval(200);self.timer.timeout.connect(self.check_source);self.finished.connect(self.timer.stop);self.timer.start();self.refresh()
    def check_source(self):
        valid=self.canvas.data_identity==self.identity and self.canvas.drawings is self.book
        if not valid:self.reject()
        return valid
    def identities(self):return [self.table.item(row,0).data(Qt.UserRole) for row in sorted({x.row() for x in self.table.selectedIndexes()}) if self.table.item(row,0)]
    def selected(self):
        ids=self.identities();return self.book.get(ids[-1]) if ids else None
    def refresh(self):
        selected=self.book.selection;self.table.blockSignals(True);rows=[o for o in self.book.items if self.search.text().lower() in (o['kind']+' '+style_for(o)['name']).lower()];self.table.setRowCount(len(rows));self.table.clearSelection()
        for row,obj in enumerate(rows):
            anchors='\n'.join(t[:19].replace('T',' ')+' / '+f'{v:.{self.canvas.precision}f}' for t,v in obj['anchors'])
            for col,text in enumerate(((style_for(obj)['name'] or obj['kind'])+' · '+obj['kind'],anchors,'Hidden' if obj['hidden'] else 'Visible','Locked' if obj['locked'] else 'Editable')):
                item=QTableWidgetItem(text);item.setToolTip(text);item.setData(Qt.UserRole,obj['id']);self.table.setItem(row,col,item)
            self.table.setRowHeight(row,46 if len(obj['anchors'])==2 else 28)
            if obj['id'] in selected:
                from PySide6.QtCore import QItemSelectionModel
                self.table.selectionModel().select(self.table.model().index(row,0),QItemSelectionModel.Select|QItemSelectionModel.Rows)
        self.table.blockSignals(False);self.select()
        self.buttons['undo'].setEnabled(self.book.can_undo);self.buttons['redo'].setEnabled(self.book.can_redo)
    def select(self):
        ids=self.identities();self.book._selection=ids;self.canvas.update();obj=self.selected()
        for key in ('hide','lock','colour','delete','duplicate','back','front','style'):self.buttons[key].setEnabled(bool(ids))
        self.buttons['properties'].setEnabled(len(ids)==1);self.buttons['find'].setEnabled(len(ids)==1)
        self.buttons['price'].setEnabled(bool(len(ids)==1 and obj['kind']=='Level' and not obj['locked']))
    def properties(self):
        obj=self.selected()
        if obj and self.check_source():
            d=ObjectProperties(self.canvas,obj['id'],self);d.exec();d.deleteLater()
            if self.check_source():self.refresh()
    def bulk_style(self):
        if self.identities() and self.check_source():
            d=BulkAppearance(self.canvas,self.identities(),self);d.exec();d.deleteLater()
            if self.check_source():self.refresh()
    def modify(self,key):
        obj=self.selected()
        if obj and self.check_source():self.book.modify_many(self.identities(),**{key:not obj[key]});self.refresh()
    def duplicate(self):
        if not self.check_source():return
        try:self.book.duplicate(self.identities());self.refresh()
        except ValueError as exc:self.message.setText(str(exc))
    def layer(self,front):
        if self.check_source():self.book.reorder(self.identities(),front);self.refresh()
    def find(self):
        obj=self.selected()
        if not obj or not self.check_source():return
        if not self.canvas.go_to(obj['anchors'][0][0]):self.message.setText('Anchor is outside the loaded history; load earlier history or edit its coordinates.')
        prices=[a[1] for a in obj['anchors']];lo,hi=min(prices),max(prices);pad=max((hi-lo)*.2,hi*.0005);self.canvas.price_range=(max(1e-10,lo-pad),hi+pad);self.canvas.update()
    def price(self):
        obj=self.selected()
        if not obj or obj['locked'] or obj['kind']!='Level':return
        value,ok=QInputDialog.getDouble(self,'Local horizontal level','Display price (not an order)',obj['anchors'][0][1],.00000001,1e9,self.canvas.precision)
        if ok and self.check_source():self.book.move(obj['id'],[(obj['anchors'][0][0],value)]);self.refresh()
    def colour(self):
        obj=self.selected()
        if not obj:return
        ids=self.identities();value=QColorDialog.getColor(QColor(style_for(obj)['color']),self,'Local drawing colour')
        if value.isValid() and self.check_source():self.book.modify_many(ids,color=value.name());self.refresh()
    def remove(self):
        if self.check_source():self.book.delete_many(self.identities());self.refresh()
    def undo(self):
        if self.check_source():self.book.undo();self.refresh()
    def redo(self):
        if self.check_source():self.book.redo();self.refresh()
