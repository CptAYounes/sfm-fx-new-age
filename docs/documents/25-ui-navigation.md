# NA-D25 — UI Architecture, Navigation and Interaction Specification

**Document:** NA-D25 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_UI_DESIGN · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Workspace structure
The four main tabs are Chart Engine, Trading Tools, Strategy Research/Scanner/LogicTiles, and Signals/cTrader Trading Operations. Stable backend IDs remain 10/10/13/9; Tab 2 exposes dynamic contained tools rather than ten engineering pages. Ctrl+1 through Ctrl+4 select main tabs. Ctrl+K focuses View outside Tab 2 and is not reused as the vendor Ask-line shortcut.

## Source-bound navigation
Open in…, Show on Chart, Inspect in Research, Calculate scenario, Review signal and Return carry an immutable inspection envelope. It includes namespace, epoch, pair/frame, as-of, object identity/revision/hash and permitted mode. Destination validation occurs before actions. Historical inspection does not silently select another account or import current-only broker inventory. With no source, the V23 research-to-signal navigation may carry view coordinates only, never fabricate an inspection context.

## Chart interaction
Completed observed bars and optional forming observations remain separate. Pan/zoom, rulers, annotations, colour/style editing and scenario overlays are local display operations. Blank future space is not reported as a candle. Source changes archive old-epoch drawings and clear current authority. Apply/Cancel and expected-version guards preserve transactional editing; undo/redo remains local.

## Dense information and reachability
Caption rails, paging, temporary chart focus and details inspectors reduce clutter without disabling selected methods or moving analytical prices. Native/fixture labels and freshness remain visible. Rendering budgets are display limits, not zero-inventory assertions. Compact controls use the existing scrollable pages; no hidden broker action is introduced by a chart gesture.

## Review acknowledgement
Selection/revision changes reset acknowledgement. Local binding and Issue remain distinct controls and views. An error clears stale actionable selection rather than leaving a previously valid button attached to another record. Calculator handoffs are opt-in and preserve manual edits; gross scenario output is not risk approval.

## Source and authority anchors

- [app.py](../../src/sfm_fx_new_age/app.py#L30)
- [ui/navigation.py](../../src/sfm_fx_new_age/ui/navigation.py#L9)
- [ui/chart_workspace.py](../../src/sfm_fx_new_age/ui/chart_workspace.py#L17)
- [services/workflow.py](../../src/sfm_fx_new_age/services/workflow.py#L15)
- [tabs/tab2/workspace.py](../../src/sfm_fx_new_age/tabs/tab2/workspace.py#L12)
- [ui/inspection_panels.py](../../src/sfm_fx_new_age/ui/inspection_panels.py#L14)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
