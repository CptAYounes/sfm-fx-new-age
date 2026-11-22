# R03 — API, Command and Capability Catalogue

[core/tab_api.py · TabApi](../../src/sfm_fx_new_age/core/tab_api.py#L29)

| Command | Required fields | Optional fields | Allowed view IDs |
|---|---|---|---|
| SELECT_PAIR | symbol:str | none | 1.1, 1.2, 1.3, 1.4, 3.2, 3.3 |
| SELECT_ACCOUNT | scope_id:str | none | 1.10, 4.5 |
| ISSUE | signal_id:str, revision:int, user_initiated:bool | acknowledge_research:bool | 4.1 |
| CANCEL_SIGNAL | signal_id:str | none | 4.1 |
| CANCEL_ALL_UNISSUED | none | none | 4.1 |
| SEPARATE_BROKER_CANCEL | order_id:str, user_initiated:bool | expected_order_hash:str, expected_scope_id:str | 4.3 |
| REFRESH_HISTORY | none | order_id:str, start:str, end:str | 4.8 |
| PROPOSE_VERSIONED_PARAM_CHANGE | key:str, value:object, expected_version:int | symbol:str, expected_scope_id:str | 3.11 |
| SAVE_PREVIEW_ACTIVATE_RULE | rule_id:str, rule:dict | action:str, expected_version:int, version:int, output:str | 3.10 |
| ENABLE_OPTIONAL_H1 | enabled:bool | none | 1.5 |
| SET_CONSUMER_SWITCH | consumer_id:str, enabled:bool | none | 2.1 |
| CONNECT | none | none | 2.3 |
| RECONNECT | none | none | 2.3 |
| HUMAN_OAUTH_LOGIN | none | client_id:str, redirect_uri:str, credential_path:str, scope:str | 4.5 |
| IMPORT_CTRADER_PROFILE | path:str | none | 2.3 |
| IMPORT_CTRADER_SESSION | path:str | none | 2.3 |
| REMEMBER_CTRADER_LOGIN | enabled:bool | none | 4.5 |
| SIGN_OUT_CTRADER | none | none | 4.5 |
| START_MARKET_FEED | none | none | 2.3 |
| DISCONNECT_FEED | none | none | 2.3 |
| REQUEST_BACKFILL | symbol:str, timeframe:str, start:str, end:str | none | 2.4 |
| ENABLE_PAIR | symbol:str, enabled:bool | none | 2.5 |
| START_STOP_NONCRITICAL | consumer_id:str, enabled:bool | none | 2.9 |
| OPEN_OWNER_EDITOR | surface_id:str | none | 2.8 |
| TUNE_H4 | key:str, value:object, expected_version:int | none | 3.4 |
| TUNE_RULES | key:str, value:object, expected_version:int | none | 3.6 |
| TUNE_BANDS | key:str, value:object, expected_version:int | none | 3.8 |
| TUNE_QUALIFIER | key:str, value:object, expected_version:int | none | 3.9 |
| START_REPLAY | dataset_id:str | action:str, run_id:str, configuration:dict, bars:list, source_ref:str | 3.12 |
| START_PAUSE_STEP | run_id:str, action:str | cursor:int | 1.9 |
| SELECT_OOS | dataset_id:str, train:int, test:int | none | 3.12 |
| ENABLE_OPTIONAL_SENSOR | node_id:str, enabled:bool | none | 3.7 |
| ENABLE_RECIPE | recipe_id:str, version:int, enabled:bool | none | 3.1 |
| SELECT_METHOD | node_id:str | none | 3.5 |
| CONFIRM_SELECTED_SIGNAL | signal_id:str, revision:int | acknowledge_research:bool | 4.2 |
| BIND_RESEARCH_CANDIDATE | candidate_id:str, candidate_revision:int, variant_id:str, units:str, expected_version:int, user_initiated:bool | none | 4.2 |
| DRAW_ANNOTATION | annotation_id:str, timeframe:str, points:list, text:str, expected_version:int | none | 1.3 |
| SELECT_LEVEL | level_id:str | none | 1.4 |
| EXPORT_IMPORT_CONFIG | action:str | configuration:dict, expected_versions:dict | 2.10 |
| SET_RESEARCH_POLICY | policy:dict, expected_version:int, expected_scope_id:str | none | 4.7 |

## Snapshot-only commands

`FILTER_CANDIDATES`, `FILTER_FAVORITES`, `FILTER_LEVELS`, `FILTER_PIPELINES`, `INSPECT_COMPONENT`, `INSPECT_VARIABLE`, `LOOKUP_SIGNAL`, `SELECT_BANDS`, `SHOW_HIDE_OVERLAYS`, `SHOW_W1`, `VIEW_ORDER`, `VIEW_POSITION`

These names do not create mutation capability. Runtime checks may still refuse an implemented command.

## TabApi methods

| Method | Signature | Source line |
|---|---|---|
| TabSnapshot.__post_init__ | self | 25 |
| TabApi.__init__ | self, runtime: ApplicationRuntime, tab_id: int | 30 |
| TabApi._check | self, subtab_id: str | 40 |
| TabApi.snapshot | self, subtab_id: str | 46 |
| TabApi.command | self, subtab_id: str, name: str, payload: dict[str, Any] \| None=None | 50 |
| TabApi.datasets | self, subtab_id: str | 56 |
| TabApi.query | self, subtab_id: str, request: DataRequest | 60 |
| TabApi.subscribe | self, subtab_id: str, callback: Callable[[Event], None] | 67 |
| TabApi.subscribe_snapshots | self, subtab_id: str, callback: Callable[[TabSnapshot], None], *, initial: bool=True | 81 |
| TabApi.capabilities | self, subtab_id: str | 94 |
| TabApi.close | self | 99 |
| TabApi._workflow | self | 105 |
| TabApi.inspect | self, **selection | 109 |
| TabApi.validate_inspection | self, context | 113 |
| TabApi.inspection_object | self, context | 117 |
| TabApi.navigate | self, target, context | 123 |
| TabApi.scenario_context | self, context, scenario | 127 |
| TabApi.inspection_projection | self, context | 131 |
| TabApi.workspace | self, context | 142 |
| TabApi.save_workspace | self, context, settings, expected_version | 146 |
| TabApi.create_inspection_replay | self, context, run_id | 151 |
| TabApi.request_older_history | self, context, days=30 | 156 |
| TabApi.control_replay | self, run_id, action, *, cursor=None | 161 |
| TabApi.run_research_study | self, request | 166 |
| TabApi.research_study | self, study_id | 170 |
| TabApi.calculator_context | self, context | 174 |
