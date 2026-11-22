"""Explicit one-shot original official context acquisition, never a background feed.

Network access belongs to the connector package. This module imports no runtime,
GUI, credentials or broker transport. Raw HTTPS replies and acquisition receipts
are retained; source epochs come from an explicit read-only binding. COT is futures
context, never spot volume. Fed coverage is ONLY published, exactly timed Board
calendar entries, not an all-economy/all-currency calendar or a no-news guarantee.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from zoneinfo import ZoneInfo
from html import unescape
from typing import Any
import hashlib, json, re, sqlite3
from sfm_fx_new_age.contracts.domain import PAIRS, instant
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence, UNITS
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape

CFTC_CODES={'EURUSD':'099741','GBPUSD':'096742','USDJPY':'097741','USDCHF':'092741',
            'USDCAD':'090741','AUDUSD':'232741','NZDUSD':'112741'}
CFTC_BASE='https://publicreporting.cftc.gov/resource/6dca-aqww.json'
FED_URL='https://www.federalreserve.gov/json/calendar.json'
LIMIT=2000000


class SameOfficialHostRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        old,new=urlsplit(req.full_url),urlsplit(newurl)
        if new.scheme!='https' or new.hostname!=old.hostname:raise ValueError('Official cross-host redirect refused before request')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha(data):return hashlib.sha256(data).hexdigest()


def binding_from_database(path):
    """Read a single saved authority transaction; never restore account auth."""
    path=Path(path).resolve(strict=True)
    c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
        row=c.execute("SELECT body FROM records WHERE kind='setting' AND id='connector_remember'").fetchone()
        if not row:raise ValueError('No previously selected source binding')
        scope=json.loads(row[0]).get('scope_id')
        if not isinstance(scope,str) or not scope:raise ValueError('No previously selected source binding')
        authorities={v['symbol']:v for (body,) in c.execute("SELECT body FROM records WHERE kind='authority'") if (v:=json.loads(body)).get('scope_id')==scope}
        return validate_binding({'scope_id':scope,'authorities':authorities})
    finally:c.close()


def validate_binding(binding,*,require_all=True):
    scope=binding['scope_id'];authorities=binding['authorities']
    if not isinstance(scope,str) or not scope or not authorities or not set(authorities)<=set(PAIRS) or (require_all and set(authorities)!=set(PAIRS)):raise ValueError('Exact original source authorities required')
    for symbol,v in authorities.items():
        if (v.get('scope_id'),v.get('symbol'),v.get('origin'))!=(scope,symbol,'LIVE_OBSERVED') or not isinstance(v.get('source_epoch'),str) or not v['source_epoch']:raise ValueError('Original authority binding required')
    return binding


def fetch_original_json(url) -> tuple[bytes,Any,dict[str,Any]]:
    """TLS-verified bounded official-host-only GET; no cookies or secret headers."""
    allowed={'publicreporting.cftc.gov','www.federalreserve.gov'}
    if urlsplit(url).scheme!='https' or urlsplit(url).hostname not in allowed:raise ValueError('Official HTTPS source required')
    started=now()
    request=Request(url,headers={'User-Agent':'SFM-FX-New-Age-original-context/1.0','Accept':'application/json'})
    with build_opener(SameOfficialHostRedirect()).open(request,timeout=20) as response:
        if response.status!=200 or urlsplit(response.geturl()).hostname!=urlsplit(url).hostname:raise ValueError('Official source response/redirect refused')
        if 'application/json' not in response.headers.get('Content-Type','').lower():raise ValueError('Official JSON MIME required')
        raw=response.read(LIMIT+1)
        if not raw or len(raw)>LIMIT:raise ValueError('Official response exceeds bounded size')
        body=json.loads(raw,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite source JSON')))
        received=now()
        receipt=dict(url=url,started_at=started,received_at=received,status=response.status,sha256=sha(raw),bytes=len(raw),tls_verification=True,authentication='PUBLIC_OFFICIAL_HTTPS_NO_CREDENTIALS')
    return raw,body,receipt


def cot_records(body,received):
    if not isinstance(body,list) or len(body)!=7:raise ValueError('One latest futures-only CFTC row per required currency required')
    result={};dates=set()
    for symbol,code in CFTC_CODES.items():
        matches=[r for r in body if r.get('cftc_contract_market_code')==code and r.get('futonly_or_combined')=='FutOnly']
        if len(matches)!=1:raise ValueError('Missing or ambiguous original CFTC currency report')
        row=matches[0];report=instant(row['report_date_as_yyyy_mm_dd']+'Z').isoformat().replace('+00:00','Z')
        if not timedelta(0)<=instant(received)-instant(report)<=timedelta(days=14):raise ValueError('Latest observed CFTC report is stale or future dated')
        currency=symbol[3:] if symbol.startswith('USD') else symbol[:3]
        record=dict(id=str(row['id']),time=received,available_at=received,currency=currency,report_type='LEGACY_NONCOMMERCIAL',report_as_of=report,long=row['noncomm_positions_long_all'],short=row['noncomm_positions_short_all'],open_interest=row['open_interest_all'])
        result[symbol]=record;dates.add(report)
    if len(dates)!=1:raise ValueError('Incomplete common CFTC report date')
    return result


def fed_records(body,received,month):
    if not isinstance(body,dict) or not isinstance(body.get('events'),list):raise ValueError('Official Board calendar event list required')
    records=[];excluded=[];source_entries=0
    for index,row in enumerate(body['events']):
        if row.get('month')!=month:continue
        source_entries+=1
        # Untimed holidays and approximate dates have no precise event timestamp.
        # Retain their original rows in raw evidence; do not invent a market time.
        time=re.fullmatch(r'\s*(\d{1,2}):(\d{2})\s*([ap])\.m\.\s*',row.get('time',''))
        if not time or not re.fullmatch(r'\d{1,2}(?:\s*,\s*\d{1,2})*',row.get('days','')):
            excluded.append(dict(source_index=index,reason='SOURCE_HAS_NO_EXACT_SUPPORTED_EVENT_TIME'));continue
        hour,minute=int(time[1]),int(time[2])
        if not 1<=hour<=12 or not 0<=minute<60:raise ValueError('Invalid official event time')
        hour=hour%12+(12 if time[3]=='p' else 0)
        title=re.sub('<[^>]+>','',unescape(row['title'])).strip()
        if not title or len(title)>200:raise ValueError('Bounded original event title required')
        for day in row['days'].split(','):
            scheduled=datetime.fromisoformat(month+'-'+str(int(day)).zfill(2)).replace(hour=hour,minute=minute,tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
            identity=sha(json.dumps([index,row,day],sort_keys=True).encode())
            records.append(dict(id=identity,time=received,available_at=received,currency='USD',title=title,importance='UNSPECIFIED',scheduled_at=scheduled))
    if not records:raise ValueError('No exact original Board events in requested month')
    records.sort(key=lambda v:(instant(v['time']),v['id']))
    return records,dict(source_calendar='FEDERAL_RESERVE_BOARD_ONLY',month=month,source_entries=source_entries,expanded_exact_events=len(records),excluded_source_entries=excluded,excludes_other_agencies=True,excludes_non_USD_events=True,importance_assigned=False,timezone='America/New_York',timezone_basis='BOARD_CALENDAR_LOCAL_TIME',no_news_guarantee=False)


def write_new(path,data):
    with Path(path).open('xb') as stream:stream.write(data)
    Path(path).chmod(0o444)


def acquire_official_context(binding,output_dir) -> dict[str,Any]:
    """One synchronous acquisition. Caller owns lifecycle; nothing keeps running."""
    validate_binding(binding,require_all=False);out=Path(output_dir)
    if not out.is_absolute() or out.resolve()!=out:raise ValueError('Absolute nonsymlink output directory required')
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    query={'$where':"cftc_contract_market_code in ("+','.join("'"+v+"'" for v in CFTC_CODES.values())+") AND futonly_or_combined='FutOnly'",'$order':'report_date_as_yyyy_mm_dd DESC,cftc_contract_market_code ASC','$limit':'7'}
    raw_cot,cot,rc=fetch_original_json(CFTC_BASE+'?'+urlencode(query));write_new(out/'cftc-original.raw',raw_cot)
    records_cot=cot_records(cot,rc['received_at'])
    raw_fed,fed,rf=fetch_original_json(FED_URL);write_new(out/'fed-board-original.raw',raw_fed)
    month=instant(rf['received_at']).strftime('%Y-%m');records_fed,coverage=fed_records(fed,rf['received_at'],month)
    available=now();day=instant(available);month_start=day.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    next_month=(month_start.replace(day=28)+timedelta(days=4)).replace(day=1)
    entries={'CFTC_OFFICIAL_HTTP_V1':[],'FED_BOARD_OFFICIAL_HTTP_V1':[]}
    for symbol in binding['authorities']:
        for provider,kind,rows,receipt,venue,instrument,params in (
            ('CFTC_OFFICIAL_HTTP_V1','CFTC_REPORT',[records_cot[symbol]],rc,'CFTC_CME_FUTURES_ONLY',CFTC_CODES[symbol],{'availability_basis':'FIRST_VERIFIED_HTTP_OBSERVATION'}),
            ('FED_BOARD_OFFICIAL_HTTP_V1','OFFICIAL_CALENDAR',records_fed,rf,'US_FEDERAL_RESERVE_BOARD_EXACT_TIMED_EVENTS_ONLY','USD_OFFICIAL_BOARD_EVENTS',dict(schedule_coverage_start=month_start.isoformat().replace('+00:00','Z'),schedule_coverage_end=next_month.isoformat().replace('+00:00','Z'),coverage_policy='FED_BOARD_EXACT_TIMED_EVENTS_ONLY'))):
            # Endpoints are actual acquisition/conversion instants, not fabricated
            # publication timestamps. No report is backdated to its usual release.
            envelope:dict[str,Any]=dict(provider_id=provider,kind=kind,scope_id=binding['scope_id'],source_epoch=binding['authorities'][symbol]['source_epoch'],symbol=symbol,origin='LIVE_OBSERVED',source_ref=receipt['url']+' #original-response-sha256='+receipt['sha256'],venue=venue,instrument=instrument,price_domain='FUTURES_CONTEXT' if kind=='CFTC_REPORT' else 'EVENT_CONTEXT',unit=UNITS[kind],window_start=receipt['started_at'],window_end=available,available_at=available,valid_until=(day+timedelta(hours=12)).isoformat().replace('+00:00','Z'),complete=True,records=rows,parameters=params)
            validated=SupplementalEvidence(**dict(envelope,records=tuple(rows)));validate_wire_shape(validated)
            filename=provider+'-'+symbol+'.json';data=(json.dumps(envelope,indent=2)+'\n').encode();write_new(out/filename,data);entries[provider].append(dict(file=filename,sha256=sha(data)))
    providers=[]
    for provider,values in entries.items():
        name=provider+'-manifest.json';write_new(out/name,(json.dumps(dict(schema_version=1,entries=values),indent=2)+'\n').encode())
        providers.append(dict(provider_id=provider,origin='LIVE_OBSERVED',kinds=['CFTC_REPORT'] if provider.startswith('CFTC') else ['OFFICIAL_CALENDAR'],manifest_path=str(out/name)))
    config=out/'sources.json';write_new(config,(json.dumps(dict(schema_version=1,providers=providers),indent=2)+'\n').encode())
    receipt=dict(scope='ORIGINAL_PUBLIC_OFFICIAL_HTTPS_CONTEXT_ACQUISITION',source_scope_sha256=sha(binding['scope_id'].encode()),source_epochs={s:v['source_epoch'] for s,v in binding['authorities'].items()},responses=[rc,rf],cot_report_date=next(iter(records_cot.values()))['report_as_of'],cot_availability_basis='FIRST_VERIFIED_HTTP_OBSERVATION_NOT_CLAIMED_PUBLICATION_TIME',fed_coverage=coverage,envelopes=sum(map(len,entries.values())),provider_count=len(providers),configuration=str(config),raw_prices_synthesized=0,executed_quantities_synthesized=0,broker_requests=0,background_jobs_started=0)
    write_new(out/'acquisition-receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())
    return receipt
