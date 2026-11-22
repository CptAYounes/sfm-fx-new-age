# NA-D09 — Container and Process Architecture

**Document:** NA-D09 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_PROCESS_VIEW · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Logical execution containers
“Container” here means an executable/storage boundary, not an assertion that production uses Docker. Ordinary operation is a user-local desktop application. Clean Debian container runs are retained packaging/acceptance environments, not a requirement to deploy the desktop inside a container.

| Boundary | Owns | Must not own |
|---|---|---|
| Qt/application owner process | GUI, runtime pump, command routing, domain writes and result admission | Blocking SDK reactor loop |
| SDK child process per configured endpoint | Native protocol framing, TLS and bounded command/event queues | Arbitrary user code or blind order replay |
| OAuth callback/authentication worker | Browser grant/callback and token exchange | Unscoped account selection or Issue |
| Public-source workers | Bounded acquisition/corroboration for declared providers | Core SQL writes and broker commands |
| Projection child processes | Supported pure analytical math | Qt, secrets, database handles or execution authority |
| SQLite database | Durable scoped facts, local orders and event journal | Proof of current authentication |
| Private credential file | Application/token material | Encrypted-keychain claim |

## Communication
Worker outputs return through bounded queues and connector-owned bindings. The owner validates source/generation and commits accepted results. The event router uses P0–P3 priorities and owner-thread callback drains. Immutable projection snapshots are inputs to spawned jobs; job tokens and current state are checked when results return.

## Shutdown and faults
Closing the runtime cancels queued calculations, joins compute children, stops connector/feed/authentication resources and closes persistence. A worker fault remains visible and cannot authorize a stale result. A transport exception after possible external send creates uncertainty, not a fresh command on restart.

## Architectural consequence
Parallelism is selective. More CPUs do not make persistence, broker actions or GUI state concurrent authorities. Process containment reduces coupling but is not a complete hostile-code sandbox. Analytical extension authors remain trusted local developers operating under API/architecture fences.

## Source and authority anchors

- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16)
- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11)
- [connector/kraken_public.py](../../src/sfm_fx_new_age/connector/kraken_public.py#L34)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
