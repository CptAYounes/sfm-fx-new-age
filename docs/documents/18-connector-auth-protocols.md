# NA-D18 — Connector, Authentication and Protocol Design

**Document:** NA-D18 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_CONNECTOR_DESIGN · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Connection lifecycle
One ConnectorService supervises endpoint workers, authentication, discovered accounts, selected source bindings, subscriptions, histories and reconciliation. LIVE/DEMO are distinct namespaces and transport endpoints, not application eligibility classes. Persisted account metadata is saved unauthenticated. Multiple discovered accounts require an explicit choice except the documented single-account first-login rule after both endpoint inventories finish.

## Authentication
The browser grant uses the registered cTrader application identity and exact permitted redirect. The loopback callback has single-use random state and a bounded monotonic lifetime. An official Playground redirect supports explicit saved-refresh linking, not a fictitious local callback. Tokens are atomically saved in a user-owned 0700 directory/0600 regular file; this is permission-restricted plaintext, not an encrypted vault. Secrets never belong in the event journal or ordinary command payloads.

## Native transport
The SDK reactor runs in an isolated child, with hostname-verifying TLS and bounded command/event queues. Read requests are allowlisted. Account authentication, selected deliberate pending Limit and separate cancel paths are distinct message classes. Per-connection pacing and queue clearing prevent stale queued frames from crossing reconnects. SDK acceptance, wire transmission and broker acknowledgement are different stages.

Native symbol resolution uses authoritative asset identity and broker metadata. Ambiguous names, wrong grids and partial metadata remain explicit. Quote/history decoding preserves fixed-point scales, native clocks and immutable revisions. Request-queue admission and response budgets are separately bounded; neither extends freshness.

## Optional protocol boundary
The separate FIX Price capture requires explicit broker Price credentials, TLS, original full snapshots and native sequencing. OAuth is not a FIX password. That tool is read-only, opt-in and not recurring normal-start qualification. General FIX entitlement, all-pair native full books and execution/aggressor tapes are not inferred from implementation presence.

## Source and authority anchors

- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16)
- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [connector/protocol.py](../../src/sfm_fx_new_age/connector/protocol.py#L8)
- [connector/symbols.py](../../src/sfm_fx_new_age/connector/symbols.py#L8)
- [connector/fix_capture.py](../../src/sfm_fx_new_age/connector/fix_capture.py#L24)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
