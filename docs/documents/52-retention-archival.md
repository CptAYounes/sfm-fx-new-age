# NA-D52 — Data Retention, Archival and Evidence Preservation

**Document:** NA-D52 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_RULES_AND_POLICY_PROPOSAL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Different retention classes
Live publication snapshots, normalized original observations, durable research/state, private credentials and sealed qualification evidence have different lifetimes. A rolling display/publication cache is not the retention authority for underlying originals or broker/order state.

## Implemented bounded retention
Connector publications and diagnostics have explicit bounded buffers. Kraken retains a rolling publication subset while normalized native executions/hour quantities and derivation records remain separately archived. Provider-owned pruning is scoped; it does not delete broker bars, saved preferences or other providers. Exact current bounds are captured in source-specific documentation and references, not generalized to all state.

## Historical preservation
NZDUSD is retired from current selection/admissions but its history is retained. Corrections and method definitions preserve prior immutable versions. Failed qualification attempts remain failed and retained beside their successors. Old source evidence is not relabelled as a new current epoch. Content hashes/CRCs identify preserved bytes; they do not attest external vendor authenticity.

## Archive safeguards — proposed procedure
Archive only explicitly identified terminal task-owned data. Verify process termination/open-handle constraints where needed. Record original bytes, lengths, permissions, mtimes and archive identity; fully decompress/member-verify before considering removal. Retain database sidecars when their exact state matters; do not silently checkpoint/rewrite evidence for convenience. A blocked deletion guard must not be waived because compression succeeded.

## Policy gaps
No general approved deletion horizon, secure erase policy, backup cadence or regulatory retention schedule was found. Never infer deletion permission from this plan, disk pressure, a successful release or the existence of a compressed copy. Private credentials require a separate protection/recovery decision. The documentation package excludes large original/runtime/private data rather than duplicating it.

## Review responsibility
The owner chooses retention objectives. The maintainer applies only authorized scoped changes, produces hashes/readback and reports races or unverified process state. Preservation of evidence is not the same as indefinite availability of external sources.

## Source and authority anchors

- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [connector/kraken_public.py](../../src/sfm_fx_new_age/connector/kraken_public.py#L34)
- [services/supplemental.py](../../src/sfm_fx_new_age/services/supplemental.py#L13)
- [PROGRESS.md](../../PROGRESS.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
