# NA-D53 — Usability, Accessibility and Human Factors Specification

**Document:** NA-D53 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_UI_ASSESSMENT_AND_PROPOSALS · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Existing usability controls
Four stable workspaces, View/Previous/Next navigation, keyboard tab shortcuts and contained tools reduce navigation ambiguity. Compact cards use the shared navy/slate theme and DejaVu Sans. Scrollable pages keep lower controls reachable at compact sizes. Chart-local focus, caption paging, details inspectors and full-value tooltips reduce dense analytical clutter without changing calculations or switches.

## Safety-related human factors
The UI distinguishes source provenance from freshness, analytical signal from local binding, and local intent from native pending/position observations. A changed selection/revision resets acknowledgement. Errors clear stale actions. Calculator adoption/replacement is opt-in; manual values survive navigation. Internal invalidation is not labelled as active broker protection.

## Accessibility assessment
Existing shortcuts, configurable chart colours/text sizes and high-contrast chart preset support some accessibility needs. They are not evidence of complete screen-reader support, WCAG conformance, colour-vision certification, touch usability or every keyboard-only workflow. No formal assistive-technology audit was performed by this task.

## Proposed acceptance scenarios
- At compact and normal desktop sizes, reach essential review/bind/study controls without clipped actions.
- Identify state by text and source context, not colour alone.
- Navigate main workspaces by keyboard and preserve a visible focus indicator.
- Inspect exact full values when captions elide or offscreen geometry is omitted.
- Change source during a dialog and verify stale edits/actions are refused.
- Verify acknowledged signal identity remains understandable before Issue.

## Remaining design tradeoffs
All 83 enabled projections can still produce intersecting geometry. Paging solves caption access, not universal visual separability. Sparse time axes and display budgets are disclosed limits. Future accessibility work should test actual users/devices and assistive technologies rather than infer compliance from a dark theme or shortcut list.

## Source and authority anchors

- [ui/navigation.py](../../src/sfm_fx_new_age/ui/navigation.py#L9)
- [ui/theme.py](../../src/sfm_fx_new_age/ui/theme.py#L15)
- [ui/chart_projection_bar.py](../../src/sfm_fx_new_age/ui/chart_projection_bar.py#L6)
- [ui/chart_projection_details.py](../../src/sfm_fx_new_age/ui/chart_projection_details.py#L7)
- [ui/research_study.py](../../src/sfm_fx_new_age/ui/research_study.py#L12)
- [tests/test_gui_navigation_refinement.py](../../tests/test_gui_navigation_refinement.py#L16)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
