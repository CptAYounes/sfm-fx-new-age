# NA-D10 — Component Design and Responsibility Allocation

**Document:** NA-D10 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_COMPONENT_VIEW · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Ownership map
| Owner | Responsibility | Main consumers |
|---|---|---|
| Runtime/component registry | Composition, command dispatch, selection and lifecycle | All four tabs |
| Market/continuity/timeline | Scoped bars, quotes, native specs, calendars and gaps | Charts, scanner, preflight |
| Catalogue/consumer services | Parameters, recipes, variables, surfaces and switches | Research editor and scheduler |
| Research/projection services | Immutable evidence, analytical objects and current pointers | Chart layers and research inspectors |
| StrategySignalService | Policy observations, current research states and local binding | Tab 4 Strategy signals |
| SignalService | Local queued proposal revisions and terminal local states | Issue queue and order owner |
| OrderService | Shared preflight, atomic reservation, native outcome and cancellation | Deliberate Tab 4 actions |
| PositionService | Read-only native position observations | Operations/inspection |
| ReplayService | Isolated causal datasets, run clock and saved studies | Chart/Research replay |
| ConnectorService | Authentication, account/source bindings and all acquisition | Domain owners through admitted facts |

## Declared components versus delivered domains
The registry currently wires 29 component identities and 41 declared routes. These counts demonstrate contract wiring, not that every named domain or every scanner node has a complete independent implementation. Unsupported capability must return explicit unavailability rather than fake success.

## Shared-spine ownership
Contracts, core, services, connector, storage, shared UI and composition files are coordinator-owned according to the canonical diary. Tab-specific folders may contribute through their existing hooks but cannot independently fork shared services. One source of truth for parameters, market state and broker transport avoids contradictory cross-tab behavior.

## Integration contract
A component receives typed immutable events or validated commands, owns its mutation and emits scoped results. A tab's closing operation disposes its subscriptions, not the shared runtime. A callback error is recorded without starving other subscribers. Database transaction boundaries, object identity and expected-version checks must be preserved when responsibilities move between modules.

## Source and authority anchors

- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [core/components.py](../../src/sfm_fx_new_age/core/components.py#L13)
- [services/market.py](../../src/sfm_fx_new_age/services/market.py#L16)
- [services/research.py](../../src/sfm_fx_new_age/services/research.py#L15)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [services/strategy_signals.py](../../src/sfm_fx_new_age/services/strategy_signals.py#L17)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
