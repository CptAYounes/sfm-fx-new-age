# NA-D44 — Backup, Restore and Disaster Recovery Plan

**Document:** NA-D44 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** OPERATIONAL_POLICY_PROPOSAL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Recovery objectives
No approved recovery-time objective, recovery-point objective or scheduled backup service was found. This plan describes a proposed safe process and the state that must be preserved; it does not claim a tested production restore or an installed backup job.

## Recovery inventory
| Item | Why preserve | Caution |
|---|---|---|
| SQLite logical state | Market/research history, preferences, local orders and journal | Live WAL family must be captured consistently |
| Private credentials | App/session continuity | Sensitive plaintext; permissions/encryption decision separate |
| Provider caches/derivation originals | Auditable quantity recovery | Preserve source clocks/hashes, not current authority |
| Source/wheel/dependency identity | Reproducible compatible program | Current metadata ranges are not a lock |
| Sealed qualification evidence | Historical acceptance and failure records | Do not alter/reseal originals |
| Documentation package | Architecture/runbook reference | Not a substitute for actual state/evidence |

## Backup procedure
Quiesce the intended application or use SQLite's consistent backup mechanism. Do not take a random main-file copy while WAL is active. Write into a restricted new location, capture byte hashes and package/schema metadata, verify readability/integrity on the copy and retain independent protected storage according to an explicitly chosen policy. Avoid putting secrets into ordinary archive logs.

## Restore procedure
Restore first into a disposable isolated state directory. Verify schema support, source/package compatibility, hashes, private ownership/modes and offline startup. Historical data/preferences may load; authentication/provider authority must be re-established by their current owners. Recover in-flight orders as UNKNOWN and reconcile against the broker before new Issue. Never replay journaled Issue commands.

## Disaster handling
A corrupt database, lost token or destroyed host does not establish zero positions/orders at the broker. The operator must use authoritative broker state independently. A previous code backup cannot undo remote effects. Approve retention/encryption/recovery owners and exercise an isolated restore before calling this plan operationally qualified.

## Source and authority anchors

- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [services/replay.py](../../src/sfm_fx_new_age/services/replay.py#L13)
- [PROGRESS.md](../../PROGRESS.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
