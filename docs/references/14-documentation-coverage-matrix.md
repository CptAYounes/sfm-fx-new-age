# R14 — Documentation Coverage and Artifact Catalogue

The finite documentation catalogue is the acceptance boundary for this publication. It does not certify underlying software, security, finance, legal compliance or future operational readiness.

| Dimension | Exact count |
|---|---|
| main_documents | 60 |
| architecture_decisions | 12 |
| reference_documents | 14 |
| diagrams | 8 |
| analytical_profiles | 83 |
| active_analytical_identities | 1992 |
| backend_views | 42 |
| host_routes | 41 |
| commands | 40 |
| derived_requirements | 44 |
| frozen_corpus_requirements | 91 |
| current_product_python_modules | 152 |
| typed_contract_fields | 280 |
| installed_python_distributions | 131 |
| historical_release_cases_per_build | 1541 |
| fresh_offline_tests | 171 |

## Main document coverage

| Document | Type | Primary source owners |
|---|---|---|
| [NA-D01 — Product Charter and Product Requirements](../documents/01-product-charter.md) | PRODUCT_BASELINE | core/runtime.py; contracts/domain.py; README.md; PROGRESS.md |
| [NA-D02 — Stakeholders, User Stories and Use Cases](../documents/02-stakeholders-use-cases.md) | DERIVED_REQUIREMENTS | core/tab_api.py; services/workflow.py; services/orders.py; tabs/tab3/public_workspace.py; tabs/tab4/strategy_signals.py |
| [NA-D03 — System Scope, Authority and Non-Goals](../documents/03-scope-authority-boundaries.md) | AS_BUILT_CONSTRAINTS | contracts/domain.py; contracts/registry.py; contracts/tab_data.py; services/orders.py; README.md |
| [NA-D04 — Domain Glossary and Terminology](../documents/04-glossary.md) | REFERENCE | contracts/domain.py; contracts/analytics.py; contracts/strategy_signals.py; services/positions.py |
| [NA-D05 — Software Requirements Specification](../documents/05-software-requirements.md) | DERIVED_REQUIREMENTS | contracts/domain.py; contracts/registry.py; contracts/commands.py; services/orders.py; contracts/strategy_signals.py; contracts/backtest.py |
| [NA-D06 — Quality Attribute Requirements and Scenarios](../documents/06-quality-attributes.md) | DERIVED_QUALITY_BASELINE | core/router.py; storage/database.py; services/compute_pool.py; services/workflow.py; tests/test_owner_responsiveness.py |
| [NA-D07 — Software Architecture Description](../documents/07-architecture-description.md) | AS_BUILT_ARCHITECTURE | core/runtime.py; core/tab_api.py; services/scanner.py; connector/service.py; storage/database.py; app.py |
| [NA-D08 — System Context and External Interfaces](../documents/08-system-context.md) | AS_BUILT_CONTEXT | connector/service.py; connector/analytical_feed.py; connector/kraken_public.py; connector/bitstamp_feed.py; services/supplemental_files.py |
| [NA-D09 — Container and Process Architecture](../documents/09-container-process-architecture.md) | AS_BUILT_PROCESS_VIEW | core/runtime.py; connector/sdk_worker.py; connector/oauth.py; services/compute_pool.py; connector/kraken_public.py |
| [NA-D10 — Component Design and Responsibility Allocation](../documents/10-components-ownership.md) | AS_BUILT_COMPONENT_VIEW | core/runtime.py; core/components.py; services/market.py; services/research.py; services/orders.py; services/strategy_signals.py |
| [NA-D11 — Runtime Scenarios and Sequence Design](../documents/11-runtime-sequences.md) | AS_BUILT_DYNAMIC_VIEW | __main__.py; core/runtime.py; connector/service.py; services/strategy_signals.py; services/orders.py; storage/database.py |
| [NA-D12 — Deployment Architecture and Environment Boundaries](../documents/12-deployment-architecture.md) | AS_BUILT_DEPLOYMENT | __main__.py; scripts/launch.sh; scripts/install_desktop.py; connector/sdk_worker.py; README.md |
| [NA-D13 — Domain Model and Bounded Contexts](../documents/13-domain-model.md) | AS_BUILT_DOMAIN_DESIGN | contracts/domain.py; contracts/analytics.py; services/research.py; services/signals.py; services/positions.py |
| [NA-D14 — Data Dictionary and Serialization Contracts](../documents/14-data-dictionary.md) | AS_BUILT_DATA_REFERENCE | contracts/domain.py; contracts/analytics.py; contracts/models.py; contracts/supplemental.py; contracts/tab_data.py; contracts/backtest.py |
| [NA-D15 — Database Design, Transactions and Migration Specification](../documents/15-persistence-schema-migrations.md) | AS_BUILT_PERSISTENCE | storage/database.py; services/market.py; services/research.py; services/signals.py |
| [NA-D16 — API Design and Interface Control Document](../documents/16-api-interface-control.md) | AS_BUILT_INTERFACE_CONTRACT | core/tab_api.py; core/analytical_api.py; contracts/commands.py; contracts/tab_data.py; tabs/base.py |
| [NA-D17 — Event Model, Topic Catalogue and Routing Specification](../documents/17-event-routing.md) | AS_BUILT_EVENT_DESIGN | core/router.py; core/projections.py; core/runtime.py; contracts/models.py; contracts/data/host_typed_routes.csv |
| [NA-D18 — Connector, Authentication and Protocol Design](../documents/18-connector-auth-protocols.md) | AS_BUILT_CONNECTOR_DESIGN | connector/service.py; connector/sdk_worker.py; connector/oauth.py; connector/protocol.py; connector/symbols.py; connector/fix_capture.py |
| [NA-D19 — Market and Supplemental Source Provenance Specification](../documents/19-source-provenance.md) | AS_BUILT_DATA_AUTHORITY | connector/broker_depth.py; connector/kraken_public.py; connector/kraken_weekly.py; connector/bitstamp_feed.py; connector/analytical_feed.py; services/supplemental.py; services/supplemental_files.py |
| [NA-D20 — Temporal Model, Causality and Freshness Design](../documents/20-temporal-causality.md) | AS_BUILT_TEMPORAL_CONTRACT | contracts/domain.py; services/market.py; services/public_projections.py; services/strategy_signals.py; services/replay.py; connector/quote_history.py |
| [NA-D21 — Analytical Method and Projection Design](../documents/21-analytical-method-design.md) | AS_BUILT_ANALYTICAL_DESIGN | contracts/public_strategies.py; contracts/public_document_profiles.py; services/public_projections.py; tabs/tab3/public_algorithms.py; tabs/tab3/public_genuine_data.py; services/projection_math.py |
| [NA-D22 — Scanner DAG, Variables and LogicTiles Design](../documents/22-scanner-logictiles.md) | AS_BUILT_RULE_ENGINE | core/dag.py; services/scanner.py; services/rules.py; services/catalogues.py; core/analytical_api.py; tabs/tab3/authoring.py |
| [NA-D23 — Strategy-to-Signal Policy and Lifecycle Specification](../documents/23-strategy-signal-lifecycle.md) | AS_BUILT_SIGNAL_DESIGN | contracts/strategy_signals.py; services/strategy_signal_policy.py; services/strategy_signals.py; tabs/tab4/strategy_signals.py; tests/test_strategy_signal_lifecycle.py |
| [NA-D24 — Pending Order, Issue and Reconciliation Specification](../documents/24-order-issue-reconciliation.md) | AS_BUILT_EXECUTION_DESIGN | services/orders.py; services/signals.py; storage/database.py; connector/protocol.py; connector/service.py; services/positions.py |
| [NA-D25 — UI Architecture, Navigation and Interaction Specification](../documents/25-ui-navigation.md) | AS_BUILT_UI_DESIGN | app.py; ui/navigation.py; ui/chart_workspace.py; services/workflow.py; tabs/tab2/workspace.py; ui/inspection_panels.py |
| [NA-D26 — Plugin and Extension Developer Specification](../documents/26-plugins-extensions.md) | AS_BUILT_EXTENSION_CONTRACT | tabs/base.py; tabs/loader.py; tabs/backend_loader.py; core/analytical_api.py; tabs/tab3/backend.py; core/tab_api.py |
| [NA-D27 — Concurrency, Scheduling and Resource Ownership](../documents/27-concurrency-resource-model.md) | AS_BUILT_CONCURRENCY_DESIGN | core/runtime.py; core/router.py; services/compute_pool.py; connector/sdk_worker.py; storage/database.py; services/public_projections.py |
| [NA-D28 — Replay, Backtesting and Walk-Forward Specification](../documents/28-replay-backtesting.md) | AS_BUILT_RESEARCH_MODEL | contracts/backtest.py; services/replay.py; services/backtesting.py; ui/research_study.py; tests/test_backtest_workflow.py |
| [NA-D29 — Configuration, Parameter Registry and Environment Reference](../documents/29-configuration-parameters.md) | AS_BUILT_CONFIGURATION | __main__.py; contracts/defaults.py; services/catalogues.py; services/research_money.py; services/supplemental_files.py |
| [NA-D30 — Security Architecture and Trust Boundaries](../documents/30-security-architecture.md) | AS_BUILT_SECURITY_ASSESSMENT | connector/oauth.py; connector/sdk_worker.py; services/supplemental_files.py; contracts/commands.py; core/tab_api.py; connector/fix_capture.py |
| [NA-D31 — Threat Model and Abuse Case Analysis](../documents/31-threat-model.md) | DESIGN_ASSESSMENT | connector/oauth.py; connector/sdk_worker.py; services/supplemental_files.py; services/orders.py; services/compute_pool.py |
| [NA-D32 — Privacy, Sensitive Data and Information Handling](../documents/32-privacy-data-handling.md) | OPERATIONAL_POLICY_PROPOSAL | connector/oauth.py; connector/sdk_worker.py; storage/database.py; connector/original_capture.py; README.md |
| [NA-D33 — Software Safety and Hazard Analysis](../documents/33-safety-hazard-analysis.md) | DESIGN_ASSESSMENT | services/orders.py; services/strategy_signals.py; services/research_money.py; services/positions.py; storage/database.py |
| [NA-D34 — Software Development and Lifecycle Plan](../documents/34-software-development-plan.md) | MAINTENANCE_PROCESS_PROPOSAL | PROGRESS.md; pyproject.toml; core/runtime.py; tests/test_architecture_fences.py |
| [NA-D35 — Coding Standards and Code Review Checklist](../documents/35-coding-review-standards.md) | ENGINEERING_PROCESS_PROPOSAL | tests/test_architecture_fences.py; contracts/domain.py; contracts/commands.py; core/tab_api.py; storage/database.py |
| [NA-D36 — Build, Packaging and Reproducibility Specification](../documents/36-build-packaging.md) | AS_BUILT_BUILD_REFERENCE | pyproject.toml; scripts/launch.sh; scripts/install_desktop.py; scripts/run_checks.sh; PROGRESS.md |
| [NA-D37 — Software Test and Quality Assurance Strategy](../documents/37-test-strategy.md) | AS_BUILT_TEST_BASELINE_AND_GUIDANCE | tests/conftest.py; tests/test_architecture_fences.py; tests/test_strategy_signal_positive.py; tests/test_connector_boundary.py; PROGRESS.md |
| [NA-D38 — Acceptance Test Specification and Release Criteria](../documents/38-acceptance-test-specification.md) | DERIVED_ACCEPTANCE_SPECIFICATION | tests/test_order_flow.py; tests/test_strategy_signal_positive.py; tests/test_strategy_signal_lifecycle.py; tests/test_workspace_ui_workflows.py; tests/test_backtest_workflow.py |
| [NA-D39 — Requirements, Design and Test Traceability](../documents/39-requirements-traceability.md) | TRACEABILITY_REFERENCE | contracts/data/public_document_requirements.json; contracts/public_strategies.py; contracts/strategy_signals.py; tests/test_document_public_strategies.py; tests/test_strategy_signal_positive.py |
| [NA-D40 — Release and Configuration Management Plan](../documents/40-release-configuration-management.md) | MAINTENANCE_PROCESS_PROPOSAL | pyproject.toml; PROGRESS.md; scripts/install_desktop.py; contracts/public_strategies.py |
| [NA-D41 — Installation, Upgrade and Uninstall Guide](../documents/41-installation-upgrade.md) | OPERATOR_PROCEDURE | README.md; pyproject.toml; scripts/launch.sh; scripts/install_desktop.py; __main__.py |
| [NA-D42 — Operations Runbook](../documents/42-operations-runbook.md) | OPERATOR_PROCEDURE | connector/service.py; ui/feed_connection.py; services/orders.py; services/positions.py; __main__.py |
| [NA-D43 — Monitoring, Diagnostics and Troubleshooting Guide](../documents/43-monitoring-troubleshooting.md) | AS_BUILT_OBSERVABILITY_AND_RUNBOOK | connector/service.py; core/router.py; services/compute_pool.py; ui/feed_connection.py; checks.py |
| [NA-D44 — Backup, Restore and Disaster Recovery Plan](../documents/44-backup-disaster-recovery.md) | OPERATIONAL_POLICY_PROPOSAL | storage/database.py; connector/oauth.py; services/replay.py; PROGRESS.md |
| [NA-D45 — Incident Response and Problem Management Runbook](../documents/45-incident-response.md) | OPERATIONAL_POLICY_PROPOSAL | services/orders.py; connector/service.py; connector/oauth.py; storage/database.py; PROGRESS.md |
| [NA-D46 — User Guide and Operator Workflows](../documents/46-user-manual.md) | OPERATOR_GUIDE | README.md; app.py; tabs/tab3/public_workspace.py; tabs/tab4/strategy_signals.py; ui/research_study.py |
| [NA-D47 — Maintenance, Evolution and Support Plan](../documents/47-maintenance-evolution.md) | MAINTENANCE_PROCESS_PROPOSAL | PROGRESS.md; contracts/public_strategies.py; contracts/registry.py; tests/test_recipe_upgrade_preservation.py |
| [NA-D48 — Risk Register, Limitations and Technical Debt Assessment](../documents/48-risks-technical-debt.md) | SOURCE_GROUNDED_ASSESSMENT | README.md; pyproject.toml; connector/oauth.py; services/orders.py; contracts/backtest.py; PROGRESS.md |
| [NA-D49 — Architecture Decision Register and Rationale](../documents/49-architecture-decisions.md) | RETROSPECTIVE_DECISION_RECORDS | PROGRESS.md; core/runtime.py; core/tab_api.py; services/orders.py; storage/database.py; contracts/strategy_signals.py |
| [NA-D50 — Evidence Model and Verification Assessment](../documents/50-evidence-qualification.md) | SOURCE_AND_RECEIPT_ASSESSMENT | PROGRESS.md; tests/test_architecture_fences.py; tests/test_strategy_signal_positive.py; checks.py |
| [NA-D51 — Compatibility and Interoperability Specification](../documents/51-compatibility-interoperability.md) | AS_BUILT_COMPATIBILITY | pyproject.toml; connector/symbols.py; connector/protocol.py; contracts/domain.py; core/tab_api.py; README.md |
| [NA-D52 — Data Retention, Archival and Evidence Preservation](../documents/52-retention-archival.md) | AS_BUILT_RULES_AND_POLICY_PROPOSAL | storage/database.py; connector/kraken_public.py; services/supplemental.py; PROGRESS.md |
| [NA-D53 — Usability, Accessibility and Human Factors Specification](../documents/53-usability-accessibility.md) | AS_BUILT_UI_ASSESSMENT_AND_PROPOSALS | ui/navigation.py; ui/theme.py; ui/chart_projection_bar.py; ui/chart_projection_details.py; ui/research_study.py; tests/test_gui_navigation_refinement.py |
| [NA-D54 — Performance, Capacity and Responsiveness Qualification](../documents/54-performance-capacity.md) | RETAINED_MEASUREMENTS_AND_AS_BUILT_LIMITS | services/compute_pool.py; core/runtime.py; connector/service.py; storage/database.py; tests/test_owner_responsiveness.py; README.md |
| [NA-D55 — Change Impact and Dependency Analysis](../documents/55-change-impact-analysis.md) | ENGINEERING_REFERENCE | core/runtime.py; contracts/registry.py; services/public_projections.py; services/strategy_signals.py; services/orders.py; storage/database.py |
| [NA-D56 — Compliance Scope, Licensing and Distribution Review](../documents/56-compliance-licensing.md) | NONCERTIFICATION_ASSESSMENT | pyproject.toml; connector/oauth.py; contracts/public_strategies.py; README.md |
| [NA-D57 — Developer Onboarding and Architecture Reading Guide](../documents/57-developer-onboarding.md) | DEVELOPER_GUIDE | PROGRESS.md; pyproject.toml; core/runtime.py; core/tab_api.py; tests/test_architecture_fences.py |
| [NA-D58 — Documentation Governance, Control and Maintenance](../documents/58-documentation-governance.md) | DOCUMENTATION_POLICY | PROGRESS.md; tests/test_architecture_fences.py; README.md |
| [NA-D59 — Dependency Inventory and Software Bill of Materials](../documents/59-dependency-sbom.md) | OBSERVED_ENVIRONMENT_INVENTORY | pyproject.toml; connector/sdk_worker.py; README.md |
| [NA-D60 — Failure Modes, Recovery Matrix and Residual Guarantees](../documents/60-failure-modes-recovery.md) | AS_BUILT_FAILURE_DESIGN | services/orders.py; services/continuity.py; services/strategy_signals.py; connector/service.py; services/supplemental_files.py; services/compute_pool.py |

## Reference scope

Exact source/symbol/field/API/view/route/method/corpus/test/parameter/schema/dependency/CLI/release/crosswalk extracts accompany the prose. Static imports and literal record-kind extraction are explicitly not dynamic call-graph or exhaustive runtime coverage.
