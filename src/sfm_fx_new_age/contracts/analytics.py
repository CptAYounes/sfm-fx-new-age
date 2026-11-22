"""Versioned Qt-neutral producer/consumer contracts for every tab lane."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
import hashlib
import json

from .domain import Origin, FRAMES, decimal, instant, symbol_check, record

SCHEMA_VERSION = 1


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False,
                                     default=str).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Lineage:
    source_scope: str
    source_epoch: str
    symbol: str
    timeframe: str
    available_at: str
    origin: Origin
    method_version: str
    profile_hash: str

    def __post_init__(self):
        symbol_check(self.symbol); instant(self.available_at)
        if self.timeframe not in FRAMES or not all((self.source_scope, self.source_epoch, self.method_version, self.profile_hash)):
            raise ValueError('Complete source, method and profile lineage required')
        object.__setattr__(self, 'origin', Origin(self.origin))


@dataclass(frozen=True, slots=True)
class Level:
    level_id: str
    revision: int
    kind: str
    low: Decimal
    high: Decimal
    side: str
    state: str
    root_ids: tuple[str, ...]
    lineage: Lineage

    def __post_init__(self):
        for field in ('low', 'high'): object.__setattr__(self, field, decimal(getattr(self, field), positive=True))
        if (not self.level_id or type(self.revision) is not int or self.revision < 1 or self.low > self.high
            or self.side not in {'BUY', 'SELL', 'NEUTRAL'} or self.state not in {'PROVISIONAL', 'CONFIRMED', 'TOUCHED', 'INVALIDATED', 'EXPIRED'}
            or not self.root_ids): raise ValueError('Invalid level contract')


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    level_id: str
    root_id: str
    cluster_id: str
    fingerprint: str
    domain: str
    side: str
    low: Decimal
    high: Decimal
    strength: Decimal
    reliability: Decimal
    expires_at: str
    lineage: Lineage
    confirmed: bool = True
    locality: str = 'ENTRY_LOCAL'

    def __post_init__(self):
        for field in ('low', 'high', 'strength', 'reliability'):
            object.__setattr__(self, field, decimal(getattr(self, field)))
        if (not all((self.evidence_id, self.root_id, self.cluster_id, self.fingerprint, self.domain))
            or self.low <= 0 or self.low > self.high or self.side not in {'BUY', 'SELL', 'NEUTRAL'}
            or not 0 <= self.strength <= 1 or not 0 <= self.reliability <= 1
            or self.locality not in {'ENTRY_LOCAL', 'CONTEXT', 'UNLOCATED'} or type(self.confirmed) is not bool
            or instant(self.expires_at) <= instant(self.lineage.available_at)):
            raise ValueError('Invalid evidence contract')


@dataclass(frozen=True, slots=True)
class Recipe:
    recipe_id: str
    version: int
    name: str
    required_nodes: tuple[str, ...]
    source_ref: str
    profile_hash: str
    state: str = 'RESEARCH_ONLY'

    def __post_init__(self):
        if (not all((self.recipe_id, self.name, self.source_ref, self.profile_hash)) or type(self.version) is not int or self.version < 1
            or not self.required_nodes or self.state not in {'RESEARCH_ONLY', 'DISABLED'}):
            raise ValueError('Source-backed research recipe required')


@dataclass(frozen=True, slots=True)
class Variant:
    variant_id: str
    buffer_code: str
    buffer_fraction: Decimal
    stop_price: Decimal
    distance_pips: Decimal
    w1_atr_fraction: Decimal
    actual_band: str
    target_price: Decimal | None
    reward_r: Decimal | None
    blockers: tuple[str, ...] = ()

    def __post_init__(self):
        for key in ('buffer_fraction','stop_price','distance_pips','w1_atr_fraction'):
            object.__setattr__(self,key,decimal(getattr(self,key)))
        for key in ('target_price','reward_r'):
            if getattr(self,key) is not None:object.__setattr__(self,key,decimal(getattr(self,key),positive=True))
        if (not self.variant_id or not self.buffer_code or not self.actual_band or self.buffer_fraction<0
            or self.distance_pips<=0 or self.w1_atr_fraction<=0 or type(self.blockers) is not tuple
            or self.stop_price<=0 and 'INVALID_STOP_PRICE' not in self.blockers):raise ValueError('Invalid variant geometry')


@dataclass(frozen=True, slots=True)
class MarketCandidate:
    candidate_id: str
    setup_id: str
    revision: int
    recipe_id: str
    recipe_version: int
    zone_id: str
    side: str
    entry: Decimal
    anchor: Decimal
    target: Decimal | None
    evidence_ids: tuple[str, ...]
    variants: tuple[Variant, ...]
    lineage: Lineage
    expires_at: str
    confidence: Decimal | None = None
    quality: Decimal | None = None
    blockers: tuple[str, ...] = ()
    research_state: str = 'RESEARCH_UNCALIBRATED'
    gates: tuple[tuple[str, bool | None], ...] = ()

    def __post_init__(self):
        for field in ('entry', 'anchor'): object.__setattr__(self, field, decimal(getattr(self, field), positive=True))
        if self.target is not None: object.__setattr__(self, 'target', decimal(self.target, positive=True))
        for key in ('confidence','quality'):
            if getattr(self,key) is not None:
                object.__setattr__(self,key,decimal(getattr(self,key)))
                if not 0<=getattr(self,key)<=100:raise ValueError('Research indices must be 0..100, not probabilities')
        if self.gates and (type(self.gates) is not tuple or len(dict(self.gates))!=14
            or set(dict(self.gates))!={f'QG{i:02d}' for i in range(1,15)}
            or any(type(value) is not bool and value is not None for _,value in self.gates)):raise ValueError('Explicit 14-gate qualification required')
        if (not all((self.candidate_id, self.setup_id, self.recipe_id, self.zone_id)) or type(self.revision) is not int or self.revision < 1
            or type(self.recipe_version) is not int or self.recipe_version < 1 or self.side not in {'BUY', 'SELL'} or not self.evidence_ids
            or not self.variants or self.research_state != 'RESEARCH_UNCALIBRATED'
            or instant(self.expires_at) <= instant(self.lineage.available_at)):
            raise ValueError('Invalid research candidate contract')


@dataclass(frozen=True, slots=True)
class Overlay:
    overlay_id: str
    revision: int
    kind: str
    object_id: str
    low: Decimal
    high: Decimal
    state: str
    lineage: Lineage

    def __post_init__(self):
        for field in ('low', 'high'): object.__setattr__(self, field, decimal(getattr(self, field), positive=True))
        if not self.overlay_id or type(self.revision) is not int or self.revision < 1 or self.low > self.high or self.state not in {'ACTIVE', 'REVOKED', 'EXPIRED'}:
            raise ValueError('Invalid overlay contract')


@dataclass(frozen=True, slots=True)
class VariableDefinition:
    key: str
    owner: str
    data_type: str
    unit: str
    scope: str
    symbol: str | None = None
    timeframe: str | None = None
    quote_basis: str = 'NOT_APPLICABLE'
    maturity: str = 'NOT_APPLICABLE'
    max_age_seconds: int | None = None
    version: int = 1

    def __post_init__(self):
        if not all((self.key, self.owner, self.unit, self.scope)) or self.data_type not in {'number', 'integer', 'boolean', 'string', 'enum', 'zone'}:
            raise ValueError('Typed producer-owned variable required')
        if self.symbol: symbol_check(self.symbol)
        if self.timeframe and self.timeframe not in FRAMES: raise ValueError('Unknown timeframe')
        if self.quote_basis not in {'BID', 'ASK', 'MID', 'UNKNOWN', 'NOT_APPLICABLE'}: raise ValueError('Unknown quote basis')
        if self.maturity not in {'FORMING', 'COMPLETED', 'CONFIRMED', 'PROVISIONAL', 'NOT_APPLICABLE'}: raise ValueError('Unknown maturity')
        if self.max_age_seconds is not None and (type(self.max_age_seconds) is not int or self.max_age_seconds<1):raise ValueError('Positive integer variable freshness bound required')
        if type(self.version) is not int or self.version<1:raise ValueError('Positive variable definition version required')


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    key: str
    owner: str
    data_type: str
    unit: str
    scope: str = 'GLOBAL'
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    choices: tuple[str, ...] = ()
    activation_boundary: str = 'CORE_EVENT'
    default: Any = None

    def __post_init__(self):
        if not all((self.key, self.owner, self.unit, self.scope)) or self.data_type not in {'number','integer','boolean','string','enum'}:
            raise ValueError('Typed parameter ownership required')
        if self.activation_boundary != 'CORE_EVENT': raise ValueError('Only core-event activation is implemented')
        if self.default is not None: self.validate(self.default)

    def validate(self, value: Any) -> None:
        expected = {'boolean': bool, 'integer': int, 'string': str}
        if self.data_type in expected and type(value) is not expected[self.data_type]: raise ValueError('Parameter type mismatch')
        if self.data_type=='enum' and (type(value) is not str or not self.choices): raise ValueError('Enumerated choice required')
        if self.data_type in {'number', 'integer'}:
            if isinstance(value, bool): raise ValueError('Boolean is not numeric')
            number = decimal(value)
            if self.minimum is not None and number < decimal(self.minimum): raise ValueError('Below parameter minimum')
            if self.maximum is not None and number > decimal(self.maximum): raise ValueError('Above parameter maximum')
        if self.choices and value not in self.choices: raise ValueError('Unknown parameter choice')


@dataclass(frozen=True, slots=True)
class MutableSurface:
    surface_id: str
    owner: str
    parameter_keys: tuple[str, ...]
    subtab_id: str
    command: str = 'PROPOSE_VERSIONED_PARAM_CHANGE'
    classification: str = 'RESEARCH_CONFIGURATION'

    def __post_init__(self):
        if not all((self.surface_id, self.owner, self.subtab_id)) or not self.parameter_keys or self.classification not in {'DISPLAY', 'RESEARCH_CONFIGURATION'}:
            raise ValueError('Only registered display/research mutable surfaces permitted')
