# NA-D58 — Documentation Governance, Control and Maintenance

**Document:** NA-D58 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** DOCUMENTATION_POLICY · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Package purpose and placement
This is a companion architecture/engineering library for the inspected 0.2.0 New Age source. It lives beside the source repository because an existing test intentionally rejects additional Markdown files inside that repository. No architecture fence was weakened and no sealed source/evidence was edited to accommodate documentation.

## Control model
Each main document has a stable NA-D identifier, type, documentation version, baseline, evidence classification and source anchors. Markdown is the editable canonical document content. HTML/PDF are reader exports; CSV/JSON references are generated source/receipt extracts. Document checksums bind this publication. They are not broker approval or product acceptance replacement.

## Authority and updates
Current source owns implementation facts; explicit owner decisions own product/safety scope; dated retained receipts own historical qualification claims. Proposed procedures remain labelled. `PROGRESS.md` remains the sole project progress/handoff diary. Do not create competing status, roadmap-tracking or handoff notes within this package.

## Update workflow
For an implementation change, update the affected explanatory document, contract/reference extract, crosswalk and ADR as appropriate. Refresh source hashes, regenerate reader exports, verify links/anchors/counts, and preserve the previous published package if it has been delivered. Do not modify historical sealed product evidence or declare fresh native qualification from regenerated prose.

## Completion criteria
The finite publication contains all 60 main document types, the 12 retrospective ADRs, source-derived reference catalogues, diagrams, traceability matrices, reader exports and validation receipts listed by its manifest. Mechanical checks establish membership/link/hash consistency; semantic review still determines whether design statements are honest and useful.

## Ownership and signoff
The owner has requested creation, not supplied signatures accepting every proposed policy. Documents are authored/source-grounded, not fabricated approvals. Formal external compliance, backup SLA, encrypted secret storage and future execution scope remain explicit decisions. No automatic scheduled maintenance or publishing service is installed by this package.

## Source and authority anchors

- [PROGRESS.md](../../PROGRESS.md#L1)
- [tests/test_architecture_fences.py](../../tests/test_architecture_fences.py#L13)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
