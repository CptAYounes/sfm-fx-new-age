# Public-edition provenance and boundaries

## 0.2.1 maintenance update

The November 23, 2026 update retains this initial-publication history while adding resolver-compatible dependency remediation and targeted OAuth/credential/TLS hardening. Current public source hashes are rebound explicitly in `publication.json`; original source digests are retained. The operating local checkout, credentials and broker runtime are not part of this mutation. See the [security review](security-review.md), current [environment inventory](verification/security-environment.cdx.json) and [advisory report](verification/security-dependencies.json). The original tagged 0.2.0 release is unchanged; 0.2.1 is a separate release.

## Scope

This repository publishes SFM FX New Age 0.2.0 and its complete companion engineering library at the owner's request. The owner selected open-source publication; the public edition uses the permissive root MIT license for original source and documentation. Dependencies, third-party data and trademarks keep their own terms.

The publication was assembled in an isolated copy. The operating source checkout, normal application database, saved credentials, native runtime and sealed local evidence were not used as a writable publication workspace. No broker operation or application restart is part of publishing this repository.

## Included

- All 158 packaged product files, all unit tests, scripts and operator-verification source files.
- The complete original user manual, now at `docs/legacy-user-guide.md`.
- All 60 main documents, 12 ADRs, 14 reference chapters, 8 diagram families, source/contract catalogues, traceability tables and SBOM inventory.
- Searchable HTML and printable PDF handbooks, regenerated for in-repository links.
- A sanitized historical engineering diary, community policies, a ready-to-enable public CI template and portable verification.

## Deliberate public-edition differences

- The root README is a public entry point; the full prior manual is retained.
- A registration-specific display name in one setup-dialog sentence was made generic. No analytical, execution or persistence behavior was changed by this wording edit.
- Owner-local absolute paths and a private registration's display name are generalized in copied documentation; broker-order and local-correlation identifiers in the diary are redacted.
- Project metadata declares MIT, authorship, repository/support URLs and development/documentation extras.
- The private-archive-dependent immutable-research test is self-contained. All original rejection cases remain. Community/reference documents are allowed by the notebook fence; competing progress diaries are still refused.
- Source hyperlinks point into this checkout, not a sibling directory. The documentation checksum manifest describes the public edition.
- The portable public checker does not pretend Git preserves original file mtimes or that private native receipts are distributed.

## Excluded deliberately

`.runtime`, virtual environments, caches, build trees, source-control history, token/application connection files, private FIX configuration, account/state databases, native market captures and private host telemetry are excluded. The original local Git repository had no commits to publish; public history starts with this audited snapshot. Credentials and provider data are not required for offline tests.

Historical references to `.runtime/...` remain documentary identifiers, not downloadable evidence. Retained test catalogues and measurements describe earlier private qualification; they are not new native observations. Do not convert a historical PASS into current account health, broker authority, an actual fill or a profitable edge.

## Present verification

The publication checks exercise the distributed source. The CI template is included at `.github/ci-template.yml` but remains inactive because the saved maintainer OAuth grant lacks `workflow` permission; no hosted-CI PASS is claimed. `publication.json` records public file identities and differences; `MANIFEST.sha256` binds documentation files. The initial public release's actual test/build results are recorded in the release notes and the publication entry of the single engineering diary. No claim of exhaustive legal, dependency-security, broker or strategy certification is made.
