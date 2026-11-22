# NA-D57 — Developer Onboarding and Architecture Reading Guide

**Document:** NA-D57 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** DEVELOPER_GUIDE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Read in dependency order
Start with Product Charter, Scope/Authority, Architecture Description and Runtime Sequences. Read the actual `PROGRESS.md` current checkpoint and latest applicable entries before any edit. Then examine contracts/domain/registry, runtime composition, scoped API, owning service and relevant tests. Use this package's source/contract/API catalogues to locate exact symbols rather than searching by obsolete engine names.

## Establish a safe environment
Use the intended project venv; do not mix the host's global Python/pip with application dependencies. Start with headless offline checks or explicitly labelled fixtures. A fresh ApplicationRuntime is in-memory/offline by default. Ordinary GUI startup can resume a previously consented saved session, so choose disposable state for experiments instead of assuming every launch is no-network.

## First vertical slice
Follow a declared subtab snapshot through TabApi → runtime/tab-data owner → domain store. Then follow a public method through source inputs → projection → explicit policy → Tab 4 state → human local bind → separate shared preflight. Read OrderService's UNKNOWN/reconciliation path before touching any broker-facing code.

## Working rules
Keep shared-spine ownership and tab boundaries. Do not add a second database, connector or order path. Test source/epoch/origin, causal time, native grids, positive behavior and refusal. Release subscriptions/children. Preserve old immutable evidence and literal user choices. Do not claim native acceptance from fixtures or current readiness from saved rows.

## Completion and continuity
Record only verified changes, commands/results, limitations and next safe action in the sole diary. This package is an architecture/reference set, not a replacement progress notebook. No subagent workflow or additional external service is required to use it. If a task requires credentials/entitlement, obtain the smallest explicit secure input rather than guessing.

## Source and authority anchors

- [PROGRESS.md](../../PROGRESS.md#L1)
- [pyproject.toml](../../pyproject.toml#L1)
- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [tests/test_architecture_fences.py](../../tests/test_architecture_fences.py#L13)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
