"""Publicly documented method catalogue; names/branding do not imply custom rules.

These explicit engineering profiles are uncalibrated projection definitions,
not exhaustive implementations of every discretionary interpretation.
"""
from dataclasses import dataclass
from .analytics import digest

@dataclass(frozen=True)
class ProjectionMethod:
    key:str
    name:str
    family:str
    warmup:int
    rules:str
    sources:tuple[str,...]
    parameters:tuple[tuple[str,object],...]=()
    version:int=1
    input_frames:tuple[str,...]=()
    data_kind:str=''
    document_recipes:tuple[str,...]=()
    @property
    def recipe_id(self):
        return 'sfm.order_block.research.v1' if self.key=='order_block' else 'public.forex.'+self.key+'.v1'
    @property
    def method_version(self):return 'PUBLIC_FOREX_'+self.key.upper()+'_V'+str(self.version)
    @property
    def profile_hash(self):return digest(self)
    @property
    def required_nodes(self):
        if self.key=='order_block':return ('ORDER_BLOCK',)
        if self.key=='pullback_ob':return ('SMC_STRUCTURE',)
        if self.key in {'structure','liquidity','elliott_impulse','elliott_abc','abcd','gartley','bat','butterfly','support_resistance','fibonacci','ote',
            'mss','sweep_context','liquidity_pools','pool_rejection','pool_breakout','sweep_reversal','breaker','mitigation_block','inducement',
            'previous_day_sweep','previous_day_breakout','session_sweep','range_rotation','elliott_alternatives','macro_elliott','harmonic_prz'}:return ('SWING_MAP',)
        if self.key in {'trend_ob','trend_fvg','smc_zone_retest'}:return ('SMC_STRUCTURE','SWING_MAP')
        return ()

C='https://help.ctrader.com/indicators/built-in/'
B='https://cmcmarketsfunded.com/learn/'
W='https://www.wyckoffanalytics.com/wyckoff-method/'
E='https://www.elliottwave.com/waveopedia/'
H='https://harmonictrader.com/harmonic-patterns/'
P='https://www.learntotradethemarket.com/forex-trading-strategies/price-action-setups-pin-bars-fakeys-inside-bars'

def method(key,name,family,warmup,rules,sources,**params):
    return ProjectionMethod(key,name,family,warmup,rules,tuple(sources),tuple(sorted(params.items())))

METHODS=(
 method('sma_cross','SMA crossover','Trend',51,'20/50 completed-close SMA crossing; equality is not a new cross.',[C+'trend/simple-moving-average/'],fast=20,slow=50),
 method('ema_cross','EMA crossover','Trend',51,'20/50 close EMA, arithmetic-mean seed at each full period; strict crossover.',[C+'trend/exponential-moving-average/'],fast=20,slow=50),
 method('macd','MACD signal crossover','Momentum',35,'12/26 close EMAs; 9-period EMA of valid MACD values. Strict signal crossover; no price-axis oscillator line.',[C+'oscillators/macd-crossover/']),
 method('rsi','RSI oversold/overbought re-entry','Momentum',16,'Wilder RSI(14), mean seed; BUY crossing back above 30, SELL back below 70. Flat=50; no loss=100.',[C+'oscillators/relative-strength-index/']),
 method('stochastic','Stochastic extreme crossover','Momentum',19,'14-bar raw %K; SMA(3) slow K and SMA(3) D; cross from K<=20 BUY / K>=80 SELL. Flat range=50.',[C+'oscillators/stochastic-oscillator/']),
 method('adx','ADX directional crossover','Trend',29,'Wilder TR/DM(14), DX and ADX(14); DI crossover only with current ADX>=25. Negative DM uses previous low minus current low.',[C+'trend/directional-movement-system/']),
 method('ichimoku','Ichimoku cloud breakout','Trend',79,'9/26/52 midranges. Cloud at index i uses spans computed i-26; close crosses outside cloud with matching Tenkan/Kijun direction. Never backdate current close as evidence.',[C+'other/ichimoku-kinko-hyo/']),
 method('donchian','Donchian channel breakout','Breakout',21,'Strict completed close beyond previous 20-bar high/low, excluding the breakout bar. One crossing event, not one per trend bar.',[C+'volatility/donchian-channel/']),
 method('momentum','Time-series momentum','Momentum',22,'20-bar close ratio minus one; crossing zero projects direction. This is a price momentum lens, not the custom M38/M39 portfolio rules.',[C+'oscillators/momentum-oscillator/']),
 method('bollinger','Bollinger band re-entry','Mean reversion',22,'SMA(20) +/-2 population standard deviations. BUY on return inside from below lower band, SELL from above upper band.',[C+'volatility/bollinger-bands/']),
 method('engulfing','Bullish / bearish engulfing','Candlesticks',2,'Opposite non-doji bodies; current body strictly exceeds and contains previous body. Shape observation only, not a context-qualified trade. Prior trend and optional volume qualification are not inferred.',['https://cmcmarkets.com/en-gb/technical-analysis/bullish-and-bearish-candle-stick-patterns']),
 method('pinbar','Hammer / shooting-star rejection','Candlesticks',1,'Dominant wick>=2*body and >=60% range; opposite wick<=20% range and body<=30%. Shape only; no fabricated trend or volume confirmation.',[P]),
 method('inside_break','Inside-bar breakout','Candlesticks',3,'Strict inside bar followed by strict completed close outside its mother high/low.',[P]),
 method('structure','Market structure · BOS / CHoCH','Structure',6,'First strict close across latest already-confirmed shared-profile swing (default 2-left/2-right). Same-direction break=BOS, opposite prior break=CHoCH; initial direction=BOS. Each pivot consumed once.',[B+'break-of-structure/']),
 method('liquidity','Liquidity sweep and reclaim','Structure',6,'Wick strictly breaches an already-confirmed pivot but closes back inside; labels price-derived liquidity, not actual institutional orders. Includes measured equal-high/low clusters.',[B+'liquidity-sweep/']),
 method('order_block','Order blocks','Structure',20,'Existing causal opposite-candle / displacement / pivot-break producer; full source high/low, touch and close-beyond-distal invalidation. Its SFM stable ID is retained, not excluded.',[B+'order-block/']),
 method('fvg','Fair-value gaps','Structure',3,'Strict three-closed-bar high/low gap. Subsequent contact=TOUCHED, full wick traversal=FILLED, strict distal close=INVALIDATED. Starts only after confirmation.',[B+'fair-value-gap/']),
 method('pullback_ob','Order-block pullback / mitigation','Structure',21,'First later intersection of a causally confirmed order block, directional candle response and close back beyond proximal. Distinct from the custom M21 capital/qualification rules.',[B+'order-block/']),
 method('pullback_fvg','FVG pullback / mitigation','Structure',4,'First later gap intersection with directional candle response and close beyond proximal, before invalidation/full fill.',[B+'fair-value-gap/']),
 method('wyckoff','Wyckoff · Spring / UTAD / SOS / SOW','Structure',22,'Bounded 20-bar range hypothesis; >=2 separated tests on each boundary within 10% width. Sweep/reclaim=Spring/UTAD; later lower-range test without a new low or upper test without a new high=TEST. Strong close outside range=SOS/SOW. OHLC hypothesis, not volume-confirmed phase certainty.',[W]),
 method('elliott_impulse','Elliott impulse hypothesis','Patterns',26,'Six consecutive alternating confirmed pivots. Wave2<100% wave1, wave3 exceeds wave1 and is not shortest, wave4 does not overlap wave1, wave5 exceeds wave3. No recursive degree, diagonal or truncation claim.',[E+'impulse/',E+'motive-waves/']),
 method('elliott_abc','Elliott ABC zigzag hypothesis','Patterns',16,'Four consecutive alternating confirmed pivots; B retraces less than A and C extends beyond A. Completed-pivot price skeleton only; no claim of verified 5-3-5 internal subdivisions.',[E+'zigzags/']),
 method('abcd','Harmonic AB=CD','Patterns',16,'Four consecutive alternating confirmed pivots: BC/AB .382-.886; CD/BC 1.13-2.618; CD/AB=1 +/-5%. Price-ratio skeleton, not time symmetry or calibration.',[H+'abcd-pattern/']),
 method('gartley','Harmonic Gartley','Patterns',21,'Five consecutive alternating confirmed pivots. B/XA=.618 +/-5%, BC/AB .382-.886, AD/XA=.786 +/-5%, CD/BC 1.27-1.618 and CD/AB=1 +/-5%. Relative tolerance is engineering configuration.',[H+'gartley-pattern/']),
 method('bat','Harmonic Bat','Patterns',21,'Five consecutive alternating confirmed pivots. B/XA .382-.5, BC/AB .382-.886, AD/XA=.886 +/-5%, CD/BC 1.618-2.618 and CD/AB>=.95. Explicit bounded price skeleton, not calibrated prediction.',[H+'bat-pattern/']),
 method('butterfly','Harmonic Butterfly','Patterns',21,'Five consecutive alternating confirmed pivots. B/XA=.786 +/-5%, BC/AB .382-.886, AD/XA=1.27 +/-5%, CD/BC 1.618-2.618 and CD/AB .95-1.3335. Explicit bounded price skeleton.',[H+'butterfly-pattern/']),
 method('support_resistance','Confirmed swing support / resistance','Levels',6,'Last eight causally confirmed swing highs/lows, each line starts at its confirmation time, not its earlier pivot time.',[B+'break-of-structure/']),
 method('fibonacci','Fibonacci retracement','Levels',10,'Latest alternating confirmed swing leg; .382/.5/.618/.786 measurements from leg end toward origin. No predictive success claim.',[B+'fibonacci-retracement/']),
 method('ote','Optimal trade entry (OTE)','Levels',10,'Confirmed leg .62-.79 retracement zone and .705 midpoint. Versioned explicit decimal convention, not automatic entry.',[B+'optimal-trade-entry/']),
 method('previous_extremes','Previous D1 / W1 high and low','Levels',2,'Latest causally completed D1/W1 high and low projected onto each pair chart with original source-frame labels. No broker-calendar reconstruction.',[B+'liquidity-sweep/']),
 method('open_midpoint','D1 / W1 open and midpoint','Levels',2,'Observed latest completed D1/W1 open plus (high+low)/2; explicitly last-completed, never invented current-session OHLC.',[B+'smart-money-concepts/']),
 method('compression','Compression breakout','Breakout',42,'Previous 10-bar range<=50% preceding 30-bar range; current directional body>=60% own range and close strictly outside compression. No custom M20 execution lifecycle.',[C+'volatility/donchian-channel/']),
)
from .public_document_profiles import document_methods
METHODS=METHODS+document_methods(method)
BY_KEY={m.key:m for m in METHODS}
BY_RECIPE={m.recipe_id:m for m in METHODS}
assert len(BY_KEY)==len(BY_RECIPE)==len(METHODS)
