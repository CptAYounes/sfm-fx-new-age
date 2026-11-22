"""Trusted analytical plugin result DTO; contains no execution command or service handle."""
from dataclasses import dataclass
from typing import Any
from .analytics import Level,Evidence,MarketCandidate,Overlay
from .domain import instant


@dataclass(frozen=True)
class VariableUpdate:
    key:str
    value:Any
    available_at:str
    freshness:str='CURRENT'

    def __post_init__(self):
        instant(self.available_at)
        if not self.key or self.freshness not in {'CURRENT','STALE','MISSING','ERROR'}:raise ValueError('Typed variable observation required')


@dataclass(frozen=True)
class AnalyticalResult:
    state:str
    value:Any=None
    objects:tuple[Level|Evidence|MarketCandidate|Overlay,...]=()
    reason:str=''
    variables:tuple[VariableUpdate,...]=()

    def __post_init__(self):
        if type(self.objects) is not tuple or len(self.objects)>1000 or any(type(item) not in {Level,Evidence,MarketCandidate,Overlay} for item in self.objects):raise ValueError('Bounded typed analytical objects required')
        if self.state not in {'EVALUATED','NO_DATA','WARMUP','UNSUPPORTED'}:raise ValueError('Explicit analytical result state required')
        if type(self.variables) is not tuple or len(self.variables)>1000 or any(type(item) is not VariableUpdate for item in self.variables):raise ValueError('Bounded typed variable observations required')
        if self.state!='EVALUATED' and (self.objects or self.variables):raise ValueError('Unavailable analytical methods cannot publish objects or variables')
