# NA-D45 — Incident Response and Problem Management Runbook

**Document:** NA-D45 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** OPERATIONAL_POLICY_PROPOSAL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Incident classes
Classify uncertain broker action, source-integrity loss, credential exposure, state corruption, UI/owner failure and dependency outage separately. A missing setup is not itself an incident. A historical PASS cannot close a present source/transport failure.

## Immediate containment
For suspected uncertain execution, stop further new Issue attempts and preserve reservations/native identifiers. For source-integrity failure, withdraw that source through its owner rather than substituting guessed data. For suspected secret exposure, avoid logging/copying the secret, disable affected local use and obtain operator-led provider revocation/rotation. Do not claim that local Sign out revokes the provider grant.

## Evidence collection
Record UTC/local observation time, exact package/source identity, sanitized error classes, relevant scope/epoch, current source/input state and task-owned process state. Retain original failure receipts and read-only state snapshots where authorized. Distinguish an independently changing normal database from an immutable snapshot; do not falsely claim perpetual byte equality while another process writes.

## Recovery sequence
1. Determine the owning layer and actual failure, not merely the last visible symptom.
2. Restore or reauthenticate only the intended source/account/runtime.
3. Reconcile broker uncertainty before enabling new action.
4. Run bounded relevant positive/refusal checks against a source-bound candidate.
5. Verify task-owned children joined and actual current observation recovered.
6. Record verified findings and remaining limits in the sole project diary.

## Problem review
Separate observed cause, plausible hypothesis, repair and independently verified result. Preserve failed attempts instead of rewriting them as successful successors. A timeout or wrapper failure is not automatically a product defect, but it also cannot be credited as a product pass. External provider access, purchases and human credentials are irreducible dependencies, not grounds for fabrication.

## Governance gap
There is no documented formal incident commander/on-call rota or response SLA. Role assignments and notification channels require explicit owner decisions; this package does not invent contacts or send any external notice.

## Source and authority anchors

- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [PROGRESS.md](../../PROGRESS.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
