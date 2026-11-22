"""User tools open/close inside Tab 2. Internal switchboard is not a UI tool."""
from dataclasses import dataclass
from typing import Callable
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QBrush,QColor
from sfm_fx_new_age.ui.theme import COLORS
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QMdiArea,QMdiSubWindow,QComboBox,QScrollArea
from .calculator import CalculatorWidget


@dataclass(frozen=True)
class ToolDefinition:
    tool_id:str
    title:str
    factory:Callable


class ToolWindow(QMdiSubWindow):
    api=None
    def closeEvent(self,event):
        content=self.widget()
        target=content.widget() if isinstance(content,QScrollArea) else content
        release=getattr(target,'dispose',None)
        if callable(release):release()
        if self.api:self.api.close();self.api=None
        super().closeEvent(event)


class ToolsWorkspace(QWidget):
    def __init__(self,parent=None,definitions=None,api_factory=None):
        super().__init__(parent);self.setObjectName('tradingToolsWorkspace')
        self.api_factory=api_factory
        self._disposing=False
        entries=definitions if definitions is not None else (ToolDefinition('forex-calculator','Forex P/L Calculator',CalculatorWidget),)
        self.definitions={item.tool_id:item for item in entries}
        if len(self.definitions)!=len(entries):raise ValueError('Duplicate tool identity')
        self.windows={};layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(10)
        bar=QHBoxLayout();title=QLabel('Your tools');title.setProperty('role','heading');bar.addWidget(title);bar.addStretch()
        self.picker=QComboBox();self.picker.setObjectName('toolPicker');self.picker.setAccessibleName('Available trading tool')
        for item in entries:self.picker.addItem(item.title,item.tool_id)
        bar.addWidget(self.picker)
        self.open_button=QPushButton('Open tool');self.open_button.setObjectName('openTool');self.open_button.clicked.connect(lambda:self.open_tool(self.picker.currentData()));bar.addWidget(self.open_button)
        self.tile_button=QPushButton('Arrange');self.tile_button.clicked.connect(self.arrange);bar.addWidget(self.tile_button)
        self.close_button=QPushButton('Close all');self.close_button.setObjectName('closeAllTools');self.close_button.clicked.connect(self.close_tools);bar.addWidget(self.close_button)
        layout.addLayout(bar)
        self.area=QMdiArea();self.area.setObjectName('toolContainer');self.area.setBackground(QBrush(QColor(COLORS['bg'])));layout.addWidget(self.area,1)
        self.area.destroyed.connect(lambda _:setattr(self,'_disposing',True))
        self.empty=QLabel('Open a tool above. Its window stays inside this workspace.',self.area.viewport());self.empty.setProperty('role','muted');self.empty.setWordWrap(True);self.empty.setAlignment(Qt.AlignCenter)
        self.area.subWindowActivated.connect(lambda _:self.refresh());self.refresh()

    def open_tool(self,identity):
        definition=self.definitions.get(identity)
        if definition is None:raise ValueError('Unregistered tool')
        existing=self.windows.get(identity)
        if existing is not None:
            if existing.isMinimized():existing.showNormal()
            self.area.setActiveSubWindow(existing);return existing
        frame=ToolWindow();frame.setObjectName('toolWindow_'+identity);frame.setAttribute(Qt.WA_DeleteOnClose)
        frame.setWindowTitle(definition.title);frame.setWindowFlags(Qt.SubWindow|Qt.WindowTitleHint|Qt.WindowMinMaxButtonsHint|Qt.WindowCloseButtonHint)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame)
        frame.api=self.api_factory() if self.api_factory else None
        try:content=definition.factory(frame.api,scroll) if frame.api else definition.factory(scroll)
        except Exception:
            if frame.api:frame.api.close()
            frame.deleteLater();raise
        scroll.setWidget(content);frame.setWidget(scroll);self.area.addSubWindow(frame)
        self.windows[identity]=frame
        frame.destroyed.connect(lambda _:self._removed(identity))
        frame.resize(min(680,max(430,self.area.width()-16)),min(520,max(280,self.area.height()-16)));frame.move(8,8)
        initial_size=frame.size()
        def settle_initial_geometry():
            # Cross-workspace navigation opens the tool in the same event as
            # the main-tab switch. Its container may still have hidden-tab
            # geometry; resize once after layout, never over a manual resize.
            if self.windows.get(identity) is frame and frame.size()==initial_size and frame.pos().x()==8 and frame.pos().y()==8:
                frame.resize(min(680,max(430,self.area.viewport().width()-16)),min(520,max(280,self.area.viewport().height()-16)))
        QTimer.singleShot(0,self,settle_initial_geometry)
        self.empty.hide();frame.show();self.refresh();return frame

    def _removed(self,identity):
        self.windows.pop(identity,None)
        if not self._disposing:self.refresh()
    def arrange(self):self.area.tileSubWindows()
    def close_tools(self):self.area.closeAllSubWindows();self.refresh()
    def refresh(self):
        if self._disposing:return
        active=self.area.subWindowList()
        self.empty.setVisible(not active);self.close_button.setEnabled(bool(active));self.tile_button.setEnabled(len(active)>1)
        self.empty.setGeometry(20,20,max(0,self.area.viewport().width()-40),max(0,self.area.viewport().height()-40))
    def resizeEvent(self,event):super().resizeEvent(event);self.refresh()
    def dispose(self):self._disposing=True;self.close_tools()
