# NA-D51 — Compatibility and Interoperability Specification

**Document:** NA-D51 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_COMPATIBILITY · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Compatibility matrix
| Dimension | Current contract | Qualification boundary |
|---|---|---|
| OS/display | Debian/X11 desktop | No blanket Windows/macOS/Wayland/mobile certification |
| Python | Metadata >=3.13; retained/tested 3.13 environment | Future interpreter support requires actual checks |
| GUI | PySide6 | OS XCB/GL/fonts remain external dependencies |
| cTrader account class | Demo/live metadata, no application gate | Authentication/scope/current-source checks still required |
| Symbols | Exact active fiat pair identity from native assets/specs | No guessing ambiguous suffix variants |
| Timeframes | W1/D1/H4/H1 | No arbitrary timeframe expansion |
| Public analytics | 83 declared profiles | Not every discretionary variant |
| Historical study | 14 supported marker models | Not every analytical method as an executable strategy |
| Tab integration | Additive scoped API v1 | Same-process trusted extensions only |

## Broker interoperability
Native symbol names need not equal canonical pair strings. The resolver uses authoritative base/quote asset identities and exact native IDs. Partial/ambiguous/disabled metadata withholds only affected lanes. Native IDs cannot silently rebind during an active epoch. Pip/tick sizes, lot units and volume min/max/step come from the destination broker, not a universal 0.01-lot assumption.

## Currency interoperability
Account currency/exponent and symbol currency metadata remain explicit. Research conversion uses available source-bound direct/inverse observations and conservative Decimal estimates. Missing/stale conversion remains unavailable. Account-class agnosticism does not automatically prove every money calculation is currency-agnostic.

## Protocol/data compatibility
Broker displayed depth, venue checksum L2, predecessor-chain full public orders and integer-sequenced books remain distinct evidence kinds. FIX Price credentials are separate from OAuth. Version changes retain immutable predecessor bytes and known preferences. No compatibility claim licenses translating weaker evidence into a stronger source claim.

## Upgrade review
Check contract fields, source scaling/clocks, persisted versions, saved preferences and installed payload together. A package import or generic protocol enum alone is not operational provider compatibility.

## Source and authority anchors

- [pyproject.toml](../../pyproject.toml#L1)
- [connector/symbols.py](../../src/sfm_fx_new_age/connector/symbols.py#L8)
- [connector/protocol.py](../../src/sfm_fx_new_age/connector/protocol.py#L8)
- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
