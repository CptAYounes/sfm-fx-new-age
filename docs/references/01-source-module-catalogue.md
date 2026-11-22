# R01 — Source, Module and Ownership Catalogue

Every product Python module is included below. Full exact class/function signatures and lexical import edges are in the CSV/JSON extracts. Static edges are not a complete dynamic call graph and do not prove execution.

| Module | Lines | Top-level definitions |
|---|---|---|
| [__init__.py](../../src/sfm_fx_new_age/__init__.py#L1) | 3 | Package/data marker |
| [__main__.py](../../src/sfm_fx_new_age/__main__.py#L12) | 131 | main |
| [app.py](../../src/sfm_fx_new_age/app.py#L30) | 551 | label; BrandMark; SubtabPanel; MainWindow; create_main_window; run_app |
| [checks.py](../../src/sfm_fx_new_age/checks.py#L11) | 48 | run_checks; main |
| [connector/__init__.py](../../src/sfm_fx_new_age/connector/__init__.py#L1) | 1 | Package/data marker |
| [connector/analytical_feed.py](../../src/sfm_fx_new_age/connector/analytical_feed.py#L31) | 221 | ConnectedAnalyticalFeed |
| [connector/bitstamp_book.py](../../src/sfm_fx_new_age/connector/bitstamp_book.py#L24) | 194 | micros; clock; native_id; snapshot_orders; NativeChainBook |
| [connector/bitstamp_feed.py](../../src/sfm_fx_new_age/connector/bitstamp_feed.py#L27) | 307 | utcnow; ConnectedBitstampBook |
| [connector/broker_depth.py](../../src/sfm_fx_new_age/connector/broker_depth.py#L22) | 162 | ConnectedBrokerDepth |
| [connector/depth_capture.py](../../src/sfm_fx_new_age/connector/depth_capture.py#L20) | 125 | decode_observed_levels; acquire_original_depth |
| [connector/fix_capture.py](../../src/sfm_fx_new_age/connector/fix_capture.py#L24) | 167 | load_price_credentials; original_bindings; PriceSession; snapshot_envelope; capture_fix_price |
| [connector/fix_protocol.py](../../src/sfm_fx_new_age/connector/fix_protocol.py#L13) | 158 | FixError; text; stamp; encode_quote; Decoder; one; groups; positive; QuoteBook |
| [connector/fxopen_feed.py](../../src/sfm_fx_new_age/connector/fxopen_feed.py#L32) | 312 | public_get; ConnectedFXOpenReported |
| [connector/fxopen_reported.py](../../src/sfm_fx_new_age/connector/fxopen_reported.py#L31) | 202 | stamp; milliseconds; from_ms; signature; parse_range; addressed; ReportedTape; corroborate; extend; totals; evidences |
| [connector/history.py](../../src/sfm_fx_new_age/connector/history.py#L10) | 81 | NativeHistory |
| [connector/kraken_book.py](../../src/sfm_fx_new_age/connector/kraken_book.py#L13) | 49 | NativeBook |
| [connector/kraken_history.py](../../src/sfm_fx_new_age/connector/kraken_history.py#L22) | 120 | RangeArchive; acquire_hour_history; history_rows |
| [connector/kraken_public.py](../../src/sfm_fx_new_age/connector/kraken_public.py#L34) | 468 | PublicationMailbox; stamp; native_get; discover; NativeTrades; closed_hours; ConnectedKrakenFeed |
| [connector/kraken_weekly.py](../../src/sfm_fx_new_age/connector/kraken_weekly.py#L18) | 249 | stamp; WeeklySource; ConnectedWeeklyRecovery |
| [connector/lanes.py](../../src/sfm_fx_new_age/connector/lanes.py#L5) | 65 | eligible_lanes; project_binding; lane_matches; prune_admissions |
| [connector/native_feed_audit.py](../../src/sfm_fx_new_age/connector/native_feed_audit.py#L11) | 54 | native_quote_health; protocol_capabilities; audit_native_feed |
| [connector/oauth.py](../../src/sfm_fx_new_age/connector/oauth.py#L17) | 178 | token_http_request; token_error_code; SecretStore; OAuthConfig; OAuthSession |
| [connector/official_context.py](../../src/sfm_fx_new_age/connector/official_context.py#L29) | 154 | SameOfficialHostRedirect; now; sha; binding_from_database; validate_binding; fetch_original_json; cot_records; fed_records; write_new; acquire_official_context |
| [connector/original_capture.py](../../src/sfm_fx_new_age/connector/original_capture.py#L21) | 91 | ReadOnlyCaptureSdk; acquire_original_inputs |
| [connector/protocol.py](../../src/sfm_fx_new_age/connector/protocol.py#L8) | 54 | milliseconds; timestamp; new_limit_request; symbol_spec; trendbar; execution_state |
| [connector/quote_history.py](../../src/sfm_fx_new_age/connector/quote_history.py#L21) | 150 | NativeQuoteHistory |
| [connector/sdk_worker.py](../../src/sfm_fx_new_age/connector/sdk_worker.py#L16) | 182 | redact; paced_protocol; verified_client; sdk_worker_main; SdkProcess |
| [connector/service.py](../../src/sfm_fx_new_age/connector/service.py#L27) | 837 | ConnectorService |
| [connector/symbols.py](../../src/sfm_fx_new_age/connector/symbols.py#L8) | 76 | SymbolResolution; native_id; resolve_symbols |
| [contracts/__init__.py](../../src/sfm_fx_new_age/contracts/__init__.py#L1) | 7 | Package/data marker |
| [contracts/analytics.py](../../src/sfm_fx_new_age/contracts/analytics.py#L14) | 247 | digest; Lineage; Level; Evidence; Recipe; Variant; MarketCandidate; Overlay; VariableDefinition; ParameterDefinition; MutableSurface |
| [contracts/backtest.py](../../src/sfm_fx_new_age/contracts/backtest.py#L11) | 40 | StudyRequest |
| [contracts/chart_display.py](../../src/sfm_fx_new_age/contracts/chart_display.py#L45) | 120 | color; number; anchor_count; validate_style; validate_drawing; style_for; validate_display |
| [contracts/commands.py](../../src/sfm_fx_new_age/contracts/commands.py#L58) | 103 | CommandCapability; capability; validate_payload |
| [contracts/data/__init__.py](../../src/sfm_fx_new_age/contracts/data/__init__.py#L1) | 1 | Package/data marker |
| [contracts/defaults.py](../../src/sfm_fx_new_age/contracts/defaults.py#L6) | 18 | register_core_parameters |
| [contracts/domain.py](../../src/sfm_fx_new_age/contracts/domain.py#L14) | 252 | Origin; SignalState; OrderState; instant; decimal; symbol_check; record; SymbolSpec; Bar; Quote; AccountContext; Candidate; BrokerOutcome |
| [contracts/enums.py](../../src/sfm_fx_new_age/contracts/enums.py#L6) | 34 | Priority; Freshness; Availability; CommandStatus |
| [contracts/extensions.py](../../src/sfm_fx_new_age/contracts/extensions.py#L9) | 32 | VariableUpdate; AnalyticalResult |
| [contracts/models.py](../../src/sfm_fx_new_age/contracts/models.py#L12) | 101 | utc_now; freeze; thaw; _frozen; Event; Command; CommandResult; SubtabDefinition; RouteDefinition |
| [contracts/public_document_profiles.py](../../src/sfm_fx_new_age/contracts/public_document_profiles.py#L16) | 71 | document_methods |
| [contracts/public_projection_inputs.py](../../src/sfm_fx_new_age/contracts/public_projection_inputs.py#L2) | 22 | ProjectionInputUnavailable; optional_projection_source |
| [contracts/public_strategies.py](../../src/sfm_fx_new_age/contracts/public_strategies.py#L10) | 87 | ProjectionMethod; method |
| [contracts/registry.py](../../src/sfm_fx_new_age/contracts/registry.py#L18) | 69 | tab_titles; _rows; _items; load_subtabs; load_routes |
| [contracts/strategy_signals.py](../../src/sfm_fx_new_age/contracts/strategy_signals.py#L13) | 99 | SignalPolicy; validate_observation |
| [contracts/supplemental.py](../../src/sfm_fx_new_age/contracts/supplemental.py#L14) | 54 | SupplementalEvidence |
| [contracts/supplemental_wire.py](../../src/sfm_fx_new_age/contracts/supplemental_wire.py#L21) | 95 | validate_wire_shape |
| [contracts/tab_data.py](../../src/sfm_fx_new_age/contracts/tab_data.py#L30) | 51 | DataRequest |
| [contracts/venue_book.py](../../src/sfm_fx_new_age/contracts/venue_book.py#L5) | 11 | book_checksum |
| [core/__init__.py](../../src/sfm_fx_new_age/core/__init__.py#L1) | 3 | Package/data marker |
| [core/analytical_api.py](../../src/sfm_fx_new_age/core/analytical_api.py#L14) | 113 | AnalyticalExtensionApi |
| [core/command_handlers.py](../../src/sfm_fx_new_age/core/command_handlers.py#L14) | 149 | SharedCommandHandlers |
| [core/components.py](../../src/sfm_fx_new_age/core/components.py#L13) | 54 | ComponentState; ComponentRegistry |
| [core/dag.py](../../src/sfm_fx_new_age/core/dag.py#L9) | 29 | scanner_graph; dirty_descendants |
| [core/projections.py](../../src/sfm_fx_new_age/core/projections.py#L12) | 58 | ViewProjection; ProjectionStore |
| [core/router.py](../../src/sfm_fx_new_age/core/router.py#L15) | 114 | BackpressureError; PriorityEventRouter |
| [core/runtime.py](../../src/sfm_fx_new_age/core/runtime.py#L36) | 486 | SubtabRuntime; TabRuntime; ApplicationRuntime |
| [core/tab_api.py](../../src/sfm_fx_new_age/core/tab_api.py#L19) | 189 | TabSnapshot; TabApi |
| [core/tab_data.py](../../src/sfm_fx_new_age/core/tab_data.py#L8) | 216 | TabDataService |
| [resources/__init__.py](../../src/sfm_fx_new_age/resources/__init__.py#L1) | 1 | Package/data marker |
| [services/__init__.py](../../src/sfm_fx_new_age/services/__init__.py#L1) | 1 | Package/data marker |
| [services/backtesting.py](../../src/sfm_fx_new_age/services/backtesting.py#L11) | 140 | summary; evaluate_study |
| [services/candidate_binding.py](../../src/sfm_fx_new_age/services/candidate_binding.py#L11) | 67 | CandidateBindingService |
| [services/catalogues.py](../../src/sfm_fx_new_age/services/catalogues.py#L12) | 267 | CatalogueService |
| [services/chart_projection.py](../../src/sfm_fx_new_age/services/chart_projection.py#L6) | 45 | setup_projection; scenario_projection |
| [services/chart_studies.py](../../src/sfm_fx_new_age/services/chart_studies.py#L6) | 26 | moving_average; ChartStudyService |
| [services/compute_pool.py](../../src/sfm_fx_new_age/services/compute_pool.py#L11) | 106 | worker_limit; host_capacity; ProjectionPool |
| [services/consumers.py](../../src/sfm_fx_new_age/services/consumers.py#L9) | 44 | ConsumerService |
| [services/continuity.py](../../src/sfm_fx_new_age/services/continuity.py#L16) | 136 | SessionCalendar; ContinuityService |
| [services/geometry.py](../../src/sfm_fx_new_age/services/geometry.py#L16) | 74 | risk_band; atr_variants; confidence; qualify |
| [services/market.py](../../src/sfm_fx_new_age/services/market.py#L16) | 204 | market_key; MarketService |
| [services/orders.py](../../src/sfm_fx_new_age/services/orders.py#L18) | 269 | BrokerTransport; FixtureBroker; AccountService; OrderService |
| [services/point_figure_preparation.py](../../src/sfm_fx_new_age/services/point_figure_preparation.py#L24) | 118 | hash_bytes; exact_sha; verified_native_ticks; prepare_original_point_figure |
| [services/positions.py](../../src/sfm_fx_new_age/services/positions.py#L11) | 57 | PositionService |
| [services/projection_math.py](../../src/sfm_fx_new_age/services/projection_math.py#L6) | 54 | calculate; compute_frame |
| [services/public_projections.py](../../src/sfm_fx_new_age/services/public_projections.py#L13) | 287 | PublicProjectionService |
| [services/replay.py](../../src/sfm_fx_new_age/services/replay.py#L13) | 119 | ReplayService |
| [services/research.py](../../src/sfm_fx_new_age/services/research.py#L15) | 84 | ResearchStore |
| [services/research_money.py](../../src/sfm_fx_new_age/services/research_money.py#L13) | 125 | ResearchMoneyService |
| [services/rules.py](../../src/sfm_fx_new_age/services/rules.py#L11) | 172 | Truth; Value; _unknown; _truth; evaluate_rule; validate_rule |
| [services/scanner.py](../../src/sfm_fx_new_age/services/scanner.py#L16) | 261 | Computation; NodeResult; ScannerScheduler; primitives; confirmed_swings; AnalyticsService |
| [services/signals.py](../../src/sfm_fx_new_age/services/signals.py#L12) | 81 | SignalService |
| [services/strategy_signal_policy.py](../../src/sfm_fx_new_age/services/strategy_signal_policy.py#L17) | 206 | stamp; recovery; prior_output; level_response; marker_trigger; extract_trigger; build_observation |
| [services/strategy_signals.py](../../src/sfm_fx_new_age/services/strategy_signals.py#L17) | 202 | StrategySignalService |
| [services/supplemental.py](../../src/sfm_fx_new_age/services/supplemental.py#L13) | 104 | SupplementalEvidenceStore |
| [services/supplemental_files.py](../../src/sfm_fx_new_age/services/supplemental_files.py#L21) | 138 | read_bytes; parse_json; load_config; SupplementalFileIngress |
| [services/timeline.py](../../src/sfm_fx_new_age/services/timeline.py#L10) | 86 | Tick; TickTimeline |
| [services/tool_calculator.py](../../src/sfm_fx_new_age/services/tool_calculator.py#L15) | 36 | calculate; convert_pnl |
| [services/workflow.py](../../src/sfm_fx_new_age/services/workflow.py#L15) | 162 | WorkflowService |
| [services/zone_confidence_reference.py](../../src/sfm_fx_new_age/services/zone_confidence_reference.py#L46) | 288 | _timestamp; _finite_nonnegative; _unit; _normalised_interval; _locality; score_zone_confidence |
| [storage/__init__.py](../../src/sfm_fx_new_age/storage/__init__.py#L1) | 1 | Package/data marker |
| [storage/database.py](../../src/sfm_fx_new_age/storage/database.py#L12) | 365 | StateConflict; Database |
| [tabs/__init__.py](../../src/sfm_fx_new_age/tabs/__init__.py#L1) | 1 | Package/data marker |
| [tabs/backend_loader.py](../../src/sfm_fx_new_age/tabs/backend_loader.py#L6) | 12 | load_analytical_installers |
| [tabs/base.py](../../src/sfm_fx_new_age/tabs/base.py#L18) | 55 | ToolContribution; TabPlugin |
| [tabs/loader.py](../../src/sfm_fx_new_age/tabs/loader.py#L8) | 18 | load_tab_plugins |
| [tabs/tab1/__init__.py](../../src/sfm_fx_new_age/tabs/tab1/__init__.py#L1) | 1 | Package/data marker |
| [tabs/tab1/plugin.py](../../src/sfm_fx_new_age/tabs/tab1/plugin.py#L4) | 6 | build_plugin |
| [tabs/tab2/__init__.py](../../src/sfm_fx_new_age/tabs/tab2/__init__.py#L1) | 1 | Package/data marker |
| [tabs/tab2/calculator.py](../../src/sfm_fx_new_age/tabs/tab2/calculator.py#L8) | 125 | CalculatorWidget |
| [tabs/tab2/plugin.py](../../src/sfm_fx_new_age/tabs/tab2/plugin.py#L4) | 9 | build_plugin |
| [tabs/tab2/workspace.py](../../src/sfm_fx_new_age/tabs/tab2/workspace.py#L12) | 91 | ToolDefinition; ToolWindow; ToolsWorkspace |
| [tabs/tab3/__init__.py](../../src/sfm_fx_new_age/tabs/tab3/__init__.py#L1) | 1 | Package/data marker |
| [tabs/tab3/authoring.py](../../src/sfm_fx_new_age/tabs/tab3/authoring.py#L11) | 205 | rows; RuleBuilderPanel; ParameterEditorPanel |
| [tabs/tab3/backend.py](../../src/sfm_fx_new_age/tabs/tab3/backend.py#L9) | 37 | install |
| [tabs/tab3/candidates.py](../../src/sfm_fx_new_age/tabs/tab3/candidates.py#L18) | 123 | settings; order_block_evidence; compose_candidates |
| [tabs/tab3/order_blocks.py](../../src/sfm_fx_new_age/tabs/tab3/order_blocks.py#L18) | 114 | detect_structure; structure_producer; profile_values; order_block_producer |
| [tabs/tab3/plugin.py](../../src/sfm_fx_new_age/tabs/tab3/plugin.py#L4) | 12 | build_plugin |
| [tabs/tab3/public_activity_alternatives.py](../../src/sfm_fx_new_age/tabs/tab3/public_activity_alternatives.py#L21) | 104 | alternative_kind; evaluate_activity |
| [tabs/tab3/public_algorithms.py](../../src/sfm_fx_new_age/tabs/tab3/public_algorithms.py#L9) | 315 | blank; marker; zone; series; indicator_method; candle_method; structure_events; gap_zones; structural_method; wyckoff; impulse_matches; abc_matches; harmonic_matches; pattern_method; evaluate |
| [tabs/tab3/public_features.py](../../src/sfm_fx_new_age/tabs/tab3/public_features.py#L9) | 154 | sma; ema; rolling; cross; Features |
| [tabs/tab3/public_genuine_data.py](../../src/sfm_fx_new_age/tabs/tab3/public_genuine_data.py#L18) | 274 | source_input; bins_for; value_area; source_zone; quantity_per_bar; point_figure; evaluate_genuine; evaluate_live_body |
| [tabs/tab3/public_pattern_models.py](../../src/sfm_fx_new_age/tabs/tab3/public_pattern_models.py#L8) | 110 | hypotheses; harmonic_hypotheses; evaluate_pattern |
| [tabs/tab3/public_point_figure_auto.py](../../src/sfm_fx_new_age/tabs/tab3/public_point_figure_auto.py#L20) | 79 | automatic_point_figure |
| [tabs/tab3/public_price_models.py](../../src/sfm_fx_new_age/tabs/tab3/public_price_models.py#L11) | 244 | pool_lifecycle; breaker; mitigation; inducement; void_return; previous_body; tested_range; range_rotation; simple_context; evaluate_price |
| [tabs/tab3/public_sequence_features.py](../../src/sfm_fx_new_age/tabs/tab3/public_sequence_features.py#L14) | 253 | cached; true_ranges; atr; displacement; known_swings; alternating_at; structure; pivot_pools; sweeps; origin; gaps; held; retest; stages; emit_setup; sweep_models; acceptance; breakout_models; prior_day_pools; higher_bias; zone_models |
| [tabs/tab3/public_sessions.py](../../src/sfm_fx_new_age/tabs/tab3/public_sessions.py#L19) | 68 | completed_windows; evaluate_session |
| [tabs/tab3/public_workspace.py](../../src/sfm_fx_new_age/tabs/tab3/public_workspace.py#L12) | 140 | PublicStrategiesPanel |
| [tabs/tab3/public_wyckoff.py](../../src/sfm_fx_new_age/tabs/tab3/public_wyckoff.py#L7) | 76 | wyckoff_events; evaluate_wyckoff |
| [tabs/tab3/workspace.py](../../src/sfm_fx_new_age/tabs/tab3/workspace.py#L10) | 54 | StrategyPanel |
| [tabs/tab4/__init__.py](../../src/sfm_fx_new_age/tabs/tab4/__init__.py#L1) | 1 | Package/data marker |
| [tabs/tab4/capital.py](../../src/sfm_fx_new_age/tabs/tab4/capital.py#L8) | 43 | CapitalPanel |
| [tabs/tab4/pending.py](../../src/sfm_fx_new_age/tabs/tab4/pending.py#L7) | 55 | PendingOrdersPanel |
| [tabs/tab4/plugin.py](../../src/sfm_fx_new_age/tabs/tab4/plugin.py#L4) | 13 | build_plugin |
| [tabs/tab4/strategy_signals.py](../../src/sfm_fx_new_age/tabs/tab4/strategy_signals.py#L12) | 135 | StrategySignalsPanel; SignalQueueWorkspace |
| [testing/__init__.py](../../src/sfm_fx_new_age/testing/__init__.py#L1) | 1 | Package/data marker |
| [testing/checkpoint.py](../../src/sfm_fx_new_age/testing/checkpoint.py#L15) | 63 | run_checkpoint |
| [testing/fixtures.py](../../src/sfm_fx_new_age/testing/fixtures.py#L15) | 64 | stamp; populate_fixture; fixture_runtime |
| [ui/__init__.py](../../src/sfm_fx_new_age/ui/__init__.py#L1) | 1 | Package/data marker |
| [ui/chart_axes.py](../../src/sfm_fx_new_age/ui/chart_axes.py#L10) | 239 | ChartAxesMixin |
| [ui/chart_axis.py](../../src/sfm_fx_new_age/ui/chart_axis.py#L6) | 38 | price_ticks; price_badges |
| [ui/chart_canvas.py](../../src/sfm_fx_new_age/ui/chart_canvas.py#L19) | 360 | CandleCanvas |
| [ui/chart_interactions.py](../../src/sfm_fx_new_age/ui/chart_interactions.py#L11) | 284 | ChartInteractionMixin |
| [ui/chart_object_interactions.py](../../src/sfm_fx_new_age/ui/chart_object_interactions.py#L11) | 186 | ObjectInteractionMixin |
| [ui/chart_object_manager.py](../../src/sfm_fx_new_age/ui/chart_object_manager.py#L9) | 89 | DrawingManager |
| [ui/chart_objects.py](../../src/sfm_fx_new_age/ui/chart_objects.py#L6) | 104 | DrawingBook |
| [ui/chart_preferences.py](../../src/sfm_fx_new_age/ui/chart_preferences.py#L9) | 95 | ChartPreferences |
| [ui/chart_projection_bar.py](../../src/sfm_fx_new_age/ui/chart_projection_bar.py#L6) | 62 | ProjectionBar |
| [ui/chart_projection_details.py](../../src/sfm_fx_new_age/ui/chart_projection_details.py#L7) | 45 | PublicProjectionDetails |
| [ui/chart_projection_layout.py](../../src/sfm_fx_new_age/ui/chart_projection_layout.py#L8) | 107 | ProjectionCaptionMixin |
| [ui/chart_properties.py](../../src/sfm_fx_new_age/ui/chart_properties.py#L10) | 189 | ColorButton; scroll_form; StyleControls; ObjectProperties; DrawingDefaults; BulkAppearance |
| [ui/chart_public_strategies.py](../../src/sfm_fx_new_age/ui/chart_public_strategies.py#L7) | 99 | PublicStrategyPaintMixin |
| [ui/chart_workflow.py](../../src/sfm_fx_new_age/ui/chart_workflow.py#L17) | 216 | ChartWorkflowMixin; WorkflowStatus |
| [ui/chart_workspace.py](../../src/sfm_fx_new_age/ui/chart_workspace.py#L17) | 267 | chart_csv; ChartPanel |
| [ui/feed_connection.py](../../src/sfm_fx_new_age/ui/feed_connection.py#L10) | 170 | RememberCheckBox; FeedDialog; FeedCard |
| [ui/inspection_panels.py](../../src/sfm_fx_new_age/ui/inspection_panels.py#L14) | 279 | identity; row_context; describe; InspectionPanel; SignalDetailPanel; ReplayPanel |
| [ui/navigation.py](../../src/sfm_fx_new_age/ui/navigation.py#L9) | 79 | WrappingMainTabBar; MainTabDeck |
| [ui/research_study.py](../../src/sfm_fx_new_age/ui/research_study.py#L12) | 70 | StudyControls |
| [ui/scanner_overview.py](../../src/sfm_fx_new_age/ui/scanner_overview.py#L10) | 62 | _text; ScannerOverview |
| [ui/session_link.py](../../src/sfm_fx_new_age/ui/session_link.py#L14) | 58 | ApplicationLinkDialog; link_through_api |
| [ui/theme.py](../../src/sfm_fx_new_age/ui/theme.py#L15) | 87 | stylesheet; apply_theme |
| [ui_model.py](../../src/sfm_fx_new_age/ui_model.py#L9) | 45 | SubtabViewModel; TabViewModel; build_ui_model |

## Source preservation

The baseline covers source, tests, scripts, verification helpers and original README/diary/project metadata. Generated caches, virtual environments and mutable runtime databases are excluded. Product package resources/contract data are separately included in the input hash roster.
