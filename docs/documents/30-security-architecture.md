# NA-D30 — Security Architecture and Trust Boundaries

**Document:** NA-D30 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** AS_BUILT_SECURITY_ASSESSMENT · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## 0.2.1 public security update — November 23, 2026

The original baseline below is retained as historical authoring evidence. The public 0.2.1 update adds a fixed HTTPS token destination, redirect refusal, bounded/duplicate-key-refusing token JSON, typed token/expiry checks, nonblocking regular single-link credential reads, bounded atomic saves and a required full service-identity verifier. The optional FIX client explicitly requires TLS 1.2+, certificate validation and hostname checking. Storage remains filesystem-permission-protected plaintext, not an encrypted keychain. Synthetic regression tests cover these controls; they are not new live account/TLS or broker-action receipts.

Compatible dependency updates resolve 13 of the original 37 advisories including the critical trust-store finding; 24 SDK-constrained package advisories remain. See the [current security review](../security-review.md) and [machine-readable review](../verification/security-dependencies.json) for exposure distinctions and limits. Provider authentication is not a patch for local client dependencies.

## Assets and boundaries
Protected assets include OAuth/application secrets, account identifiers, order intent/correlation, source integrity, local research history and saved operator choices. Boundaries separate human/browser authorization, external network responses, SDK/acquisition workers, the application owner, file publishers and durable state.

## Implemented controls
- Exact registered callback and single-use state; exchange generation checks reject late login results.
- Owner-only regular credential files and atomic replacement; symlink/unsafe permission checks.
- Hostname-verifying SDK TLS and fixed/validated provider acquisition paths.
- Scoped account/source identities and command/dataset allowlists.
- Strict payload shapes, bounded sizes, immutable observation hashes and CAS edits.
- Ephemeral provider authority and late-source/generation rejection.
- Deliberate Issue, atomic duplicate barrier and UNKNOWN recovery instead of blind replay.
- Secret redaction before ordinary events/diagnostic output.

## Explicit limitations
Credential persistence is plaintext protected by filesystem permissions, not encryption or an OS keychain. The local user and same-process extensions are trusted. TabApi is not a remote authentication/authorization system. Checksums/content hashes establish byte integrity/corroboration, not vendor signatures. No penetration test, external security certification, current CVE clearance or hardened multi-user deployment is claimed.

## Operational guidance — proposed practice
Use a dedicated protected user environment, restrict backup access, avoid forwarding raw credential-bearing URLs, and preserve OS trust-store/time correctness. Treat every external payload as data, not instructions. Avoid running diagnostic tools with production write authority when offline fixtures suffice. Separate public-source acquisition from explicitly approved broker actions.

## Change gate
Changes involving private files, callback handling, TLS, command validation, input admission or Issue require focused adversarial/refusal tests and exact source review. New remote access or untrusted plugin support requires a new security model, not reuse of the current local trust assumptions.

## Source and authority anchors

- [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17)
- [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16)
- [services/supplemental_files.py](../../src/sfm_fx_new_age/services/supplemental_files.py#L21)
- [contracts/commands.py](../../src/sfm_fx_new_age/contracts/commands.py#L58)
- [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19)
- [connector/fix_capture.py](../../src/sfm_fx_new_age/connector/fix_capture.py#L24)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
