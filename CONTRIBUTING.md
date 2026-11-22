# Contributing

Fork this repository, create a focused branch, and open a pull request against `main`. You may also use or adapt the project without contributing back under the MIT license.

## Before coding

1. Read the [architecture](docs/documents/07-architecture-description.md), [developer guide](docs/development.md), and current decisions in [PROGRESS.md](PROGRESS.md).
2. Search existing issues. For a substantial architectural or trading-behavior change, open a design discussion first.
3. Keep the issue, implementation, tests and documentation in agreement. Mark proposals and unverified assumptions explicitly.

## Local checks

Use Python 3.13 with the supplied reference constraints. Install `.[dev,ctrader]` for the complete offline suite; the optional SDK is not a request to authenticate.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements/constraints-py313.txt -e '.[dev,ctrader]'
QT_QPA_PLATFORM=offscreen python -m pytest tests -q
python -m sfm_fx_new_age --check
python -m sfm_fx_new_age --offline-checkpoint
python scripts/verify_publication.py
python -m build
```

Use `QT_QPA_PLATFORM=offscreen` for GUI tests. Tests must not borrow personal credentials, a live state database or a broker session. Keep synthetic inputs labelled. Do not run connected scripts under `verification/` or `scripts/verify_ctrader_feed.py` as ordinary unit tests.

## Architectural rules

- Preserve the four-workspace / 42-backend-identity contract unless an agreed design explicitly changes it.
- UI extensions consume a scoped TabApi. Do not open a second database, broker socket or order gateway from a plugin.
- Keep pure analytical math separate from owner-side state, persistence and broker operations.
- Preserve source/account/epoch identity, causality, freshness and missing-data behavior.
- Binding is not Issue. Do not turn a navigation, research, replay or fixture path into automatic broker execution.
- Add behavioral regression tests. Never replace an unavailable source with invented data to make a test green.

## Pull request checklist

- Explain the problem, intended behavior, limitations and related issue.
- Include reproducible commands and actual results; label checks you did not run.
- Document user-visible behavior, schema/API changes and compatibility impact.
- Exclude credentials, tokens, account IDs, native captures, databases and runtime exports.
- Avoid unrelated refactors and generated-file churn. If documentation changes, regenerate readers and the documentation manifest as described in [development](docs/development.md).
- Update the single `PROGRESS.md` diary only after a verified substantive work batch; do not create competing progress/handoff notebooks.

By submitting a contribution, you agree it may be distributed under the repository's MIT license and confirm you have the right to submit it. No CLA or transfer of copyright is required. Conduct follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
