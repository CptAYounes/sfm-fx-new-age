# Getting started

## Requirements

The reference desktop is Debian 13 / X11 with Python 3.13. Packaging declares Python 3.13+; other Python/Qt combinations and macOS/Windows have not been qualified by the initial public release. The reference constraints are specifically for Python 3.13.

On Debian 13, install the Qt/X11 runtime libraries and venv support:

```bash
sudo apt-get install python3.13-venv libgl1 libegl1 libopengl0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libdbus-1-3 libfontconfig1 libglib2.0-0t64 fonts-dejavu-core
```

Ubuntu or other distributions may use different package names. A regular X11 desktop does not need Xvfb. Headless CI uses Qt's offscreen plugin.

## Install a source checkout

```bash
git clone https://github.com/CptAYounes/sfm-fx-new-age.git
cd sfm-fx-new-age
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements/constraints-py313.txt -e '.[dev]'
```

Optional cTrader adapter and complete SDK-specific offline tests:

```bash
python -m pip install -c requirements/constraints-py313.txt -e '.[dev,ctrader]'
```

`requirements/constraints-py313.txt` pins the reference development environment; it does not vendor dependencies, credentials or provider data. Downloading/installing packages needs internet access. The following application checks do not need a market connection:

```bash
python -m sfm_fx_new_age --check
python -m sfm_fx_new_age --summary-json
python -m sfm_fx_new_age --offline-checkpoint
QT_QPA_PLATFORM=offscreen python -m pytest tests -q
```

## Explore without a broker

```bash
python -m sfm_fx_new_age --fixture-session
```

This is a labelled in-memory synthetic session. It is not observed market data, broker proof or a profitable strategy. Ordinary launch is `python -m sfm_fx_new_age`; without configuration it stays unconnected. For a disposable real-mode workspace, supply `--state-dir /path/to/new-local-state`. Never point tests at your normal state directory.

Normal application state is under `$XDG_DATA_HOME/sfm-fx-new-age` or `~/.local/share/sfm-fx-new-age`, unless overridden. A previously configured and owner-enabled saved session can automatically reconnect. Sign-out, disconnect and grant revocation have different effects; read the [operator manual](legacy-user-guide.md#saved-application-authorization).

## Connect deliberately

No registered cTrader application credentials ship with this repository. Bring your own application registration and explicitly authorize a selected account. Use the setup UI described in the full guide; never paste tokens into an issue, commit, command payload or public log. Starting a feed does not grant an automated trading strategy. Proposal binding is local and separate from the deliberate human Issue action.

## Desktop shortcut

Once the checkout environment is installed, `python scripts/install_desktop.py` installs this checkout's user-local launcher. It refuses to overwrite unrelated entries. This is optional and changes your user application-menu/Desktop files; do not run it just to execute unit tests.

## Troubleshooting

- **Qt cannot load xcb:** install the OS dependencies above and use a working X11 display. Offscreen is for tests, not an interactive desktop.
- **No data/signals:** inspect source configuration, method enablement, freshness, trigger and genuine-data blockers. Do not replace missing data with invented samples.
- **SDK-only tests skipped:** install the `ctrader` extra. Tests remain offline after installation.
- **Unexpected saved login:** stop and relaunch with a new explicit state directory; do not experiment against your normal broker state.

See [support](../SUPPORT.md), [the full manual](legacy-user-guide.md), and [60 detailed engineering documents](README.md).
