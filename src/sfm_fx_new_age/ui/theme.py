"""Palette translated from supplied sfm-fx-calculator 1.4.0 (Tk) into Qt."""
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

COLORS = {
    'bg': '#0B1220', 'panel': '#141F30', 'panel_border': '#223149',
    'input': '#1D2C41', 'hover': '#263B55', 'text': '#F3F7FD',
    'muted': '#9AAFC9', 'dim': '#6D829E', 'blue': '#56BDF5',
    'green': '#66E3AA', 'red': '#FF8591', 'line': '#2B3B52',
    'result': '#102D35', 'result_idle': '#132538', 'white': '#FFFFFF',
}
FONT = 'DejaVu Sans'


def stylesheet() -> str:
    c = COLORS
    return f"""
    QWidget {{ background: {c['bg']}; color: {c['text']}; font-family: '{FONT}'; font-size: 12px; }}
    QMainWindow, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {c['bg']}; }}
    QFrame#card, QWidget#card {{ background: {c['panel']}; border: 1px solid {c['panel_border']}; border-radius: 10px; }}
    QFrame#feedConnectionCard {{ background: {c['result_idle']}; border: 1px solid {c['blue']}; border-radius: 12px; }}
    QFrame#feedConnectionCard QLabel {{ background: transparent; border: none; }}
    QLabel#sessionStatus {{ color: {c['blue']}; font-size: 11px; font-weight: 600; }}
    QLabel#selectedAccount {{ font-size: 10px; }}
    QLabel#chartHeading, QLabel#dialogTitle {{ font-size: 16px; font-weight: 600; }}
    QLabel#chartOrigin, QLabel#chartDetail, QLabel#chartOhlc {{ color: {c['muted']}; font-size: 10px; }}
    QLabel#chartHealth {{ color: {c['muted']}; font-size: 11px; background: {c['result_idle']}; padding: 5px 8px; border-radius: 6px; }}
    QLabel#chartViewState {{ color: {c['blue']}; font-size: 10px; }}
    QMenu {{ background: {c['panel']}; color: {c['text']}; border: 1px solid {c['line']}; padding: 6px; }}
    QMenu::item {{ padding: 7px 20px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {c['hover']}; color: {c['blue']}; }}
    QLabel#chartQuote {{ color: {c['text']}; font-size: 11px; padding-left: 8px; }}
    QFrame#card QLabel {{ background: transparent; border: none; }}
    QLabel[role='muted'] {{ color: {c['muted']}; background: transparent; }}
    QLabel[role='caption'] {{ color: {c['muted']}; font-size: 10px; font-weight: 600; background: transparent; }}
    QLabel[role='heading'] {{ font-size: 17px; font-weight: 600; background: transparent; }}
    QLabel[role='accent'] {{ color: {c['blue']}; background: transparent; font-weight: 600; }}
    QLabel[role='status'] {{ color: {c['blue']}; background: {c['result_idle']}; padding: 5px 10px; border-radius: 8px; }}
    QLabel#brand {{ font-size: 18px; font-weight: 600; color: {c['text']}; }}
    QPushButton {{ background: {c['input']}; border: 1px solid {c['line']}; border-radius: 8px; padding: 6px 10px; font-weight: 500; }}
    QPushButton[role='connect'] {{ background: {c['blue']}; color: {c['bg']}; font-weight: 600; }}
    QPushButton[role='connect']:disabled {{ color: {c['dim']}; background: {c['input']}; border-color: {c['line']}; }}
    QPushButton:checked {{ color: {c['blue']}; border-color: {c['blue']}; background: {c['result_idle']}; }}
    QPushButton:hover {{ background: {c['hover']}; border-color: {c['blue']}; }}
    QPushButton:pressed {{ background: {c['panel_border']}; }}
    QPushButton:focus, QComboBox:focus {{ border: 1px solid {c['blue']}; }}
    QPushButton:disabled {{ color: {c['dim']}; border-color: {c['panel_border']}; }}
    QPushButton[role='primary'] {{ color: {c['green']}; background: {c['result']}; }}
    QPushButton[role='primary']:disabled {{ color: {c['dim']}; background: {c['input']}; border-color: {c['panel_border']}; }}
    QComboBox, QLineEdit {{ background: {c['input']}; color: {c['text']}; border: 1px solid {c['line']}; border-radius: 8px; padding: 6px 10px; min-width: 70px; }}
    QComboBox QAbstractItemView {{ background: {c['panel']}; selection-background-color: {c['hover']}; }}
    QTabWidget::pane {{ border: 1px solid {c['panel_border']}; border-radius: 10px; }}
    QTabBar::tab {{ background: {c['panel']}; color: {c['muted']}; padding: 8px 10px; border: 1px solid {c['panel_border']}; border-radius: 8px; margin-right: 4px; }}
    QTabBar#pairChartSubtabs::tab {{ padding: 6px 8px; border-radius: 7px; font-size: 11px; }}
    QTabBar::tab:selected {{ color: {c['blue']}; background: {c['input']}; border-bottom: 2px solid {c['blue']}; }}
    QTabBar::tab:hover {{ color: {c['text']}; background: {c['hover']}; }}
    QTabBar QToolButton {{ background: {c['input']}; color: {c['blue']}; border: 1px solid {c['line']}; width: 28px; }}
    QTableWidget {{ background: {c['panel']}; alternate-background-color: {c['result_idle']}; border: 1px solid {c['panel_border']}; gridline-color: {c['line']}; selection-background-color: {c['hover']}; selection-color: {c['white']}; }}
    QTableWidget::item {{ padding: 4px; background: transparent; }}
    QTableWidget::item:selected {{ background: {c['hover']}; }}
    QHeaderView::section {{ background: {c['input']}; color: {c['muted']}; border: none; border-right: 1px solid {c['line']}; border-bottom: 1px solid {c['line']}; padding: 6px; font-size: 10px; font-weight: 600; }}
    QCheckBox {{ spacing: 8px; color: {c['muted']}; background: transparent; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {c['line']}; background: {c['input']}; }}
    QCheckBox::indicator:checked {{ background: {c['blue']}; }}
    QScrollBar:vertical {{ background: {c['bg']}; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {c['line']}; min-height: 24px; border-radius: 4px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QStatusBar {{ color: {c['muted']}; background: {c['bg']}; padding: 5px; }}
    QStatusBar::item {{ border: none; }}
    QToolTip {{ color: {c['text']}; background: {c['panel']}; border: 1px solid {c['blue']}; }}
    """


def apply_theme(app: QApplication) -> None:
    # Multiple attached views share one QApplication. Reinstalling the global style
    # repolishes every existing widget, including inactive windows, on each open.
    css = stylesheet()
    if app.property('sfmCalculatorTheme') == css and app.styleSheet() == css:
        return
    if app.style().objectName().lower() != 'fusion':
        app.setStyle('Fusion')
    font = QFont(FONT, 10)
    if app.font() != font:
        app.setFont(font)
    if app.styleSheet() != css:
        app.setStyleSheet(css)
    app.setProperty('sfmCalculatorTheme', css)
