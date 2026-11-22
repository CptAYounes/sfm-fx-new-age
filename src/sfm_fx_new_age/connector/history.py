"""Bounded read-only native order/deal history pagination, never an execution route."""
from uuid import uuid4
from datetime import timedelta

from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.analytics import digest
from .protocol import milliseconds


class NativeHistory:
    def __init__(self,db,send,clock):self.db,self.send,self.clock=db,send,clock

    def start(self,context,epoch,start,end):
        if sum(job['state']=='RUNNING' for job in self.db.list('native_history_job'))>=4:raise ValueError('Native history concurrent-job budget exhausted')
        if instant(start)>instant(end) or instant(end)>instant(self.clock()):raise ValueError('Causal native history interval required')
        if instant(end)-instant(start)>timedelta(days=31):raise ValueError('Native history request exceeds 31-day engineering budget')
        job={'id':str(uuid4()),'scope_id':context.scope_id,'source_epoch':epoch,'endpoint':context.endpoint_class,
            'account_id':context.account_id,'start':start,'end':end,'state':'RUNNING','pages':0,'records':0,
            'pending':[{'kind':kind,'from':milliseconds(start),'to':milliseconds(end)} for kind in ('ORDER','DEAL')],
            'inflight':None,'processed_pages':[],'reason':''}
        self.db.put('native_history_job',job['id'],job)
        self._next(job)
        return self.db.get('native_history_job',job['id'])

    def _next(self,job):
        if not job['pending']:job['state']='COMPLETE'
        elif job['pages']>=256:
            job['state']='BUDGET_EXHAUSTED';job['reason']='Incomplete; request a narrower interval'
        else:
            window=job['pending'].pop(0);job['inflight']=window
            payload={'ctidTraderAccountId':job['account_id'],'fromTimestamp':window['from'],'toTimestamp':window['to']}
            if window['kind']=='DEAL':payload['maxRows']=1000
            self.db.put('native_history_job',job['id'],job)
            try:self.send(job['endpoint'],'ProtoOAOrderListReq' if window['kind']=='ORDER' else 'ProtoOADealListReq',payload,context={'history_job':job['id'],**window})
            except Exception as exc:
                job['state']='REQUEST_FAILED';job['reason']=type(exc).__name__
                self.db.put('native_history_job',job['id'],job)
                raise
        self.db.put('native_history_job',job['id'],job)

    def page(self,request,body):
        job=self.db.get('native_history_job',request['history_job'])
        if not job or job['state']!='RUNNING':return
        window={key:request[key] for key in ('kind','from','to')}
        if job['inflight']!=window:raise ValueError('Native history page does not match current request')
        identity=digest([window,body])
        if identity in job['processed_pages']:return
        if str(body.get('ctidTraderAccountId'))!=job['account_id']:raise ValueError('Native history account mismatch')
        rows=body.get('order' if window['kind']=='ORDER' else 'deal',[])
        if type(rows) is not list or len(rows)>10000:raise ValueError('Bounded native history page required')
        if type(body.get('hasMore')) is not bool:raise ValueError('Explicit native history completeness required')
        with self.db.transaction() as conn:
            for row in rows:
                native_id=str(row['orderId' if window['kind']=='ORDER' else 'dealId'])
                key=digest([job['scope_id'],window['kind'],native_id,row])
                existing=conn.execute("SELECT 1 FROM records WHERE kind='native_history_record' AND id=?",(key,)).fetchone()
                if not existing:
                    self.db.write(conn,'native_history_record',key,{'id':key,'scope_id':job['scope_id'],'kind':window['kind'],
                        'native_id':native_id,'payload':row,'observed_at':self.clock(),'origin':'LIVE_OBSERVED','job_id':job['id']})
                    job['records']+=1
        job['pages']+=1;job['processed_pages'].append(identity);job['inflight']=None
        if body['hasMore']:
            if window['from']>=window['to']:
                job['state']='INCOMPLETE_SAME_TIMESTAMP_OVERFLOW';job['reason']='Server reports more than one page within one millisecond'
                self.db.put('native_history_job',job['id'],job);return
            middle=(window['from']+window['to'])//2
            job['pending']=[{'kind':window['kind'],'from':window['from'],'to':middle},
                {'kind':window['kind'],'from':middle+1,'to':window['to']}]+job['pending']
        self._next(job)

    def fail(self,identity,reason):
        job=self.db.get('native_history_job',identity)
        if job and job['state']=='RUNNING':
            job['state']='REQUEST_FAILED';job['reason']=reason
            self.db.put('native_history_job',identity,job)

    def disconnect(self,endpoint=None):
        for job in self.db.list('native_history_job'):
            if job['state']=='RUNNING' and (endpoint is None or job['endpoint']==endpoint):
                job['state']='INTERRUPTED';job['reason']='Connection closed; no completeness assertion'
                self.db.put('native_history_job',job['id'],job)
