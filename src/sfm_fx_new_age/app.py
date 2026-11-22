from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QCheckBox, QComboBox, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QPushButton, QScrollArea, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QSizePolicy, QTabBar,
)


from .contracts.models import thaw
from .core.runtime import ApplicationRuntime
from .core.tab_api import TabApi
from .tabs.loader import load_tab_plugins
from .tabs.tab2.workspace import ToolsWorkspace,ToolDefinition
from .ui.theme import COLORS, apply_theme
from .ui.navigation import MainTabDeck
from .ui.scanner_overview import ScannerOverview
from .ui.chart_workspace import ChartPanel,CHART_LABELS
from .ui.feed_connection import FeedCard,FeedDialog
from .contracts.domain import PAIRS,FRAMES
from .ui_model import SubtabViewModel, build_ui_model


def label(text: str, role: str = 'muted') -> QLabel:
    widget = QLabel(text)
    widget.setProperty('role', role)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.PlainText)
    return widget


class BrandMark(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(32, 32)

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(COLORS['panel']))
        painter.setPen(QPen(QColor(COLORS['line']), 1))
        painter.drawRoundedRect(1, 1, 30, 30, 8, 8)
        painter.setPen(QPen(QColor(COLORS['blue']), 2.5))
        points = [(5, 24), (12, 18), (17, 22), (24, 8), (28, 12)]
        for a, b in zip(points, points[1:]):
            painter.drawLine(*a, *b)


class SubtabPanel(QWidget):
    """Shared functioning snapshot view, replaced through a tab plugin as features grow."""
    def __init__(self, api: TabApi, model: SubtabViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api, self.model = api, model
        self.setObjectName(f"subtab_{model.subtab_id.replace('.', '_')}")
        self._fingerprint: str | None = None
        self._rows: list[dict[str, Any]] = []
        self._ack_selection=None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        title_row = QHBoxLayout()
        title = label(model.title, 'heading')
        title.setObjectName('subtabTitle')
        title_row.addWidget(title, 1)
        self.state = label('NO DATA', 'status')
        self.state.setObjectName('viewStatus')
        title_row.addWidget(self.state)
        layout.addLayout(title_row)
        layout.addWidget(label('Select a pair to use across all views.' if model.subtab_id == '1.1' else model.purpose))
        card = QFrame()
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        self.origin = label('NO SOURCE', 'caption')
        self.origin.setObjectName('dataOrigin')
        card_layout.addWidget(self.origin)
        self.table = QTableWidget()
        self.table.setObjectName('snapshotTable')
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(60 if model.subtab_id == '4.1' else 100)
        # Let the page shrink the table before scrolling its own actions away.
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        card_layout.addWidget(self.table, 1)
        self.empty = label('No source connected. Values are not fabricated.')
        self.empty.setObjectName('emptyState')
        card_layout.addWidget(self.empty)
        layout.addWidget(card, 1)
        self.buttons: dict[str, QPushButton] = {}
        if model.subtab_id=='4.1':
            review=QPushButton('Review signal / Show on Chart');review.setObjectName('queueReviewSignal');review.clicked.connect(self._review_selected);layout.addWidget(review)
        if model.subtab_id == '4.1':
            self.acknowledge = QCheckBox('I acknowledge that this proposal is RESEARCH_ONLY, not a validated success probability')
            self.acknowledge.setObjectName('researchAcknowledgement')
            self.acknowledge.stateChanged.connect(self._update_actions)
            layout.addWidget(self.acknowledge)
            commands = [('ISSUE', 'Issue'), ('CANCEL_SIGNAL', 'Cancel signal'), ('CANCEL_ALL_UNISSUED', 'Cancel all unissued')]
            row = QHBoxLayout()
            for name, text in commands:
                button = QPushButton(text)
                button.setObjectName(f"command_4_1_{name.lower()}")
                if name == 'ISSUE':
                    button.setProperty('role', 'primary')
                button.clicked.connect(lambda checked=False, command=name: self._dispatch(command))
                self.buttons[name] = button
                row.addWidget(button)
            row.addStretch(1)
            layout.addLayout(row)
        self.result_label = label('')
        self.result_label.setObjectName('commandResult')
        self.result_label.hide()
        layout.addWidget(self.result_label)
        self.contract = label(f"{model.subtab_id}  ·  {model.backend_owner}  ·  Tab API v{api.version}", 'caption')
        self.contract.setObjectName('subtabContract')
        self.setToolTip(self.contract.text())
        self.contract.hide()
        layout.addWidget(self.contract)
        self._update_actions()
        # Read only the visible domain, not all 42 views on startup.

    def _selection_changed(self) -> None:
        self._reset_ack()
        self._update_actions()
        selected = self._selection()
        if self.model.subtab_id == '1.1' and selected:
            self.api.command('1.1', 'SELECT_PAIR', {'symbol': selected['symbol']})
            self.refresh()

    def _reset_ack(self):
        from sfm_fx_new_age.contracts.analytics import digest
        signature=digest(self._selection())
        if signature!=self._ack_selection:
            self._ack_selection=signature
            if hasattr(self,'acknowledge'):self.acknowledge.setChecked(False)

    def inspection_context(self):
        from .ui.inspection_panels import row_context
        return row_context(self.api,self._selection()) if self._selection() else None

    def apply_inspection(self,context):
        self.api.validate_inspection(context);self.refresh()
        for i,row in enumerate(self._rows):
            if row.get('signal_id')==context.get('object_id'):self.table.selectRow(i);break

    def _review_selected(self):
        try:
            context=self.inspection_context()
            if context:self.api.navigate('4.2',context)
        except ValueError as exc:self.result_label.setText(str(exc));self.result_label.show()

    def _selection(self) -> dict[str, Any] | None:
        row = self.table.currentRow()
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def _update_actions(self) -> None:
        if not self.buttons:
            return
        selected = self._selection()
        queued = bool(selected and selected.get('state') == 'QUEUED')
        acknowledged = bool(selected and (selected.get('profile') != 'RESEARCH_ONLY' or self.acknowledge.isChecked()))
        self.buttons['ISSUE'].setEnabled(queued and acknowledged)
        self.buttons['ISSUE'].setToolTip('Select a queued signal and acknowledge its research label. Broker preflight runs on Issue.')
        self.buttons['CANCEL_SIGNAL'].setEnabled(queued)
        self.buttons['CANCEL_ALL_UNISSUED'].setEnabled(any(row.get('state') == 'QUEUED' for row in self._rows))

    def _dispatch(self, command_name: str) -> None:
        selected = self._selection()
        payload: dict[str, Any] = {}
        if selected and command_name in {'ISSUE', 'CANCEL_SIGNAL'}:
            payload['signal_id'] = selected.get('signal_id')
        if command_name == 'ISSUE':
            payload['user_initiated'] = True
            payload['revision'] = (selected or {}).get('revision')
            payload['acknowledge_research'] = self.acknowledge.isChecked()
        result = self.api.command(self.model.subtab_id, command_name, payload)
        self.result_label.setText(f'{result.status.value}: {result.message}')
        self.result_label.show()
        self.refresh()

    def refresh(self) -> None:
        snapshot = self.api.snapshot(self.model.subtab_id)
        data = thaw(snapshot.data)
        rows = data.get('rows', [])
        fingerprint = json.dumps([snapshot.status, data], sort_keys=True, default=str)
        if fingerprint == self._fingerprint:
            return
        selected = self._selection()
        identity_key = 'symbol' if self.model.subtab_id == '1.1' else 'signal_id'
        selected_id = None if self.model.subtab_id == '1.1' else (selected or {}).get(identity_key)
        self._fingerprint = fingerprint
        self.state.setText('PAIR SELECTOR' if self.model.subtab_id == '1.1' else snapshot.status.replace('_', ' '))
        context = data.get('context', {})
        atr = context.get('w1_atr14')
        source_label = 'No market source' if data['origin'] == 'NO_SOURCE' else data['origin']
        self.origin.setText(f"{source_label}  ·  {data['symbol']}" + (f'  ·  COMPLETED W1 ATR(14): {atr}' if atr else ''))
        self.table.blockSignals(True)
        self._rows = rows
        columns = list(dict.fromkeys(key for row in rows for key in row))
        preferred = ['symbol', 'signal_id', 'side', 'entry_price', 'units', 'state', 'origin', 'broker_order_id']
        columns = [key for key in preferred if key in columns] + [key for key in columns if key not in preferred]
        if self.model.subtab_id == '4.1':
            columns = [key for key in ('symbol', 'signal_id', 'side', 'entry_price', 'units', 'state') if key in columns]
        self.table.setColumnCount(len(columns))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels([key.replace('_', ' ').upper() for key in columns])
        for i, row in enumerate(rows):
            for j, key in enumerate(columns):
                value = row.get(key)
                text = ('Active' if value else '—') if self.model.subtab_id == '1.1' and key == 'selected' else (
                    '—' if value is None else json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value))
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self.table.setItem(i, j, item)
        self.table.resizeColumnsToContents()
        for j in range(len(columns)):
            if self.model.subtab_id == '4.1':
                self.table.setColumnWidth(j, 180 if columns[j] == 'signal_id' else 100)
            else:
                self.table.setColumnWidth(j, min(260, max(110, self.table.columnWidth(j))))
        if self.model.subtab_id == '1.1':
            self.table.setMinimumHeight(self.table.horizontalHeader().sizeHint().height() + sum(self.table.rowHeight(i) for i in range(len(rows))) + 4)
        if selected_id:
            for i, row in enumerate(rows):
                if row.get(identity_key) == selected_id:
                    self.table.selectRow(i)
                    break
        elif self.model.subtab_id == '1.1':
            for i, row in enumerate(rows):
                if row.get('selected'):
                    self.table.selectRow(i)
                    break
        self.table.blockSignals(False)
        self.empty.setVisible(not rows)
        self.empty.setText('Feature not implemented at this checkpoint.' if snapshot.status == 'NOT_AVAILABLE'
                           else 'No source data available. The application does not invent market or broker values.')
        self._reset_ack();self._update_actions()


class MainWindow(QMainWindow):
    def __init__(self, runtime: ApplicationRuntime | None = None) -> None:
        super().__init__()
        self._owns_runtime = runtime is None
        self.runtime = runtime or ApplicationRuntime()
        self._dirty=set(d.subtab_id for d in self.runtime.definitions);self._navigation_history=[];self._navigation_events=[];self._visible_key=None
        self._last_clock_refresh=0
        apply_theme(QApplication.instance())
        self.setObjectName('sfmFxNewAgeMainWindow')
        self.setWindowTitle('SFM FX New Age Engine')
        from importlib.resources import files
        self.setWindowIcon(QIcon(str(files('sfm_fx_new_age.resources').joinpath('sfm-logo.png'))))
        self.resize(1440, 900)
        self.setMinimumSize(960, 640)
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(16, 12, 16, 6)
        layout.setSpacing(12)
        header = QHBoxLayout()
        header.addWidget(BrandMark())
        brand = QLabel('SFM FX New Age Engine')
        brand.setObjectName('brand')
        header.addWidget(brand)
        header.addStretch(1)
        self.feed_card=FeedCard(self)
        self.session_label,self.account_label=self.feed_card.status,self.feed_card.account
        self.feed_dialog=None
        self.feed_card.requested.connect(self.open_feed)
        header.addWidget(self.feed_card)
        layout.addLayout(header)
        self.return_button=QPushButton('← Return');self.return_button.setObjectName('returnInspection');self.return_button.setEnabled(False)
        self.return_button.clicked.connect(self._return_inspection);header.insertWidget(2,self.return_button)
        self.inspection_label=label('Inspection navigation · no execution authority','caption');self.inspection_label.setObjectName('inspectionNavigation');self.inspection_label.hide()
        self.inspection_label.setWordWrap(True);layout.addWidget(self.inspection_label)

        toolbar = QWidget()
        self.view_toolbar = toolbar
        toolbar.setObjectName('subtabNavigation')
        jump_row = QHBoxLayout(toolbar)
        jump_row.setContentsMargins(4, 0, 4, 0)
        caption = label('VIEW', 'caption')
        jump_row.addWidget(caption)
        self.subtab_picker = QComboBox()
        self.subtab_picker.setObjectName('subtabPicker')
        self.subtab_picker.setAccessibleName('Subtab navigation')
        self.subtab_picker.setMinimumWidth(260)
        self.subtab_picker.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.subtab_picker.setToolTip('Choose a view in the current section. Focus: Ctrl+K')
        caption.setBuddy(self.subtab_picker)
        self.subtab_picker.currentIndexChanged.connect(self._jump_subtab)
        jump_row.addWidget(self.subtab_picker, 1)
        self.view_position = label('', 'caption')
        self.view_position.setMinimumWidth(80)
        jump_row.addWidget(self.view_position)
        self.previous_view = QPushButton('Previous')
        self.next_view = QPushButton('Next')
        self.previous_view.setAccessibleName('Previous subtab')
        self.next_view.setAccessibleName('Next subtab')
        self.previous_view.clicked.connect(lambda: self._move_subtab(-1))
        self.next_view.clicked.connect(lambda: self._move_subtab(1))
        jump_row.addWidget(self.previous_view)
        jump_row.addWidget(self.next_view)
        self.main_tabs = MainTabDeck(toolbar)
        self.chart_tabs=QTabBar()
        self.chart_tabs.setObjectName('pairChartSubtabs');self.chart_tabs.setAccessibleName('Views for the selected forex pair')
        self.chart_tabs.setExpanding(True);self.chart_tabs.setUsesScrollButtons(True)
        self.chart_tabs.setElideMode(Qt.ElideNone)
        for title in CHART_LABELS:self.chart_tabs.addTab(title)
        self.chart_tabs.currentChanged.connect(self._chart_changed)
        self.main_tabs.layout().insertWidget(2,self.chart_tabs)
        self._pair_views={pair:0 for pair in PAIRS}
        self.main_tabs.setObjectName('mainTabs')
        self.tab_plugins = load_tab_plugins()
        self.tab_apis = {}
        for tab_model in build_ui_model(self.runtime):
            api = self.runtime.api(tab_model.tab_id)
            self.tab_apis[tab_model.tab_id] = api
            for definition in api.definitions:
                api.subscribe(definition.subtab_id,lambda event,identity=definition.subtab_id:self._changed(identity,event))
            if tab_model.tab_id == 2:
                definitions=tuple(ToolDefinition(t.tool_id,t.title,t.factory) for t in self.tab_plugins[2].tools.values())
                self.tools = ToolsWorkspace(definitions=definitions,api_factory=lambda:self.runtime.api(2))
                self.main_tabs.addTab(self.tools,tab_model.title)
                continue # The ten 2.* contracts stay internal, not rendered as user pages.
            nested = QTabWidget()
            nested.setObjectName(f'mainTab_{tab_model.tab_id}_subtabs')
            nested.setDocumentMode(True)
            nested.setUsesScrollButtons(True)
            nested.setElideMode(Qt.ElideNone)
            for subtab in tab_model.subtabs:
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                panel = self.tab_plugins[tab_model.tab_id].create_widget(api, subtab, scroll)
                if panel is None:
                    panel = ChartPanel(api,subtab,scroll) if tab_model.tab_id==1 else ScannerOverview(api, subtab, scroll) if subtab.subtab_id == '2.2' else SubtabPanel(api, subtab, scroll)
                if isinstance(panel,ChartPanel):
                    panel.connectRequested.connect(self.open_feed)
                    panel.frameRequested.connect(lambda frame:self.chart_tabs.setCurrentIndex({'W1':1,'D1':2,'H4':3,'H1':4}[frame]))
                if hasattr(panel,'signalsRequested'):panel.signalsRequested.connect(self._show_strategy_signals)
                scroll.setWidget(panel)
                nested.addTab(scroll, subtab.title.replace('&', '&&'))
                nested.setTabToolTip(nested.count() - 1, subtab.title)
            nested.currentChanged.connect(self.refresh_current)
            nested.tabBar().hide()
            if tab_model.tab_id==1:
                for i in range(nested.count()):self.chart_tabs.setTabToolTip(i,nested.tabText(i).replace('&&','&'))
            self.main_tabs.addTab(nested, tab_model.title.replace('&', '&&'))
        self.main_tabs.currentChanged.connect(self.refresh_current)
        layout.addWidget(self.main_tabs, 1)
        self.setCentralWidget(outer)
        self._shortcuts = []
        for index in range(4):
            shortcut = QShortcut(QKeySequence(f'Ctrl+{index+1}'), self)
            shortcut.activated.connect(lambda index=index: self.main_tabs.setCurrentIndex(index))
            self._shortcuts.append(shortcut)
        shortcut = QShortcut(QKeySequence('Ctrl+K'), self)
        shortcut.activated.connect(self.subtab_picker.setFocus)
        self._shortcuts.append(shortcut)
        self.main_tabs.tabBar().setToolTip('Main sections · Ctrl+1 through Ctrl+4')
        self.core_timer = QTimer(self)
        self.core_timer.setInterval(50)
        self.core_timer.timeout.connect(self.runtime.pump)
        self.core_timer.start()
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(500)
        self.poll_timer.timeout.connect(self.refresh_current)
        self.poll_timer.start()
        self.refresh_current()
        QTimer.singleShot(0,self._resume_connection)

    def _resume_connection(self):
        if not self.runtime.closed and not self.runtime.fixture_mode:self.runtime.connector.resume_saved_session()

    def _changed(self,identity,event):
        self._dirty.add(identity)
        if identity=='1.1' and event.topic=='UI.NAVIGATE':
            self._navigation_events.append(thaw(event.payload));QTimer.singleShot(0,self._drain_navigation)

    def _drain_navigation(self):
        for event in self._navigation_events[:]:
            self._navigation_events.remove(event);self._navigate(event['target'],event['context'])

    def _active_panel(self):
        nested=self.main_tabs.currentWidget()
        if isinstance(nested,ToolsWorkspace):return None
        scroll=nested.currentWidget() if nested else None
        return scroll.widget() if isinstance(scroll,QScrollArea) else None

    def _show_strategy_signals(self,symbol,frame):
        # View coordinates are not a source inspection or execution authority.
        if symbol not in PAIRS or frame not in FRAMES:raise ValueError('Known research view coordinates required')
        nested=self.main_tabs.widget(3)
        index=next(i for i in range(nested.count()) if nested.widget(i).widget().model.subtab_id=='4.1')
        workspace=nested.widget(index).widget();panel=workspace.research_signals
        panel.context=None;panel.pair.setCurrentText(symbol);panel.frame.setCurrentText(frame)
        workspace.pages.setCurrentIndex(0);self.main_tabs.setCurrentIndex(3);nested.setCurrentIndex(index)
        self.inspection_label.hide();self.refresh_current(force=True)

    def _navigate(self,target,context,remember=True):
        try:
            self.tab_apis[1].validate_inspection(context)
            if remember:
                source=self._active_panel();previous=getattr(source,'inspection_context',lambda:None)()
                self._navigation_history.append((source.model.subtab_id if source else 'calculator',previous));self._navigation_history=self._navigation_history[-32:]
            if target=='calculator':
                self.main_tabs.setCurrentIndex(1);window=self.tools.open_tool('forex-calculator');window.widget().widget().apply_inspection(context)
            else:
                tab=int(target.split('.')[0]);nested=self.main_tabs.widget(tab-1)
                index=next(i for i in range(nested.count()) if nested.widget(i).widget().model.subtab_id==target)
                self.main_tabs.setCurrentIndex(tab-1);nested.setCurrentIndex(index);nested.widget(index).widget().apply_inspection(context)
            self.inspection_label.hide()
            self.return_button.setEnabled(bool(self._navigation_history));self.refresh_current(force=True)
        except (ValueError,RuntimeError) as exc:
            self.inspection_label.setText('Navigation refused: '+str(exc)+' · select Current source to recapture this view.');self.inspection_label.show()

    def _return_inspection(self):
        if not self._navigation_history:return
        target,context=self._navigation_history.pop();self.return_button.setEnabled(bool(self._navigation_history))
        if context:self._navigate(target,context,remember=False)
        elif target=='calculator':self.main_tabs.setCurrentIndex(1)
        else:
            tab=int(target.split('.')[0]);nested=self.main_tabs.widget(tab-1)
            index=next(i for i in range(nested.count()) if nested.widget(i).widget().model.subtab_id==target)
            self.main_tabs.setCurrentIndex(tab-1);nested.setCurrentIndex(index);self.refresh_current(force=True)

    def _move_subtab(self, delta: int) -> None:
        if self.main_tabs.currentIndex()==1:return
        if self.main_tabs.currentIndex()==0:
            self.subtab_picker.setCurrentIndex(max(0,min(len(PAIRS)-1,self.subtab_picker.currentIndex()+delta)));return
        nested = self.main_tabs.currentWidget()
        if nested is not None:
            nested.setCurrentIndex(max(0, min(nested.count()-1, nested.currentIndex()+delta)))

    def _jump_subtab(self, index: int) -> None:
        if self.main_tabs.currentIndex()==1:return
        if self.main_tabs.currentIndex()==0 and index>=0:
            previous=self.runtime.selected_pair
            self._pair_views[previous]=self.main_tabs.widget(0).currentIndex()
            pair=self.subtab_picker.itemData(index)
            if pair in PAIRS:
                for i in range(self.main_tabs.widget(0).count()):
                    panel=self.main_tabs.widget(0).widget(i).widget();panel._save_workspace();panel.context=None;panel.run_id=None;panel._inspected_stamp=None
                self.tab_apis[1].command('1.1','SELECT_PAIR',{'symbol':pair})
                self.main_tabs.widget(0).setCurrentIndex(self._pair_views[pair]);self.refresh_current()
            return
        nested = self.main_tabs.currentWidget()
        if nested is not None and index >= 0:
            nested.setCurrentIndex(index)

    def _chart_changed(self,index):
        if hasattr(self,'main_tabs') and self.main_tabs.count():
            self.main_tabs.widget(0).setCurrentIndex(index)
            self._pair_views[self.runtime.selected_pair]=index

    def open_feed(self):
        if self.feed_dialog is None:
            self.feed_dialog=FeedDialog(self.tab_apis[2],self.tab_apis[4],self,fixture_mode=self.runtime.fixture_mode)
        self.feed_dialog.refresh();self.feed_dialog.show();self.feed_dialog.raise_();self.feed_dialog.activateWindow()
        status=self.runtime.connector.status()
        if not self.runtime.fixture_mode and status.get('configuration') and status['sdk_installed'] and status['state'] in {'CONFIGURED','SIGNED_OUT','LOGIN_REQUIRED','DISCONNECTED'}:
            self.feed_dialog.begin_login()

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        if hasattr(self, 'main_tabs'):
            self._adapt_subtab_bars()

    def _adapt_subtab_bars(self) -> None:
        for index in range(self.main_tabs.count()):
            if index!=1:self.main_tabs.widget(index).tabBar().hide()

    def refresh_current(self, *args: Any, force=False) -> None:
        # Only the dedicated core timer ingests; navigation must yield to paint.
        nested = self.main_tabs.currentWidget()
        tool_mode=self.main_tabs.currentIndex()==1
        self.view_toolbar.setVisible(not tool_mode)
        if tool_mode:
            self.chart_tabs.hide();self.tools.refresh()
        elif nested is not None:
            if hasattr(self, 'subtab_picker'):
                self.subtab_picker.blockSignals(True)
                chart_mode=self.main_tabs.currentIndex()==0
                titles=list(PAIRS) if chart_mode else [nested.tabText(i).replace('&&', '&') for i in range(nested.count())]
                if [self.subtab_picker.itemText(i) for i in range(self.subtab_picker.count())] != titles:
                    self.subtab_picker.clear()
                    for title in titles:self.subtab_picker.addItem(title,title if chart_mode else None)
                selected=PAIRS.index(self.runtime.selected_pair) if chart_mode else nested.currentIndex()
                self.subtab_picker.setCurrentIndex(selected)
                self.subtab_picker.blockSignals(False)
                self.view_position.setText(f'Pair {selected+1} of {len(PAIRS)}' if chart_mode else f'View {selected+1} of {nested.count()}')
                self.previous_view.setEnabled(selected > 0)
                self.next_view.setEnabled(selected < len(titles)-1)
                self.subtab_picker.setAccessibleName('Forex pair' if chart_mode else 'Subtab navigation')
                self.subtab_picker.setToolTip('Select a forex pair · Ctrl+K' if chart_mode else 'Choose a view · Ctrl+K')
                self.chart_tabs.setVisible(chart_mode)
                self.chart_tabs.blockSignals(True);self.chart_tabs.setCurrentIndex(self.main_tabs.widget(0).currentIndex());self.chart_tabs.blockSignals(False)
            self._adapt_subtab_bars()
            scroll = nested.currentWidget()
            panel = scroll.widget() if isinstance(scroll, QScrollArea) else None
            if panel is not None and callable(getattr(panel, 'refresh', None)):
                import time
                key=panel.model.subtab_id;now=time.monotonic()
                if force or key!=self._visible_key or key in self._dirty or now-self._last_clock_refresh>=5:
                    panel.refresh();self._dirty.discard(key);self._visible_key=key;self._last_clock_refresh=now
        account = self.runtime.accounts.current
        self.feed_card.refresh(self.runtime.connector.status(),account,self.runtime.fixture_mode)
        self.statusBar().showMessage('cTrader adapter '+('synthetic fixture · no network' if self.runtime.fixture_mode else self.runtime.connector.state.lower()))

    def closeEvent(self, event: Any) -> None:
        self.core_timer.stop()
        self.poll_timer.stop()
        if self.feed_dialog is not None:self.feed_dialog.close()
        self.tools.dispose()
        for i in (0,2,3):
            nested=self.main_tabs.widget(i)
            for j in range(nested.count()):
                dispose=getattr(nested.widget(j).widget(),'dispose',None)
                if dispose:dispose()
        for api in self.tab_apis.values():
            api.close()
        if self._owns_runtime:
            self.runtime.close()
        super().closeEvent(event)


def create_main_window(runtime: ApplicationRuntime | None = None) -> MainWindow:
    return MainWindow(runtime)


def run_app(runtime: ApplicationRuntime | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName('sfm-fx-new-age')
    app.setDesktopFileName('sfm-fx-new-age')
    window = create_main_window(runtime)
    window.show()
    try:
        return app.exec()
    finally:
        if runtime is not None:
            runtime.close()
