# NA-D32 — Privacy, Sensitive Data and Information Handling

**Document:** NA-D32 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** OPERATIONAL_POLICY_PROPOSAL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Data classification
| Class | Examples | Handling |
|---|---|---|
| Secret | Client secret, access/refresh token, auth code, FIX password | Private connector store; no chat, journal or documentation payload |
| Sensitive operational | Account IDs, broker inventory, balance, orders, private state paths | Restricted local state/backups; minimize exports |
| Research/source evidence | Broker bars, venue originals, analytical results | Preserve provenance and source-use limits |
| Public engineering | Source references, field names, generated diagrams | Share only after checking no operational values leaked |

## As-built handling
Secrets are excluded from ordinary SDK events and journal payloads. App/session imports use private file references instead of secret command fields. Closed acquisition directories can include account metadata even when their receipts omit login secrets; they are not automatically safe to publish. The state database and source caches are local, but no full-disk/database encryption is supplied by the application.

## Documentation package boundary
This companion contains source-derived definitions, inventories, selected sanitized release facts and new offline check receipts. It does not copy normal application databases, private credential files, raw broker positions/balances, native market captures or the sealed multi-gigabyte release tree. Field names such as `client_secret` appear as schema names, never values.

## Proposed operational policy
Keep working evidence private by default. Before sharing a bug report, remove tokens, callback URLs/codes, account identities, private paths and raw provider payloads not needed for reproduction. Preserve local originals when creating sanitized derivatives and hash both distinctly. Backups containing secrets require separate access protection and an explicitly chosen encryption/recovery policy.

## Unresolved governance
No approved jurisdiction-specific retention schedule, organizational privacy notice, disclosure process or regulatory classification was found. This document does not invent one or certify legal compliance. Obtain the appropriate owner/professional determination before external distribution of sensitive operational data.

## Source and authority anchors

- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [connector/original_capture.py](../../src/sfm_fx_new_age/connector/original_capture.py#L21)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
