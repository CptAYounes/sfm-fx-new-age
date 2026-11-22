"""Prepare a declared research P&F count from independently decoded native pages.

Offline, opt-in and execution-inert. Original quote values/clocks are unchanged.
A caller's count choices are research settings, not authenticated market facts or
proof of the human operator's approval. No settings or side are chosen implicitly.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,json,sqlite3
from typing import Any
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from sfm_fx_new_age.services.supplemental_files import read_bytes,parse_json
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.domain import instant,PAIRS
from sfm_fx_new_age.tabs.tab3.public_genuine_data import point_figure

REQUEST_FIELDS={'schema_version','source_capture_directory','capture_receipt_sha256','source_envelope_sha256','symbol','output_directory','parameters','count_owner_label','acknowledge_research_only'}


def hash_bytes(raw):return hashlib.sha256(raw).hexdigest()
def exact_sha(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def verified_native_ticks(capture_directory,symbol,receipt_sha256,envelope_sha256) -> tuple[dict[str,Any],str]:
    root=Path(capture_directory)
    if not root.is_absolute() or root.resolve()!=root or symbol not in PAIRS or not exact_sha(receipt_sha256) or not exact_sha(envelope_sha256):raise ValueError('Exact original capture identity required')
    receipt_raw=read_bytes(root/'capture-receipt.json',2000000);receipt=parse_json(receipt_raw)
    if hash_bytes(receipt_raw)!=receipt_sha256 or receipt.get('result')!='ORIGINAL_ACQUISITION_COMPLETE_NOT_ALL_STRATEGIES_COMPLETE' or receipt.get('synthetic_observations')!=0 or not all(receipt.get(k) is True for k in ('sdk_processes_stopped','auth_thread_stopped','runtime_closed')):raise ValueError('Closed original acquisition receipt required')
    manifest_raw=read_bytes(root/'native-quotes/manifest.json',64000);manifest=parse_json(manifest_raw)
    if set(manifest)!={'schema_version','entries'} or manifest['schema_version']!=1 or not isinstance(manifest['entries'],list) or not 1<=len(manifest['entries'])<=7:raise ValueError('Original quote manifest required')
    filenames=[entry['file'] for entry in manifest['entries']]
    if len(filenames)!=len(set(filenames)):raise ValueError('Unique quote files required')
    selected=[entry for entry in manifest['entries'] if entry['file']==symbol+'-tpo.json']
    if len(selected)!=1 or selected[0]['sha256']!=envelope_sha256:raise ValueError('Exact source envelope digest required')
    raw=read_bytes(root/'native-quotes'/(symbol+'-tpo.json'),6000000)
    if hash_bytes(raw)!=envelope_sha256:raise ValueError('Original envelope checksum mismatch')
    body=parse_json(raw);evidence=SupplementalEvidence(**dict(body,records=tuple(body['records'])));validate_wire_shape(evidence)
    if evidence.kind!='INTRABAR_PRICES' or evidence.origin!='LIVE_OBSERVED' or evidence.provider_id!='CTRADER_ORIGINAL_BID_HISTORY_V1' or evidence.symbol!=symbol:raise ValueError('Original native BID source required')
    jobs=[v for v in receipt.get('original_quote_jobs',[]) if v['symbol']==symbol]
    if len(jobs)!=1:raise ValueError('Exact original source job required')
    claimed=jobs[0];database=root/'state.sqlite3'
    # Immutable SQLite is safe only after producer shutdown and zero outstanding WAL.
    if database.resolve()!=database or not database.is_file() or any((root/('state.sqlite3'+suffix)).exists() and (root/('state.sqlite3'+suffix)).stat().st_size for suffix in ('-wal','-journal')):raise ValueError('Closed nonsymlink source database without pending transactions required')
    before=database.stat();signature=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    c=sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
        budget=[1000000]
        def progress():budget[0]-=1000;return int(budget[0]<=0)
        c.set_progress_handler(progress,1000)
        def get(kind,identity):
            row=c.execute('SELECT body FROM records WHERE kind=? AND id=?',(kind,identity)).fetchone()
            if row is None:raise ValueError('Missing native source record')
            return parse_json(row[0])
        job=get('native_quote_history_job',claimed['id'])
        for key in ('id','source_epoch','symbol','start','end','state','pages','record_count','accepted_pages'):
            if job[key]!=claimed[key]:raise ValueError('Native job does not match acquisition receipt')
        if job['state']!='COMPLETE' or job['pending'] or job['inflight'] is not None or not 1<=len(job['accepted_pages'])<=64 or len(set(job['accepted_pages']))!=len(job['accepted_pages']):raise ValueError('Explicit native history exhaustion required')
        if (job['scope_id'],job['source_epoch'],job['symbol'],job['start'],job['end'])!=(body['scope_id'],body['source_epoch'],symbol,body['window_start'],body['window_end']):raise ValueError('Original source epoch/interval mismatch')
        expected=[];windows=[]
        for key in job['accepted_pages']:
            page=get('native_quote_history_page',key);payload=page['payload'];window=page['window']
            if payload.get('hasMore') is not False or str(payload.get('ctidTraderAccountId'))!=job['account_id'] or page['origin']!='LIVE_OBSERVED' or page['source_epoch']!=body['source_epoch'] or page['job_id']!=job['id'] or page['scope_id']!=body['scope_id'] or page['symbol']!=symbol or page['quote_basis']!='BID':raise ValueError('Unexhausted or mismatched native page')
            windows.append(window);clock=price=None
            for index,tick in enumerate(payload.get('tickData',[])):
                clock=int(tick['timestamp']) if clock is None else clock+int(tick['timestamp']);price=int(tick['tick']) if price is None else price+int(tick['tick'])
                if not window['start']<=clock<=window['end'] or price<=0:raise ValueError('Invalid native delta observation')
                stamp=datetime.fromtimestamp(clock/1000,timezone.utc).isoformat().replace('+00:00','Z')
                expected.append(dict(id=digest([key,index,tick]),time=stamp,available_at=page['observed_at'],price=str(Decimal(price)/Decimal(100000))))
                if len(expected)>20000:raise ValueError('Original observation budget exhausted')
        windows.sort(key=lambda v:v['start'])
        start=int(instant(job['start']).timestamp()*1000);end=int(instant(job['end']).timestamp()*1000)-1
        if windows[0]['start']!=start or windows[-1]['end']!=end or any(a['end']+1!=b['start'] for a,b in zip(windows,windows[1:])):raise ValueError('Original interval coverage incomplete')
        expected.sort(key=lambda r:(instant(r['time']),r['id']))
        if expected!=body['records'] or len(expected)!=job['record_count']:raise ValueError('Raw-native decoded observations do not match envelope')
        specs=c.execute("SELECT body FROM records WHERE kind='spec' AND json_extract(body,'$.scope_id')=? AND json_extract(body,'$.symbol')=? LIMIT 2",(body['scope_id'],symbol)).fetchall()
        if len(specs)!=1:raise ValueError('Unique native symbol specification required')
        spec=parse_json(specs[0][0]);tick_size=str(spec['tick_size'])
        if Decimal(tick_size)!=Decimal(str(body['parameters']['tick_size'])):raise ValueError('Native price-grid declaration mismatch')
    finally:c.close()
    if signature(before)!=signature(database.stat()):raise ValueError('Original source database changed during verification')
    if read_bytes(root/'capture-receipt.json',2000000)!=receipt_raw or read_bytes(root/'native-quotes/manifest.json',64000)!=manifest_raw or read_bytes(root/'native-quotes'/(symbol+'-tpo.json'),6000000)!=raw:raise ValueError('Original publication changed during read')
    return body,tick_size


def prepare_original_point_figure(request_path) -> dict[str,Any]:
    raw=read_bytes(Path(request_path),64000);request=parse_json(raw)
    if not isinstance(request,dict) or set(request)!=REQUEST_FIELDS or type(request['schema_version']) is not int or request['schema_version']!=1 or request['acknowledge_research_only'] is not True:raise ValueError('Exact explicit research-count request required')
    owner=request['count_owner_label']
    if not isinstance(owner,str) or not 1<=len(owner)<=160 or any(ord(c)<32 for c in owner):raise ValueError('Bounded explicit count owner label required')
    for field in ('source_capture_directory','output_directory','symbol'):
        if not isinstance(request[field],str):raise ValueError('Textual original count identity required')
    body,tick=verified_native_ticks(request['source_capture_directory'],request['symbol'],request['capture_receipt_sha256'],request['source_envelope_sha256'])
    output=Path(request['output_directory'])
    if not output.is_absolute() or output.resolve()!=output or output.exists():raise ValueError('New absolute nonsymlink output directory required')
    if not isinstance(request['parameters'],dict):raise ValueError('Explicit count parameters required')
    data:dict[str,Any]=dict(body,kind='POINT_FIGURE_TICKS',provider_id='CTRADER_ORIGINAL_EXPLICIT_PF_V1',source_ref='Declared research settings; approval unproved; owner '+owner+' / original quote envelope '+request['source_envelope_sha256']+' / request '+hash_bytes(raw),parameters=request['parameters'])
    evidence=SupplementalEvidence(**dict(data,records=tuple(data['records'])));validate_wire_shape(evidence)
    current=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    if instant(current)>instant(data['valid_until']):raise ValueError('Original source expired; no clock renewal or rebind')
    if Decimal(str(data['parameters']['box_size']))%Decimal(tick):raise ValueError('Box must align with original native tick size')
    try:columns,count,extent,targets=point_figure(data,dict(spec=dict(tick_size=tick)))
    except ProjectionInputUnavailable as exc:raise ValueError(exc.reason) from None
    # Interpretation is first available now, never backdated to quote acquisition.
    data['available_at']=max((body['available_at'],current),key=instant)
    evidence=SupplementalEvidence(**dict(data,records=tuple(data['records'])));validate_wire_shape(evidence)
    payload=(json.dumps(data,indent=2)+'\n').encode();name=request['symbol']+'-point-figure.json';manifest=dict(schema_version=1,entries=[dict(file=name,sha256=hash_bytes(payload))]);config=dict(schema_version=1,providers=[dict(provider_id=data['provider_id'],origin='LIVE_OBSERVED',kinds=['POINT_FIGURE_TICKS'],manifest_path=str(output/'manifest.json'))])
    proof=dict(result='ORIGINAL_POINT_FIGURE_PREPARED_EXPLICIT_COUNT',symbol=request['symbol'],source_envelope_sha256=request['source_envelope_sha256'],request_sha256=hash_bytes(raw),count_owner_label=owner,settings_are_market_observations=False,operator_approval_independently_authenticated=False,scope='DECLARED_RESEARCH_SETTINGS_ORIGINAL_BID_QUOTES_NO_EXECUTION_AUTHORITY',original_observations=len(data['records']),observations_unchanged=data['records']==body['records'],completed_count_columns=count,count_extent=str(extent),targets=[str(v) for v in targets],last_developing_column_excluded=True,available_at=data['available_at'],valid_until=data['valid_until'],source_epoch_unchanged=True,configuration=str(output/'sources.json'),synthetic_observations=0,network_started=False)
    if read_bytes(Path(request_path),64000)!=raw:raise ValueError('Count request changed while preparing')
    from sfm_fx_new_age.connector.official_context import write_new
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    write_new(output/name,payload)
    for filename,value in (('manifest.json',manifest),('sources.json',config),('count-receipt.json',proof)):write_new(output/filename,(json.dumps(value,indent=2)+'\n').encode())
    return proof
