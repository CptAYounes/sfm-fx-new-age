"""Immutable replay datasets and deterministic research runs, isolated from account execution."""
from __future__ import annotations
from dataclasses import replace
from datetime import timezone
from decimal import Decimal
from itertools import product
from typing import Callable

from sfm_fx_new_age.contracts.domain import Bar,Origin,record,instant
from sfm_fx_new_age.contracts.analytics import digest


class ReplayService:
    def __init__(self,db,emit):self.db,self.emit=db,emit

    def study(self,request,methods):
        from .backtesting import evaluate_study
        return evaluate_study(self,request,methods)

    def study_result(self,study_id):
        result=self.db.get('research_study',study_id)
        if not result:raise ValueError('Unknown research study')
        if digest({k:v for k,v in result.items() if k!='result_hash'})!=result['result_hash']:
            raise ValueError('Stored research result hash mismatch')
        return result

    def import_dataset(self,dataset_id:str,bars:tuple[Bar,...],*,source_ref:str):
        if not dataset_id or not bars or not source_ref:raise ValueError('Dataset, bars and provenance required')
        scopes={(b.scope_id,b.source_epoch,b.origin) for b in bars}
        if len(scopes)!=1:raise ValueError('One source scope/epoch/origin per replay dataset')
        ordered=sorted(bars,key=lambda b:(instant(b.available_at),b.symbol,b.timeframe,instant(b.open_time),b.revision))
        keys=set();previous={}
        for bar in ordered:
            key=(bar.symbol,bar.timeframe,bar.open_time,bar.revision)
            if key in keys:raise ValueError('Duplicate replay bar revision')
            keys.add(key)
            series=key[:3]
            if series in previous and bar.revision<=previous[series]:raise ValueError('Noncausal replay correction')
            previous[series]=bar.revision
        body={'dataset_id':dataset_id,'source_ref':source_ref,'bars':[record(b) for b in ordered],
              'dataset_hash':digest([record(b) for b in ordered]),'origin':Origin.HISTORICAL_REPLAY.value,
              'original_origin':ordered[0].origin.value,'schema_version':1}
        old=self.db.get('replay_dataset',dataset_id)
        if old and old!=body:raise ValueError('Replay dataset identity is immutable')
        self.db.put('replay_dataset',dataset_id,body)
        return {k:v for k,v in body.items() if k!='bars'}

    def create(self,run_id,dataset_id,configuration:dict):
        data=self.db.get('replay_dataset',dataset_id)
        if not data:raise ValueError('Known replay dataset required')
        if self.db.get('replay_run',run_id):raise ValueError('Run identity already exists')
        body={'run_id':run_id,'dataset_id':dataset_id,'dataset_hash':data['dataset_hash'],'configuration':configuration,
              'configuration_hash':digest(configuration),'cursor':-1,'state':'PAUSED','as_of':None,
              'origin':Origin.HISTORICAL_REPLAY.value,'execution_allowed':False,'schema_version':1}
        self.db.put('replay_run',run_id,body)
        return body

    def control(self,run_id,action,*,cursor:int|None=None):
        run=self.db.get('replay_run',run_id)
        if not run:raise ValueError('Unknown replay run')
        data=self.db.get('replay_dataset',run['dataset_id']);bars=data['bars']
        if action not in {'PLAY','PAUSE','STEP','SEEK'}:raise ValueError('Unknown replay control')
        if action=='PLAY':run['state']='RUNNING'
        elif action=='PAUSE':run['state']='PAUSED'
        else:
            index=run['cursor']+1 if action=='STEP' else cursor
            if type(index) is not int or not -1<=index<len(bars):raise ValueError('Replay cursor out of bounds')
            # One availability batch is atomic: never show half a timestamp on a replay frame.
            if index>=0:
                stamp=bars[index]['available_at']
                while index+1<len(bars) and instant(bars[index+1]['available_at'])==instant(stamp):index+=1
            run.update(cursor=index,as_of=bars[index]['available_at'] if index>=0 else None,state='PAUSED')
        self.db.put('replay_run',run_id,run)
        self.emit('REPLAY.STATE','REPLAY_CLOCK',run)
        return run

    def tick(self):
        for run in self.db.list('replay_run'):
            if run['state']!='RUNNING':continue
            data=self.db.get('replay_dataset',run['dataset_id'])
            if run['cursor']+1>=len(data['bars']):
                self.control(run['run_id'],'PAUSE');continue
            body=self.control(run['run_id'],'STEP');body['state']='RUNNING';self.db.put('replay_run',run['run_id'],body)

    def snapshot(self,run_id,*,symbol=None,timeframe=None):
        run=self.db.get('replay_run',run_id)
        if not run:raise ValueError('Unknown replay run')
        data=self.db.get('replay_dataset',run['dataset_id']);latest={}
        for row in data['bars'][:run['cursor']+1]:
            if symbol and row['symbol']!=symbol or timeframe and row['timeframe']!=timeframe:continue
            latest[(row['symbol'],row['timeframe'],row['open_time'])]=row|{
                'origin':Origin.HISTORICAL_REPLAY.value,'source_epoch':'REPLAY:'+run_id,'scope_id':'REPLAY:'+run_id}
        return {**run,'total_items':len(data['bars']),'rows':sorted(latest.values(),key=lambda r:(instant(r['open_time']),r['symbol'],r['timeframe']))}

    def walk_forward(self,dataset_id,train:int,test:int):
        dataset=self.db.get('replay_dataset',dataset_id)
        if not dataset or type(train) is not int or type(test) is not int or min(train,test)<1:raise ValueError('Positive chronological windows required')
        original={}
        for r in dataset['bars']:original.setdefault(instant(r['available_at']),r['available_at'])
        times=[original[t] for t in sorted(original)]
        return [{'train_from':times[i],'train_through':times[i+train-1],
                 'test_from':times[i+train],'test_through':times[i+train+test-1]}
                for i in range(0,len(times)-train-test+1,test)]

    @staticmethod
    def parameter_sweep(parameters:dict,*,max_runs:int=256):
        if not parameters or any(type(v) is not list or not v for v in parameters.values()):raise ValueError('Nonempty parameter axes required')
        size=1
        for values in parameters.values():
            size*=len(values)
            if size>max_runs:raise ValueError('Parameter sweep exceeds run budget')
        return [dict(zip(sorted(parameters),values)) for values in product(*(parameters[k] for k in sorted(parameters)))]

    @staticmethod
    def classify_bar_outcome(bar:Bar,side:str,stop:Decimal,target:Decimal):
        if side not in {'BUY','SELL'} or stop==target:raise ValueError('Directional stop and target required')
        hit_stop=bar.low<=stop if side=='BUY' else bar.high>=stop
        hit_target=bar.high>=target if side=='BUY' else bar.low<=target
        return 'AMBIGUOUS_INTRABAR' if hit_stop and hit_target else 'STOP_TOUCHED' if hit_stop else 'TARGET_TOUCHED' if hit_target else 'NEITHER_TOUCHED'
