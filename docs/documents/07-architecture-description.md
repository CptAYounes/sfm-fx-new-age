# NA-D07 — Software Architecture Description

**Document:** NA-D07 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_ARCHITECTURE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Architectural style
New Age is a desktop modular application with a shared in-process owner, typed event routing and scoped tab APIs. It is not a microservice deployment. Python owns presentation orchestration, analytical services, persistence and cTrader adapter supervision. Qt is confined to application/UI/tab presentation layers; shared domain/core/service/storage modules are Qt-neutral.

`ApplicationRuntime` is the composition root. It opens one Database, creates component/projection registries, connects domain services, installs analytical producers through a bounded extension facade, exposes four tab APIs, and owns a single connector supervisor. Its default in-memory construction is offline and fixture-free. The normal GUI entry explicitly selects durable state and native analytical feed behavior.

## Principal boundaries
- **Presentation:** `app.py`, `ui/` and tab widgets render scoped snapshots and invoke allowlisted commands.
- **Application/core:** owns dispatch, current selection, subscriptions, pump scheduling and inter-workspace inspection.
- **Domain/services:** owns market history, catalogues, research, rules, projections, signals, order preflight and reconciliation.
- **Infrastructure:** SQLite persistence, isolated SDK reactor processes, OAuth store and bounded public-source workers.
- **Pure compute:** spawned jobs calculate supported projections from immutable bounded snapshots; owner revalidates results before commit.

## Critical design invariants
There is one authoritative Issue edge, one shared market/persistence ownership graph, and no network acquisition in a chart or research plugin. Durable authentication metadata does not restore authority. A current projection must satisfy source/epoch/profile identity and expiry. Research output cannot carry execution fields.

## Viewpoint navigation
The context document explains actors and external systems. Container/deployment documents describe processes and storage. Component and API references locate exact owners. Runtime sequences explain successful and uncertain paths. Data, temporal and source documents explain validity. Security, safety and qualification documents state residual limits. The architecture is complete only when these viewpoints agree; a box diagram alone does not prove operational readiness.

## Source and authority anchors

- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [services/scanner.py](../../src/sfm_fx_new_age/services/scanner.py#L16)
- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [app.py](../../src/sfm_fx_new_age/app.py#L30)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
