# R02 — Typed Contract and Field Catalogue

Extracted from contract AST declarations; runtime validators in the source remain authoritative. Not a generic JSON Schema claim. Decimal values serialize as exact strings.

## Lineage

[contracts/analytics.py · Lineage](../../src/sfm_fx_new_age/contracts/analytics.py#L20)

| Field/member | Type | Default/value |
|---|---|---|
| source_scope | str | REQUIRED |
| source_epoch | str | REQUIRED |
| symbol | str | REQUIRED |
| timeframe | str | REQUIRED |
| available_at | str | REQUIRED |
| origin | Origin | REQUIRED |
| method_version | str | REQUIRED |
| profile_hash | str | REQUIRED |


## Level

[contracts/analytics.py · Level](../../src/sfm_fx_new_age/contracts/analytics.py#L38)

| Field/member | Type | Default/value |
|---|---|---|
| level_id | str | REQUIRED |
| revision | int | REQUIRED |
| kind | str | REQUIRED |
| low | Decimal | REQUIRED |
| high | Decimal | REQUIRED |
| side | str | REQUIRED |
| state | str | REQUIRED |
| root_ids | tuple[str, ...] | REQUIRED |
| lineage | Lineage | REQUIRED |


## Evidence

[contracts/analytics.py · Evidence](../../src/sfm_fx_new_age/contracts/analytics.py#L57)

| Field/member | Type | Default/value |
|---|---|---|
| evidence_id | str | REQUIRED |
| level_id | str | REQUIRED |
| root_id | str | REQUIRED |
| cluster_id | str | REQUIRED |
| fingerprint | str | REQUIRED |
| domain | str | REQUIRED |
| side | str | REQUIRED |
| low | Decimal | REQUIRED |
| high | Decimal | REQUIRED |
| strength | Decimal | REQUIRED |
| reliability | Decimal | REQUIRED |
| expires_at | str | REQUIRED |
| lineage | Lineage | REQUIRED |
| confirmed | bool | True |
| locality | str | 'ENTRY_LOCAL' |


## Recipe

[contracts/analytics.py · Recipe](../../src/sfm_fx_new_age/contracts/analytics.py#L86)

| Field/member | Type | Default/value |
|---|---|---|
| recipe_id | str | REQUIRED |
| version | int | REQUIRED |
| name | str | REQUIRED |
| required_nodes | tuple[str, ...] | REQUIRED |
| source_ref | str | REQUIRED |
| profile_hash | str | REQUIRED |
| state | str | 'RESEARCH_ONLY' |


## Variant

[contracts/analytics.py · Variant](../../src/sfm_fx_new_age/contracts/analytics.py#L102)

| Field/member | Type | Default/value |
|---|---|---|
| variant_id | str | REQUIRED |
| buffer_code | str | REQUIRED |
| buffer_fraction | Decimal | REQUIRED |
| stop_price | Decimal | REQUIRED |
| distance_pips | Decimal | REQUIRED |
| w1_atr_fraction | Decimal | REQUIRED |
| actual_band | str | REQUIRED |
| target_price | Decimal \| None | REQUIRED |
| reward_r | Decimal \| None | REQUIRED |
| blockers | tuple[str, ...] | () |


## MarketCandidate

[contracts/analytics.py · MarketCandidate](../../src/sfm_fx_new_age/contracts/analytics.py#L125)

| Field/member | Type | Default/value |
|---|---|---|
| candidate_id | str | REQUIRED |
| setup_id | str | REQUIRED |
| revision | int | REQUIRED |
| recipe_id | str | REQUIRED |
| recipe_version | int | REQUIRED |
| zone_id | str | REQUIRED |
| side | str | REQUIRED |
| entry | Decimal | REQUIRED |
| anchor | Decimal | REQUIRED |
| target | Decimal \| None | REQUIRED |
| evidence_ids | tuple[str, ...] | REQUIRED |
| variants | tuple[Variant, ...] | REQUIRED |
| lineage | Lineage | REQUIRED |
| expires_at | str | REQUIRED |
| confidence | Decimal \| None | None |
| quality | Decimal \| None | None |
| blockers | tuple[str, ...] | () |
| research_state | str | 'RESEARCH_UNCALIBRATED' |
| gates | tuple[tuple[str, bool \| None], ...] | () |


## Overlay

[contracts/analytics.py · Overlay](../../src/sfm_fx_new_age/contracts/analytics.py#L164)

| Field/member | Type | Default/value |
|---|---|---|
| overlay_id | str | REQUIRED |
| revision | int | REQUIRED |
| kind | str | REQUIRED |
| object_id | str | REQUIRED |
| low | Decimal | REQUIRED |
| high | Decimal | REQUIRED |
| state | str | REQUIRED |
| lineage | Lineage | REQUIRED |


## VariableDefinition

[contracts/analytics.py · VariableDefinition](../../src/sfm_fx_new_age/contracts/analytics.py#L181)

| Field/member | Type | Default/value |
|---|---|---|
| key | str | REQUIRED |
| owner | str | REQUIRED |
| data_type | str | REQUIRED |
| unit | str | REQUIRED |
| scope | str | REQUIRED |
| symbol | str \| None | None |
| timeframe | str \| None | None |
| quote_basis | str | 'NOT_APPLICABLE' |
| maturity | str | 'NOT_APPLICABLE' |
| max_age_seconds | int \| None | None |
| version | int | 1 |


## ParameterDefinition

[contracts/analytics.py · ParameterDefinition](../../src/sfm_fx_new_age/contracts/analytics.py#L206)

| Field/member | Type | Default/value |
|---|---|---|
| key | str | REQUIRED |
| owner | str | REQUIRED |
| data_type | str | REQUIRED |
| unit | str | REQUIRED |
| scope | str | 'GLOBAL' |
| minimum | Decimal \| None | None |
| maximum | Decimal \| None | None |
| choices | tuple[str, ...] | () |
| activation_boundary | str | 'CORE_EVENT' |
| default | Any | None |


## MutableSurface

[contracts/analytics.py · MutableSurface](../../src/sfm_fx_new_age/contracts/analytics.py#L237)

| Field/member | Type | Default/value |
|---|---|---|
| surface_id | str | REQUIRED |
| owner | str | REQUIRED |
| parameter_keys | tuple[str, ...] | REQUIRED |
| subtab_id | str | REQUIRED |
| command | str | 'PROPOSE_VERSIONED_PARAM_CHANGE' |
| classification | str | 'RESEARCH_CONFIGURATION' |


## StudyRequest

[contracts/backtest.py · StudyRequest](../../src/sfm_fx_new_age/contracts/backtest.py#L11)

| Field/member | Type | Default/value |
|---|---|---|
| study_id | str | REQUIRED |
| dataset_id | str | REQUIRED |
| symbol | str | REQUIRED |
| timeframe | str | REQUIRED |
| method_id | str | REQUIRED |
| stop_bps | tuple[str, ...] | ('10', '20') |
| reward_r | tuple[str, ...] | ('1', '2') |
| holding_bars | int | 5 |
| train | int | 100 |
| test | int | 30 |
| cost_bps | str | '0' |
| information_clock | str | 'AS_OBSERVED' |


## CommandCapability

[contracts/commands.py · CommandCapability](../../src/sfm_fx_new_age/contracts/commands.py#L58)

| Field/member | Type | Default/value |
|---|---|---|
| name | str | REQUIRED |
| backend_owner | str | REQUIRED |
| status | str | REQUIRED |
| required_fields | tuple[str, ...] | () |
| optional_fields | tuple[str, ...] | () |
| detail | str | '' |


## Origin

[contracts/domain.py · Origin](../../src/sfm_fx_new_age/contracts/domain.py#L14)

| Field/member | Type | Default/value |
|---|---|---|
| LIVE_OBSERVED | class/enum constant | 'LIVE_OBSERVED' |
| HISTORICAL_REPLAY | class/enum constant | 'HISTORICAL_REPLAY' |
| SYNTHETIC_FIXTURE | class/enum constant | 'SYNTHETIC_FIXTURE' |


## SignalState

[contracts/domain.py · SignalState](../../src/sfm_fx_new_age/contracts/domain.py#L20)

| Field/member | Type | Default/value |
|---|---|---|
| QUEUED | class/enum constant | 'QUEUED' |
| ISSUE_RESERVED | class/enum constant | 'ISSUE_RESERVED' |
| ISSUED | class/enum constant | 'ISSUED' |
| CANCELED | class/enum constant | 'CANCELED' |
| EXPIRED | class/enum constant | 'EXPIRED' |
| REVOKED | class/enum constant | 'REVOKED' |


## OrderState

[contracts/domain.py · OrderState](../../src/sfm_fx_new_age/contracts/domain.py#L29)

| Field/member | Type | Default/value |
|---|---|---|
| RESERVED | class/enum constant | 'RESERVED' |
| SUBMITTING | class/enum constant | 'SUBMITTING' |
| ACCEPTED_PENDING | class/enum constant | 'ACCEPTED_PENDING' |
| PARTIALLY_FILLED | class/enum constant | 'PARTIALLY_FILLED' |
| FILLED | class/enum constant | 'FILLED' |
| REJECTED | class/enum constant | 'REJECTED' |
| CANCELED | class/enum constant | 'CANCELED' |
| EXPIRED | class/enum constant | 'EXPIRED' |
| UNKNOWN | class/enum constant | 'UNKNOWN' |


## SymbolSpec

[contracts/domain.py · SymbolSpec](../../src/sfm_fx_new_age/contracts/domain.py#L78)

| Field/member | Type | Default/value |
|---|---|---|
| account_id | str | REQUIRED |
| symbol | str | REQUIRED |
| broker_symbol_id | int | REQUIRED |
| pip_size | Decimal | REQUIRED |
| tick_size | Decimal | REQUIRED |
| volume_min | Decimal | REQUIRED |
| volume_max | Decimal | REQUIRED |
| volume_step | Decimal | REQUIRED |
| units_per_lot | Decimal | REQUIRED |
| origin | Origin | REQUIRED |
| scope_id | str | 'UNBOUND' |


## Bar

[contracts/domain.py · Bar](../../src/sfm_fx_new_age/contracts/domain.py#L110)

| Field/member | Type | Default/value |
|---|---|---|
| symbol | str | REQUIRED |
| timeframe | str | REQUIRED |
| open_time | str | REQUIRED |
| close_time | str | REQUIRED |
| available_at | str | REQUIRED |
| open | Decimal | REQUIRED |
| high | Decimal | REQUIRED |
| low | Decimal | REQUIRED |
| close | Decimal | REQUIRED |
| source_epoch | str | REQUIRED |
| origin | Origin | REQUIRED |
| scope_id | str | 'UNBOUND' |
| revision | int | 1 |
| quote_basis | str | 'UNKNOWN' |
| construction | str | 'NATIVE_OBSERVED' |
| tick_volume | int \| None | None |


## Quote

[contracts/domain.py · Quote](../../src/sfm_fx_new_age/contracts/domain.py#L148)

| Field/member | Type | Default/value |
|---|---|---|
| account_id | str | REQUIRED |
| symbol | str | REQUIRED |
| bid | Decimal | REQUIRED |
| ask | Decimal | REQUIRED |
| available_at | str | REQUIRED |
| source_epoch | str | REQUIRED |
| origin | Origin | REQUIRED |
| scope_id | str | 'UNBOUND' |
| bid_at | str \| None | None |
| ask_at | str \| None | None |
| sequence | int | 0 |


## AccountContext

[contracts/domain.py · AccountContext](../../src/sfm_fx_new_age/contracts/domain.py#L177)

| Field/member | Type | Default/value |
|---|---|---|
| account_id | str | REQUIRED |
| endpoint_class | str | REQUIRED |
| currency | str | REQUIRED |
| authenticated | bool | REQUIRED |
| trading_scope | bool | REQUIRED |
| origin | Origin | REQUIRED |
| account_type | str | 'UNKNOWN' |
| broker_id | str | 'UNSPECIFIED' |


## Candidate

[contracts/domain.py · Candidate](../../src/sfm_fx_new_age/contracts/domain.py#L201)

| Field/member | Type | Default/value |
|---|---|---|
| signal_id | str | REQUIRED |
| setup_id | str | REQUIRED |
| revision | int | REQUIRED |
| symbol | str | REQUIRED |
| side | str | REQUIRED |
| entry_price | Decimal | REQUIRED |
| invalidation_price | Decimal | REQUIRED |
| units | Decimal | REQUIRED |
| expires_at | str | REQUIRED |
| available_at | str | REQUIRED |
| source_epoch | str | REQUIRED |
| origin | Origin | REQUIRED |
| profile | str | 'RESEARCH_ONLY' |
| scope_id | str | 'UNBOUND' |
| market_candidate_id | str \| None | None |
| market_candidate_revision | int \| None | None |
| source_candidate_hash | str \| None | None |
| variant_id | str \| None | None |


## BrokerOutcome

[contracts/domain.py · BrokerOutcome](../../src/sfm_fx_new_age/contracts/domain.py#L243)

| Field/member | Type | Default/value |
|---|---|---|
| state | OrderState | REQUIRED |
| broker_order_id | str \| None | None |
| position_id | str \| None | None |
| detail | str | '' |


## Priority

[contracts/enums.py · Priority](../../src/sfm_fx_new_age/contracts/enums.py#L6)

| Field/member | Type | Default/value |
|---|---|---|
| P0 | class/enum constant | 0 |
| P1 | class/enum constant | 1 |
| P2 | class/enum constant | 2 |
| P3 | class/enum constant | 3 |


## Freshness

[contracts/enums.py · Freshness](../../src/sfm_fx_new_age/contracts/enums.py#L13)

| Field/member | Type | Default/value |
|---|---|---|
| CURRENT | class/enum constant | 'CURRENT' |
| LAST_KNOWN | class/enum constant | 'LAST_KNOWN' |
| STALE | class/enum constant | 'STALE' |
| GAP | class/enum constant | 'GAP' |
| UNKNOWN | class/enum constant | 'UNKNOWN' |
| RECONCILING | class/enum constant | 'RECONCILING' |


## Availability

[contracts/enums.py · Availability](../../src/sfm_fx_new_age/contracts/enums.py#L22)

| Field/member | Type | Default/value |
|---|---|---|
| WIRED | class/enum constant | 'WIRED' |
| NOT_AVAILABLE | class/enum constant | 'NOT_AVAILABLE' |
| UNCONFIGURED | class/enum constant | 'UNCONFIGURED' |
| DISCONNECTED | class/enum constant | 'DISCONNECTED' |
| ERROR | class/enum constant | 'ERROR' |


## CommandStatus

[contracts/enums.py · CommandStatus](../../src/sfm_fx_new_age/contracts/enums.py#L30)

| Field/member | Type | Default/value |
|---|---|---|
| ACCEPTED | class/enum constant | 'ACCEPTED' |
| RECORDED | class/enum constant | 'RECORDED' |
| REJECTED | class/enum constant | 'REJECTED' |
| NOT_IMPLEMENTED | class/enum constant | 'NOT_IMPLEMENTED' |


## VariableUpdate

[contracts/extensions.py · VariableUpdate](../../src/sfm_fx_new_age/contracts/extensions.py#L9)

| Field/member | Type | Default/value |
|---|---|---|
| key | str | REQUIRED |
| value | Any | REQUIRED |
| available_at | str | REQUIRED |
| freshness | str | 'CURRENT' |


## AnalyticalResult

[contracts/extensions.py · AnalyticalResult](../../src/sfm_fx_new_age/contracts/extensions.py#L21)

| Field/member | Type | Default/value |
|---|---|---|
| state | str | REQUIRED |
| value | Any | None |
| objects | tuple[Level \| Evidence \| MarketCandidate \| Overlay, ...] | () |
| reason | str | '' |
| variables | tuple[VariableUpdate, ...] | () |


## Event

[contracts/models.py · Event](../../src/sfm_fx_new_age/contracts/models.py#L39)

| Field/member | Type | Default/value |
|---|---|---|
| topic | str | REQUIRED |
| source_component | str | REQUIRED |
| payload | Mapping[str, Any] | field(default_factory=dict) |
| priority | Priority | Priority.P2 |
| partition_key | str | 'GLOBAL' |
| source_epoch | str | 'LOCAL-FOUNDATION' |
| event_id | str | field(default_factory=lambda: str(uuid4())) |
| produced_at_utc | str | field(default_factory=utc_now) |
| freshness | Freshness | Freshness.CURRENT |


## Command

[contracts/models.py · Command](../../src/sfm_fx_new_age/contracts/models.py#L57)

| Field/member | Type | Default/value |
|---|---|---|
| name | str | REQUIRED |
| target_component | str | REQUIRED |
| source_view | str | REQUIRED |
| payload | Mapping[str, Any] | field(default_factory=dict) |
| priority | Priority | Priority.P2 |
| command_id | str | field(default_factory=lambda: str(uuid4())) |
| created_at_utc | str | field(default_factory=utc_now) |


## CommandResult

[contracts/models.py · CommandResult](../../src/sfm_fx_new_age/contracts/models.py#L73)

| Field/member | Type | Default/value |
|---|---|---|
| command_id | str | REQUIRED |
| status | CommandStatus | REQUIRED |
| message | str | REQUIRED |
| emitted_topics | tuple[str, ...] | () |


## SubtabDefinition

[contracts/models.py · SubtabDefinition](../../src/sfm_fx_new_age/contracts/models.py#L81)

| Field/member | Type | Default/value |
|---|---|---|
| main_tab | int | REQUIRED |
| main_tab_title | str | REQUIRED |
| subtab_id | str | REQUIRED |
| title | str | REQUIRED |
| backend_owner | str | REQUIRED |
| subscribed_topics | tuple[str, ...] | REQUIRED |
| commands | tuple[str, ...] | REQUIRED |
| priority | Priority | REQUIRED |
| purpose | str | REQUIRED |


## RouteDefinition

[contracts/models.py · RouteDefinition](../../src/sfm_fx_new_age/contracts/models.py#L94)

| Field/member | Type | Default/value |
|---|---|---|
| source | str | REQUIRED |
| destination | str | REQUIRED |
| topic | str | REQUIRED |
| trigger | str | REQUIRED |
| priority | Priority | REQUIRED |
| rule | str | REQUIRED |
| status | str | REQUIRED |


## ProjectionMethod

[contracts/public_strategies.py · ProjectionMethod](../../src/sfm_fx_new_age/contracts/public_strategies.py#L10)

| Field/member | Type | Default/value |
|---|---|---|
| key | str | REQUIRED |
| name | str | REQUIRED |
| family | str | REQUIRED |
| warmup | int | REQUIRED |
| rules | str | REQUIRED |
| sources | tuple[str, ...] | REQUIRED |
| parameters | tuple[tuple[str, object], ...] | () |
| version | int | 1 |
| input_frames | tuple[str, ...] | () |
| data_kind | str | '' |
| document_recipes | tuple[str, ...] | () |


## SignalPolicy

[contracts/strategy_signals.py · SignalPolicy](../../src/sfm_fx_new_age/contracts/strategy_signals.py#L13)

| Field/member | Type | Default/value |
|---|---|---|
| key | str | REQUIRED |
| trigger | str | REQUIRED |
| description | str | REQUIRED |
| version | int | 1 |


## SupplementalEvidence

[contracts/supplemental.py · SupplementalEvidence](../../src/sfm_fx_new_age/contracts/supplemental.py#L14)

| Field/member | Type | Default/value |
|---|---|---|
| provider_id | str | REQUIRED |
| kind | str | REQUIRED |
| scope_id | str | REQUIRED |
| source_epoch | str | REQUIRED |
| symbol | str | REQUIRED |
| origin | str | REQUIRED |
| source_ref | str | REQUIRED |
| venue | str | REQUIRED |
| instrument | str | REQUIRED |
| price_domain | str | REQUIRED |
| unit | str | REQUIRED |
| window_start | str | REQUIRED |
| window_end | str | REQUIRED |
| available_at | str | REQUIRED |
| valid_until | str | REQUIRED |
| complete | bool | REQUIRED |
| records | tuple[dict, ...] | REQUIRED |
| parameters | dict | REQUIRED |
| revision | int | 1 |
| schema_version | int | 1 |


## DataRequest

[contracts/tab_data.py · DataRequest](../../src/sfm_fx_new_age/contracts/tab_data.py#L30)

| Field/member | Type | Default/value |
|---|---|---|
| dataset | str | REQUIRED |
| symbol | str \| None | None |
| timeframe | str \| None | None |
| as_of | str \| None | None |
| object_id | str \| None | None |
| run_id | str \| None | None |
| limit | int | 500 |
| cursor | int | 0 |
| history | bool | False |
| expected_hash | str \| None | None |
| acknowledge_research | bool | False |
