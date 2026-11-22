"""Wrapping main-tab bar: exact canonical labels remain readable at compact widths."""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyle, QStyleOptionTab, QStylePainter, QTabBar, QWidget, QVBoxLayout, QStackedWidget

from .theme import COLORS


class WrappingMainTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setExpanding(True)
        self.setUsesScrollButtons(False)
        self.setElideMode(Qt.ElideNone)
        self.setMinimumWidth(0)
        self.setAccessibleName('Main sections')
        self.setFocusPolicy(Qt.StrongFocus)

    def tabSizeHint(self, index: int) -> QSize:
        available = max(1, self.width())
        width = max(180, available // max(1, self.count()))
        return QSize(width, 54)

    def minimumTabSizeHint(self, index: int) -> QSize:
        return QSize(150, 54)

    def paintEvent(self, event) -> None:
        painter = QStylePainter(self)
        for index in range(self.count()):
            option = QStyleOptionTab()
            self.initStyleOption(option, index)
            text = option.text.replace('&&', '&')
            option.text = ''
            painter.drawControl(QStyle.CE_TabBarTab, option)
            painter.setPen(QColor(COLORS['blue'] if index == self.currentIndex() else COLORS['muted']))
            painter.drawText(option.rect.adjusted(10, 5, -10, -5), Qt.AlignCenter | Qt.TextWordWrap, text)
            if self.hasFocus() and index == self.currentIndex():
                painter.setPen(QColor(COLORS['text']))
                painter.drawRect(option.rect.adjusted(4, 4, -5, -5))


class MainTabDeck(QWidget):
    """Native bar + shared view selector + stack, with one navigation hierarchy.

    Nested pages remain ordinary QTabWidgets, preserving lane widget/index contracts.
    No backend ownership or subscriptions live here.
    """
    currentChanged = Signal(int)

    def __init__(self, toolbar: QWidget, parent=None):
        super().__init__(parent)
        self._bar = WrappingMainTabBar(self)
        self._bar.setObjectName('mainSectionBar')
        self._stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._bar)
        layout.addWidget(toolbar)
        layout.addWidget(self._stack, 1)
        self._bar.currentChanged.connect(self._select)

    def _select(self, index):
        self._stack.setCurrentIndex(index)
        self.currentChanged.emit(index)

    def addTab(self, widget, title):
        index = self._stack.addWidget(widget)
        self._bar.addTab(title)
        self._bar.setTabToolTip(index, title.replace('&&', '&'))
        return index

    def tabBar(self): return self._bar
    def count(self): return self._stack.count()
    def widget(self, index): return self._stack.widget(index)
    def currentWidget(self): return self._stack.currentWidget()
    def currentIndex(self): return self._bar.currentIndex()
    def setCurrentIndex(self, index): self._bar.setCurrentIndex(index)
    def tabText(self, index): return self._bar.tabText(index)
