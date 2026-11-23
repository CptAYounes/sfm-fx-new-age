# NA-D59 — Dependency Inventory and Software Bill of Materials

**Document:** NA-D59 · **Documentation edition:** 1.0 · **Baseline:** New Age 0.2.0 / V23 candidate-04

**Classification:** OBSERVED_ENVIRONMENT_INVENTORY · **Authored:** 2026-11-22 · **Approval:** source-grounded authoring; no fabricated owner signoff.

## 0.2.1 public dependency review — November 23, 2026

The authoring inventory below remains historical. The public security update adds a distinct [39-distribution resolved verification-environment SBOM](../verification/security-environment.cdx.json), reference constraints and a [package/advisory identity report](../verification/security-dependencies.json). Compatible certifi/urllib3/idna/pytest/setuptools upgrades resolve 13 original advisory IDs including the critical certifi issue; 24 SDK-constrained package matches remain. The `ctrader` extra now includes a full compatible hostname-verifier dependency. The project version is 0.2.1; the old 0.2.0 source and inventory are not rewritten to imply they were upgraded. See the [security review](../security-review.md).

## Inventory scope
The package includes a machine-readable observed-environment inventory and CycloneDX-format component list. Components are read from installed Python distribution metadata in the application environment; direct requirements come from `pyproject.toml`. The top-level product is 0.2.0. This is not a complete OS/container SBOM, dependency resolver lock, signed provenance attestation or vulnerability scan.

## Direct dependency roles
| Component | Role |
|---|---|
| PySide6 | Qt desktop presentation and this package's PDF export tooling |
| websocket-client | Public venue websocket acquisition |
| ctrader-open-api (optional extra) | Native cTrader protocol/SDK integration |
| pytest (development extra) | Automated test execution |
| setuptools/wheel (build requirements) | Packaging backend and wheel generation |

The observed full installed inventory may include transitive and development/tooling distributions. It is not asserted to be the minimal production dependency closure. Component purls identify package/version only; no upstream source authenticity is inferred.

## Version and license semantics
The project specifies version ranges, not a committed complete lockfile. Observed versions and available license metadata are recorded exactly where present; missing/ambiguous/long license fields are marked unreviewed rather than silently assigned a license. No CVE/advisory status is reported because none was checked.

## Proposed supply-chain workflow
For a future release, select an approved dependency snapshot, retain wheel hashes/origins and applicable notices, build/install independently, run affected compatibility/security tests and review current advisories from primary sources. Do not upgrade the user's environment merely to generate documentation.

## Preservation
This task performs no package installation or dependency mutation in the New Age venv. The inventory capture is read-only. The documentation builder uses already installed Markdown/Qt tooling and system Graphviz/Poppler; these reader-generation tools are separate from claims about the production runtime closure.

## Source and authority anchors

- [pyproject.toml](../../pyproject.toml#L1)
- [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16)
- [README.md](../../README.md#L1)

These anchors identify inspected local implementation/decisions. Source links require the sibling checkout. Historical qualification is not a new live observation; proposed practices are not claimed as implemented.

[Documentation index](../README.md) · [Reader handbook](../SFM_FX_New_Age_Engineering_Handbook.html)
