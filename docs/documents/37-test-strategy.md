# NA-D37 — Software Test and Quality Assurance Strategy

**Document:** NA-D37 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_TEST_BASELINE_AND_GUIDANCE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Test layers
| Layer | Purpose | What it cannot prove |
|---|---|---|
| Static architecture/contracts | Ownership, imports, identities and declared wiring | Native source or broker behavior |
| Pure algorithm/domain | Numeric semantics, causality, units and invalid inputs | Profitability or provider availability |
| Fixture integration | Binding, preflight, Issue state machine and restart | Real broker acceptance |
| Actual Qt widgets/offscreen | Navigation, controls, acknowledgement and disposal | Every display/desktop combination |
| Source/installed parity | Same exact cases and package payload | Future dependency compatibility |
| Native read-only lifecycle | Real ordinary startup, observed sources and shutdown | New broker-action permission |
| Explicit broker-action proof | Bounded authorized transport outcome | Strategy quality or permission to repeat |
| Saved-evidence readers | Hash/source/outcome reconciliation | A new current native observation |

## Existing estate
The retained V23 candidate-04 record contains 76 test modules and 1,541 cases in each source/isolated-installed estate, executed in ten disjoint bounded groups. It is not represented as a single monolithic pytest run. The test inventory appendix preserves exact function/parameterized-case identities and records their evidence class.

## Documentation-time checks
This task freshly executed 171 offline tests in ten selected modules, architecture checks, runtime summary and the synthetic restart checkpoint. This fresh subset does not replace full V23 acceptance or refresh its native timing/source observations. No new broker action, provider acquisition or normal-state edit was used.

## Quality rules
Keep fixture origins visibly synthetic. Test exact identity-set membership, not just counts. Include positive output and stale/wrong-source/refusal paths. Retain historical failures and successful successors separately. A skipped SDK test is not native acceptance; a timeout is not a pass. Preserve unchanged production/test bytes when verifying documentation-only changes.

## Future selection
Choose affected layers from the change-impact matrix. Run bounded groups when whole-process Qt/resource lifetime makes one suite unreliable, then reconcile collection and terminal outcomes mechanically. Do not infer passing totals from progress dots or earlier reports.

## Source and authority anchors

- [tests/conftest.py](../../tests/conftest.py#L7)
- [tests/test_architecture_fences.py](../../tests/test_architecture_fences.py#L13)
- [tests/test_strategy_signal_positive.py](../../tests/test_strategy_signal_positive.py#L14)
- [tests/test_connector_boundary.py](../../tests/test_connector_boundary.py#L18)
- [PROGRESS.md](../../PROGRESS.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
