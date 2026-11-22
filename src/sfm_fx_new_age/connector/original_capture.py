"""Explicit bounded original-data acquisition CLI implementation.

Uses the production connector, a new isolated state directory, and only the
previously remembered source. It never edits the normal application database,
starts a background daemon, restores trading permission, or sends broker writes.
The output is a captured source epoch, not a perpetual live feed; a later source
epoch requires a new acquisition. OAuth renewal remains connector/store-owned.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from time import monotonic,sleep
import hashlib,json,sqlite3
from typing import Any
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.storage.database import Database
from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES
from .sdk_worker import SdkProcess,READ_REQUESTS
from .official_context import acquire_official_context,write_new


class ReadOnlyCaptureSdk(SdkProcess):
    def __init__(self,configuration):super().__init__(configuration);self.read_counts={};self.denied_writes=0
    def send(self,body):
        kind=body.get('kind')
        if kind=='READ' and body.get('name') in READ_REQUESTS:
            name=body['name'];self.read_counts[name]=self.read_counts.get(name,0)+1
        elif kind!='AUTH_ACCOUNT':
            self.denied_writes+=1;raise PermissionError('Original capture SDK refuses broker mutations')
        return super().send(body)


def acquire_original_inputs(source_database,output_directory,*,timeout_seconds=180) -> dict[str,Any]:
    source=Path(source_database).resolve(strict=True);out=Path(output_directory)
    if not out.is_absolute() or out.resolve()!=out:raise ValueError('Absolute nonsymlink output directory required')
    if not 30<=timeout_seconds<=240:raise ValueError('Bounded acquisition timeout required')
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    c=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    try:
        c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
        settings=c.execute("SELECT kind,id,body FROM records WHERE kind='setting' AND id IN ('connector_public_profile','connector_remember')").fetchall()
    finally:c.close()
    values={identity:json.loads(body) for _,identity,body in settings}
    remembered=values.get('connector_remember',{})
    if not remembered.get('enabled') or not remembered.get('scope_id') or not values.get('connector_public_profile'):raise ValueError('Explicit remembered original source configuration required')
    db=Database(out/'state.sqlite3')
    try:
        with db.transaction() as conn:conn.executemany('INSERT INTO records VALUES(?,?,?)',settings)
    finally:db.close()
    workers=[];runtime=ApplicationRuntime(out/'state.sqlite3');started=monotonic();proof:dict[str,Any]={}
    def factory(config):
        worker=ReadOnlyCaptureSdk(config);workers.append(worker);return worker
    runtime.connector.worker_factory=factory
    def deny(*args,**kwargs):raise PermissionError('Original capture has no broker mutation authority')
    runtime.connector.submit=deny;runtime.connector.cancel=deny
    def until(predicate):
        while monotonic()-started<timeout_seconds:
            runtime.connector.poll();runtime.pump()
            if predicate():return
            if runtime.connector.state in {'LOGIN_REQUIRED','CONNECTION_FAILED','APPLICATION_AUTH_FAILED'}:raise ValueError('Original-source authentication or connection unavailable')
            sleep(.08)
        raise TimeoutError('Original capture deadline exhausted; no completeness claim')
    try:
        runtime.connector.resume_saved_session()
        until(lambda:runtime.connector.feed_status().get('completed_history_jobs')==len(PAIRS)*len(FRAMES))
        account=runtime.accounts.current
        if not account or not account.authenticated or account.scope_id!=remembered['scope_id']:raise ValueError('Remembered original source was not authenticated')
        end=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0);start=end-timedelta(hours=1)
        stamp=lambda value:value.isoformat().replace('+00:00','Z')
        jobs=[runtime.connector.quote_history.start(s,stamp(start),stamp(end)) for s in PAIRS]
        def quote_jobs_done():
            values=[runtime.database.get('native_quote_history_job',j) for j in jobs]
            return all(value is not None and value['state']!='RUNNING' for value in values)
        until(quote_jobs_done)
        quote=runtime.connector.quote_history.export_tpo(jobs,out/'native-quotes')
        official=acquire_official_context(dict(scope_id=account.scope_id,authorities={s:runtime.market.authority(s) for s in PAIRS}),out/'official-context')
        providers=[]
        for receipt in (quote,official):providers.extend(json.loads(Path(receipt['configuration']).read_bytes())['providers'])
        configuration=out/'sources.json';write_new(configuration,(json.dumps(dict(schema_version=1,providers=providers),indent=2)+'\n').encode())
        proof=dict(result='ORIGINAL_ACQUISITION_COMPLETE_NOT_ALL_STRATEGIES_COMPLETE',scope='BOUNDED_ORIGINAL_CTRADER_AND_OFFICIAL_CONTEXT_CAPTURE',source_scope_sha256=hashlib.sha256(account.scope_id.encode()).hexdigest(),feed=runtime.connector.feed_status(),original_ticks=sum(j['record_count'] for j in quote['jobs']),original_quote_jobs=quote['jobs'],official_responses=official['responses'],fed_coverage=official['fed_coverage'],configuration=str(configuration),source_database_modified=False,synthetic_observations=0,executed_volume_claim=False,elapsed_seconds=round(monotonic()-started,3))
    except Exception as exc:
        proof=dict(result='ACQUISITION_INCOMPLETE',error_type=type(exc).__name__,synthetic_observations=0,source_database_modified=False,source_epoch_not_promoted=True)
    finally:
        auth=runtime.connector.auth_worker;runtime.close()
        if auth and auth.is_alive():auth.join(timeout=35)
        counts={}
        for worker in workers:
            for name,n in worker.read_counts.items():counts[name]=counts.get(name,0)+n
        proof.update(read_request_counts=counts,denied_broker_mutations=sum(w.denied_writes for w in workers),sdk_processes_stopped=all(not w.process.is_alive() for w in workers),auth_thread_stopped=not(auth and auth.is_alive()),runtime_closed=runtime.closed,delegated_agents_started=0,background_jobs_left=0)
        write_new(out/'capture-receipt.json',(json.dumps(proof,indent=2)+'\n').encode())
    if not proof['sdk_processes_stopped'] or not proof['auth_thread_stopped']:raise RuntimeError('Original capture lifecycle did not close')
    return proof
