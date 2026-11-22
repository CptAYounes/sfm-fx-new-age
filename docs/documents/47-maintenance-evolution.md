# NA-D47 — Maintenance, Evolution and Support Plan

**Document:** NA-D47 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** MAINTENANCE_PROCESS_PROPOSAL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Maintenance principles
Preserve the accepted product identity while repairing a named defect. Use current source/evidence, not older system assumptions. Keep immutable historical definitions/observations, saved literal user choices and failed qualification attempts recoverable. Distinguish normal user uptake from source/build/native acceptance.

## Change classes
| Class | Required review focus |
|---|---|
| Defect repair | Reproduce actual behavior; affected positive/refusal checks |
| Analytical semantics | Version/profile hash, causal roots, numerical parity and disclosure |
| Provider change | Exact instrument/units/sequence/time/coverage and source admission |
| UI refinement | Reachable controls, manual edits, identity-bound actions and disposal |
| Database change | Migration, old evidence preservation and restore compatibility |
| Broker-action expansion | Separate authority/hazard review and explicit approval |
| Dependency update | Isolated package/desktop/API compatibility and current security review |

## Maintenance workflow
Locate owner and exact AST anchors, identify dependent consumers, make a dependency-complete repair, run focused tests and broader required gates, then update source-linked documentation and the sole diary. Do not create a new mutable handoff/status notebook. Do not change unrelated provider/trading policy to make an engineering check easier.

## Compatibility and deprecation
Retired pairs remain historical rather than deleted. Immutable method revisions remain inspectable; newest definitions are listed by default. A supported API helper cannot quietly expand data or mutation scope. Deprecation needs a migration/retention story, consumer tests and user-visible explanation.

## Support boundary
The current qualified desktop scope is finite. Future uptime, all-platform support, every discretionary strategy interpretation, optional entitled feeds and profitable operation are not support promises. Formal support hours, escalation contacts and end-of-life dates remain owner decisions, not dates invented by this plan.

## Source and authority anchors

- [PROGRESS.md](../../PROGRESS.md#L1)
- [contracts/public_strategies.py](../../src/sfm_fx_new_age/contracts/public_strategies.py#L10)
- [contracts/registry.py](../../src/sfm_fx_new_age/contracts/registry.py#L18)
- [tests/test_recipe_upgrade_preservation.py](../../tests/test_recipe_upgrade_preservation.py#L13)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
