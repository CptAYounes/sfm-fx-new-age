# SFM FX New Age — Architecture and Engineering Library

**Edition 1.0 · Public adaptation · 2026-11-22 · Historical source baseline: 0.2.0 / V23 candidate-04**

> **Public edition:** all chapters and reference data are retained. Links now resolve inside this repository; private paths and identifiers are sanitized. Historical qualification statements below describe the authoring baseline, not a fresh public-clone or broker run. Start with [Getting started](getting-started.md), [Development](development.md) and [publication boundaries](publication.md). The current project license is [MIT](../LICENSE); the original licensing-gap discussion in NA-D56 is historical. Current public verification: `python scripts/verify_publication.py` from the repository root.

This is the complete finite companion set: **60 main architecture/engineering documents, 12 retrospective ADRs, 14 source-linked reference documents and 8 rendered diagrams**, plus machine-readable traceability, catalogues, SBOM and verification receipts. It describes the actual New Age signal/research desktop, not the older SFM FX Engine/cBot architecture.

## Current public update — 0.2.1

The original authoring baseline and test totals below are historical. The [November 23 security recheck](security-review.md) records compatible dependency remediation, targeted OAuth/credential/TLS hardening, a current verification-environment inventory and the remaining SDK-constrained advisories. Public source modifications are bound by `publication.json`; original source digests are retained rather than represented as still matching. No operating account/session was used to validate this update.

## Open first

- [Engineering handbook — offline HTML](SFM_FX_New_Age_Engineering_Handbook.html): all main documents, ADRs, reference chapters and diagrams; local full-text navigation search.
- [Engineering handbook — PDF](SFM_FX_New_Age_Engineering_Handbook.pdf): all 60 main documents and 12 ADRs, with diagram atlas and reference-file directory. Detailed source-derived reference tables remain in HTML/Markdown/CSV.
- [Architecture description](documents/07-architecture-description.md) · [Scope and authority](documents/03-scope-authority-boundaries.md) · [Operator guide](documents/46-user-manual.md).

## Evidence and limits

Current source members match the retained V23 candidate-04 hashes. This task freshly ran **171 offline tests across 10 modules**, architecture checks, runtime summary and the explicitly synthetic restart/reconciliation checkpoint. It did not rerun full native release qualification or send any real broker action. The retained 1,541-case source/installed estates and native measurements remain historical evidence, not new observations.

**No product source, test, original README/PROGRESS, launcher, credential, normal-state database or sealed release evidence was changed.** This sibling location preserves the repository's strict Markdown fence and sealed source identity. `../PROGRESS.md` remains the sole mutable progress/handoff diary. This library contains architecture/reference/procedure documents, not a competing progress tracker.

Proposed operational policies are labelled; no owner signature, security/regulatory certification, profitable edge or current market setup is invented. Source links resolve inside this checkout; the prose, diagrams, PDF, HTML and CSVs remain readable independently.

## Suggested reading routes

- **Owner/operator:** 01, 03, 24, 33, 42, 46, 48.
- **Architect:** 07–24, 27, 30–31, 49–55 and ADRs.
- **Developer:** 16–29, 34–41, 55, 57–59 and reference catalogues.
- **Reviewer:** 05–06, 33, 37–40, 48, 50, 54, 56 and verification receipts.

## Main document catalogue

| ID | Document | Classification |
|---|---|---|
| NA-D01 | [Product Charter and Product Requirements](documents/01-product-charter.md) | PRODUCT_BASELINE |
| NA-D02 | [Stakeholders, User Stories and Use Cases](documents/02-stakeholders-use-cases.md) | DERIVED_REQUIREMENTS |
| NA-D03 | [System Scope, Authority and Non-Goals](documents/03-scope-authority-boundaries.md) | AS_BUILT_CONSTRAINTS |
| NA-D04 | [Domain Glossary and Terminology](documents/04-glossary.md) | REFERENCE |
| NA-D05 | [Software Requirements Specification](documents/05-software-requirements.md) | DERIVED_REQUIREMENTS |
| NA-D06 | [Quality Attribute Requirements and Scenarios](documents/06-quality-attributes.md) | DERIVED_QUALITY_BASELINE |
| NA-D07 | [Software Architecture Description](documents/07-architecture-description.md) | AS_BUILT_ARCHITECTURE |
| NA-D08 | [System Context and External Interfaces](documents/08-system-context.md) | AS_BUILT_CONTEXT |
| NA-D09 | [Container and Process Architecture](documents/09-container-process-architecture.md) | AS_BUILT_PROCESS_VIEW |
| NA-D10 | [Component Design and Responsibility Allocation](documents/10-components-ownership.md) | AS_BUILT_COMPONENT_VIEW |
| NA-D11 | [Runtime Scenarios and Sequence Design](documents/11-runtime-sequences.md) | AS_BUILT_DYNAMIC_VIEW |
| NA-D12 | [Deployment Architecture and Environment Boundaries](documents/12-deployment-architecture.md) | AS_BUILT_DEPLOYMENT |
| NA-D13 | [Domain Model and Bounded Contexts](documents/13-domain-model.md) | AS_BUILT_DOMAIN_DESIGN |
| NA-D14 | [Data Dictionary and Serialization Contracts](documents/14-data-dictionary.md) | AS_BUILT_DATA_REFERENCE |
| NA-D15 | [Database Design, Transactions and Migration Specification](documents/15-persistence-schema-migrations.md) | AS_BUILT_PERSISTENCE |
| NA-D16 | [API Design and Interface Control Document](documents/16-api-interface-control.md) | AS_BUILT_INTERFACE_CONTRACT |
| NA-D17 | [Event Model, Topic Catalogue and Routing Specification](documents/17-event-routing.md) | AS_BUILT_EVENT_DESIGN |
| NA-D18 | [Connector, Authentication and Protocol Design](documents/18-connector-auth-protocols.md) | AS_BUILT_CONNECTOR_DESIGN |
| NA-D19 | [Market and Supplemental Source Provenance Specification](documents/19-source-provenance.md) | AS_BUILT_DATA_AUTHORITY |
| NA-D20 | [Temporal Model, Causality and Freshness Design](documents/20-temporal-causality.md) | AS_BUILT_TEMPORAL_CONTRACT |
| NA-D21 | [Analytical Method and Projection Design](documents/21-analytical-method-design.md) | AS_BUILT_ANALYTICAL_DESIGN |
| NA-D22 | [Scanner DAG, Variables and LogicTiles Design](documents/22-scanner-logictiles.md) | AS_BUILT_RULE_ENGINE |
| NA-D23 | [Strategy-to-Signal Policy and Lifecycle Specification](documents/23-strategy-signal-lifecycle.md) | AS_BUILT_SIGNAL_DESIGN |
| NA-D24 | [Pending Order, Issue and Reconciliation Specification](documents/24-order-issue-reconciliation.md) | AS_BUILT_EXECUTION_DESIGN |
| NA-D25 | [UI Architecture, Navigation and Interaction Specification](documents/25-ui-navigation.md) | AS_BUILT_UI_DESIGN |
| NA-D26 | [Plugin and Extension Developer Specification](documents/26-plugins-extensions.md) | AS_BUILT_EXTENSION_CONTRACT |
| NA-D27 | [Concurrency, Scheduling and Resource Ownership](documents/27-concurrency-resource-model.md) | AS_BUILT_CONCURRENCY_DESIGN |
| NA-D28 | [Replay, Backtesting and Walk-Forward Specification](documents/28-replay-backtesting.md) | AS_BUILT_RESEARCH_MODEL |
| NA-D29 | [Configuration, Parameter Registry and Environment Reference](documents/29-configuration-parameters.md) | AS_BUILT_CONFIGURATION |
| NA-D30 | [Security Architecture and Trust Boundaries](documents/30-security-architecture.md) | AS_BUILT_SECURITY_ASSESSMENT |
| NA-D31 | [Threat Model and Abuse Case Analysis](documents/31-threat-model.md) | DESIGN_ASSESSMENT |
| NA-D32 | [Privacy, Sensitive Data and Information Handling](documents/32-privacy-data-handling.md) | OPERATIONAL_POLICY_PROPOSAL |
| NA-D33 | [Software Safety and Hazard Analysis](documents/33-safety-hazard-analysis.md) | DESIGN_ASSESSMENT |
| NA-D34 | [Software Development and Lifecycle Plan](documents/34-software-development-plan.md) | MAINTENANCE_PROCESS_PROPOSAL |
| NA-D35 | [Coding Standards and Code Review Checklist](documents/35-coding-review-standards.md) | ENGINEERING_PROCESS_PROPOSAL |
| NA-D36 | [Build, Packaging and Reproducibility Specification](documents/36-build-packaging.md) | AS_BUILT_BUILD_REFERENCE |
| NA-D37 | [Software Test and Quality Assurance Strategy](documents/37-test-strategy.md) | AS_BUILT_TEST_BASELINE_AND_GUIDANCE |
| NA-D38 | [Acceptance Test Specification and Release Criteria](documents/38-acceptance-test-specification.md) | DERIVED_ACCEPTANCE_SPECIFICATION |
| NA-D39 | [Requirements, Design and Test Traceability](documents/39-requirements-traceability.md) | TRACEABILITY_REFERENCE |
| NA-D40 | [Release and Configuration Management Plan](documents/40-release-configuration-management.md) | MAINTENANCE_PROCESS_PROPOSAL |
| NA-D41 | [Installation, Upgrade and Uninstall Guide](documents/41-installation-upgrade.md) | OPERATOR_PROCEDURE |
| NA-D42 | [Operations Runbook](documents/42-operations-runbook.md) | OPERATOR_PROCEDURE |
| NA-D43 | [Monitoring, Diagnostics and Troubleshooting Guide](documents/43-monitoring-troubleshooting.md) | AS_BUILT_OBSERVABILITY_AND_RUNBOOK |
| NA-D44 | [Backup, Restore and Disaster Recovery Plan](documents/44-backup-disaster-recovery.md) | OPERATIONAL_POLICY_PROPOSAL |
| NA-D45 | [Incident Response and Problem Management Runbook](documents/45-incident-response.md) | OPERATIONAL_POLICY_PROPOSAL |
| NA-D46 | [User Guide and Operator Workflows](documents/46-user-manual.md) | OPERATOR_GUIDE |
| NA-D47 | [Maintenance, Evolution and Support Plan](documents/47-maintenance-evolution.md) | MAINTENANCE_PROCESS_PROPOSAL |
| NA-D48 | [Risk Register, Limitations and Technical Debt Assessment](documents/48-risks-technical-debt.md) | SOURCE_GROUNDED_ASSESSMENT |
| NA-D49 | [Architecture Decision Register and Rationale](documents/49-architecture-decisions.md) | RETROSPECTIVE_DECISION_RECORDS |
| NA-D50 | [Evidence Model and Verification Assessment](documents/50-evidence-qualification.md) | SOURCE_AND_RECEIPT_ASSESSMENT |
| NA-D51 | [Compatibility and Interoperability Specification](documents/51-compatibility-interoperability.md) | AS_BUILT_COMPATIBILITY |
| NA-D52 | [Data Retention, Archival and Evidence Preservation](documents/52-retention-archival.md) | AS_BUILT_RULES_AND_POLICY_PROPOSAL |
| NA-D53 | [Usability, Accessibility and Human Factors Specification](documents/53-usability-accessibility.md) | AS_BUILT_UI_ASSESSMENT_AND_PROPOSALS |
| NA-D54 | [Performance, Capacity and Responsiveness Qualification](documents/54-performance-capacity.md) | RETAINED_MEASUREMENTS_AND_AS_BUILT_LIMITS |
| NA-D55 | [Change Impact and Dependency Analysis](documents/55-change-impact-analysis.md) | ENGINEERING_REFERENCE |
| NA-D56 | [Compliance Scope, Licensing and Distribution Review](documents/56-compliance-licensing.md) | NONCERTIFICATION_ASSESSMENT |
| NA-D57 | [Developer Onboarding and Architecture Reading Guide](documents/57-developer-onboarding.md) | DEVELOPER_GUIDE |
| NA-D58 | [Documentation Governance, Control and Maintenance](documents/58-documentation-governance.md) | DOCUMENTATION_POLICY |
| NA-D59 | [Dependency Inventory and Software Bill of Materials](documents/59-dependency-sbom.md) | OBSERVED_ENVIRONMENT_INVENTORY |
| NA-D60 | [Failure Modes, Recovery Matrix and Residual Guarantees](documents/60-failure-modes-recovery.md) | AS_BUILT_FAILURE_DESIGN |

## Architecture decisions

| ID | Retrospective decision |
|---|---|
| ADR-001 | [Local modular desktop with one shared runtime](decisions/ADR-001-local-shared-runtime.md) |
| ADR-002 | [Four workspaces, 42 stable contracts, dynamic Trading Tools](decisions/ADR-002-stable-workspaces.md) |
| ADR-003 | [Scoped API and explicit command/data ownership](decisions/ADR-003-scoped-tab-api.md) |
| ADR-004 | [Exact namespace plus connection epoch](decisions/ADR-004-source-namespace.md) |
| ADR-005 | [Causal immutable histories and separate current pointers](decisions/ADR-005-causal-history.md) |
| ADR-006 | [One deliberate pending Limit Issue edge](decisions/ADR-006-human-issue.md) |
| ADR-007 | [Durable reservation and UNKNOWN reconciliation](decisions/ADR-007-unknown-reconcile.md) |
| ADR-008 | [Distinct source semantics and disclosed activity alternatives](decisions/ADR-008-strict-source-semantics.md) |
| ADR-009 | [SQLite WAL/FULL with explicit atomic/savepoint boundaries](decisions/ADR-009-durable-sqlite.md) |
| ADR-010 | [Pure spawned analytical math with owner-side admission](decisions/ADR-010-pure-worker-math.md) |
| ADR-011 | [Isolated replay and explicit historical model clocks](decisions/ADR-011-isolated-research.md) |
| ADR-012 | [Version immutable semantics and preserve literal user choices](decisions/ADR-012-semantic-versioning.md) |

## Source-derived reference chapters

- [01-source-module-catalogue](references/01-source-module-catalogue.md)
- [02-typed-contract-catalogue](references/02-typed-contract-catalogue.md)
- [03-api-command-catalogue](references/03-api-command-catalogue.md)
- [04-view-route-dataset-catalogue](references/04-view-route-dataset-catalogue.md)
- [05-complete-strategy-policy-catalogue](references/05-complete-strategy-policy-catalogue.md)
- [06-original-corpus-crosswalk](references/06-original-corpus-crosswalk.md)
- [07-test-evidence-catalogue](references/07-test-evidence-catalogue.md)
- [08-registered-parameters-surfaces](references/08-registered-parameters-surfaces.md)
- [09-persistence-schema-records](references/09-persistence-schema-records.md)
- [10-dependency-sbom-reference](references/10-dependency-sbom-reference.md)
- [11-cli-reference](references/11-cli-reference.md)
- [12-release-evidence-readme](references/12-release-evidence-readme.md)
- [13-requirements-traceability](references/13-requirements-traceability.md)
- [14-documentation-coverage-matrix](references/14-documentation-coverage-matrix.md)

## Diagrams and machine-readable references

[Diagram atlas](diagrams/README.md) · [Package catalogue](package.json) · [Requirements CSV](references/requirements-traceability.csv) · [SBOM](references/sbom.cdx.json) · [Source preservation receipt](verification/source-preservation.json)

## Publication verification

Run the included `tooling/verify_package.py` for portable public checks of checksums, document membership, source anchors, relative links, exact trace identities, counts and rendered assets. The archived `verify_authoring_baseline.py` requires unavailable private authoring inputs and is historical only; public Git clones do not preserve authoring mtimes. Reader generation uses the source venv’s installed Markdown/Qt tools and system Graphviz/Poppler. No network dependency is needed to read the exports.

From this documentation directory on the authoring host:

```sh
../.venv/bin/python -B tooling/verify_package.py
sha256sum -c MANIFEST.sha256
```

`tooling/render_readers.py` rebuilds HTML/PDF from the canonical Markdown and the supplied diagrams; it does not rebuild or launch the product. Preserve a delivered edition before editing or regenerating it. Run the verifier read-only after publication. Intentional documentation edits use the explicit manifest refresh in the development guide; old retained verification reports are historical, not rewritten to claim new qualification. The ZIP’s adjacent `.sha256` file binds the delivered archive; the internal manifest binds every package member except the manifest itself.
