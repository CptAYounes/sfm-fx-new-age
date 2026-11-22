#!/usr/bin/env python3
"""Exercise the installed .desktop via GIO under a disposable X11 display/state directory."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import tempfile
import time


def verify(shortcut: Path, output: Path) -> None:
    if not os.environ.get('DISPLAY'):
        raise RuntimeError('Run with xvfb-run; a real X11 display is required')
    # File-manager launching has no environment override arguments: isolate only local state.
    scratch = Path(os.environ.get('TMPDIR', str(Path.home()/'.hermes/cache/scratch')))
    with tempfile.TemporaryDirectory(prefix='sfm-desktop-launch-', dir=scratch) as temporary:
        env = os.environ.copy()
        env['XDG_DATA_HOME'] = str(Path(temporary)/'data')
        env['QT_QPA_PLATFORM'] = 'xcb'
        log_path = Path(temporary)/'launch.log'
        pid = None
        with log_path.open('w') as log:
            subprocess.run(['gio', 'launch', str(shortcut)], env=env, stdout=log, stderr=log, check=True, timeout=15)
            try:
                deadline = time.monotonic() + 20
                window = None
                while time.monotonic() < deadline:
                    tree = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True, check=True).stdout
                    matched = re.search(r'(0x[0-9a-f]+) "SFM FX New Age Engine"', tree)
                    if matched:
                        window = matched.group(1)
                        break
                    time.sleep(0.1)
                if window is None:
                    raise AssertionError('Desktop entry did not produce a visible SFM window: ' + log_path.read_text())
                details = subprocess.run(['xprop', '-id', window, '_NET_WM_PID', 'WM_CLASS', '_NET_WM_ICON'],
                                         capture_output=True, text=True, check=True).stdout
                match = re.search(r'_NET_WM_PID\(CARDINAL\) = (\d+)', details)
                assert match, details
                pid = int(match.group(1))
                assert 'sfm-fx-new-age' in details, details[:300]
                assert '_NET_WM_ICON(CARDINAL)' in details, 'Window icon missing'
                from PIL import ImageGrab
                output.parent.mkdir(parents=True, exist_ok=True)
                ImageGrab.grab(xdisplay=os.environ['DISPLAY']).save(output)
                # Use the window's own Qt WM_DELETE_WINDOW protocol, not kill or synthetic app output.
                import ctypes
                x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
                x11.XOpenDisplay.argtypes = [ctypes.c_char_p]; x11.XOpenDisplay.restype = ctypes.c_void_p
                x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]; x11.XInternAtom.restype = ctypes.c_ulong
                x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
                x11.XFlush.argtypes = [ctypes.c_void_p]
                x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
                class Data(ctypes.Union):
                    _fields_ = [('b', ctypes.c_char*20), ('s', ctypes.c_short*10), ('l', ctypes.c_long*5)]
                class ClientMessage(ctypes.Structure):
                    _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong), ('send_event', ctypes.c_int),
                                ('display', ctypes.c_void_p), ('window', ctypes.c_ulong), ('message_type', ctypes.c_ulong),
                                ('format', ctypes.c_int), ('data', Data)]
                class XEvent(ctypes.Union):
                    _fields_ = [('client', ClientMessage), ('pad', ctypes.c_long*24)]
                display = x11.XOpenDisplay(None)
                if not display: raise AssertionError('X11 verification connection failed')
                try:
                    event = XEvent(); event.client.type = 33; event.client.send_event = 1
                    event.client.display = display; event.client.window = int(window, 16)
                    event.client.message_type = x11.XInternAtom(display, b'WM_PROTOCOLS', 0)
                    event.client.format = 32
                    event.client.data.l[0] = x11.XInternAtom(display, b'WM_DELETE_WINDOW', 0)
                    assert x11.XSendEvent(display, int(window, 16), 0, 0, ctypes.byref(event)) != 0
                    x11.XFlush(display)
                finally: x11.XCloseDisplay(display)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    status = Path(f'/proc/{pid}/status')
                    if not status.exists() or re.search(r'State:\s+Z', status.read_text()): break
                    time.sleep(0.1)
                else: raise AssertionError('Application did not close after WM_DELETE_WINDOW')
                dbpath = Path(env['XDG_DATA_HOME'])/'sfm-fx-new-age/state.sqlite3'
                assert dbpath.exists()
                with sqlite3.connect(dbpath) as conn:
                    assert conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 0
                    assert conn.execute("SELECT COUNT(*) FROM records WHERE kind IN ('bar','quote','signal','account_metadata')").fetchone()[0] == 0
                print('PASS: installed Desktop entry -> visible X11 window -> shared SFM icon -> graceful close')
                print('PASS: ordinary startup did not seed fixtures, authenticate an account or create orders')
                print('Screenshot:', output.resolve())
            finally:
                if pid:
                    status = Path(f'/proc/{pid}/status')
                    if status.exists() and not re.search(r'State:\s+Z', status.read_text()):
                        os.kill(pid, signal.SIGTERM)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shortcut', type=Path, default=Path.home()/'Desktop/SFM FX New Age.desktop')
    parser.add_argument('--screenshot', type=Path, default=Path('.runtime/screenshots/desktop-launch-verified.png'))
    args = parser.parse_args()
    verify(args.shortcut, args.screenshot)
