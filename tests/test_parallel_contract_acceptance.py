"""Shared release gates for independently implemented presentation lanes."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dataclasses import replace
import importlib,sys
import pytest

from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.tab_data import DataRequest,DATASETS
from sfm_fx_new_age.contracts.domain import Origin
from sfm_fx_new_age.services.orders import FixtureBroker
from sfm_fx_new_age.testing.fixtures import populate_fixture,FIXTURE_NOW


def test_four_tab_threads_query_every_dataset_without_mutation_or_service_handles(runtime):
    runtime.pump()
    apis=[runtime.api(i) for i in range(1,5)]
    before=runtime.database.connection.total_changes
    def run(api):
        visited=set()
        for _ in range(10):
            for definition in api.definitions:
                for dataset in DATASETS[definition.subtab_id]:
                    result=api.query(definition.subtab_id,DataRequest(dataset,limit=5))
                    assert result['dataset']==dataset and len(result['rows'])<=5
                    assert result['scope_id']==runtime.market.scope_id
                    with pytest.raises(TypeError):result['rows']=()
                visited.add(definition.subtab_id)
        return visited
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(run,apis))
    assert set.union(*results)==set(DATASETS)
    assert [len(v) for v in results]==[10,10,13,9]
    assert runtime.database.connection.total_changes==before
    assert runtime.orders.transport.submissions==[]


def test_production_headless_loader_discovers_lane_owned_backend_file(tmp_path,monkeypatch):
    import sfm_fx_new_age.tabs.tab3 as package
    backend=tmp_path/'backend.py'
    backend.write_text('''from sfm_fx_new_age.contracts.extensions import AnalyticalResult

def install(api):
    api.register_producer('SMC_STRUCTURE',lambda inputs,deps:AnalyticalResult('EVALUATED',{'proof':'SYNTHETIC_DISCOVERED_FILE'}),
        method_version='SYNTHETIC_DISCOVERED_V1',source_ref='SYNTHETIC_FILE_TEST_ONLY',trigger_frames=('D1',))
''')
    monkeypatch.setattr(package,'__path__',[str(tmp_path)])
    importlib.invalidate_caches()
    name='sfm_fx_new_age.tabs.tab3.backend'
    # The shipped backend now exists and may already be imported. This test
    # intentionally substitutes a private module through the package path.
    monkeypatch.delitem(sys.modules,name,raising=False)
    try:
        r=ApplicationRuntime(clock=lambda:FIXTURE_NOW,transport=FixtureBroker())
        try:
            populate_fixture(r);r.pump()
            assert r.analytics.snapshot('EURUSD')['outputs']['SMC_STRUCTURE']['proof']=='SYNTHETIC_DISCOVERED_FILE'
            assert r.orders.transport.submissions==[]
        finally:r.close()
    finally:
        sys.modules.pop(name,None)
        if hasattr(package,'backend'):monkeypatch.delattr(package,'backend')


def test_current_only_datasets_refuse_pseudo_historical_queries(runtime):
    with pytest.raises(ValueError,match='current-state only'):
        runtime.api(4).query('4.6',DataRequest('positions',as_of='2026-11-04T12:00:00Z'))
    historical=runtime.api(1).query('1.3',DataRequest('bars',as_of='2026-11-04T12:00:00Z'))
    assert all(v['available_at']<='2026-11-04T12:00:00Z' for v in historical['rows'])


def test_same_content_in_another_source_cannot_continue_a_previous_page(runtime):
    api=runtime.api(1);first=api.query('1.1',DataRequest('watchlist',limit=2))
    account=runtime.accounts.current
    runtime.accounts.select(replace(account,account_id='NEW_SCOPE'))
    with pytest.raises(ValueError,match='Dataset changed'):
        api.query('1.1',DataRequest('watchlist',limit=2,cursor=2,expected_hash=first['data_hash']))


def test_disabled_display_does_not_leak_forming_bar_extras(runtime):
    data=runtime.api(1).query('1.5',DataRequest('bars'))
    assert data['status']=='DISABLED' and data['rows']==()
    assert 'forming_bars' not in data


def test_shared_history_extras_obey_the_requested_response_budget(runtime):
    runtime.signals.cancel('FIXTURE-SIGNAL-1')
    q=runtime.api(3).query('3.13',DataRequest('signal_history',limit=1))
    assert len(q['rows'])<=1 and len(q['state_history'])==1
    assert q['state_history_total']>=2 and q['state_history_truncated'] is True
