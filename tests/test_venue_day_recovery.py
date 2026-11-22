"""NONMARKET exact-day controls; connected proof is a separate live gate."""
from datetime import datetime,timezone
from threading import Event
from hashlib import sha256
import json
import pytest
from sfm_fx_new_age.connector.kraken_weekly import WeeklySource

class NonmarketDay(WeeklySource):
    def __init__(self,path):super().__init__(path,Event())
    def get(self,endpoint):
        begin=int(datetime(2026,10,16,tzinfo=timezone.utc).timestamp())
        rows=[[begin,'1','1','1','1','1','20',10],[begin+86400,'1','1','1','1','1','99',50]]
        raw=json.dumps({'result':{'USDJPY':rows,'last':begin+86400}})
        self.audit.append(dict(endpoint=endpoint,sha256=sha256(raw.encode()).hexdigest(),received_at='2026-11-16T12:00:00Z',raw=raw))
        return json.loads(raw)['result'],'2026-11-16T12:00:00Z'
    def boundary(self,symbol,start,end,hours,**kwargs):
        # Exact original closed tail stand-ins, never market acceptance.
        return (__import__('decimal').Decimal('3'),2,{'origin':'NONMARKET_TAIL'}) if start.day==15 else (__import__('decimal').Decimal('2'),1,{'origin':'NONMARKET_TAIL'})

def test_broker_day_uses_actual_native_day_plus_exact_tails(tmp_path):
    source=NonmarketDay(tmp_path)
    rows,proof=source.recover('USDJPY',({'open_time':'2026-10-15T21:00:00Z','close_time':'2026-10-16T21:00:00Z'},),(),frame='D1')
    assert rows[0]['quantity']=='21' and rows[0]['trade_count']==11
    assert rows[0]['id'].startswith('KRAKEN:D1:') and proof['frame']=='D1'
    assert proof['derivation']=='SUM_NATIVE_UTC_DAYS + EXACT_START_TAIL - EXACT_END_TAIL'
    assert proof['weeks'][0]['start']=='2026-10-15T21:00:00Z'

def test_day_recovery_refuses_missing_original_native_day(tmp_path):
    source=NonmarketDay(tmp_path)
    with pytest.raises(ValueError,match='day missing'):
        source.recover('USDJPY',({'open_time':'2026-10-14T21:00:00Z','close_time':'2026-10-15T21:00:00Z'},),(),frame='D1')

def test_d1_and_w1_interval_contracts_stay_distinct(tmp_path):
    source=NonmarketDay(tmp_path)
    with pytest.raises(ValueError,match='day/week interval'):
        source.recover('USDJPY',({'open_time':'2026-10-15T21:00:00Z','close_time':'2026-10-16T21:00:00Z'},),())
