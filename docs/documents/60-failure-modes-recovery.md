# NA-D60 — Failure Modes, Recovery Matrix and Residual Guarantees

**Document:** NA-D60 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_FAILURE_DESIGN · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Recovery matrix
| Failure mode | Required application state | Safe recovery | Unsafe shortcut |
|---|---|---|---|
| No authenticated source | Unavailable/disconnected | Explicit current authorization/selection | Trust saved account metadata |
| One history lane fails | Pair/frame-local partial state | Inspect explicit job; new bounded recovery when appropriate | Borrow old-epoch bars or lock healthy siblings |
| Quote side ages/crosses | Stale/withdrawn eligibility | New coherent same-source sides | Retimestamp old side |
| Supplemental batch corrupt/raced | Atomic reject/withdraw | Valid new exact manifest/publication | Admit partial rows or trust stale cache |
| Book sequence/CRC failure | Poisoned/withdrawn source | Fresh native bootstrap/corroboration | Invent sequence or ignore mismatch |
| Trigger expires/invalidates | Terminal old setup | Independently new causal setup | Re-enable to restart lifetime |
| Process result arrives late | Discard | Current owner evaluation | Commit old token/profile |
| Submit/cancel outcome uncertain | UNKNOWN | Matching native reconcile | Resend/delete reservation |
| Crash after reservation | Durable uncertain order | Reauthenticate/reconcile | Treat local rollback as external undo |
| Empty position cache | Unknown unless complete observed snapshot | Current native observation | Claim flat account |
| Shutdown with work | Cancel queued/join children | Bounded orderly close | Leave hidden late publishers |
| Unsupported DB version | Refused open | Compatible program/verified restore | Hand-edit schema/version |

## Guarantee boundaries
The program offers application-level validation, duplicate barriers, causal evidence and explicit uncertainty. It cannot guarantee external order exactly-once delivery, provider uptime, instant cancellation, broker acceptance, financial loss limits or hostile-local-user isolation. A live-looking window does not prove current market/source health.

## Engineering response
Recover at the earliest failed owner: protocol/source authority before persistence, persistence before projection, projection before signal qualification, qualification before binding, and broker reconciliation before new Issue. Do not solve a downstream empty display by fabricating upstream evidence.

## Documentation acceptance
This matrix is complete for the named principal failure families, not an exhaustive enumeration of every OS/library/hardware fault. New capabilities add new failure modes and require their own tests/runbooks. The companion's fresh checks validate documentation and selected offline behavior only; no failure injection into the user's live application or broker was performed.

## Source and authority anchors

- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [services/continuity.py](../../src/sfm_fx_new_age/services/continuity.py#L16)
- [services/strategy_signals.py](../../src/sfm_fx_new_age/services/strategy_signals.py#L17)
- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [services/supplemental_files.py](../../src/sfm_fx_new_age/services/supplemental_files.py#L21)
- [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
