# ADR-003 — Scoped API and explicit command/data ownership

**Status:** retrospective as-built record; not a newly signed owner decision.

**Documentation date:** 2026-11-22 · **Baseline:** 0.2.0 / V23 candidate-04.

## Context

Tabs require useful independent contributions without owning SQL, SDK reactors or execution services.

## Observed decision

Expose immutable snapshots, bounded queries, capabilities, allowlisted commands and consumer disposal through TabApi v1.

## Alternatives considered by this analysis

Direct service handles; generic unrestricted RPC; separate connector per tool. These are explanatory alternatives, not a claim that a historical meeting evaluated them.

## Consequences

Reduces accidental coupling; remains a trusted same-process contract, not a hostile-code sandbox.

## Revisit trigger

Untrusted extensions or remote access. Any successor must preserve historical evidence and distinguish a proposal from approval.

## Verification obligation

Inspect the source owners below and their current positive/refusal/lifecycle checks. A retrospective ADR explains the present design; it does not execute the behavior or authorize a broker action.

## Source and authority anchors

- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [contracts/commands.py](../../src/sfm_fx_new_age/contracts/commands.py#L58)
- [contracts/tab_data.py](../../src/sfm_fx_new_age/contracts/tab_data.py#L30)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Decision register](../documents/49-architecture-decisions.md) · [Index](../README.md)
