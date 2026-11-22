"""Versioned research-entry policies for the complete public-method catalogue.

These are NEW explicit engineering compositions, not claims that a public
indicator/context study defines an entry, a profitable strategy or OB-MTF
qualification. One method's observations are never independent consensus.
"""
from dataclasses import dataclass
from .public_strategies import BY_KEY
from .analytics import digest


@dataclass(frozen=True, slots=True)
class SignalPolicy:
    key: str
    trigger: str
    description: str
    version: int = 1

    @property
    def policy_id(self): return 'PUBLIC_LIMIT_RESEARCH_'+self.key.upper()+'_V'+str(self.version)
    @property
    def profile_hash(self): return digest([self, BY_KEY[self.key].profile_hash])


# Explicit exhaustive partition: adding a catalogue method without declaring
# its semantics here fails startup/tests, rather than silently using a fallback.
MARKER_METHODS = (
    'sma_cross','ema_cross','macd','rsi','stochastic','adx','ichimoku','donchian',
    'momentum','bollinger','engulfing','pinbar','inside_break','structure','liquidity',
    'pullback_ob','pullback_fvg','wyckoff','elliott_impulse','elliott_abc','abcd',
    'gartley','bat','butterfly','compression','displacement','mss','sweep_context',
    'pool_rejection','pool_breakout','sweep_reversal','compression_retest',
    'break_confirmation','trend_ob','trend_fvg','smc_zone_retest','breaker',
    'mitigation_block','inducement','liquidity_void','previous_day_sweep',
    'previous_day_breakout','session_sweep','session_breakout','range_rotation',
    'wyckoff_phase','wyckoff_spring_test','wyckoff_utad_test','wyckoff_break_retest',
    'macro_elliott','harmonic_prz','previous_body','previous_body_retest',
    'candle_pressure','trend_persistence','volume_displacement','effort_result',
)
LEVEL_METHODS = (
    'fvg','support_resistance','fibonacci','ote','previous_extremes','open_midpoint',
    'liquidity_pools','session_asia','session_london','session_new_york','killzones',
    'rolling_extremes','round_numbers','profile_tpo','volume_profile','vwap_bands',
)
SPECIAL_METHODS = {
    'order_block': ('NATIVE_OB_ZONE','Confirmed native Order Block zone; proximal Limit entry and distal invalidation. This single-method profile is NOT the separately gated D1/H4 MTF recipe.'),
    'previous_body_live': ('LIVE_BODY','Fresh coherent same-source midpoint recovery of a previous body; provisional quote trigger, not completed OHLC confirmation. Body-boundary Limit retest with original side-clock expiry.'),
    'elliott_alternatives': ('WAVE_RESPONSE','A prior available wave completion/invalidation zone plus a later directional closed-bar reclaim; competing counts remain competing, not extra votes.'),
    'regime_context': ('REGIME_RECOVERY','Observed TREND regime (ADX>=25) plus completed previous-body recovery; regime alone never chooses direction. Range/transition waits.'),
    'atr_trail': ('TRAIL_CROSS','Completed close crosses the prior available Chandelier research line. Trigger-body retracement Limit; no existing position or broker stop is modified.'),
    'cause_effect': ('PNF_RESPONSE','An unreached original P&F objective plus aligned completed-body recovery; objective must remain beyond entry and untraded. Count is not an entry by itself.'),
    'dom_imbalance': ('FLOW_RECOVERY','Original displayed-depth directional imbalance plus aligned completed-body recovery; quote must be fresh. Displayed sizes are never executed volume.'),
    'footprint_delta': ('FLOW_RECOVERY','Original documented executed-aggressor directional delta plus aligned completed-body recovery; no quote-direction substitution.'),
    'cot_macro': ('COT_RECOVERY','Previously available published COT futures bias plus aligned completed-body recovery. Futures positioning is context, not a spot entry or a new publication-time claim.'),
    'calendar_context': ('CALENDAR_RECOVERY','Explicit provider schedule coverage and no affected event within the declared +/-30-minute blackout, plus completed-body recovery. An empty/unknown calendar is never clearance; releases never assign direction.'),
}

POLICIES = {key: SignalPolicy(key,'LATEST_DIRECTIONAL_EVENT',
    'Original method directional event, confirmed at the latest observed completed bar (pivot methods at actual confirmation). '
    'New research entry policy: 50% trigger-body Limit retracement; explicit method invalidation when supplied, '
    'otherwise beyond the two-bar extreme; original opposing pivot objective, 4-hour maximum lifetime. '
    'No retrospective fill, automatic sizing, confidence probability or automatic Issue.') for key in MARKER_METHODS}
POLICIES.update({key: SignalPolicy(key,'PRIOR_LEVEL_RESPONSE',
    'Freeze this method on observations available BEFORE the trigger bar opens. '
    'A later bullish close back above the upper boundary, or bearish close back below the lower boundary, after touching the prior zone; '
    'require the declared directional zone side when present. '
    'Research Limit at the tested boundary, invalidation beyond the trigger/zone extreme; '
    'original opposing pivot objective, 4-hour maximum lifetime. Context alone emits no direction.') for key in LEVEL_METHODS})
POLICIES.update({key: SignalPolicy(key,*spec) for key,spec in SPECIAL_METHODS.items()})
assert len(POLICIES)==len(MARKER_METHODS)+len(LEVEL_METHODS)+len(SPECIAL_METHODS)==83
assert set(POLICIES)==set(BY_KEY)

# These names describe this profile, never the unrelated OB-MTF 14-gate policy.
GATE_NAMES = (
    'AUTHENTICATED_SELECTED_SOURCE','CURRENT_ENABLED_METHOD','CURRENT_PROJECTION',
    'TRIGGER_UNEXPIRED','VALID_NATIVE_GRID_GEOMETRY','FRESH_TWO_SIDED_QUOTE',
    'PENDING_LIMIT_SIDE','INTACT_INVALIDATION','OBSERVED_UNREACHED_TARGET',
    'REWARD_AFTER_OBSERVED_SPREAD','RESOLVED_SOURCE_CONTINUITY',
    'GENUINE_REQUIRED_INPUTS','CURRENT_PARAMETER_PROFILE','SPREAD_WITHIN_THREE_NATIVE_PIPS',
)


def validate_observation(row):
    """Validate at the core publication boundary; no executable payload fields."""
    import json
    from .domain import decimal,instant,FRAMES,PAIRS
    if set(row)&{'orders','units','commands','broker_order_id'}:raise ValueError('Analytical signal cannot carry execution authority')
    if row['strategy_id'] not in POLICIES or row['timeframe'] not in FRAMES or row['symbol'] not in PAIRS:raise ValueError('Known method and source coordinates required')
    if row['origin'] not in {'LIVE_OBSERVED','HISTORICAL_REPLAY','SYNTHETIC_FIXTURE'}:raise ValueError('Explicit observed/replay/fixture origin required')
    if row['policy_hash']!=POLICIES[row['strategy_id']].profile_hash:raise ValueError('Current signal policy hash required')
    if row['opportunity_id']:
        if not row['opportunity_id'].startswith('strategy:') or row['side'] not in {'BUY','SELL'}:raise ValueError('Typed directional research identity required')
        entry,stop=decimal(row['entry'],positive=True),decimal(row['stop'],positive=True)
        if stop>=entry if row['side']=='BUY' else stop<=entry:raise ValueError('Invalid research signal geometry')
        known,expiry=instant(row['available_at']),instant(row['expires_at'])
        if not 0<(expiry-known).total_seconds()<=14400:raise ValueError('Original signal lifetime must be positive and at most 4 hours')
        if not row['trigger']['root_ids'] or instant(row['trigger']['time'])>known:raise ValueError('Causal original trigger roots required')
        if row['target'] is not None:decimal(row['target'],positive=True)
    if len(json.dumps(row,allow_nan=False,default=str))>500000:raise ValueError('Signal observation exceeds budget')
