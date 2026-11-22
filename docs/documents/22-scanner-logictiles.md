# NA-D22 — Scanner DAG, Variables and LogicTiles Design

**Document:** NA-D22 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_RULE_ENGINE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Scheduler design
The declared scanner graph has 44 nodes and 130 edges. The cached scheduler propagates dirty descendants and runs registered handlers; the declaration is not proof that all advanced/external nodes are implemented. Consumer and pair switches control eligible analytical work without disabling core reconciliation. Missing handlers and missing required inputs remain explicitly unavailable.

## Variables and provenance
Variables carry owned definitions, units, source namespace/epoch, as-of and expiry. A stale or prior-source variable is UNKNOWN, not a previous value reused as current. Supporting data, profiles and causal roots enter fingerprints. Related interpretations of one source cannot be counted as independent votes.

## Rule model
LogicTiles is a bounded declarative expression tree with typed comparison, arithmetic, history and temporal operators. It uses three-valued truth: missing/stale input does not become false evidence or a successful test. Rule shape is validated even when an input is unavailable, so malformed expressions cannot hide behind UNKNOWN.

| Action | Effect |
|---|---|
| Preview only | Pure evaluation, no persisted activation |
| Save draft | CAS-versioned saved rule; not active |
| Activate saved | Exact saved revision becomes analytical active definition |
| Suspend | Disable that analytical rule |
| Use prior saved | Explicitly select an existing revision, not erase history |

## Output and extension limits
Rules and producer extensions may publish analytical objects/variables only. They cannot replace execution nodes or gain database/connector/order handles through the installation facade. Configuration import cannot silently activate rules. Source/parameter changes invalidate the relevant cached work; current result visibility depends on the owner, not GUI row caching.

## Maintenance rule
A scanner change must preserve graph acyclicity, method/variable ownership, bounded evaluation, UNKNOWN semantics and source fingerprints. Review positive calculations as well as refusal cases; a graph that only returns unavailable is not evidence of delivered analytical functionality.

## Source and authority anchors

- [core/dag.py](../../src/sfm_fx_new_age/core/dag.py#L9)
- [services/scanner.py](../../src/sfm_fx_new_age/services/scanner.py#L16)
- [services/rules.py](../../src/sfm_fx_new_age/services/rules.py#L11)
- [services/catalogues.py](../../src/sfm_fx_new_age/services/catalogues.py#L12)
- [core/analytical_api.py](../../src/sfm_fx_new_age/core/analytical_api.py#L14)
- [tabs/tab3/authoring.py](../../src/sfm_fx_new_age/tabs/tab3/authoring.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
