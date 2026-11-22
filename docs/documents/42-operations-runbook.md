# NA-D42 — Operations Runbook

**Document:** NA-D42 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** OPERATOR_PROCEDURE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Start and inspect
Launch normally using the existing shortcut or script. Confirm selected account namespace, source state and active pair/frame. Authentication, current source metadata, history completion and fresh quotes are independent. A closed-market label preserves readable history; it does not make old quotes fresh. Check per-pair missing history/input states instead of assuming one global green light.

## Routine research
Enable the methods you want in Tab 3; inspect current counts/details and source labels. Use chart focus/details to manage dense displays without disabling calculations unintentionally. Review Tab 4 Strategy signals. Off, Data needed, Waiting, No setup, stale, expired and invalidated are valid states, not reasons to manufacture a setup.

## Deliberate action
Local binding requires exact current opportunity and native-valid units. It creates a proposal only. Issue is separate and revalidates shared preflight. A software-valid preview is not account-wide risk approval or a guarantee of execution. The application does not install broker-native SL/TP or autonomous position protection.

## Uncertainty and cancellation
When an order is UNKNOWN, inspect/reconcile the matching account/native identity. Do not repeatedly press Issue, delete reservations or switch accounts to escape a blocker. Cancel unissued proposals locally; cancel a confirmed broker pending order only through its separate confirmation path. Pending acceptance never proves a position.

## Disconnect, sign out and shutdown
Disconnect stops the transport while keeping saved credentials. Sign out disables remembered reconnect and removes saved access/refresh tokens but does not cancel orders. Close the application gracefully so SDK/acquisition/compute resources join. Do not kill unrelated processes or restart the user's instance as a documentation/diagnostic convenience.

## Escalate
Escalate unresolved broker state, missing entitlement/credentials, incompatible schema or changed provider semantics. Provide sanitized source/epoch/time/error evidence. This runbook is not authorization to run connected diagnostics or a trading schedule.

## Source and authority anchors

- [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27)
- [ui/feed_connection.py](../../src/sfm_fx_new_age/ui/feed_connection.py#L10)
- [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18)
- [services/positions.py](../../src/sfm_fx_new_age/services/positions.py#L11)
- [__main__.py](../../src/sfm_fx_new_age/__main__.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
