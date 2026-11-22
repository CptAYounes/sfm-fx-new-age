# NA-D43 — Monitoring, Diagnostics and Troubleshooting Guide

**Document:** NA-D43 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_OBSERVABILITY_AND_RUNBOOK · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Available observability
The connection dialog exposes endpoint/account state, history/subscription counts, analytical-source states and compute metrics. Router metrics include queue counts by priority, subscribers, callback errors, published/delivered topics and maximum observed latency. Projection metrics include submitted/completed/accepted/coalesced work, active/pending lanes, worker errors and joined state. These are local diagnostic snapshots, not an installed external monitoring service.

| Symptom | First checks | Do not infer |
|---|---|---|
| Blank chart | Current scope/epoch, pair metadata, history lane and cutoff | Need to generate candles |
| Method Data needed | Exact genuine input kind, scope, window and expiry | Indicator is broken or No setup |
| No setup | Method enabled, completed causal input and disclosed trigger | Missing implementation merely because no signal |
| Stale/blocked signal | Both quote clocks, projection/profile identity, continuity | Acknowledge can override it |
| Missing pair | Authoritative asset mapping and lane-local failure | All siblings must stop |
| UNKNOWN order | Matching native reconcile and client/broker IDs | Safe to resend |
| High CPU/stall | Owner pump/heartbeat and worker queues separately | More workers solve serial I/O/rendering |
| Login failure | Sanitized configured identity/error/renewal state | Masked secrets are necessarily wrong |

## Diagnostic evidence
Record aware time, application/package identity, exact source namespace/epoch and error class. Preserve failed receipts. Do not include tokens, credential-bearing URLs, raw private errors or normal databases in a casual report. A callback error can coexist with a responsive process; inspect the error ring rather than relying on window visibility.

## Safe offline checks
`--check`, `--summary-json` and `--offline-checkpoint` are headless/offline paths. Connected verifiers and acquisition flags are separate operations that require their defined current state and task scope. Do not run the generic full check script as a substitute for a bounded authorized native diagnostic.

## Monitoring gap
No on-call alert routing, telemetry server, user notification SLA or indefinite watch service was installed/found as a release commitment. Threshold/alert automation requires its own owner-approved design and privacy boundary.

## Source and authority anchors

- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [core/router.py](../../src/sfm_fx_new_age/core/router.py#L15)
- [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11)
- [ui/feed_connection.py](../../src/sfm_fx_new_age/ui/feed_connection.py#L10)
- [checks.py](../../src/sfm_fx_new_age/checks.py#L11)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
