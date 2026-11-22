# NA-D15 — Database Design, Transactions and Migration Specification

**Document:** NA-D15 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_PERSISTENCE · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## Physical model
The application opens SQLite with WAL, foreign keys enabled and `synchronous=FULL`. Schema user version is 2. The actual schema appendix contains source-derived SQL plus index definitions, not an invented normalized warehouse.

| Table | Primary purpose | Key constraints |
|---|---|---|
| `records` | Typed JSON facts, definitions, historical/current objects | Composite `(kind,id)` |
| `orders` | Local order correlation and duplicate reservation barrier | Order ID PK; unique `(scope_id,signal_id)` |
| `events` | Persisted event journal | Autoincrement sequence and unique event ID |

Expression indexes support market series, analytical scope, public projection history and supplemental interval/provider reads. `projection_utc` normalizes aware instants to microsecond UTC ordering; raw mixed-offset string ordering and SQLite floating-time rounding are not substituted.

## Write semantics
`transaction()` uses BEGIN IMMEDIATE or a nested savepoint, rolling back its own operation on failure. `batch_writes()` shares durable commits within a bounded owner turn while preserving completed independent operations if a later operation fails. It is not an all-or-nothing workflow substitute. Multi-step atomic workflows must use `transaction()`.

Some generic record writes are upserts. Immutable history is therefore enforced by its owning services and identity checks, not by a universal append-only SQL trigger. The journal and immutable revisions support audit; a mutable current pointer remains a projection, not immutable evidence.

## Migration behavior
An older orders table without `scope_id` is migrated atomically. Historical unscoped rows use an explicit `LEGACY_UNBOUND:` namespace rather than a guessed broker/source. Unsupported schema versions are refused. Existing records and old method definition bytes are retained when semantic versions advance.

## Operational cautions
Never copy only the main database while a live WAL is active and call it a consistent backup. Use a transactionally consistent SQLite backup or a quiesced complete database family. Preserve evidence before repair. No destructive pruning or schema change is authorized by this documentation task. Restore and upgrade procedures remain separately testable operations.

## Source and authority anchors

- [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12)
- [services/market.py](../../src/sfm_fx_new_age/services/market.py#L16)
- [services/research.py](../../src/sfm_fx_new_age/services/research.py#L15)
- [services/signals.py](../../src/sfm_fx_new_age/services/signals.py#L12)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
