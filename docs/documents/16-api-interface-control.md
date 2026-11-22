# NA-D16 — API Design and Interface Control Document

**Document:** NA-D16 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_INTERFACE_CONTRACT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Public integration surfaces
`TabApi` version 1 exposes scoped snapshots, bounded queries, capability discovery, commands, subscriptions and inspection/replay helpers. It is a Python in-process API, not a deployed REST service. No new HTTP endpoints or OpenAPI specification is fabricated for an application that does not expose them.

| Operation | Contract |
|---|---|
| `snapshot(subtab_id)` | Immutable view snapshot only within the tab's declared identities |
| `query(subtab_id, DataRequest)` | Read-only dataset allowlist, current scope and bounded pagination |
| `capabilities(subtab_id)` | Explicit implemented/partial/snapshot-only/unimplemented state |
| `command(subtab_id,name,payload)` | Declared subtab command and exact payload validation |
| `subscribe` / `subscribe_snapshots` | Owner-thread callbacks with explicit release |
| `inspect` / `navigate` | Immutable source-bound handoff; target permission checks |
| `close()` | Dispose that consumer, not shared services |

The generated command matrix enumerates required/optional fields and the exact subtab owners. A syntactically valid command is not necessarily eligible at runtime: source, revision, account and freshness checks remain with the service owner.

## Extension interface
`AnalyticalExtensionApi` is supplied during installation, then closed. It permits bounded analytical registration, not replacement of execution owners. `TabPlugin` registration remains lane-scoped. A Trading Tools factory receives a fresh scoped API and Qt parent; it must release its API/subscriptions on closure.

## Errors and compatibility
Wrong-tab access, disposed handles, unsupported datasets, malformed payloads and stale revisions are explicit failures. Unknown domain capability must not be represented as accepted. Additive API v1 helpers retain existing scope/lifecycle rules; semantic changes require versioned definitions and consumer regression checks.

## Trust limit
This facade and static import fences constrain cooperating application code; they do not turn Python objects into a security sandbox against a malicious same-process extension. Loading untrusted arbitrary plugins is outside the qualified extension model.

## Source and authority anchors

- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [core/analytical_api.py](../../src/sfm_fx_new_age/core/analytical_api.py#L14)
- [contracts/commands.py](../../src/sfm_fx_new_age/contracts/commands.py#L58)
- [contracts/tab_data.py](../../src/sfm_fx_new_age/contracts/tab_data.py#L30)
- [tabs/base.py](../../src/sfm_fx_new_age/tabs/base.py#L18)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
