"""Broker-supplied session calendars and continuity/backfill ownership; never guess market hours."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from typing import Any
import json

from sfm_fx_new_age.contracts.domain import FRAMES,instant,symbol_check,record
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.storage.database import StateConflict


@dataclass(frozen=True)
class SessionCalendar:
    calendar_id: str
    timezone_name: str
    weekly_windows: tuple[tuple[int,int],...]
    closed_dates: tuple[str,...] = ()
    day_close_minute: int = 0
    week_open_day: int = 0 # Python Monday=0; explicit provider metadata
    source_ref: str = ''
    version: int = 1

    def __post_init__(self):
        # Restore immutable nested shape after SQLite/JSON round trips.
        object.__setattr__(self,'weekly_windows',tuple(tuple(window) for window in self.weekly_windows))
        object.__setattr__(self,'closed_dates',tuple(self.closed_dates))
        ZoneInfo(self.timezone_name)
        if not self.calendar_id or not self.source_ref or self.version<1 or not 0<=self.day_close_minute<1440 or not 0<=self.week_open_day<=6:
            raise ValueError('Source-owned calendar, anchors and revision required')
        previous=-1
        for start,end in sorted(self.weekly_windows):
            if type(start) is not int or type(end) is not int or not 0<=start<end<=604800 or start<previous: raise ValueError('Invalid/overlapping calendar windows')
            previous=end
        for date in self.closed_dates: datetime.strptime(date,'%Y-%m-%d')

    def is_open(self, when: str) -> bool:
        value=instant(when).astimezone(ZoneInfo(self.timezone_name))
        if value.date().isoformat() in self.closed_dates: return False
        seconds=((value.weekday()+1)%7)*86400+value.hour*3600+value.minute*60+value.second # cTrader Sunday=0
        return any(start<=seconds<end for start,end in self.weekly_windows)

    def next_open(self, when: str) -> str | None:
        """Next scheduled open from native weekly windows; no holiday inference."""
        value=instant(when);zone=ZoneInfo(self.timezone_name)
        local=value.astimezone(zone)
        sunday=local.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=(local.weekday()+1)%7)
        candidates=[]
        for week in range(3):
            for start,_ in self.weekly_windows:
                candidate=(sunday+timedelta(weeks=week,seconds=start)).astimezone(timezone.utc)
                stamp=candidate.isoformat().replace('+00:00','Z')
                if candidate>value and self.is_open(stamp):candidates.append(candidate)
        return min(candidates).isoformat().replace('+00:00','Z') if candidates else None

    def next_close(self, start: str, frame: str) -> str:
        value=instant(start).astimezone(ZoneInfo(self.timezone_name))
        if frame not in FRAMES: raise ValueError('Unsupported frame')
        if frame in {'H1','H4'}:
            hours=1 if frame=='H1' else 4
            result=(value.astimezone(timezone.utc)+timedelta(hours=hours))
        elif frame=='D1':result=value+timedelta(days=1)
        else:result=value+timedelta(weeks=1)
        return result.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


class ContinuityService:
    def __init__(self,db,market,emit,clock):self.db,self.market,self.emit,self.clock=db,market,emit,clock

    def set_calendar(self,symbol: str,calendar: SessionCalendar):
        symbol_check(symbol)
        key=json.dumps([self.market.scope_id,symbol])
        old=self.db.get('calendar',key)
        body={**record(calendar),'scope_id':self.market.scope_id,'symbol':symbol}
        if old and old['version']>=calendar.version and old!=body:raise StateConflict('Calendar revision conflict')
        self.db.put('calendar',key,body)
        self.emit('DATA.SESSION_METADATA','SYMBOL_SESSION_REGISTRY',body,Priority.P1,symbol)

    def calendar(self,symbol):
        body=self.db.get('calendar',json.dumps([self.market.scope_id,symbol]))
        if not body:return None
        return SessionCalendar(**{key:body[key] for key in SessionCalendar.__dataclass_fields__})

    def coverage(self,symbol,frame,as_of):
        authority=self.market.authority(symbol);calendar=self.calendar(symbol)
        if not authority:return {'symbol':symbol,'timeframe':frame,'status':'NO_SOURCE','gaps':[]}
        bars=self.market.bars(symbol,frame,as_of,authority['source_epoch']);gaps=[]
        if calendar:
            for a,b in zip(bars,bars[1:]):
                cursor=a.close_time
                while instant(cursor)<instant(b.open_time) and len(gaps)<5000:
                    end=calendar.next_close(cursor,frame)
                    if calendar.is_open(cursor):gaps.append({'from':cursor,'to':end})
                    cursor=end
        return {'symbol':symbol,'timeframe':frame,'source_epoch':authority['source_epoch'],
            'scope_id':self.market.scope_id,'completed_bars':len(bars),'last_close':bars[-1].close_time if bars else None,
            'status':'CALENDAR_UNKNOWN' if calendar is None else 'GAPS' if gaps else 'OBSERVED_CONTIGUOUS' if bars else 'NO_DATA',
            'market_open':calendar.is_open(as_of) if calendar else None,'gaps':gaps,
            'open_stream_gap':bool(self.db.get('stream_gap',json.dumps([self.market.scope_id,symbol,authority['source_epoch']])))}

    def mark_stream_gap(self,symbol,epoch,reason):
        body={'scope_id':self.market.scope_id,'symbol':symbol,'source_epoch':epoch,'reason':reason,'observed_at':self.clock()}
        self.db.put('stream_gap',json.dumps([self.market.scope_id,symbol,epoch]),body)
        self.emit('DATA.CONTINUITY','BAR_TIMELINE',body,Priority.P1,symbol)

    def request_backfill(self,symbol,frame,start,end):
        symbol_check(symbol)
        if frame not in FRAMES or instant(start)>=instant(end) or instant(end)>instant(self.clock()):raise ValueError('Valid historical interval required')
        authority=self.market.authority(symbol)
        if not authority:raise ValueError('Active source required for backfill')
        body={'symbol':symbol,'timeframe':frame,'from':start,'to':end,'scope_id':self.market.scope_id,
              'source_epoch':authority['source_epoch']}
        identity=digest(body);existing=self.db.get('backfill',identity)
        if existing:return existing
        body.update(id=identity,status='QUEUED',received_bars=0,cursor=None)
        self.db.put('backfill',identity,body)
        self.emit('DATA.BACKFILL','BAR_TIMELINE',body,Priority.P1,symbol)
        return body

    def apply_page(self,identity,bars,*,complete:bool,cursor:str|None=None):
        job=self.db.get('backfill',identity)
        if not job or job['scope_id']!=self.market.scope_id:raise ValueError('Matching backfill scope required')
        authority=self.market.authority(job['symbol'])
        if not authority or authority['source_epoch']!=job['source_epoch']:raise StateConflict('Backfill source changed')
        if job['status']=='COMPLETE':raise StateConflict('Backfill already completed')
        if not complete and (not cursor or cursor==job.get('cursor')):raise ValueError('Forward pagination cursor required')
        for bar in bars:
            if (bar.symbol,bar.timeframe,bar.source_epoch)!=(job['symbol'],job['timeframe'],job['source_epoch']):raise ValueError('Mixed backfill source')
            if instant(bar.open_time)<instant(job['from']) or instant(bar.close_time)>instant(job['to']):raise ValueError('Backfill outside interval')
        for bar in bars:self.market.ingest(bar)
        job.update(status='COMPLETE' if complete else 'PARTIAL',cursor=cursor,received_bars=job['received_bars']+len(bars))
        self.db.put('backfill',identity,job)
        self.emit('DATA.BACKFILL','BAR_TIMELINE',job,Priority.P1,job['symbol'])
        return job
