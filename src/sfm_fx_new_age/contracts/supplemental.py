"""Validated, source-bound envelopes for optional analytical observations.

This validates a trusted connector adapter's declared provenance; it does not
independently authenticate an external provider. No provider is enabled by default.
"""
from dataclasses import dataclass
from .domain import Origin,instant,symbol_check,decimal

KINDS={'TRADED_PRINTS','AGGRESSOR_PRINTS','EXECUTED_BAR_QUANTITIES','EXECUTED_WEEK_QUANTITIES','INTRABAR_PRICES','POINT_FIGURE_TICKS','VENUE_BOOK','VENUE_L2_CHECKSUM_BOOK','VENUE_NATIVE_CHAIN_BOOK','BROKER_DEPTH','CFTC_REPORT','OFFICIAL_CALENDAR'}
UNITS={'TRADED_PRINTS':'EXECUTED_BASE_UNITS','AGGRESSOR_PRINTS':'EXECUTED_BASE_UNITS','EXECUTED_BAR_QUANTITIES':'EXECUTED_BASE_UNITS','EXECUTED_WEEK_QUANTITIES':'EXECUTED_BASE_UNITS','INTRABAR_PRICES':'OBSERVED_PRICE',
       'POINT_FIGURE_TICKS':'OBSERVED_PRICE','VENUE_BOOK':'DISPLAYED_BASE_UNITS','VENUE_L2_CHECKSUM_BOOK':'DISPLAYED_BASE_UNITS','VENUE_NATIVE_CHAIN_BOOK':'DISPLAYED_BASE_UNITS','BROKER_DEPTH':'DISPLAYED_BASE_UNITS','CFTC_REPORT':'FUTURES_CONTRACTS','OFFICIAL_CALENDAR':'OFFICIAL_RELEASE'}

@dataclass(frozen=True)
class SupplementalEvidence:
    provider_id:str
    kind:str
    scope_id:str
    source_epoch:str
    symbol:str
    origin:str
    source_ref:str
    venue:str
    instrument:str
    price_domain:str
    unit:str
    window_start:str
    window_end:str
    available_at:str
    valid_until:str
    complete:bool
    records:tuple[dict,...]
    parameters:dict
    revision:int=1
    schema_version:int=1

    def __post_init__(self):
        symbol_check(self.symbol);Origin(self.origin)
        if self.schema_version!=1 or self.kind not in KINDS or self.unit!=UNITS[self.kind]:raise ValueError('Supported real-data kind and exact unit required')
        if not all((self.provider_id,self.scope_id,self.source_epoch,self.source_ref,self.venue,self.instrument)):raise ValueError('Explicit provider and source/instrument provenance required')
        expected='FUTURES_CONTEXT' if self.kind=='CFTC_REPORT' else 'EVENT_CONTEXT' if self.kind=='OFFICIAL_CALENDAR' else 'SPOT_PAIR'
        if self.price_domain!=expected or expected=='SPOT_PAIR' and self.instrument!=self.symbol:raise ValueError('No unlabelled foreign-contract price mapping')
        if type(self.complete) is not bool or not self.complete:raise ValueError('Explicit complete source interval required')
        if type(self.revision) is not int or self.revision<1 or not 0<len(self.records)<=20000:raise ValueError('Positive revision and bounded source rows required')
        if not instant(self.window_start)<instant(self.window_end)<=instant(self.available_at)<=instant(self.valid_until):raise ValueError('Ordered source interval / availability / validity required')
        seen=set();previous=None
        for r in self.records:
            if not isinstance(r,dict) or not r.get('id') or r['id'] in seen:raise ValueError('Unique immutable source observation IDs required')
            seen.add(r['id']);t=instant(r['time']);a=instant(r['available_at'])
            if not instant(self.window_start)<=t<instant(self.window_end) or not t<=a<=instant(self.available_at):raise ValueError('Source row exceeds observed or availability interval')
            if previous is not None and (t,r['id'])<=previous:raise ValueError('Stable time / observation ID ordering required')
            previous=(t,r['id'])
            if self.kind in {'TRADED_PRINTS','AGGRESSOR_PRINTS','INTRABAR_PRICES','POINT_FIGURE_TICKS'}:decimal(r['price'],positive=True)
            if self.kind in {'TRADED_PRINTS','AGGRESSOR_PRINTS'}:decimal(r['quantity'],positive=True)
            if self.kind=='AGGRESSOR_PRINTS' and r.get('aggressor') not in {'BUY','SELL'}:raise ValueError('Actual documented aggressor required; unknown is not inferred')
