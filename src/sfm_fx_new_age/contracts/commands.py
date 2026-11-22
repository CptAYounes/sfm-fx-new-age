"""Additive TabApi v1 command-discovery and payload contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Read-only actions expose snapshots; they do not pretend to implement visual filtering.
SNAPSHOT_COMMANDS = frozenset({'FILTER_FAVORITES', 'FILTER_LEVELS', 'SELECT_BANDS', 'SHOW_HIDE_OVERLAYS',
    'FILTER_PIPELINES', 'INSPECT_VARIABLE', 'INSPECT_COMPONENT', 'FILTER_CANDIDATES',
    'VIEW_ORDER', 'LOOKUP_SIGNAL', 'VIEW_POSITION', 'SHOW_W1'})

# (required fields, optional fields). Exact primitive types; bool is NOT an integer revision.
PAYLOADS: dict[str, tuple[dict[str, type], dict[str, type]]] = {
    'SELECT_PAIR': ({'symbol': str}, {}),
    'SELECT_ACCOUNT': ({'scope_id': str}, {}),
    'ISSUE': ({'signal_id': str, 'revision': int, 'user_initiated': bool}, {'acknowledge_research': bool}),
    'CANCEL_SIGNAL': ({'signal_id': str}, {}),
    'CANCEL_ALL_UNISSUED': ({}, {}),
    'SEPARATE_BROKER_CANCEL': ({'order_id': str, 'user_initiated': bool}, {'expected_order_hash':str,'expected_scope_id':str}),
    'REFRESH_HISTORY': ({}, {'order_id': str, 'start':str, 'end':str}),
    'PROPOSE_VERSIONED_PARAM_CHANGE': ({'key': str, 'value': object, 'expected_version': int}, {'symbol':str,'expected_scope_id':str}),
    'SAVE_PREVIEW_ACTIVATE_RULE': ({'rule_id': str, 'rule': dict}, {'action': str, 'expected_version': int, 'version': int, 'output': str}),
    'ENABLE_OPTIONAL_H1': ({'enabled': bool}, {}),
    'SET_CONSUMER_SWITCH': ({'consumer_id': str, 'enabled': bool}, {}),
    'CONNECT': ({}, {}),
    'RECONNECT': ({}, {}),
    'HUMAN_OAUTH_LOGIN': ({}, {'client_id': str, 'redirect_uri': str, 'credential_path': str, 'scope': str}),
    'IMPORT_CTRADER_PROFILE': ({'path':str},{}),
    'IMPORT_CTRADER_SESSION': ({'path':str},{}),
    'REMEMBER_CTRADER_LOGIN': ({'enabled':bool},{}),
    'SIGN_OUT_CTRADER': ({},{}),
    'START_MARKET_FEED': ({}, {}),
    'DISCONNECT_FEED': ({}, {}),
    'REQUEST_BACKFILL': ({'symbol': str, 'timeframe': str, 'start': str, 'end': str}, {}),
    'ENABLE_PAIR': ({'symbol': str, 'enabled': bool}, {}),
    'START_STOP_NONCRITICAL': ({'consumer_id': str, 'enabled': bool}, {}),
    'OPEN_OWNER_EDITOR': ({'surface_id': str}, {}),
    'TUNE_H4': ({'key': str, 'value': object, 'expected_version': int}, {}),
    'TUNE_RULES': ({'key': str, 'value': object, 'expected_version': int}, {}),
    'TUNE_BANDS': ({'key': str, 'value': object, 'expected_version': int}, {}),
    'TUNE_QUALIFIER': ({'key': str, 'value': object, 'expected_version': int}, {}),
    'START_REPLAY': ({'dataset_id': str}, {'action': str, 'run_id': str, 'configuration': dict, 'bars': list, 'source_ref': str}),
    'START_PAUSE_STEP': ({'run_id': str, 'action': str}, {'cursor': int}),
    'SELECT_OOS': ({'dataset_id': str, 'train': int, 'test': int}, {}),
    'ENABLE_OPTIONAL_SENSOR': ({'node_id': str, 'enabled': bool}, {}),
    'ENABLE_RECIPE': ({'recipe_id': str, 'version': int, 'enabled': bool}, {}),
    'SELECT_METHOD': ({'node_id': str}, {}),
    'CONFIRM_SELECTED_SIGNAL': ({'signal_id': str, 'revision': int}, {'acknowledge_research': bool}),
    'BIND_RESEARCH_CANDIDATE': ({'candidate_id':str,'candidate_revision':int,'variant_id':str,'units':str,'expected_version':int,'user_initiated':bool}, {}),
    'DRAW_ANNOTATION': ({'annotation_id': str, 'timeframe': str, 'points': list, 'text': str, 'expected_version': int}, {}),
    'SELECT_LEVEL': ({'level_id': str}, {}),
    'EXPORT_IMPORT_CONFIG': ({'action': str}, {'configuration': dict, 'expected_versions': dict}),
    'SET_RESEARCH_POLICY': ({'policy': dict, 'expected_version': int, 'expected_scope_id': str}, {}),
}


@dataclass(frozen=True, slots=True)
class CommandCapability:
    name: str
    backend_owner: str
    status: str
    required_fields: tuple[str, ...] = ()
    optional_fields: tuple[str, ...] = ()
    detail: str = ''


def capability(name: str, owner: str) -> CommandCapability:
    if name in SNAPSHOT_COMMANDS:
        return CommandCapability(name, owner, 'SNAPSHOT_ONLY', detail='Read via snapshot; visual filtering is tab-owned')
    if name not in PAYLOADS:
        return CommandCapability(name, owner, 'NOT_IMPLEMENTED', detail='No backend handler; never simulated as accepted')
    required, optional = PAYLOADS[name]
    partial = name in {'REFRESH_HISTORY'}
    detail = ('Pure preview; saved version/CAS required for explicit analytical activation' if name == 'SAVE_PREVIEW_ACTIVATE_RULE' else
              'order_id reconciles one order; start/end requests bounded read-only native order/deal history; matching session required' if name == 'REFRESH_HISTORY' else
              'Existing connector session identity only; no authentication fields accepted' if name == 'SELECT_ACCOUNT' else '')
    return CommandCapability(name, owner, 'PARTIAL' if partial else 'IMPLEMENTED',
                             tuple(required), tuple(optional), detail)


def validate_payload(name: str, payload: dict[str, Any]) -> None:
    if name not in PAYLOADS:
        return
    required, optional = PAYLOADS[name]
    unknown = set(payload) - set(required) - set(optional)
    if unknown:
        raise ValueError('Unknown command fields: ' + ', '.join(sorted(unknown)))
    for field, expected in (required | optional).items():
        if field not in payload:
            if field in required:
                raise ValueError(f'Required command field: {field}')
            continue
        value = payload[field]
        if expected is not object and type(value) is not expected:
            raise ValueError(f'{field} requires exact {expected.__name__} type')
        if expected is str and not value:
            raise ValueError(f'{field} must not be empty')
    if 'revision' in payload and payload['revision'] < 1:
        raise ValueError('Positive signal revision required')
    if 'expected_version' in payload and payload['expected_version'] < 0:
        raise ValueError('Nonnegative expected parameter version required')
    import json
    json.dumps(payload, allow_nan=False)
