"""Source H1 session windows with IANA timezone/DST and explicit completeness."""
from datetime import datetime,timedelta,time,timezone
from zoneinfo import ZoneInfo
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from .public_features import Features
from .public_sequence_features import breakout_models,sweep_models

SESSION_WINDOWS={
    'session_asia':('Asia/Tokyo',9,15,'Asian / Tokyo'),
    'session_london':('Europe/London',8,16,'London'),
    'session_new_york':('America/New_York',8,17,'New York'),
}
KILLZONES=(('America/New_York',20,24,'Asia killzone'),('America/New_York',2,5,'London killzone'),
           ('America/New_York',7,10,'New York killzone'),('America/New_York',10,12,'London-close killzone'))


def completed_windows(rows,window):
    tz,start,end,name=window;tz=ZoneInfo(tz);by_open={instant(b['open_time']):b for b in rows}
    dates=sorted({instant(b['open_time']).astimezone(tz).date() for b in rows});out=[];incomplete=0
    if not rows:return out,0
    last=max(instant(b['close_time']) for b in rows)
    for date in dates:
        opened=datetime.combine(date,time(start),tzinfo=tz).astimezone(timezone.utc)
        closed=datetime.combine(date+timedelta(days=end//24),time(end%24),tzinfo=tz).astimezone(timezone.utc)
        if closed>last:continue
        expected=[];t=opened
        while t<closed:expected.append(t);t+=timedelta(hours=1)
        found=[by_open.get(t) for t in expected]
        if not found or any(b is None or instant(b['close_time'])!=t+timedelta(hours=1) for t,b in zip(expected,found)):
            incomplete+=1;continue
        known=max([b['available_at'] for b in found],key=instant)
        if instant(known)<closed:raise ValueError('Session available before its final close')
        out.append(dict(id=digest([window,found]),name=name,timezone=str(tz),open_time=opened.isoformat(),close_time=closed.isoformat(),
                        available_at=known,low=min(float(b['low']) for b in found),high=max(float(b['high']) for b in found),
                        roots=tuple(digest(b) for b in found),bars=len(found)))
    return out,incomplete


def evaluate_session(key,f,inputs,deps):
    from .public_algorithms import blank,zone
    rows=list(inputs['bars'].get('H1',()))[-2048:]
    if not rows:raise ProjectionInputUnavailable('Native H1 history required; no reconstruction from H4/D1/W1')
    out=blank();windows=KILLZONES if key=='killzones' else (SESSION_WINDOWS[key],) if key in SESSION_WINDOWS else tuple(SESSION_WINDOWS.values())
    complete=[];missing=0
    for window in windows:
        found,bad=completed_windows(rows,window);complete.extend(found);missing+=bad
    complete.sort(key=lambda s:(instant(s['available_at']),s['name']))
    if not complete:raise ProjectionInputUnavailable('No fully observed contiguous completed H1 session window; missing or boundary-misaligned H1 support')
    if key in SESSION_WINDOWS or key=='killzones':
        for session in complete[-8:]:
            zone(out,f,f.n-1,session['low'],session['high'],session['name']+' complete H1 range','NEUTRAL',available=session['available_at'],roots=session['roots'])
            out['zones'][-1].update(session_start=session['open_time'],session_end=session['close_time'],session_timezone=session['timezone'],source_timeframe='H1',observed_h1_bars=session['bars'])
    else:
        sf=Features(rows,(deps.get('SWING_MAP',{}).get('output') or {}).get('H1',()))
        pools=[]
        for s in complete:
            start=sf.first_open_at_or_after(s['available_at'])
            if start is None:continue
            for side,field in [('BUY','low'),('SELL','high')]:
                p=s[field];pools.append(dict(id=digest([s['id'],field]),start=start,expiry=start+23,low=p,high=p,side=side,
                                            available_at=s['available_at'],roots=s['roots'],label=s['name']+' '+field))
        if key=='session_sweep':out=sweep_models(sf,inputs,pools=pools,label='Complete session sweep')
        else:out=breakout_models(sf,inputs,pools=[dict(p,side='BUY' if p['side']=='SELL' else 'SELL') for p in pools],kind='session')
        for row in out['markers']+out['zones']:row['source_timeframe']='H1'
    out['metrics'].update(source_timeframe='H1',complete_windows=len(complete),incomplete_windows=missing,session_policy='EXPLICIT_LOCAL_WINDOWS_V1',broker_session_or_news_inferred=False)
    return out
