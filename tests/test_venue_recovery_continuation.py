"""NONMARKET controls for real reconnect and late-ready scheduling defects."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import pytest
from test_connector_boundary import connected
from test_feed_bootstrap_isolation import full_feed
from test_cross_broker_compatibility import ControlledThread
from sfm_fx_new_age.contracts.domain import Bar,Origin

def test_republication_after_same_epoch_child_rebind_advances_immutable_revision(connected):
    r,c,_=full_feed(connected);f=c.analytical_feed;v=f.venue
    v.binding=f._identity()
    info={'native_pair':'EURUSD'}
    rows=({'id':'NONMARKET:HOUR','time':'2026-11-05T10:00:00Z','end_time':'2026-11-05T11:00:00Z','available_at':'2026-11-05T11:01:00Z','quantity':'100','trade_count':1},)
    kind='EXECUTED_BAR_QUANTITIES';start=rows[0]['time'];end=rows[0]['end_time']
    v._accept('EURUSD',info,rows,r.clock(),kind,start,end,'NONMARKET_CONTROL')
    first=r.analytics.supplemental.snapshot('EURUSD',r.clock())[kind]
    v.disconnect();v.binding=f._identity()
    r.clock=lambda:'2026-11-05T12:00:01Z';r.analytics.supplemental.clock=r.clock
    v._accept('EURUSD',info,rows,r.clock(),kind,start,end,'NONMARKET_CONTROL')
    second=r.analytics.supplemental.snapshot('EURUSD',r.clock())[kind]
    assert second['revision']==first['revision']+1
    assert second['records']==first['records']  # Original event/receipt clocks retained.
    assert second['available_at']>first['available_at']
    with pytest.raises(ValueError):
        v._accept('EURUSD',info,rows,'2026-11-05T11:59:59Z',kind,start,end,'NONMARKET_CONTROL')


def test_new_ready_weekly_pair_does_not_inherit_other_pair_cooldown(connected,monkeypatch,tmp_path):
    import sfm_fx_new_age.connector.kraken_weekly as module
    from sfm_fx_new_age.connector.lanes import project_binding
    r,c,_=full_feed(connected);v=c.analytical_feed.venue;w=v.weekly
    binding=project_binding(c.analytical_feed._identity(),{'EURUSD','GBPUSD'})
    r.database.path=str(tmp_path/'NONMARKET.sqlite')
    monkeypatch.setattr(module,'Thread',ControlledThread)
    end=datetime(2026,11,2,tzinfo=timezone.utc)
    def bars(symbol):
        return tuple(Bar(symbol,'W1',(end-timedelta(weeks=i+1)).isoformat(),(end-timedelta(weeks=i)).isoformat(),(end-timedelta(weeks=i)).isoformat(),Decimal('1'),Decimal('1.1'),Decimal('.9'),Decimal('1'),'NONMARKET',Origin.SYNTHETIC_FIXTURE) for i in range(21))
    monkeypatch.setattr(r.market,'bars',lambda symbol,*args:bars(symbol))
    v.pairs={'EURUSD':{},'GBPUSD':{}};w.binding=binding
    w.hour_inputs['EURUSD']=('NONMARKET_HOUR_CONTROL',)
    w.poll(binding);first=w.worker
    assert set(first.args[1])=={'EURUSD'}
    first.alive=False;w.poll(binding)  # Finishes the first cohort; 300s cooldown.
    assert w.worker is None
    w.hour_inputs['GBPUSD']=('NONMARKET_HOUR_CONTROL',)
    w.poll(binding)
    assert w.worker is not None and set(w.worker.args[1])=={'GBPUSD'}
    w.disconnect()
