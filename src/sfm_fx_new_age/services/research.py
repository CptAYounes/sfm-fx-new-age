"""Single shared analytical object store, with causal immutable revisions and typed ingress."""
from __future__ import annotations
import json
from typing import Callable

from sfm_fx_new_age.contracts.analytics import Level,Evidence,MarketCandidate,Overlay,Recipe
from sfm_fx_new_age.contracts.domain import instant,record,symbol_check
from sfm_fx_new_age.contracts.enums import Priority
from sfm_fx_new_age.storage.database import Database,StateConflict

KINDS={Level:'level',Evidence:'evidence',MarketCandidate:'market_candidate',Overlay:'overlay',Recipe:'recipe'}
IDS={'level':'level_id','evidence':'evidence_id','market_candidate':'candidate_id','overlay':'overlay_id','recipe':'recipe_id'}


class ResearchStore:
    def __init__(self,db:Database,emit:Callable):self.db,self.emit=db,emit

    def publish(self,item)->dict:return self.publish_many((item,))[0]

    def publish_many(self,items)->list[dict]:
        if len(items)>1000:raise ValueError('Analytical batch exceeds budget')
        entries=[]
        for item in items:
            if type(item) not in KINDS:raise ValueError('Typed analytical object required')
            kind=KINDS[type(item)];body=record(item);identity=body[IDS[kind]];lineage=body.get('lineage',{})
            scope=lineage.get('source_scope','GLOBAL_RESEARCH');epoch=lineage.get('source_epoch','GLOBAL_RESEARCH')
            version=body.get('revision',body.get('version',1));key=json.dumps([scope,epoch,identity,version],separators=(',',':'))
            entries.append((kind,key,body,identity,scope,epoch,version))
        published=[]
        with self.db.transaction() as conn:
            for kind,key,body,identity,scope,epoch,version in entries:
                row=conn.execute('SELECT body FROM records WHERE kind=? AND id=?',(kind,key)).fetchone()
                if row:
                    if json.loads(row[0])!=body:raise StateConflict('Immutable analytical revision cannot be overwritten')
                    continue
                previous=[json.loads(row[0]) for row in conn.execute(
                    f"SELECT body FROM records WHERE kind=? AND json_extract(body,'$.{IDS[kind]}')=? "
                    "AND COALESCE(json_extract(body,'$.lineage.source_scope'),'GLOBAL_RESEARCH')=? "
                    "AND COALESCE(json_extract(body,'$.lineage.source_epoch'),'GLOBAL_RESEARCH')=?",(kind,identity,scope,epoch))]
                previous=[r for r in previous if r[IDS[kind]]==identity and r.get('lineage',{}).get('source_scope','GLOBAL_RESEARCH')==scope
                          and r.get('lineage',{}).get('source_epoch','GLOBAL_RESEARCH')==epoch]
                if previous:
                    latest=max(previous,key=lambda r:r.get('revision',r.get('version',1)))
                    if version<=latest.get('revision',latest.get('version',1)):raise StateConflict('Analytical version regression')
                    if body.get('lineage') and instant(body['lineage']['available_at'])<instant(latest['lineage']['available_at']):raise StateConflict('Availability regression')
                self.db.write(conn,kind,key,body);published.append((kind,body,identity))
        for kind,body,identity in published:
            self.emit('ANALYTICS.REVISION','SHARED_ANALYTICS_STORE',{'kind':kind,'object':body},Priority.P2,identity)
        return [entry[2] for entry in entries]

    def query(self,kind:str,*,scope:str,epoch:str,symbol:str,as_of:str,history=False,limit=500)->list[dict]:
        if kind not in IDS or kind=='recipe':raise ValueError('Unknown scoped analytical query')
        symbol_check(symbol);cutoff=instant(as_of)
        if type(limit) is not int or not 1<=limit<=5000:raise ValueError('Bounded query required')
        rows=[]
        with self.db.lock:
            stored=[json.loads(row[0]) for row in self.db.connection.execute("""SELECT body FROM records
                WHERE kind=? AND json_extract(body,'$.lineage.source_scope')=?
                AND json_extract(body,'$.lineage.source_epoch')=? AND json_extract(body,'$.lineage.symbol')=?""",(kind,scope,epoch,symbol))]
        for row in stored:
            line=row['lineage']
            if (line['source_scope'],line['source_epoch'],line['symbol'])!=(scope,epoch,symbol) or instant(line['available_at'])>cutoff:continue
            rows.append(row)
        rows.sort(key=lambda r:(instant(r['lineage']['available_at']),r[IDS[kind]],r.get('revision',1)))
        if not history:
            selected={}
            for row in rows:selected[row[IDS[kind]]]=row
            rows=list(selected.values())
        return rows[-limit:]

    def recipes(self,*,history=False):
        rows=self.db.list('recipe')
        if history:return rows
        current={}
        for row in rows:
            previous=current.get(row['recipe_id'])
            if previous is None or row['version']>previous['version']:current[row['recipe_id']]=row
        return list(current.values())

    def signal_history(self,scope:str,*,signal_id:str|None=None,limit=500,as_of:str|None=None)->list[dict]:
        if not 1<=limit<=5000:raise ValueError('Bounded history required')
        rows=[r for r in self.db.list('signal_revision') if r.get('scope_id')==scope and (signal_id is None or r['signal_id']==signal_id)
              and (as_of is None or instant(r['available_at'])<=instant(as_of))]
        return sorted(rows,key=lambda r:(instant(r['available_at']),r['signal_id'],r['revision']))[-limit:]
