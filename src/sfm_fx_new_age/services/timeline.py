"""One canonical bid-tick timeline for H1/H4/D1/W1; no fill-forward or invented volume."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from datetime import timedelta,timezone
from sfm_fx_new_age.contracts.domain import Bar,Origin,decimal,instant,symbol_check,FRAMES,record


@dataclass(frozen=True)
class Tick:
    symbol:str
    bid:Decimal
    event_time:str
    available_at:str
    source_epoch:str
    scope_id:str
    origin:Origin

    def __post_init__(self):
        symbol_check(self.symbol)
        object.__setattr__(self,'bid',decimal(self.bid,positive=True))
        object.__setattr__(self,'origin',Origin(self.origin))
        if not all((self.source_epoch,self.scope_id)) or instant(self.available_at)<instant(self.event_time):raise ValueError('Causal tick/source required')


class TickTimeline:
    def __init__(self,market,continuity):self.market,self.continuity=market,continuity;self.forming={};self.last={}

    def reset(self,scope,epoch):
        self.forming={k:v for k,v in self.forming.items() if k[:2]!=(scope,epoch)}
        self.last={k:v for k,v in self.last.items() if k[:2]!=(scope,epoch)}

    def ingest(self,tick:Tick,*,finalize:bool=True):
        if tick.scope_id!=self.market.scope_id:raise ValueError('Tick scope mismatch')
        authority=self.market.authority(tick.symbol)
        if not authority or authority['source_epoch']!=tick.source_epoch or authority['origin']!=tick.origin.value:raise ValueError('Canonical active tick source required')
        key=(tick.scope_id,tick.source_epoch,tick.symbol)
        if key in self.last and instant(tick.event_time)<instant(self.last[key]):
            self.continuity.mark_stream_gap(tick.symbol,tick.source_epoch,'OUT_OF_ORDER_CANONICAL_TICK');return []
        self.last[key]=tick.event_time;calendar=self.continuity.calendar(tick.symbol)
        if not calendar:return []
        completed=[]
        for frame in FRAMES:
            series=self.market.bars(tick.symbol,frame,tick.available_at,tick.source_epoch)
            frame_key=key+(frame,);current=self.forming.get(frame_key)
            if current is None:
                if not series:continue # Native timeframe anchor is required; never guess broker bar boundaries.
                start=series[-1].close_time
                if instant(tick.event_time)<instant(start):continue
                end=calendar.next_close(start,frame);steps=0
                while instant(end)<=instant(tick.event_time):
                    start=end;end=calendar.next_close(start,frame);steps+=1
                    if steps>10000:raise ValueError('Native bar anchor too old; backfill required')
                current=self._start(tick,start,end,False);self.forming[frame_key]=current
            if instant(tick.event_time)>=instant(current['close_time']):
                if current['complete'] and finalize:
                    bar=Bar(tick.symbol,frame,current['open_time'],current['close_time'],tick.available_at,
                        current['open'],current['high'],current['low'],current['close'],tick.source_epoch,tick.origin,tick.scope_id,
                        quote_basis='BID',construction='CANONICAL_BID_TICKS')
                    self.market.ingest(bar);completed.append(bar)
                start=current['close_time'];end=calendar.next_close(start,frame);gap=False;steps=0
                while instant(end)<=instant(tick.event_time):
                    gap=gap or calendar.is_open(start)
                    start=end;end=calendar.next_close(start,frame);steps+=1
                    if steps>10000:raise ValueError('Backfill required before resuming tick timeline')
                if gap:self.continuity.mark_stream_gap(tick.symbol,tick.source_epoch,'NO_TICKS_IN_EXPECTED_INTERVAL')
                current=self._start(tick,start,end,not gap)
                self.forming[frame_key]=current
            current['high']=max(current['high'],tick.bid);current['low']=min(current['low'],tick.bid);current['close']=tick.bid
            current['last_tick_at']=tick.event_time
        return completed

    @staticmethod
    def _start(tick,start,end,complete):
        return {'open_time':start,'close_time':end,'open':tick.bid,'high':tick.bid,'low':tick.bid,'close':tick.bid,
                'last_tick_at':tick.event_time,'complete':complete,'quote_basis':'BID','construction':'CANONICAL_BID_TICKS'}

    def snapshot(self,symbol):
        authority=self.market.authority(symbol)
        if not authority:return []
        rows=[]
        for key,value in self.forming.items():
            if key[:3]!=(self.market.scope_id,authority['source_epoch'],symbol):continue
            rows.append({**{k:str(v) if isinstance(v,Decimal) else v for k,v in value.items()},'timeframe':key[3],
                         'symbol':symbol,'source_epoch':key[1],'scope_id':key[0],'maturity':'FORMING'})
        return rows
