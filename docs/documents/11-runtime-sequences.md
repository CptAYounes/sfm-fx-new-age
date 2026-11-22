# NA-D11 — Runtime Scenarios and Sequence Design

**Document:** NA-D11 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_DYNAMIC_VIEW · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Scenario A — Ordinary desktop startup
The CLI selects explicit/XDG state, constructs the runtime with native analytical feed support, then imports Qt and opens the application. Construction itself does not authenticate. GUI startup may resume an already consented remembered session. Account inventories/authentication and the exact prior selection precede source-bound metadata/history/feed work. Missing lanes remain partial; healthy pairs continue.

## Scenario B — Analytical observation to local proposal
An admitted source change dirties its pair. The scanner builds causal inputs and schedules supported projection calculations. The owner validates returned tokens, method switches, source/profile identity and expiry before persistence. The signal sink materializes a versioned policy observation. Tab 4 reads current eligibility without writing. The human chooses a ready row and explicit units, then binds the current opportunity into SignalService. This path has no transport submission.

## Scenario C — Issue success or uncertainty
The separate human Issue action calls the same preflight used by preview. The core validates the queued revision, account/scope, research acknowledgement, candidate lineage, continuity, native spec and price semantics. A transaction inserts one unique order reservation and marks the signal reserved. Only then does the transport receive the pending Limit request. Native acceptance maps broker order identity; an exception/timeout yields UNKNOWN. No timer or reconnect automatically resends it.

## Scenario D — Source withdrawal and recovery
A disconnect or pair metadata withdrawal removes current authority and rejects late worker results. Persisted observations remain historical. Healthy pairs may continue. Restoration requires current bindings and new valid observations; a new epoch cannot borrow old books, quote freshness or authentication.

## Scenario E — Restart reconciliation
A persisted in-flight order becomes uncertain on recovery. The user restores the matching authenticated account and reconciles native facts. Local cancellation of unissued signals cannot remove a broker pending order. Separate broker cancellation requires an exactly confirmed pending identity. The sequence diagrams expose these distinctions rather than drawing a fictitious exactly-once external transaction.

## Source and authority anchors

- [__main__.py](../../src/sfm_fx_new_age/__main__.py#L12)
- [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36)
- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [services/strategy_signals.py](../../src/sfm_fx_new_age/services/strategy_signals.py#L17)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
