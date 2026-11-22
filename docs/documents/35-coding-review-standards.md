# NA-D35 — Coding Standards and Code Review Checklist

**Document:** NA-D35 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** ENGINEERING_PROCESS_PROPOSAL · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Source-grounded standards
Keep shared domain/core/services/storage Qt-neutral. Tabs must not import SQL or broker SDK/order service internals. Connector code owns acquisition; runtime construction and headless checks remain offline. Typed contracts validate source identity, finite Decimal values, aware time, exact primitive types and bounded payloads at ownership boundaries.

## Review checklist
- **Ownership:** Does each mutation remain with its existing market, catalogue, signal, order or persistence owner?
- **Identity:** Are account scope, source epoch, origin, method/profile/revision and object hashes retained end to end?
- **Causality:** Could late data, correction, re-enable or publication retime a past event?
- **Failure:** Are unavailable/UNKNOWN explicit, and can a remote action be accidentally retried?
- **Atomicity:** Is an all-or-nothing workflow transactional rather than only commit-batched?
- **Resources:** Are queues/payloads/timeouts/loops bounded and task-owned children joined?
- **UI:** Do source changes clear stale actions, acknowledge resets and preserve manual edits?
- **Security:** Are credentials references rather than values, and are error texts sanitized?
- **Tests:** Is there a meaningful positive path as well as refusal coverage?
- **Evidence:** Do claims match exact execution, origins and package source?

## Versioning rules
Do not change immutable definition bytes in place. Keep stable recipe identifiers where specified, publish new semantic versions, preserve history and migrate only known literal choices. A migration must not invent absent/malformed user preferences. Public ID membership is a set assertion, not just a count.

## Practical style
Prefer small cohesive functions and explicit state transitions over hidden side effects. Do not add a second connector/database to simplify a widget. Avoid broad exception swallowing; report a safe nonsecret state. Never make a fixture/native proof claim from a plausible-looking output. This proposed checklist supplements, not replaces, the executable architecture fences.

## Source and authority anchors

- [tests/test_architecture_fences.py](../../tests/test_architecture_fences.py#L13)
- [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14)
- [contracts/commands.py](../../src/sfm_fx_new_age/contracts/commands.py#L58)
- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
