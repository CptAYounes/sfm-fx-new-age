# NA-D26 — Plugin and Extension Developer Specification

**Document:** NA-D26 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_EXTENSION_CONTRACT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Extension types
New Age has tab/view factories, dynamic Tab 2 tools and install-time analytical producer registration. These are separate extension mechanisms with distinct ownership. There is no documented arbitrary remote plugin marketplace or hostile-code sandbox.

## Tab and tool contributions
A TabPlugin can claim only its own declared backend identities. Duplicate/nonexistent registrations fail. Tab 2 tools register a stable tool ID, title and factory. Opening creates a fresh scoped TabApi and Qt parent; reopening an already open identity focuses it. Closing releases its consumers and widgets, not the shared connector/database/runtime. Factories must not launch a second feed or order gateway.

## Analytical contributions
The backend loader discovers lane-owned installers. The temporary AnalyticalExtensionApi permits source-backed sensors, variables, recipes and pure evaluators under explicit ownership. It closes after installation. Execution nodes cannot be replaced by an analytical extension. Missing inputs and unsupported capability remain explicit. Research output must not smuggle commands, units or broker identities into a publication.

## Required engineering contract
1. Declare stable identities, semantic version, input units and provenance before registering.
2. Validate bounded outputs and causal clocks; preserve UNKNOWN/unavailable semantics.
3. Use shared variable/parameter/research owners rather than private SQL or caches with independent authority.
4. Release every subscription on close and reject disposed APIs.
5. Test duplicate ownership, wrong-tab access, stale sources, restart and positive calculation.

## Parallelism and trust
Only shipped recognized pure public evaluators are sent to projection processes; custom analytical handlers remain serial. An extension is trusted application code: access restrictions are facade/architecture contracts, not isolation against malicious same-process introspection. New untrusted-code support would require a separate design, security review and deployment model, not just an additional factory registration.

## Source and authority anchors

- [tabs/base.py](../../src/sfm_fx_new_age/tabs/base.py#L18)
- [tabs/loader.py](../../src/sfm_fx_new_age/tabs/loader.py#L8)
- [tabs/backend_loader.py](../../src/sfm_fx_new_age/tabs/backend_loader.py#L6)
- [core/analytical_api.py](../../src/sfm_fx_new_age/core/analytical_api.py#L14)
- [tabs/tab3/backend.py](../../src/sfm_fx_new_age/tabs/tab3/backend.py#L9)
- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
