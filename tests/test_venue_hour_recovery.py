"""NONMARKET protocol controls; not evidence of acquired market quantities."""
from datetime import datetime,timezone
from threading import Event
from hashlib import sha256
import json
import pytest
from sfm_fx_new_age.connector.kraken_weekly import WeeklySource

START=datetime(2026,10,15,21,tzinfo=timezone.utc)
END=datetime(2026,10,15,23,tzinfo=timezone.utc)
BARS=({'open_time':'2026-10-15T21:00:00Z','close_time':'2026-10-15T23:00:00Z'},)

class NonmarketSource(WeeklySource):
    def __init__(self,path,pages):super().__init__(path,Event());self.pages=iter(pages)
    def get(self,endpoint):
        body=next(self.pages);raw=json.dumps(body);self.requests+=1
        self.audit.append(dict(endpoint=endpoint,received_at='2026-11-16T12:00:00Z',sha256=sha256(raw.encode()).hexdigest(),raw=raw))
        return body,'2026-11-16T12:00:00Z'

def row(identity,time,quantity='2'):
    return ['1.10',quantity,str(time),'b','l','',identity]

def test_missing_hours_are_recovered_only_from_exhausted_native_trades(tmp_path):
    start=int(START.timestamp());end=int(END.timestamp())
    source=NonmarketSource(tmp_path,[{'USDJPY':[row(100,start+10),row(101,end)],'last':str(end*10**9)}])
    repaired,proof=source.repair_hours('USDJPY',(),BARS)
    assert len(repaired)==2 and [r['quantity'] for r in repaired]==['2','0']
    assert [r['trade_count'] for r in repaired]==[1,0]
    assert all(r['available_at']=='2026-11-16T12:00:00Z' for r in repaired)
    assert proof['zero_semantics']=='ONLY_ORIGINAL_EXECUTION_EXHAUSTION'
    assert source.requests==1
    cached=NonmarketSource(tmp_path,[])
    assert cached.repair_hours('USDJPY',(),BARS)[0]==repaired
    assert cached.requests==0

def test_existing_native_hours_are_preserved_without_network_or_retiming(tmp_path):
    rows=tuple(dict(id='NONMARKET:'+str(i),time='2026-10-15T'+str(21+i)+':00:00Z',end_time='2026-10-15T'+str(22+i)+':00:00Z',available_at='2026-10-16T01:00:00Z',quantity='5',trade_count=2) for i in range(2))
    source=NonmarketSource(tmp_path,[])
    repaired,proof=source.repair_hours('USDJPY',rows,BARS)
    assert repaired==rows and proof['recovered_hours']==0 and source.requests==0

def test_unexhausted_range_does_not_become_zero_quantity(tmp_path):
    source=NonmarketSource(tmp_path,[{'USDJPY':[],'last':str(int(START.timestamp())*10**9)}])
    with pytest.raises(ValueError,match='incomplete'):
        source.repair_hours('USDJPY',(),BARS)
    assert not list(tmp_path.glob('*.json'))

def test_native_sequence_gap_does_not_create_hour_totals(tmp_path):
    source=NonmarketSource(tmp_path,[{'USDJPY':[row(100,int(START.timestamp())+1),row(102,int(END.timestamp()))],'last':str(int(END.timestamp())*10**9)}])
    with pytest.raises(ValueError,match='continuity'):
        source.repair_hours('USDJPY',(),BARS)
    assert not list(tmp_path.glob('*.json'))
