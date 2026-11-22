"""Tab3→Tab4 navigation must work without inventing an active inspection."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import pytest
from PySide6.QtWidgets import QApplication
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.contracts.public_strategies import METHODS
from test_strategy_signal_positive import bindable_runtime

@pytest.mark.parametrize('mode',['fresh','after_disconnect','active_fixture'])
def test_strategy_signals_navigation_is_source_optional_and_retains_valid_context(monkeypatch,mode):
    app=QApplication.instance() or QApplication([])
    r=ApplicationRuntime() if mode=='fresh' else bindable_runtime()
    if mode=='after_disconnect':r.accounts.disconnect();r.pump()
    method=METHODS[0];errors=[]
    monkeypatch.setattr(sys,'excepthook',lambda kind,value,tb:errors.append((kind.__name__,str(value))))
    w=create_main_window(r);w.show()
    try:
        w.main_tabs.setCurrentIndex(2);app.processEvents()
        public=w._active_panel();public.frame_picker.setCurrentText('H1')
        if not public.checkboxes[method.key].isChecked():public.checkboxes[method.key].click()
        app.processEvents()
        public.signals_button.click();app.processEvents()
        assert not errors,errors
        assert w.main_tabs.currentIndex()==3
        panel=w._active_panel().research_signals
        assert panel.table.rowCount()==83
        assert panel.frame.currentText()=='H1'
        assert any(x['strategy_id']==method.key and x['enabled'] for x in panel._rows)
        if mode=='active_fixture':
            assert panel.frame.currentText()=='H1'
            assert all(x['source_epoch']==r.market.authority('EURUSD')['source_epoch'] for x in panel._rows)
        else:
            assert r.accounts.current is None
            assert not any(x['opportunity_id'] for x in panel._rows)
            assert not panel.bind.isEnabled()
        assert not r.database.orders()
    finally:
        w.close();r.close();app.processEvents()
