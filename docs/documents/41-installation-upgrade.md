# NA-D41 — Installation, Upgrade and Uninstall Guide

**Document:** NA-D41 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** OPERATOR_PROCEDURE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Installation prerequisites
Use the documented Debian/X11 environment, Python 3.13 virtual environment and the OS OpenGL/EGL/XCB/DBus/font libraries listed in the source README. PySide6 wheels do not provide all desktop OS libraries. The current host's global `python3`/pip pairing differs from the application environment; always invoke the intended environment's Python explicitly.

## Local development installation
From the source root, create the venv with `python3.13 -m venv .venv`, then use `.venv/bin/python -m pip install -e '.[dev,ctrader]'` when the optional SDK is desired. These are documented setup commands, not commands executed by this package. Check architecture and offline behavior before configuring any real session. Ordinary launch is `./scripts/launch.sh`; a labelled synthetic session uses `--fixture-session`.

## Desktop registration
The optional user-local installer is `.venv/bin/python scripts/install_desktop.py`. It checks for unrelated launchers and uses the packaged icon. Do not rewrite a working launcher merely to publish documentation. The actual configured executable and its package/source root should be inspected when investigating stale launches.

## Upgrade procedure — proposed safe practice
Stop only the application instance the operator intends to upgrade. Preserve a consistent state backup and private credential reference, note current package/schema identity, install the qualified candidate and verify offline startup. Then allow the operator's normal session flow. Reconcile uncertain orders and observe source freshness before any new Issue. A restart is not permission for a broker test.

## Uninstall/rollback boundary
Removing the program must not silently delete research, state, credentials, caches or evidence. Data deletion and token revocation are separate explicit decisions. Sign out removes saved tokens locally but is not proof of server-side revocation or broker cancellation. No uninstall, installation, upgrade or launcher change was performed during this documentation task.

## Source and authority anchors

- [README.md](../../README.md#L1)
- [pyproject.toml](../../pyproject.toml#L1)
- [scripts/launch.sh](../../scripts/launch.sh#L1)
- [scripts/install_desktop.py](../../scripts/install_desktop.py#L16)
- [__main__.py](../../src/sfm_fx_new_age/__main__.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
