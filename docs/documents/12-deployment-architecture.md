# NA-D12 — Deployment Architecture and Environment Boundaries

**Document:** NA-D12 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_DEPLOYMENT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Supported deployment baseline
The documented qualified environment is Debian 13/X11 with Python 3.13 and PySide6. Package metadata permits Python >=3.13, but that declaration is not qualification of every later interpreter or every Linux desktop. The application is installed user-locally from its source/wheel and launched through the CLI or existing Desktop wrapper.

## Deployment nodes
- **Host user environment:** application/Qt process, user-local executable and Desktop/menu entries, packaged SFM icon.
- **Owned child execution:** SDK reactor processes and demand-grown pure projection pool; foreground-joined feed/authentication workers.
- **Operational storage:** explicit `--state-dir` or XDG data directory, `state.sqlite3` and SQLite WAL/SHM family, private credential directory and provider caches.
- **External services:** broker/cTrader authorization endpoints and declared public/context publishers.
- **Acceptance-only environment:** isolated installed wheel and clean Debian/X11 userland with disposable state; not ordinary live deployment.

## Configuration boundaries
Default in-memory runtime and headless verification are offline. Ordinary remembered-session GUI startup may connect after prior user consent. `--fixture-session` is explicitly synthetic and separate from normal state. `--strict-genuine-data` disables disclosed activity alternatives; it does not magically provision additional providers. `--compute-workers 1` uses serial calculation without changing product semantics.

## Installation and rollback implications
OS XCB/OpenGL/font libraries are outside pip dependencies and must be provisioned by the host. Keep Python packages in the project/installation environment, not mixed system interpreters. A rollback must consider source, wheel, launcher, state schema and credential compatibility together. Do not point an older program at a newer database without a verified compatibility path.

## Current task boundary
This documentation package lives beside the repository to preserve its source hashes and Markdown fence. It neither installs a new launcher nor changes the user's running application, credentials, broker session or saved method selections.

## Source and authority anchors

- [__main__.py](../../src/sfm_fx_new_age/__main__.py#L12)
- [scripts/launch.sh](../../scripts/launch.sh#L1)
- [scripts/install_desktop.py](../../scripts/install_desktop.py#L16)
- [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
