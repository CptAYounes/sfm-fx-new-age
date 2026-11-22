"""Transactional local-object properties and reusable per-tool appearance controls."""
from copy import deepcopy
from PySide6.QtCore import Qt,QTimer,QDateTime,QTimeZone,QDate
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QCheckBox,QComboBox,
 QDoubleSpinBox,QSpinBox,QTextEdit,QTabWidget,QWidget,QDialogButtonBox,QPushButton,QColorDialog,QDateTimeEdit,QScrollArea)
from PySide6.QtGui import QColor
from sfm_fx_new_age.contracts.chart_display import style_for,validate_style,validate_display,OBJECT_STYLE,KINDS


class ColorButton(QPushButton):
    def __init__(self,value,parent=None):
        super().__init__(parent);self.value=value;self.set_value(value);self.clicked.connect(self.choose)
    def set_value(self,value):
        self.value=value;self.setText(value);self.setToolTip('Choose an RGB colour');self.setStyleSheet('border-left: 12px solid '+value+';')
    def choose(self):
        c=QColorDialog.getColor(QColor(self.value),self,'Display colour')
        if c.isValid():self.set_value(c.name())


def scroll_form(tabs,title):
    page=QWidget();form=QFormLayout(page);form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);tabs.addTab(scroll,title)
    return form


class StyleControls:
    """Shared controls, not another drawing model or persistence owner."""
    def build_style(self,tabs,kind,style):
        self.fields={};self.initial_style=deepcopy(style)
        f=scroll_form(tabs,'Appearance')
        self.color=ColorButton(style['color']);self.color.setObjectName('objectStrokeColour');f.addRow('Line / outline colour',self.color)
        self.linked_colours={}
        for key,label,follow in (('fill_color','Fill colour','Follow outline'),('text_color','Text / label colour','Follow outline'),('label_background','Label background','Follow chart background')):
            row=QHBoxLayout();linked=QCheckBox(follow);linked.setChecked(style[key] is None);field=ColorButton(style[key] or (self.canvas.display['background'] if key=='label_background' else style['color']))
            linked.setObjectName('objectLinked_'+key);field.setObjectName('objectColour_'+key);field.setEnabled(not linked.isChecked());linked.toggled.connect(lambda checked,field=field:field.setEnabled(not checked));row.addWidget(linked);row.addWidget(field,1);f.addRow(label,row);self.linked_colours[key]=(linked,field)
            if key=='fill_color':linked.setEnabled(kind in {'Rectangle','Ellipse','Triangle'});field.setEnabled(not linked.isChecked() and linked.isEnabled())
        self.width=QDoubleSpinBox();self.width.setRange(.5,6);self.width.setSingleStep(.5);self.width.setValue(style['width']);f.addRow('Line width',self.width)
        self.line=QComboBox();self.line.addItems(('Solid','Dash','Dot','Dash dot'));self.line.setCurrentText(style['line_style']);f.addRow('Line style',self.line)
        self.opacity=QDoubleSpinBox();self.opacity.setRange(0,80);self.opacity.setSuffix(' %');self.opacity.setValue(style['opacity']);f.addRow('Fill opacity',self.opacity)
        self.opacity.setEnabled(kind in {'Rectangle','Ellipse','Triangle'})
        for key,label in (('fill','Fill shape'),('show_label','Show label / text'),('show_prices','Show Fibonacci prices'),('extend_left','Extend left'),('extend_right','Extend right'),('show_angle','Show view angle (changes with zoom)')):
            field=QCheckBox(label);field.setChecked(style[key]);self.fields[key]=field;f.addRow(field)
            if key=='fill':field.setEnabled(kind in {'Rectangle','Ellipse','Triangle'})
            if key=='show_prices':field.setEnabled(kind=='Fibonacci')
            if key in {'extend_left','extend_right'}:field.setEnabled(kind in {'Trend','Ray','Fibonacci'})
            if key=='show_angle':field.setEnabled(kind in {'Trend','Ray'})
        self.snap=QComboBox();self.snap.addItems(('Inherit','Nearby','Always','Off'));self.snap.setCurrentText(style['snap']);f.addRow('This tool’s snapping',self.snap)
        self.snap.setToolTip('Inherit uses chart settings. Shift or Alt temporarily disables price snapping; only observed candles can supply OHLC snaps.')
        t=scroll_form(tabs,'Text / Fibonacci')
        self.text=QTextEdit();self.text.setAcceptRichText(False);self.text.setPlainText(style['text']);self.text.setMaximumHeight(120);self.text.setEnabled(kind=='Text');t.addRow('Plain text note',self.text)
        self.font_size=QDoubleSpinBox();self.font_size.setRange(8,28);self.font_size.setValue(style['font_size']);t.addRow('Label / text size',self.font_size)
        self.bold=QCheckBox('Bold labels / text');self.bold.setChecked(style['bold']);t.addRow(self.bold)
        self.fib=QLineEdit(', '.join(f'{r*100:.12g}' for r in style['fib_levels']));self.fib.setEnabled(kind=='Fibonacci');self.fib_initial=self.fib.text()
        self.fib.setToolTip('1–16 unique percentages, -500 to 1000; analytical display only');t.addRow('Fibonacci levels (%)',self.fib)
        self.numeric_initial={k:getattr(self,k).value() for k in ('width','opacity','font_size')}
        if kind=='Fibonacci':
            row=QHBoxLayout()
            for title,values in (('Retracement','0, 23.6, 38.2, 50, 61.8, 78.6, 100'),('With extensions','-27.2, 0, 38.2, 50, 61.8, 100, 127.2, 161.8, 261.8')):
                b=QPushButton(title);b.clicked.connect(lambda checked=False,v=values:self.fib.setText(v));row.addWidget(b)
            t.addRow(row)
    def style_values(self):
        values=dict(color=self.color.value,width=self.width.value(),line_style=self.line.currentText(),opacity=self.opacity.value(),
            text=self.text.toPlainText(),font_size=self.font_size.value(),bold=self.bold.isChecked(),snap=self.snap.currentText(),**{k:f.isChecked() for k,f in self.fields.items()})
        values['fib_levels']=deepcopy(self.initial_style['fib_levels']) if self.fib.text()==self.fib_initial else [float(v.strip())/100 for v in self.fib.text().split(',')]
        values.update({key:None if linked.isChecked() else field.value for key,(linked,field) in self.linked_colours.items()})
        for k,initial in self.numeric_initial.items():
            if getattr(self,k).value()==initial:values[k]=self.initial_style[k]
        return validate_style(values)


class ObjectProperties(QDialog,StyleControls):
    def __init__(self,canvas,identity,parent=None):
        super().__init__(parent if parent is not None else canvas);self.canvas=canvas;self.book=canvas.drawings;self.source=canvas.data_identity;self.identity=identity
        self.setObjectName('chartObjectProperties');self.setWindowTitle('Local object properties');self.resize(540,510)
        obj=self.book.get(identity)
        if obj is None:raise ValueError('The local object no longer exists')
        self.original=deepcopy(obj);style=style_for(obj);self.anchor_fields=[];self.anchor_initial=[]
        outer=QVBoxLayout(self);notice=QLabel('Local annotation · '+obj['kind']+' · no broker order changes. Apply saves; Cancel discards only unapplied edits.');notice.setWordWrap(True);outer.addWidget(notice)
        self.name=QLineEdit(style['name']);self.name.setMaxLength(80);self.name.setPlaceholderText('Object name');outer.addWidget(self.name)
        tabs=QTabWidget();outer.addWidget(tabs,1);self.build_style(tabs,obj['kind'],style)
        g=scroll_form(tabs,'Coordinates · UTC')
        note=QLabel('Exact UTC / price coordinates. Unchanged fields retain their original precision. Unlock the object to edit coordinates.');note.setWordWrap(True);g.addRow(note)
        for n,(stamp,price) in enumerate(obj['anchors']):
            row=QHBoxLayout();time=QDateTimeEdit();time.setTimeZone(QTimeZone(b'UTC'));time.setDisplayFormat('yyyy-MM-dd HH:mm:ss.zzz');time.setCalendarPopup(True)
            time.setDateRange(QDate(1,1,1),QDate(9999,12,31));time.setDateTime(QDateTime.fromString(stamp,Qt.ISODateWithMs));time.setEnabled(not obj['locked'])
            value=QDoubleSpinBox();value.setDecimals(10);value.setRange(1e-10,1e10);value.setValue(price);value.setSingleStep(.01 if canvas.precision==3 else .0001);value.setEnabled(not obj['locked'])
            row.addWidget(time,2);row.addWidget(value,1);g.addRow('Anchor '+str(n+1),row);self.anchor_fields.append((time,value));self.anchor_initial.append((time.dateTime().toMSecsSinceEpoch(),value.value()))
        self.as_default=QCheckBox('Use this appearance for future '+obj['kind']+' objects');outer.addWidget(self.as_default)
        self.error=QLabel();self.error.setWordWrap(True);outer.addWidget(self.error)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Apply|QDialogButtonBox.Cancel);buttons.accepted.connect(self.ok);buttons.rejected.connect(self.reject);buttons.button(QDialogButtonBox.Apply).clicked.connect(self.apply);outer.addWidget(buttons)
        self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self.check_source);self.finished.connect(self.timer.stop);self.timer.start()
    def check_source(self):
        valid=self.canvas.data_identity==self.source and self.canvas.drawings is self.book and self.book.get(self.identity) is not None
        if not valid:self.reject()
        return valid
    def apply(self):
        if not self.check_source():return False
        try:
            obj=self.book.get(self.identity)
            if obj!=self.original:raise ValueError('This object changed in another edit. Close and reopen Properties to reload it; your edits were not applied.')
            values=self.style_values()|{'name':self.name.text()};validate_style(values)
            anchors=[]
            for (t,v),initial,old in zip(self.anchor_fields,self.anchor_initial,self.original['anchors']):
                stamp=old[0] if t.dateTime().toMSecsSinceEpoch()==initial[0] else t.dateTime().toUTC().toString(Qt.ISODateWithMs)
                price=old[1] if v.value()==initial[1] else v.value();anchors.append((stamp,price))
            if obj['locked']:anchors=obj['anchors']
            defaults=None
            if self.as_default.isChecked():
                defaults=deepcopy(self.canvas.display['drawing_defaults']);defaults[obj['kind']]={k:v for k,v in values.items() if k!='name'};validate_display({'drawing_defaults':defaults})
            self.book.replace(self.identity,anchors,values)
            self.original=deepcopy(obj)
            for i,(t,v) in enumerate(self.anchor_fields):self.anchor_initial[i]=(t.dateTime().toMSecsSinceEpoch(),v.value())
            if defaults is not None:self.canvas.set_display({'drawing_defaults':defaults})
            self.error.setText('Applied locally · no broker instruction');return True
        except (ValueError,TypeError) as exc:self.error.setText(str(exc));return False
    def ok(self):
        if self.apply():self.accept()


class DrawingDefaults(QDialog,StyleControls):
    """Edit future drawing appearance without creating a sacrificial object."""
    def __init__(self,canvas,parent=None):
        super().__init__(parent if parent is not None else canvas);self.canvas=canvas;self.source=canvas.data_identity;self.staged=deepcopy(canvas.display['drawing_defaults'])
        self.base_defaults=deepcopy(canvas.display['drawing_defaults']);self.setObjectName('chartDrawingDefaults');self.setWindowTitle('Drawing defaults');self.resize(530,500)
        outer=QVBoxLayout(self);notice=QLabel('Future local drawings only. Existing objects, coordinates and broker data are unchanged. Apply saves all staged tool styles.');notice.setWordWrap(True);outer.addWidget(notice)
        self.kind=QComboBox();self.kind.addItems(KINDS);outer.addWidget(self.kind);self.tabs=QTabWidget();outer.addWidget(self.tabs,1)
        self.error=QLabel();self.error.setWordWrap(True);outer.addWidget(self.error)
        reset=QPushButton('Reset this tool style');reset.clicked.connect(self.reset);outer.addWidget(reset)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Apply|QDialogButtonBox.Cancel);buttons.accepted.connect(self.ok);buttons.rejected.connect(self.reject);buttons.button(QDialogButtonBox.Apply).clicked.connect(self.apply);outer.addWidget(buttons)
        self.previous=None;self.load_kind();self.kind.currentTextChanged.connect(self.change_kind)
        self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self.check_source);self.finished.connect(self.timer.stop);self.timer.start()
    def check_source(self):
        if self.canvas.data_identity!=self.source:self.reject();return False
        return True
    def load_kind(self):
        while self.tabs.count():
            w=self.tabs.widget(0);self.tabs.removeTab(0);w.deleteLater()
        self.previous=self.kind.currentText();self.build_style(self.tabs,self.previous,deepcopy(OBJECT_STYLE)|self.staged.get(self.previous,{}))
    def change_kind(self,kind):
        try:self.staged[self.previous]=self.style_values()
        except (ValueError,TypeError) as exc:
            self.kind.blockSignals(True);self.kind.setCurrentText(self.previous);self.kind.blockSignals(False);self.error.setText(str(exc));return
        self.load_kind();self.error.clear()
    def reset(self):
        self.staged.pop(self.previous,None);self.load_kind();self.error.setText('Default staged for this tool; Apply to save.')
    def apply(self):
        if not self.check_source():return False
        try:
            if self.canvas.display['drawing_defaults']!=self.base_defaults:raise ValueError('Drawing defaults changed elsewhere. Close and reopen this editor to reload them.')
            self.staged[self.previous]=self.style_values();self.canvas.set_display({'drawing_defaults':deepcopy(self.staged)});self.base_defaults=deepcopy(self.staged);self.error.setText('Future drawing defaults applied locally');return True
        except (ValueError,TypeError) as exc:self.error.setText(str(exc));return False
    def ok(self):
        if self.apply():self.accept()


class BulkAppearance(QDialog):
    """Opt-in shared style fields; never overwrite names, geometry or flags."""
    def __init__(self,canvas,identities,parent=None):
        super().__init__(parent if parent is not None else canvas);self.canvas=canvas;self.book=canvas.drawings;self.source=canvas.data_identity
        self.identities=list(identities);self.original={i:deepcopy(self.book.get(i)) for i in identities};self.fields={};self.enabled={}
        self.setObjectName('chartBulkAppearance');self.setWindowTitle('Style selected objects');self.resize(500,440)
        outer=QVBoxLayout(self);notice=QLabel('Only checked settings are applied to '+str(len(identities))+' local objects. Coordinates, names, lock and visibility are preserved.');notice.setWordWrap(True);outer.addWidget(notice)
        tabs=QTabWidget();outer.addWidget(tabs,1);form=scroll_form(tabs,'Shared appearance');style=style_for(next(iter(self.original.values()),{}))
        for key,label in (('color','Line / outline colour'),('fill_color','Fill colour'),('text_color','Text / label colour'),('label_background','Label background'),('width','Line width'),('line_style','Line style'),('fill','Fill shapes'),('opacity','Fill opacity (%)'),('font_size','Label size'),('bold','Bold labels'),('show_label','Show labels'),('snap','Price snapping')):
            use=QCheckBox(label);self.enabled[key]=use
            if key=='color' or key.endswith('_color') or key=='label_background':field=ColorButton(style[key] or (canvas.display['background'] if key=='label_background' else style['color']))
            elif key in {'fill','bold','show_label'}:field=QComboBox();field.addItems(('Off','On'));field.setCurrentText('On' if style[key] else 'Off')
            elif key in {'line_style','snap'}:
                field=QComboBox();field.addItems(('Solid','Dash','Dot','Dash dot') if key=='line_style' else ('Inherit','Nearby','Always','Off'));field.setCurrentText(style[key])
            else:
                field=QDoubleSpinBox();field.setRange(*{'width':(.5,6),'opacity':(0,80),'font_size':(8,28)}[key]);field.setSingleStep(.5 if key=='width' else 1);field.setValue(style[key])
            field.setEnabled(False);use.toggled.connect(field.setEnabled);self.fields[key]=field;form.addRow(use,field)
        self.error=QLabel();self.error.setWordWrap(True);outer.addWidget(self.error)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);b.accepted.connect(self.ok);b.rejected.connect(self.reject);outer.addWidget(b)
        self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self.check_source);self.finished.connect(self.timer.stop);self.timer.start()
    def check_source(self):
        valid=self.canvas.data_identity==self.source and self.canvas.drawings is self.book and all(self.book.get(i) for i in self.identities)
        if not valid:self.reject()
        return valid
    def apply(self):
        if not self.check_source():return False
        try:
            if any(self.book.get(i)!=o for i,o in self.original.items()):raise ValueError('A selected object changed. Close and reopen the style editor; nothing was applied.')
            values={k:f.value if isinstance(f,ColorButton) else f.currentText()=='On' if k in {'fill','bold','show_label'} else f.currentText() if isinstance(f,QComboBox) else f.value() for k,f in self.fields.items() if self.enabled[k].isChecked()}
            if not values:self.error.setText('Check at least one setting to apply.');return False
            validate_style(values);self.book.modify_many(self.identities,**values);self.original={i:deepcopy(self.book.get(i)) for i in self.identities};return True
        except (ValueError,TypeError) as exc:self.error.setText(str(exc));return False
    def ok(self):
        if self.apply():self.accept()
