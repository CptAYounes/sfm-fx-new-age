# Repository guidance

Read `PROGRESS.md` and `CONTRIBUTING.md` before editing. `PROGRESS.md` is the sole progress diary; architecture/reference documents and community policies are not progress trackers.

Use dependency order: contracts → shared core → services/connector/storage → scoped tabs/UI → tests/docs. Keep changes focused. Preserve one human Issue edge, no implicit connection from checks/fixtures/replays, exact source/account/epoch identity and honest unavailable states.

Use Python 3.13, `requirements/constraints-py313.txt` and the offline test commands in CONTRIBUTING.md. Never use host credentials or private state for tests, never start connected verification without explicit authorization, and never infer broker proof or profitability from synthetic tests. Update documentation integrity manifests after intentional documentation edits. Report real outputs and remaining limitations.
