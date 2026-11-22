# NA-D29 — Configuration, Parameter Registry and Environment Reference

**Document:** NA-D29 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_CONFIGURATION · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Configuration layers
| Layer | Owner and persistence | Limitation |
|---|---|---|
| CLI flags | Main entrypoint; generated CLI reference | Certain capture/check modes are mutually exclusive |
| State location | `--state-dir` or absolute XDG data directory | A path is not authentication |
| Registered parameters | Catalogue definitions plus CAS history | Type/range/owner constraints remain controlling |
| Pair overrides | Selected-account/pair namespace | Global changes and pair changes invalidate different scopes |
| Method/consumer switches | Durable preferences | Enablement is not data readiness or Issue authority |
| Supplemental configuration | Explicit per-launch local publisher declaration | Saved evidence cannot restore provider authority |
| Credentials | Private file through connector owner | Never ordinary configuration/journal data |

## Inspected defaults
The source registers quote age at 30 seconds, pivot-left/right at two completed bars and five ordered ATR-band boundaries. The generated parameter reference preserves exact units/defaults/limits. These are engineering/research defaults, not new trading policy approval. Native broker min/max/step/tick metadata governs actual order legality; no universal lot step is inferred from the calculator.

## Update semantics
Edits validate expected version, exact types and known owner surfaces. Pair settings bind expected account scope. Configuration import is atomic and conflict-checked; it cannot silently activate analytical rules. UI refresh preserves unapplied edits and their original concurrency baseline. Unknown/malformed choices are not turned into newly enabled preferences.

## Research money
Capital-context denominator starts UNCONFIGURED. BALANCE uses observed native balance/currency/exponent; EQUITY remains unavailable without an authoritative implementation. An optional positive scenario budget drives research estimates only. Estimates do not auto-fill units, reserve capital or set account-wide risk permission. `approved_amount` remains unset and `account_risk_permission` false.

## Operator caution
Do not include secret/token values in command examples, bug reports or exported configuration. Record the setting identity/version and sanitized error instead. Changing a freshness setting does not renew source timestamps or extend a trigger's original expiry.

## Source and authority anchors

- [__main__.py](../../src/sfm_fx_new_age/__main__.py#L12)
- [contracts/defaults.py](../../src/sfm_fx_new_age/contracts/defaults.py#L6)
- [services/catalogues.py](../../src/sfm_fx_new_age/services/catalogues.py#L12)
- [services/research_money.py](../../src/sfm_fx_new_age/services/research_money.py#L13)
- [services/supplemental_files.py](../../src/sfm_fx_new_age/services/supplemental_files.py#L21)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
