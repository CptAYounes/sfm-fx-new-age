# R11 — Command Line Reference

Extracted from the actual parser. Acquisition/capture flags may connect and need deliberately scoped authorization; they are not executed by these documents. Parser branches impose additional exclusivity constraints.

| Flag | Action/default | Actual help |
|---|---|---|
| --check | store_true / not explicitly supplied | run architecture checks |
| --summary-json | store_true / not explicitly supplied | print runtime summary |
| --offline-checkpoint | store_true / not explicitly supplied | exercise synthetic shared backend and restart reconciliation, no network |
| --fixture-session | store_true / not explicitly supplied | open explicitly labelled in-memory synthetic UI session, not real market data |
| --strict-genuine-data | store_true / not explicitly supplied | disable tick/quote-activity substitutes; require genuine executions/aggressors or scoped displayed DOM as appropriate, without claiming a complete native venue book |
| --compute-workers | store / auto | pure analytical process ceiling: auto uses available CPUs/quota/memory and reserves a core slot; 1 is serial |
| --state-dir | store / not explicitly supplied | override local application state directory |
| --supplemental-config | store / not explicitly supplied | explicit local read-only analytical source configuration; never opens a network feed |
| --validate-supplemental-config | store / not explicitly supplied | validate source configuration without Qt, input admission, authentication or database writes |
| --acquire-official-context | store / not explicitly supplied | one-shot original CFTC/Federal Reserve Board HTTPS acquisition into a new directory, bound to saved source epochs; no GUI, credentials or broker calls |
| --acquire-original-inputs | store / not explicitly supplied | bounded read-only capture of original broker bars/ticks and CFTC/Board context into a new isolated directory; all SDK processes are joined before return |
| --capture-original-depth | store / not explicitly supplied | bounded native broker depth capture into a new private directory; no invented venue sequence or DOM admission |
| --audit-native-feed | store / not explicitly supplied | bounded real cTrader quote/history/depth health and installed-protocol capability audit; no trades or synthetic data |
| --prepare-original-point-figure | store / not explicitly supplied | validate a source-hash-bound operator count request and prepare original P&F ticks; no network or automatic count settings |
| --capture-fix-depth | store / not explicitly supplied | bounded TLS FIX Price full-book capture; fails before network if separate private FIX credentials are absent |
| --fix-price-credentials | store / not explicitly supplied | existing user-owned 0600 private FIX Price JSON; never OAuth, cTID or Trade credentials |

## Safe fresh checks executed here

`--check`, `--summary-json` and `--offline-checkpoint` completed in separate headless offline invocations. See the saved receipts. `--fixture-session` is labelled synthetic. Ordinary GUI startup may reconnect only an already consented remembered session.
