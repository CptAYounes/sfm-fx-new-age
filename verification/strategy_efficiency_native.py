"""Native X11 readiness counts on original recorded observations only."""
from collections import Counter
from pathlib import Path
import json
import sys
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractItemView
from original_source_checks import original_runtime, RUN, PACKAGE
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES
from sfm_fx_new_age.contracts.public_strategies import METHODS


def main():
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == 'xcb'
    r, layers, _, original = original_runtime()
    window = None
    proof = dict(result='FAIL', source='RECORDED_ORIGINAL_DATA_NOT_NEW_LIVE_CAPTURE',
        input_row_sha256=original['input_row_sha256'], package_root=str(PACKAGE),
        synthetic_observations=0, pair_frame_checks=[], screenshots=[])
    try:
        window = create_main_window(r)
        window.resize(1280, 900)
        window.show()
        window.core_timer.stop()
        window.poll_timer.stop()
        app.processEvents()
        for symbol in PAIRS:
            for frame in FRAMES:
                r.api(3).navigate('3.1', r.api(3).inspect(symbol=symbol, timeframe=frame))
                app.processEvents()
                window.refresh_current(force=True)
                panel = window._active_panel()
                expected = dict(Counter(v['state'] for v in layers if v['symbol']==symbol and v['timeframe']==frame))
                assert panel._readiness_counts == expected, (symbol, frame, panel._readiness_counts, expected)
                assert sum(panel._readiness_counts.values()) == len(METHODS)
                assert expected['DATA_UNAVAILABLE'] == 6
                assert 'Data needed 6' in panel.status.text()
                assert 'not live connection health' in panel.status.toolTip()
                assert panel.details.isReadOnly()
                proof['pair_frame_checks'].append(dict(symbol=symbol, timeframe=frame, states=expected))
        r.api(3).navigate('3.1', r.api(3).inspect(symbol='EURUSD', timeframe='H4'))
        app.processEvents()
        window.refresh_current(force=True)
        panel = window._active_panel()
        before = dict(panel._readiness_counts)
        panel.search.setFocus()
        QTest.keyClicks(panel.search, 'VWAP')
        app.processEvents()
        assert panel._readiness_counts == before
        assert sum(not panel.table.isRowHidden(i) for i in range(len(METHODS))) == 1
        panel.search.clear()
        index = next(i for i,m in enumerate(METHODS) if m.key=='footprint_delta')
        panel.table.scrollToItem(panel.table.item(index, 1), QAbstractItemView.PositionAtCenter)
        panel.table.selectRow(index)
        app.processEvents()
        detail = panel.details.toPlainText()
        assert 'known aggressor side' in detail and 'quote uptick/downtick does not establish the aggressor' in detail
        screenshot = RUN/'original-readiness-source-requirements.png'
        assert window.grab().save(str(screenshot))
        proof['screenshots'].append(str(screenshot))
        box = panel.checkboxes['footprint_delta']
        assert box.isChecked()
        QTest.mouseClick(box, Qt.LeftButton, pos=QPoint(8, box.height()//2))
        r.pump()
        panel.refresh()
        app.processEvents()
        assert not box.isChecked()
        assert panel._readiness_counts['OFF'] == 1
        assert panel._readiness_counts['DATA_UNAVAILABLE'] == 5
        QTest.mouseClick(box, Qt.LeftButton, pos=QPoint(8, box.height()//2))
        r.pump()
        panel.refresh()
        app.processEvents()
        assert box.isChecked() and panel._readiness_counts == before
        proof.update(result='PASS', search_does_not_change_total=True,
            switch_count_update_verified=True, exact_input_requirement_visible=True,
            fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')],
            sdk_workers_started=bool(r.connector.workers))
        assert not proof['fixture_imports'] and not proof['sdk_workers_started']
    finally:
        if window is not None:
            window.close()
        r.close()
        app.processEvents()
        proof['runtime_closed'] = r.closed
        path = RUN/'readiness-native-receipt.json'
        with path.open('x') as stream:
            json.dump(proof, stream, indent=2)
            stream.write('\n')
        path.chmod(0o444)
    print(json.dumps({k:v for k,v in proof.items() if k!='pair_frame_checks'}, indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
