import importlib.util
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_install', ROOT/'scripts/install_desktop.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def test_desktop_install_readback_exec_and_idempotence(tmp_path):
    home = tmp_path/'home'
    targets = installer.install(home, home/'Desktop')
    wrapper, menu, desktop = targets
    assert wrapper.read_text().startswith('#!/usr/bin/env bash\n')
    assert os.access(wrapper, os.X_OK) and os.access(desktop, os.X_OK)
    assert menu.read_bytes() == desktop.read_bytes()
    assert f'Exec={wrapper}' in desktop.read_text()
    assert 'Terminal=false' in desktop.read_text()
    assert 'sfm-logo.png' in desktop.read_text()
    assert '--fixture-session' not in desktop.read_text()
    assert installer.install(home, home/'Desktop') == targets
    result = subprocess.run([str(wrapper), '--check'], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert '"ok": true' in result.stdout


def test_installer_does_not_overwrite_unrelated_shortcut(tmp_path):
    home = tmp_path/'home'; desktop = home/'Desktop'
    desktop.mkdir(parents=True)
    target = desktop/'SFM FX New Age.desktop'; target.write_text('unrelated contents')
    with pytest.raises(RuntimeError): installer.install(home, desktop)
    assert target.read_text() == 'unrelated contents'
    assert not (home/'.local/bin/sfm-fx-new-age').exists()


def test_packaged_brand_icon_is_loadable():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    app = QApplication.instance() or QApplication([])
    assert not QIcon(str(ROOT/'src/sfm_fx_new_age/resources/sfm-logo.png')).isNull()
