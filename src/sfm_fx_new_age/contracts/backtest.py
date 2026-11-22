"""Bounded research-only historical marker study. Not order configuration."""
from dataclasses import dataclass
from .domain import FRAMES,symbol_check,decimal

# Only self-contained closed-price marker methods; context/supplemental profiles
# are not silently treated as executable rules or supplied invented histories.
STUDY_METHODS=('sma_cross','ema_cross','macd','rsi','stochastic','adx','ichimoku','donchian','momentum','bollinger','engulfing','pinbar','inside_break','compression')
MODEL_VERSION='NEXT_OBSERVED_OPEN_FIXED_BPS_OHLC_V1'

@dataclass(frozen=True)
class StudyRequest:
    study_id:str
    dataset_id:str
    symbol:str
    timeframe:str
    method_id:str
    stop_bps:tuple[str,...]=('10','20')
    reward_r:tuple[str,...]=('1','2')
    holding_bars:int=5
    train:int=100
    test:int=30
    cost_bps:str='0'
    information_clock:str='AS_OBSERVED'

    def __post_init__(self):
        for key in ('study_id','dataset_id'):
            value=getattr(self,key)
            if type(value) is not str or not 1<=len(value)<=160:raise ValueError('Bounded research identity required')
        symbol_check(self.symbol)
        if self.timeframe not in FRAMES or self.method_id not in STUDY_METHODS:raise ValueError('Supported self-contained historical marker method required')
        for key,lo,hi in [('holding_bars',1,100),('train',2,1500),('test',1,500)]:
            if type(getattr(self,key)) is not int or not lo<=getattr(self,key)<=hi:raise ValueError('Bounded integer research window required')
        for key in ('stop_bps','reward_r'):
            values=getattr(self,key)
            if type(values) is not tuple or not 1<=len(values)<=16 or any(type(v) is not str for v in values):raise ValueError('Tuple of finite decimal axis values required')
            decoded=tuple(decimal(v,positive=True) for v in values)
            if len(set(decoded))!=len(decoded) or max(decoded)>(500 if key=='stop_bps' else 20):raise ValueError('Research axis outside budget or duplicated')
        if len(self.stop_bps)*len(self.reward_r)>64:raise ValueError('Research sweep exceeds 64 configurations')
        if type(self.cost_bps) is not str or not 0<=decimal(self.cost_bps)<=100:raise ValueError('Explicit nonnegative model roundtrip cost required')
        if self.information_clock not in {'AS_OBSERVED','HISTORICAL_CLOSE_ASSUMPTION'}:raise ValueError('Explicit research information clock required')
