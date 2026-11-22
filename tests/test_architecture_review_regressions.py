"""Requirements recheck uncovered legacy snapshot paths diverging from shared read adapters."""
from dataclasses import replace
from sfm_fx_new_age.contracts.tab_data import DataRequest


def test_variable_snapshot_respects_selected_source_scope(runtime):
    original=runtime.accounts.current
    assert runtime.api(2).snapshot('2.7').data['rows']
    runtime.accounts.select(replace(original,account_id='OTHER_ACCOUNT'))
    assert runtime.api(2).snapshot('2.7').data['rows']==()
    assert runtime.api(2).query('2.7',DataRequest('variables'))['rows']==()
    runtime.accounts.select(original)
    assert runtime.api(2).snapshot('2.7').data['rows']


def test_snapshot_and_read_adapter_share_configured_quote_freshness(runtime):
    runtime.catalogues.set_parameter('feed.quote_max_age_seconds',10,expected_version=0)
    runtime.clock=lambda:'2026-11-05T12:00:20Z'
    snapshot=runtime.api(2).snapshot('2.4')
    records=runtime.api(1).query('1.1',DataRequest('watchlist'))
    assert all(row['freshness']=='STALE' for row in snapshot.data['rows'])
    assert all(row['age_seconds']==20 for row in snapshot.data['rows'])
    assert all(row['state']=='STALE' for row in records['rows'])
    assert {row['symbol'] for row in snapshot.data['rows']}=={row['symbol'] for row in records['rows']}


def test_old_epoch_variables_are_stale_in_both_read_surfaces(runtime):
    from sfm_fx_new_age.contracts.analytics import VariableDefinition
    from sfm_fx_new_age.contracts.domain import Origin
    runtime.catalogues.register_variable_definition(VariableDefinition('test.epoch.variable','STRATEGY_RECIPE_HOST','boolean','boolean','SOURCE',symbol='EURUSD',timeframe='D1'))
    runtime.catalogues.register_variable('test.epoch.variable',True,'boolean',owner='STRATEGY_RECIPE_HOST',source_epoch='OLD',available_at='2026-11-05T12:00:00Z')
    runtime.market.activate_source('EURUSD','NEW',Origin.SYNTHETIC_FIXTURE.value)
    row=next(row for row in runtime.api(2).snapshot('2.7').data['rows'] if row['key']=='test.epoch.variable')
    assert row['freshness']=='STALE' and row['stale_reason']=='SOURCE_EPOCH_CHANGED'
