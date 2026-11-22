# NA-D31 — Threat Model and Abuse Case Analysis

**Document:** NA-D31 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** DESIGN_ASSESSMENT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Threat modelling basis
This is a source-grounded qualitative threat analysis, not an executed penetration test. Adversaries include a malicious local file publisher, compromised external response path, unintended stale worker and mistaken/compromised local caller. A fully compromised same-user account can read its plaintext secrets and is outside the protection offered by UI/API scopes alone.

| Threat/abuse case | Existing defense | Residual exposure / review |
|---|---|---|
| Forged OAuth callback | Random single-use state, exact path/fields, expiry | Registered redirect and local-user/browser environment remain trusted |
| Secret disclosure | Private file modes and redacted journals | Plaintext disk/backups and same-user access remain |
| Cross-account data/action | Scope/epoch/origin validation | Every new consumer must retain the namespace |
| Supplemental traversal/race | Adjacent regular files, no symlinks, hash checks, atomic admission | Publisher identity remains declared, not attested |
| Stale job commits | Tokens/current-source/profile/expiry rechecks | New worker types need equivalent guards |
| Duplicate order on timeout | Durable unique reservation, UNKNOWN, reconcile | Broker outcome can remain unresolved; local rollback cannot undo it |
| Resource exhaustion | Bounded queues/payloads/reconstruction/workers | Finite host resources and provider outages remain |
| False confirmation via derived data | Disclosed units/source/interpretation and shared roots | UI wording and reviewer discipline still matter |
| Arbitrary local command caller | Scoped API and exact schemas | `user_initiated` is not cryptographic human attestation |

## Abuse-case checks
Attempt wrong epoch/account, replay-origin Issue, payload with extra auth/execution fields, future/stale observations, manifest swap, reused callback, canceled login completion and superseded process results. Expected behavior is visible refusal without partial admission, credential leakage or order retry. Existing exact test references are catalogued in the verification crosswalk.

## Recommended review cycle
Reassess this model when adding a provider, remote API, plugin loader, secret backend or broker action. Document newly exposed data and mutation edges before implementation. No unresolved risk is silently marked accepted on the owner's behalf.

## Source and authority anchors

- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16)
- [services/supplemental_files.py](../../src/sfm_fx_new_age/services/supplemental_files.py#L21)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
