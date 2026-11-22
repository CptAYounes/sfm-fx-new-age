"""Read-only native-history state-machine tests, with recording callbacks only."""
import pytest
from sfm_fx_new_age.connector.history import NativeHistory
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,FIXTURE_EPOCH


def test_time_bisection_deduplicates_parent_and_child_native_rows(runtime):
    requests=[]
    h=NativeHistory(runtime.database,lambda *args,**kw:requests.append((args,kw)),lambda:FIXTURE_NOW)
    job=h.start(runtime.accounts.current,FIXTURE_EPOCH,'2026-11-05T11:00:00Z',FIXTURE_NOW)
    def deliver(rows,more):
        args,kw=requests.pop(0);window=kw['context'];field='order' if window['kind']=='ORDER' else 'deal'
        h.page(window,{'ctidTraderAccountId':runtime.accounts.current.account_id,field:rows,'hasMore':more})
    deliver([{'orderId':'9'}],True)
    deliver([{'orderId':'9'}],False)
    deliver([],False)
    deliver([{'dealId':'42'}],False)
    result=runtime.database.get('native_history_job',job['id'])
    assert result['state']=='COMPLETE' and result['pages']==4 and result['records']==2
    assert len(runtime.database.list('native_history_record'))==2
    assert requests==[] and runtime.orders.transport.submissions==[]


def test_same_millisecond_overflow_is_explicitly_incomplete(runtime):
    requests=[];h=NativeHistory(runtime.database,lambda *args,**kw:requests.append(kw['context']),lambda:FIXTURE_NOW)
    job=h.start(runtime.accounts.current,FIXTURE_EPOCH,FIXTURE_NOW,FIXTURE_NOW)
    h.page(requests[0],{'ctidTraderAccountId':runtime.accounts.current.account_id,'order':[{'orderId':'9'}],'hasMore':True})
    assert runtime.database.get('native_history_job',job['id'])['state']=='INCOMPLETE_SAME_TIMESTAMP_OVERFLOW'


def test_history_error_or_disconnect_never_claims_completeness(runtime):
    h=NativeHistory(runtime.database,lambda *args,**kw:None,lambda:FIXTURE_NOW)
    job=h.start(runtime.accounts.current,FIXTURE_EPOCH,FIXTURE_NOW,FIXTURE_NOW)
    h.disconnect()
    assert runtime.database.get('native_history_job',job['id'])['state']=='INTERRUPTED'
    job=h.start(runtime.accounts.current,FIXTURE_EPOCH,FIXTURE_NOW,FIXTURE_NOW)
    h.fail(job['id'],'Native timeout')
    assert runtime.database.get('native_history_job',job['id'])['state']=='REQUEST_FAILED'


def test_history_concurrency_and_date_budgets_are_enforced(runtime):
    h=NativeHistory(runtime.database,lambda *args,**kw:None,lambda:FIXTURE_NOW)
    for _ in range(4):h.start(runtime.accounts.current,FIXTURE_EPOCH,FIXTURE_NOW,FIXTURE_NOW)
    with pytest.raises(ValueError):h.start(runtime.accounts.current,FIXTURE_EPOCH,FIXTURE_NOW,FIXTURE_NOW)
    h.disconnect()
    with pytest.raises(ValueError):h.start(runtime.accounts.current,FIXTURE_EPOCH,'2026-01-01T00:00:00Z',FIXTURE_NOW)
    assert runtime.orders.transport.submissions==[]


def test_history_requires_native_completeness_and_matching_account(runtime):
    requests=[];h=NativeHistory(runtime.database,lambda *args,**kw:requests.append(kw['context']),lambda:FIXTURE_NOW)
    job=h.start(runtime.accounts.current,FIXTURE_EPOCH,FIXTURE_NOW,FIXTURE_NOW)
    with pytest.raises(ValueError):h.page(requests[0],{'ctidTraderAccountId':'OTHER','order':[],'hasMore':False})
    with pytest.raises(ValueError):h.page(requests[0],{'ctidTraderAccountId':runtime.accounts.current.account_id,'order':[]})
    assert runtime.database.list('native_history_record')==[]
