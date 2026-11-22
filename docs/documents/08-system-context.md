# NA-D08 — System Context and External Interfaces

**Document:** NA-D08 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_CONTEXT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## System boundary
The managed application is the New Age desktop process and its owned children, durable state and explicitly configured input adapters. The human operator, browser/cTrader authorization service, broker endpoints, public venues, official context publishers and external file publishers are outside that boundary. The older SFM FX Engine and cBot runtime are not hidden New Age dependencies.

## External relationships
| External actor/system | Exchange | Trust limit |
|---|---|---|
| Operator | Account/method choices, units, binding, Issue/cancel confirmation | Local authenticated user context, not remote multi-user authorization |
| System browser | Human OAuth grant and loopback callback | Exact registered redirect and single-use state |
| cTrader Open API | Account inventory, specs, schedules, prices, history, reconcile and deliberate order/cancel | Selected broker/account/endpoint namespace |
| Kraken public | Exact fiat executions, quantities, taker sides and checksum depth | Venue-specific data, not global FX |
| Bitstamp public | Corroborated predecessor-linked public order book | Two declared fiat pairs and displayed public orders only |
| CFTC/Board sources | Published context | Futures/declared calendar coverage only |
| Local publisher | Hash-checked adjacent JSON payloads | Declared provider provenance, not independent vendor authentication |

## Availability dependencies
The GUI and offline research/checks can run without broker access. Current connected research requires authenticated source bindings and the method's genuine inputs. An unavailable venue affects the relevant input rather than licensing a substitute under the original name. Optional FIX Price access needs separate credentials and is not a normal-start dependency.

## Data-flow rule
External bytes enter through connector/admission owners, then typed source validation, persistence and analytical services. They do not enter a chart directly or become executable instructions. The context diagram distinguishes data edges from the deliberate broker-mutation edge so a read-only feed is never drawn as an autonomous trader.

## Source and authority anchors

- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [connector/analytical_feed.py](../../src/sfm_fx_new_age/connector/analytical_feed.py#L31)
- [connector/kraken_public.py](../../src/sfm_fx_new_age/connector/kraken_public.py#L34)
- [connector/bitstamp_feed.py](../../src/sfm_fx_new_age/connector/bitstamp_feed.py#L27)
- [services/supplemental_files.py](../../src/sfm_fx_new_age/services/supplemental_files.py#L21)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
