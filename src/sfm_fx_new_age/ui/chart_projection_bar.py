"""Reachable chart-local display controls; never toggle calculation recipes."""
from PySide6.QtCore import QEvent,QTimer
from PySide6.QtWidgets import QWidget,QHBoxLayout,QLabel,QComboBox,QPushButton,QSizePolicy


class ProjectionBar(QWidget):
    def __init__(self,canvas,details_callback,parent=None):
        super().__init__(parent);self.canvas=canvas;self._disposed=False;self.setObjectName('chartProjectionBar')
        layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(6)
        layout.addWidget(QLabel('Focus:'))
        self.focus=QComboBox();self.focus.setObjectName('chartProjectionFocus');self.focus.setAccessibleName('Public strategy chart focus')
        self.focus.setMinimumContentsLength(10);self.focus.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);self.focus.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.focus.setToolTip('Temporary public-strategy focus on this chart only. Other Project selections remain on. All selected restores every eligible public layer. Source or frame changes clear focus.')
        self.focus.currentIndexChanged.connect(self._focus);layout.addWidget(self.focus,1)
        self.captions=QComboBox();self.captions.setObjectName('chartProjectionCaptions');self.captions.setAccessibleName('Projection caption placement');self.captions.addItems(('Side rail','Overlay','Hidden'))
        self.captions.setToolTip('Side rail keeps level captions outside candles. Hidden removes text only, not geometry. This appearance preference is saved for this source/pair/frame.')
        self.captions.currentTextChanged.connect(lambda value:canvas.set_display({'projection_captions':value}));layout.addWidget(self.captions)
        self.previous=QPushButton('‹');self.previous.setObjectName('chartProjectionPrevious');self.previous.setAccessibleName('Previous caption page');self.previous.setFixedWidth(30)
        self.previous.clicked.connect(lambda:canvas.set_projection_page(canvas.projection_caption_status()['page']-1));layout.addWidget(self.previous)
        self.count=QLabel();self.count.setObjectName('chartProjectionCaptionCount');self.count.setMinimumWidth(112);layout.addWidget(self.count)
        self.next=QPushButton('›');self.next.setObjectName('chartProjectionNext');self.next.setAccessibleName('Next caption page');self.next.setFixedWidth(30)
        self.next.clicked.connect(lambda:canvas.set_projection_page(canvas.projection_caption_status()['page']+1));layout.addWidget(self.next)
        self.details=QPushButton('Projection details');self.details.setObjectName('chartProjectionDetails');self.details.setToolTip('All selected strategies and exact original values, including focused-out and off-screen records');self.details.clicked.connect(details_callback);layout.addWidget(self.details)
        self.chart_only=QPushButton('Chart focus');self.chart_only.setCheckable(True);self.chart_only.setObjectName('chartFocusMode');self.chart_only.setToolTip('Temporarily hide secondary toolbars and hints for more candle space. Source and freshness remain visible; restore tools here. No Project selections change.');layout.addWidget(self.chart_only)
        if parent is not None:self.chart_only.toggled.connect(parent._chart_focus_mode)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.sync)
        canvas.installEventFilter(self);canvas.projectionDisplayChanged.connect(self.schedule);canvas.optionsChanged.connect(self.schedule);canvas.viewChanged.connect(self.schedule);self.sync()

    def schedule(self):
        if self._disposed:return
        if not self.timer.isActive():self.timer.start(0)

    def dispose(self):
        if self._disposed:return
        self._disposed=True;self.timer.stop();self.canvas.removeEventFilter(self)
        for signal in (self.canvas.projectionDisplayChanged,self.canvas.optionsChanged,self.canvas.viewChanged):signal.disconnect(self.schedule)

    def eventFilter(self,watched,event):
        if watched is self.canvas and event.type() in {QEvent.Paint,QEvent.Resize,QEvent.Show}:self.schedule()
        return super().eventFilter(watched,event)

    def _focus(self,index):
        if index>=0:self.canvas.set_projection_focus(self.focus.itemData(index))

    def sync(self):
        if self._disposed:return
        c=self.canvas;c.reconcile_projection_focus();layers=c.public_strategy_layers()
        # Empty/unselected charts keep their original vertical space. The
        # public-specific controls are not useful without a public snapshot.
        self.setVisible(bool(layers))
        choices=[('All selected · '+str(len(layers))+' strategies',None)]+[(v['name']+' · '+v['state'].replace('_',' ').title(),v['strategy_id']) for v in layers]
        if choices!=[(self.focus.itemText(i),self.focus.itemData(i)) for i in range(self.focus.count())]:
            self.focus.blockSignals(True);self.focus.clear()
            for name,key in choices:self.focus.addItem(name,key)
            self.focus.blockSignals(False)
        self.focus.blockSignals(True);self.focus.setCurrentIndex(max(0,self.focus.findData(c.projection_focus)));self.focus.blockSignals(False)
        self.focus.setEnabled(bool(layers));self.focus.setToolTip((self.focus.currentText()+'\n')+'Temporary chart focus only; Project selections and calculations are unchanged. All selected restores eligible public layers.')
        self.captions.blockSignals(True);self.captions.setCurrentText(c.display['projection_captions']);self.captions.blockSignals(False)
        counts=c.projection_caption_status();text=f"{counts['start']}–{counts['end']} / {counts['eligible']} levels" if counts['shown'] else f"0 / {counts['eligible']} captions"
        if self.count.text()!=text:self.count.setText(text)
        self.count.setToolTip('Visible-price captions only. Page order starts nearest the last visible completed close, not a live executable quote. Equal-price identities remain separate. Off-screen and hidden values remain in Projection details.')
        self.previous.setEnabled(counts['page']>0);self.next.setEnabled(counts['page']+1<counts['pages']);self.details.setEnabled(bool(layers))
