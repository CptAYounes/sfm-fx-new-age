# NA-D04 — Domain Glossary and Terminology

**Document:** NA-D04 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** REFERENCE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Identity and time
| Term | Meaning in New Age |
|---|---|
| Account scope | Serialized broker, endpoint, account and origin namespace |
| Source epoch | Particular connection/source generation; not a revision number |
| Origin | LIVE_OBSERVED, HISTORICAL_REPLAY or SYNTHETIC_FIXTURE |
| Availability | When an observation became available to the application |
| Event time | Original market/source event time; not refreshed by publication |
| Revision | Correction or definition version within an identified object |
| Fingerprint | Content/identity digest; integrity binding, not vendor authentication |
| As-of | Aware UTC cutoff limiting causally available observations |

## Research and action
| Term | Meaning |
|---|---|
| Public method | Versioned bounded analytical profile, not an assured trading system |
| Projection | Source-bound series, marker or region for research/display |
| No setup | Evaluated inputs did not produce an eligible setup |
| Data needed | Required genuine input is missing; not No setup |
| Research signal | A method output interpreted by its disclosed entry policy |
| Bind | Human creation of a local queued proposal with explicit units |
| Issue | Separate deliberate request to create one new pending Limit order |
| Internal invalidation | Research geometry; not a broker stop or guaranteed loss limit |
| UNKNOWN | External outcome unresolved; resubmission is unsafe |
| Reconcile | Match authoritative native facts to existing local identities |
| Native inventory | Last-observed broker pending orders/positions, not automatic local adoption |

## Source semantics
Tick volume is quote activity, not executed volume. Broker DOM is observed displayed liquidity with a local receipt clock, not a complete global book. Kraken executions and taker sides are venue context, not cTrader fills. Checksum L2 and predecessor-linked full public orders are different book claims. CFTC is mapped futures positioning context; Board calendar data is its admitted official subset, not a complete economic calendar.

## Documentation language
“As-built” means inspected source behavior. “Retained qualification” means a historical evidence record. “Fresh check” means executed during this documentation task. “Recommended” denotes a proposed maintenance practice, not a newly implemented feature or owner approval. “Complete” always names the finite artifact or acceptance scope it covers.

## Source and authority anchors

- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [contracts/analytics.py](../../src/sfm_fx_new_age/contracts/analytics.py#L14)
- [contracts/strategy_signals.py](../../src/sfm_fx_new_age/contracts/strategy_signals.py#L13)
- [services/positions.py](../../src/sfm_fx_new_age/services/positions.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
