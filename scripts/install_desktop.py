#!/usr/bin/env python3
"""Install this checkout's user-local launcher; never change other SFM launchers."""
from __future__ import annotations

import argparse
from pathlib import Path
import os
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MARKER = '# Managed by SFM FX New Age desktop installer\n'


def install(home: Path, desktop: Path) -> tuple[Path, Path, Path]:
    home, desktop = home.resolve(), desktop.resolve()
    launcher = home / '.local/bin/sfm-fx-new-age'
    menu = home / '.local/share/applications/sfm-fx-new-age.desktop'
    shortcut = desktop / 'SFM FX New Age.desktop'
    icon = ROOT / 'src/sfm_fx_new_age/resources/sfm-logo.png'
    launch_script = ROOT / 'scripts/launch.sh'
    if not icon.is_file() or not os.access(launch_script, os.X_OK):
        raise RuntimeError('Packaged SFM icon and executable project launcher required')
    wrapper = MARKER + '#!/usr/bin/env bash\nset -euo pipefail\n' + (
        f'exec {shlex.quote(str(launch_script))} "$@"\n'
    )
    # Desktop entry Exec uses a no-space wrapper, independent of launch working directory.
    if any(char.isspace() for char in str(launcher)):
        raise ValueError('User-local launcher path must not contain whitespace')
    entry = MARKER + (
        '[Desktop Entry]\n'
        'Version=1.0\nType=Application\nName=SFM FX New Age\n'
        'Comment=Forex research, signals and human-issued pending orders\n'
        f'Exec={launcher}\nTryExec={launcher}\nPath={ROOT}\nIcon={icon}\n'
        'Terminal=false\nStartupNotify=false\nStartupWMClass=sfm-fx-new-age\n'
        'Categories=Office;Finance;\nKeywords=SFM;Forex;Signals;cTrader;\n'
    )
    # Refuse unrelated existing content; repeated installs of our own entries are safe.
    for target in (launcher, menu, shortcut):
        if target.is_symlink() or (target.exists() and MARKER.strip() not in target.read_text().splitlines()[:2]):
            raise RuntimeError(f'Refusing to overwrite an unmanaged target: {target}')
    launcher.parent.mkdir(parents=True, exist_ok=True)
    menu.parent.mkdir(parents=True, exist_ok=True)
    desktop.mkdir(parents=True, exist_ok=True)
    # Shebang must be the first line for direct kernel execution.
    wrapper = wrapper.replace(MARKER + '#!/usr/bin/env bash\n', '#!/usr/bin/env bash\n' + MARKER)
    launcher.write_text(wrapper); launcher.chmod(0o755)
    for target in (menu, shortcut):
        target.write_text(entry); target.chmod(0o755)
    for target in (menu, shortcut):
        if target.read_text() != entry or not os.access(target, os.X_OK):
            raise RuntimeError(f'Launcher readback failed: {target}')
    if launcher.read_text() != wrapper:
        raise RuntimeError('Wrapper readback failed')
    validator = shutil.which('desktop-file-validate')
    if validator:
        subprocess.run([validator, str(menu), str(shortcut)], check=True)
    return launcher, menu, shortcut


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--desktop', type=Path)
    args = parser.parse_args()
    desktop = args.desktop
    if desktop is None and args.home == Path.home() and shutil.which('xdg-user-dir'):
        result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True, check=True)
        desktop = Path(result.stdout.strip())
    targets = install(args.home, desktop or args.home/'Desktop')
    for path in targets:
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
