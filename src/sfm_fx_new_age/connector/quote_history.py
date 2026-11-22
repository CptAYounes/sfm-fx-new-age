"""Opt-in bounded native BID quote-history capture; no executed-volume claims.

Explicit exhaustion (hasMore=False) is required for every admitted partition.
Timestamp-collision overflow, page budgets and source changes fail closed. Raw
broker responses remain stored alongside decoded original ticks. Construction is
inert; only start() submits the allowlisted historical-read request.
"""
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from pathlib import Path
import json
from uuid import uuid4
from typing import Any
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.connector.protocol import milliseconds


class NativeQuoteHistory:
    def __init__(self,connector):self.connector=connector;self.r=connector.r

    def interrupt(self,endpoint=None):
        for job in self.r.database.list('native_quote_history_job'):
            if job['state']=='RUNNING' and (endpoint is None or job['endpoint']==endpoint):
                job.update(state='INTERRUPTED',reason='Native connection closed; capture incomplete')
                self.r.database.put('native_quote_history_job',job['id'],job)

    def start(self,symbol,start,end) -> str:
        account=self.r.accounts.current;authority=self.r.market.authority(symbol)
        if not account or not account.authenticated or account.origin.value!='LIVE_OBSERVED' or not authority or authority['origin']!='LIVE_OBSERVED':raise ValueError('Authenticated original source required')
        spec=self.r.market.spec(account.account_id,symbol)
        if not spec or not instant(start)<instant(end)<=instant(self.r.clock()) or instant(end)-instant(start)>timedelta(hours=2):raise ValueError('Native metadata and closed <=2h quote interval required')
        if sum(j['state']=='RUNNING' for j in self.r.database.list('native_quote_history_job'))>=7:raise ValueError('Native quote capture concurrent-job budget exhausted')
        job:dict[str,Any]=dict(id=str(uuid4()),scope_id=account.scope_id,source_epoch=authority['source_epoch'],symbol=symbol,account_id=account.account_id,endpoint=account.endpoint_class,symbol_id=spec.broker_symbol_id,start=start,end=end,state='RUNNING',pages=0,pending=[dict(start=milliseconds(start),end=milliseconds(end)-1)],inflight=None,accepted_pages=[],record_count=0,reason='')
        self.r.database.put('native_quote_history_job',job['id'],job);self._next(job);return job['id']

    def _next(self,job):
        authority=self.r.market.authority(job['symbol'])
        if self.r.market.scope_id!=job['scope_id'] or not authority or authority['source_epoch']!=job['source_epoch']:
            job.update(state='SOURCE_CHANGED',reason='No admission under another source epoch')
        elif not job['pending']:job.update(state='COMPLETE',inflight=None)
        elif job['pages']>=64:job.update(state='BUDGET_EXHAUSTED',reason='Incomplete native page coverage')
        else:
            window=job['pending'].pop(0);job['inflight']=window
            self.r.database.put('native_quote_history_job',job['id'],job)
            try:self.connector.request(job['endpoint'],'ProtoOAGetTickDataReq',dict(ctidTraderAccountId=job['account_id'],symbolId=job['symbol_id'],type='BID',fromTimestamp=window['start'],toTimestamp=window['end']),context=dict(native_quote_history=job['id'],**window))
            except Exception as exc:job.update(state='REQUEST_FAILED',reason=type(exc).__name__)
        self.r.database.put('native_quote_history_job',job['id'],job)

    def fail(self,request,reason):
        context=(request or {}).get('context') or {};identity=context.get('native_quote_history')
        job=self.r.database.get('native_quote_history_job',identity) if identity else None
        if job and job['state']=='RUNNING':
            job.update(state='REQUEST_FAILED',reason=reason);self.r.database.put('native_quote_history_job',identity,job)

    def page(self,request,body):
        context=request['context'];job=self.r.database.get('native_quote_history_job',context['native_quote_history'])
        if not job or job['state']!='RUNNING':return
        raw_key=digest([job['id'],context,body])
        self.r.database.put('native_quote_history_received',raw_key,dict(id=raw_key,job_id=job['id'],scope_id=job['scope_id'],source_epoch=job['source_epoch'],symbol=job['symbol'],request_window=context,payload=body,observed_at=self.r.clock(),origin='LIVE_OBSERVED'))
        window=dict(start=context['start'],end=context['end'])
        if job['inflight']!=window or str(body.get('ctidTraderAccountId'))!=job['account_id'] or type(body.get('hasMore')) is not bool:raise ValueError('Exact native quote page identity/completeness required')
        rows=body.get('tickData',[])
        if not isinstance(rows,list) or len(rows)>20000:raise ValueError('Native page row budget exceeded')
        observed=self.r.clock();key=digest([job['id'],window,body]);job['pages']+=1
        self.r.database.put('native_quote_history_page',key,dict(id=key,job_id=job['id'],scope_id=job['scope_id'],source_epoch=job['source_epoch'],symbol=job['symbol'],window=window,payload=body,observed_at=observed,origin='LIVE_OBSERVED',quote_basis='BID'))
        if body['hasMore']:
            if window['start']>=window['end']:
                job.update(state='INCOMPLETE_SAME_TIMESTAMP_OVERFLOW',reason='Server hasMore at one millisecond; no synthetic exhaustion')
            else:
                middle=(window['start']+window['end'])//2
                job['pending']=[dict(start=window['start'],end=middle),dict(start=middle+1,end=window['end'])]+job['pending']
        else:
            # Protocol times are newest-first: first absolute, following signed deltas.
            timestamp=None;relative_price=None;decoded=[]
            for index,row in enumerate(rows):
                delta=int(row['timestamp']);current=delta if timestamp is None else timestamp+delta
                if not window['start']<=current<=window['end'] or timestamp is not None and current>timestamp:raise ValueError('Native descending tick timestamp/interval mismatch')
                timestamp=current;relative_price=int(row['tick']) if relative_price is None else relative_price+int(row['tick'])
                price=Decimal(relative_price)/Decimal(100000)
                if price<=0:raise ValueError('Native quote price must be positive')
                stamp=datetime.fromtimestamp(current/1000,timezone.utc).isoformat().replace('+00:00','Z')
                decoded.append(dict(id=digest([key,index,row]),time=stamp,available_at=observed,price=str(price)))
            if job['record_count']+len(decoded)>20000:job.update(state='BUDGET_EXHAUSTED',reason='Original observation budget exceeded')
            else:
                self.r.database.put('native_quote_history_decoded',key,dict(id=key,job_id=job['id'],records=decoded))
                job['record_count']+=len(decoded);job['accepted_pages'].append(key)
        job['inflight']=None;self.r.database.put('native_quote_history_job',job['id'],job)
        if job['state']=='RUNNING':self._next(job)

    def tpo_evidence(self,identity,*,provider_id='CTRADER_ORIGINAL_BID_HISTORY_V1',available_at=None):
        """Validated same-epoch observed prices; never executed-volume evidence."""
        from .official_context import now
        job=self.r.database.get('native_quote_history_job',identity)
        if not job or job['state']!='COMPLETE' or not job['record_count']:raise ValueError('Explicitly exhausted nonempty original quote history required')
        authority=self.r.market.authority(job['symbol'])
        if self.r.market.scope_id!=job['scope_id'] or not authority or authority['source_epoch']!=job['source_epoch']:raise ValueError('Native quote export source changed')
        records=[row for key in job['accepted_pages'] for row in self.r.database.get('native_quote_history_decoded',key)['records']];records.sort(key=lambda r:(instant(r['time']),r['id']))
        duration=(instant(job['end'])-instant(job['start'])).total_seconds()
        slots={int((instant(r['time'])-instant(job['start'])).total_seconds()//1800) for r in records}
        if duration%1800 or slots!=set(range(int(duration//1800))) or duration<3600:raise ValueError('Original complete 30-minute slot observations required')
        available=available_at or now();spec=self.r.market.spec(job['account_id'],job['symbol'])
        if spec is None:raise ValueError('Native price grid unavailable')
        evidence=SupplementalEvidence(provider_id=provider_id,kind='INTRABAR_PRICES',scope_id=job['scope_id'],source_epoch=job['source_epoch'],symbol=job['symbol'],origin='LIVE_OBSERVED',source_ref='ProtoOAGetTickDataReq BID / '+','.join(job['accepted_pages']),venue='CTRADER_BROKER_BID_QUOTE_HISTORY_NOT_TRADES',instrument=job['symbol'],price_domain='SPOT_PAIR',unit='OBSERVED_PRICE',window_start=job['start'],window_end=job['end'],available_at=available,valid_until=(instant(available)+timedelta(hours=12)).isoformat().replace('+00:00','Z'),complete=True,records=tuple(records),parameters=dict(tick_size=str(spec.tick_size),slot_coverage_complete=True))
        validate_wire_shape(evidence)
        # A pair can disappear and return inside one source epoch. A fresh
        # native capture of its same closed interval must not overwrite the
        # immutable first publication or renew its original observation TTL.
        # Persisted rows alone never qualify: all new pages were exhausted and
        # decoded above; corroborate exact time/price multiplicity first.
        prior=self.r.database.supplemental_revision(evidence)
        if prior:
            from collections import Counter
            from sfm_fx_new_age.contracts.domain import record
            key=digest([evidence.scope_id,evidence.source_epoch,evidence.symbol,evidence.kind,evidence.provider_id,evidence.window_start,evidence.window_end,prior['revision']])
            original=self.r.database.get('supplemental_evidence',key)
            if not original:raise ValueError('Original TPO corroboration publication missing')
            raw=dict(original);raw['records']=tuple(raw['records'])
            retained=SupplementalEvidence(**raw);validate_wire_shape(retained)
            fields=('scope_id','source_epoch','symbol','kind','provider_id','origin','venue','instrument','price_domain','unit','window_start','window_end','complete','parameters')
            if any(getattr(retained,name)!=getattr(evidence,name) for name in fields):raise ValueError('TPO corroboration contract changed')
            prices=lambda rows:Counter((instant(row['time']),Decimal(row['price'])) for row in rows)
            if prices(retained.records)!=prices(evidence.records):raise ValueError('Closed quote interval corroboration mismatch')
            if instant(available)>instant(retained.valid_until):raise ValueError('Original TPO publication expired; no clock renewal')
            corroboration=digest([identity,digest(original)])
            self.r.database.put('native_quote_history_corroboration',corroboration,dict(id=corroboration,job_id=identity,
                scope_id=job['scope_id'],source_epoch=job['source_epoch'],symbol=job['symbol'],
                original_evidence_hash=digest(original),new_accepted_pages=list(job['accepted_pages']),
                verified_at=available,record_count=len(records),first_observation_preserved=True))
            return retained
        return evidence

    def export_tpo(self,job_ids,output_dir) -> dict[str,Any]:
        from .official_context import write_new,sha,now
        out=Path(output_dir)
        if not out.is_absolute() or out.resolve()!=out:raise ValueError('Absolute nonsymlink source output required')
        out.mkdir(mode=0o700,parents=True,exist_ok=False);entries=[];receipts=[]
        for identity in job_ids:
            from sfm_fx_new_age.contracts.domain import record
            job=self.r.database.get('native_quote_history_job',identity)
            envelope=record(self.tpo_evidence(identity))
            envelope.pop('revision');envelope.pop('schema_version')
            filename=job['symbol']+'-tpo.json';data=(json.dumps(envelope,indent=2)+'\n').encode();write_new(out/filename,data);entries.append(dict(file=filename,sha256=sha(data)));receipts.append({k:job[k] for k in ('id','source_epoch','symbol','start','end','state','pages','record_count','accepted_pages')})
        if len({r['symbol'] for r in receipts})!=len(receipts):raise ValueError('One quote interval per symbol required')
        manifest=out/'manifest.json';write_new(manifest,(json.dumps(dict(schema_version=1,entries=entries),indent=2)+'\n').encode())
        config=out/'sources.json';write_new(config,(json.dumps(dict(schema_version=1,providers=[dict(provider_id='CTRADER_ORIGINAL_BID_HISTORY_V1',origin='LIVE_OBSERVED',kinds=['INTRABAR_PRICES'],manifest_path=str(manifest))]),indent=2)+'\n').encode())
        proof=dict(scope='ORIGINAL_CTRADER_EXHAUSTED_BID_QUOTES_TPO_NOT_EXECUTED_VOLUME',jobs=receipts,configuration=str(config),synthetic_observations=0,prices_interpolated=0,quantities_invented=0)
        write_new(out/'acquisition-receipt.json',(json.dumps(proof,indent=2)+'\n').encode());return proof
