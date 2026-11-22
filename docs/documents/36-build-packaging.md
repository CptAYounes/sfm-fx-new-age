# NA-D36 — Build, Packaging and Reproducibility Specification

**Document:** NA-D36 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_BUILD_REFERENCE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Package definition
The project uses the setuptools build backend with `setuptools>=75` and `wheel`. Package name is `sfm-fx-new-age`, version 0.2.0, Python requirement >=3.13. Direct runtime dependencies are PySide6>=6.7 and websocket-client>=1.8,<2. The dev extra adds pytest>=8.0; the cTrader extra adds ctrader-open-api>=0.9.2. Package data includes contract CSV/JSON and the SFM icon.

## Entry points and environment
`sfm-fx-new-age` invokes the main application; `sfm-fx-check` invokes architecture checks. Use the project's virtual-environment interpreter. The inspected environment is Python 3.13.5 with PySide6 6.8.2.1, pytest 8.3.5, websocket-client 1.9.2 and ctrader-open-api 0.9.2. These are observed local versions, not an automatically enforced lockfile.

## Build procedure — guidance, not executed here
Provision the documented OS libraries; create a Python 3.13 virtual environment; install the desired extras; run source checks; build a wheel through the configured backend; install that wheel outside the checkout; compare package membership/content hashes and run the relevant acceptance. A fresh resolve can differ because metadata uses version ranges. Exact retained release dependencies/wheel hashes are stronger reproduction inputs than `pip install` alone.

## Reproducibility boundary
Do not claim bit-for-bit reproducible wheels merely because source/installed product files match. Build metadata/timestamps and dependency resolution can differ. The dependency inventory records the documentation-time installed environment, not vendor provenance or security status. No dependency installation or upgrade was performed by this documentation task.

## Existing launcher
The user-local Desktop installer refuses unrelated launchers and uses the packaged icon. Launcher resolution, source tree, wheel and installed payload are separate identities. A stale running process does not automatically load a new source or document package; normal user relaunch remains separate from qualification.

## Source and authority anchors

- [pyproject.toml](../../pyproject.toml#L1)
- [scripts/launch.sh](../../scripts/launch.sh#L1)
- [scripts/install_desktop.py](../../scripts/install_desktop.py#L16)
- [scripts/run_checks.sh](../../scripts/run_checks.sh#L1)
- [PROGRESS.md](../../PROGRESS.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
