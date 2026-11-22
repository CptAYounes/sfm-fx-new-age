# NA-D19 — Market and Supplemental Source Provenance Specification

**Document:** NA-D19 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_DATA_AUTHORITY · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Source matrix
| Input | Source/semantics | Must not imply |
|---|---|---|
| Broker bars/quotes/specs | Selected authenticated cTrader namespace | Consolidated market tape |
| BROKER_DEPTH | Acknowledged observed displayed levels, local receipt clock | Native sequence/full global book/executions |
| Kraken prints/taker sides | Native venue executions and documented taker direction | cTrader fills or universal FX volume |
| Executed hour/week quantities | Complete exact original intervals/derivations | Fabricated individual prints or zero-filled gaps |
| Checksum L2 | Verified top-ten venue book | Full native-sequence/L3 claim |
| Bitstamp native chain | Corroborated predecessor-linked public order scope | Hidden/global liquidity; coverage beyond declared pairs |
| CFTC/Board | Published futures context/declared official schedule | Spot inventory or all-agency news clearance |
| Operator files | Explicit configured typed publications | Independent vendor authentication |

## Admission requirements
Every publication retains provider, evidence kind, selected account scope, epoch, pair, origin, venue/instrument, price domain, units, completeness, window, original clocks, availability, expiry and revision. Registration is ephemeral; saved rows do not restore authority. Explicit configured providers retain their declared precedence; an invalid present input is not hidden by a convenient fallback.

## Historical quantity derivation
Broker-day/week totals use complete native days/hours and exact execution boundary tails. DST-shifted broker edges are preserved. Missing hours, incomplete cursors or unavailable days remain missing. Native aggregate quantities remain separate from trade prints. Cache hashes detect local changes; they are not vendor signatures.

## File publisher contract
An explicitly selected configuration declares providers and adjacent manifests. Payload paths cannot traverse or follow symlinks. Owner-controlled regular files, exact wire shape, hashes, limits and manifest-last publication protect admission. A raced or malformed batch is rejected atomically; omitted current members cannot remain authoritative merely because old rows are persisted.

## Qualification limit
The code and retained release evidence document admitted semantics at their observation times. This package makes no new live provider request and cannot guarantee that an external provider is presently reachable or unchanged. Full current readiness requires fresh source-bound observations, not these documents.

## Source and authority anchors

- [connector/broker_depth.py](../../src/sfm_fx_new_age/connector/broker_depth.py#L22)
- [connector/kraken_public.py](../../src/sfm_fx_new_age/connector/kraken_public.py#L34)
- [connector/kraken_weekly.py](../../src/sfm_fx_new_age/connector/kraken_weekly.py#L18)
- [connector/bitstamp_feed.py](../../src/sfm_fx_new_age/connector/bitstamp_feed.py#L27)
- [connector/analytical_feed.py](../../src/sfm_fx_new_age/connector/analytical_feed.py#L31)
- [services/supplemental.py](../../src/sfm_fx_new_age/services/supplemental.py#L13)
- [services/supplemental_files.py](../../src/sfm_fx_new_age/services/supplemental_files.py#L21)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
