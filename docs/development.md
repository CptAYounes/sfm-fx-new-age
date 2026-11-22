# Developer guide

## Code map

| Path | Responsibility |
|---|---|
| `src/sfm_fx_new_age/contracts/` | Typed domain objects, registries and packaged method/DAG definitions |
| `core/` | Shared runtime, event router, scoped APIs and command ownership |
| `services/` | Analytical projection, scanner, signals, orders, replay and research |
| `connector/` | Optional SDK/OAuth and explicitly scoped data-source protocols |
| `storage/` | SQLite persistence, transactions and reconciliation records |
| `tabs/` and `ui/` | Workspace adapters, tools and PySide6 rendering |
| `testing/` and `tests/` | Explicit fixtures, offline checkpoint and regression suite |
| `verification/` | Historical operator acceptance tools; many require private inputs/native access |
| `docs/` | Full engineering library, diagrams, reference data and handbooks |

Source paths in this table are relative to the package root unless shown in full. Follow [CONTRIBUTING.md](../CONTRIBUTING.md) for installation and acceptance commands.

## Offline tests and packaging

Use the exact interpreter from your venv: `python -m pip`, `python -m pytest`, `python -m build`. Do not mix system `pip` and another Python version. The initial reference constraints pin Python 3.13-compatible dependencies. Full SDK tests use protocol recordings and loopback callbacks, not a real account.

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests -q
python -m sfm_fx_new_age --check
python -m sfm_fx_new_age --offline-checkpoint
python scripts/verify_publication.py
python -m build
```

The private immutable-research exception test uses a self-contained temporary synthetic manifest in this public edition. It still checks exact hashes, regular-file/mode constraints, identity, wrong-directory and symlink rejection. It no longer requires a private `.runtime` archive. The notebook fence permits enumerated documentation/community surfaces while continuing to forbid competing progress diaries.

## Documentation editing

Markdown documents and editable Graphviz diagrams are the source. The browser/PDF handbooks are generated artifacts. Their original authoring-host qualification remains historical; public verification checks present files, links, contracts and hashes, not unavailable native receipts or Git-unstable mtimes.

To intentionally rebuild the handbooks (requires `markdown-it-py`, PySide6 and Poppler for verification):

```bash
QT_QPA_PLATFORM=offscreen python docs/tooling/render_readers.py
python scripts/verify_publication.py --refresh-doc-manifest
python scripts/verify_publication.py
```

After intentional changes to packaged product source, use `--refresh-source-manifest` instead; it rebinds current source hashes and the documentation manifest while retaining original source digests. Review the resulting diff. This is an explicit source-identity update, not permission to disguise an unexplained change.

Install documentation/build tools with `python -m pip install -c requirements/constraints-py313.txt '.[docs]'`. Graphviz is needed only if editing/regenerating the `.dot` diagrams; keep the `.svg` and `.png` companions synchronized. Never refresh a manifest merely to conceal an unexplained mismatch.

`docs/tooling/verify_authoring_baseline.py` retains the original host-specific validation procedure for historical reference. Its private baseline inputs are not distributed; do not run it as public CI. `docs/tooling/verify_package.py` delegates to the portable public checker.

## Contribution opportunities

Current priorities are clean-clone portability, additional Linux/platform qualification, accessibility/keyboard review, evidence-led performance work, and carefully scoped analytical extensions with explicit genuine-data requirements. These are opportunities, not claims that a feature is implemented or a trading system profitable. Use issues and discussions for coordination; keep only `PROGRESS.md` as the progress diary.

## Activating GitHub Actions

The initial public edition includes `.github/ci-template.yml` rather than an active workflow: the maintainer's saved OAuth authorization can publish source but lacks GitHub's separate `workflow` scope. Local offline verification and clean-clone checks passed; no hosted CI result is implied.

A maintainer can authorize the additional permission through GitHub's normal browser flow (`gh auth refresh -h github.com -s workflow`), then move the template into `.github/workflows/ci.yml`, commit and push. Fork maintainers may activate it using their own properly authorized account. Never send a token or password in an issue/chat, and do not bypass GitHub's scope checks.

The template uses read-only repository permissions, SHA-pinned official actions, Python 3.13, the full offline suite, package/documentation checks and checksum-verified Gitleaks. It does not run connected broker-acceptance scripts.
