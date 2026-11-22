# NA-D40 — Release and Configuration Management Plan

**Document:** NA-D40 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** MAINTENANCE_PROCESS_PROPOSAL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Configuration items
A release binds source/contracts, test roster/outcomes, declared dependency environment, wheel, installed product membership, launcher/icon, database compatibility, qualification harness and retained evidence manifest. The live process and mutable normal state are separate operational identities. Documentation has its own version and source-baseline binding; it does not become a trading authority artifact.

## Source control reality
The inspected repository has a `.git` directory but no commits yet; its files are untracked on master. Therefore no commit ID, signed tag, CI run or pull request is invented. This package uses per-file SHA-256 and the existing frozen candidate receipt for source identity. Establishing a real Git baseline is a proposed follow-up, not something performed here.

## Proposed release sequence
1. Freeze an exact source/test/contract roster and record hashes.
2. Execute required bounded tests and compare collection/terminal outcomes.
3. Build/install the wheel independently and verify product membership/hashes.
4. Run the named native/desktop qualifications under exact authorized scope.
5. Preserve failures, original inputs and external dependency limits.
6. Create the evidence manifest last, then independently verify it.
7. Publish the verdict in the sole mutable diary outside sealed evidence.

## Semantic changes
Retain stable recipe IDs where defined but advance semantic versions/profile hashes when rules change. Migrate only known predecessor preferences without changing literal enabled/disabled choices. Persisted observations are immutable history; do not retag old source rows as current.

## Rollback
Rollback changes code/package/launcher and restores only compatible state, with user-owned broker inventory reconciled independently. A filesystem rollback cannot undo a remote order. Never delete an uncertain reservation as part of release recovery. Formal automated CI/signing/rollout policy remains proposed unless implemented and evidenced separately.

## Source and authority anchors

- [pyproject.toml](../../pyproject.toml#L1)
- [PROGRESS.md](../../PROGRESS.md#L1)
- [scripts/install_desktop.py](../../scripts/install_desktop.py#L16)
- [contracts/public_strategies.py](../../src/sfm_fx_new_age/contracts/public_strategies.py#L10)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
