import pytest

from sfm_fx_new_age.contracts.registry import load_subtabs
from sfm_fx_new_age.core.dag import dirty_descendants, scanner_graph
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.enums import CommandStatus
from sfm_fx_new_age.testing.checkpoint import run_checkpoint


@pytest.mark.parametrize('definition',load_subtabs(),ids=lambda d:d.subtab_id)
def test_every_subtab_has_scoped_immutable_snapshot(runtime,definition):
    api=runtime.api(definition.main_tab)
    snapshot=api.snapshot(definition.subtab_id)
    assert snapshot.subtab_id==definition.subtab_id
    assert snapshot.status
    with pytest.raises(TypeError): snapshot.data['symbol']='mutated'
    bad='4.1' if definition.main_tab!=4 else '1.1'
    with pytest.raises(ValueError): api.snapshot(bad)
    with pytest.raises(ValueError): api.command(bad,'ISSUE',{})


def test_normal_startup_never_seeds_fixture_values():
    r=ApplicationRuntime()
    try:
        assert r.database.list('bar')==[]
        assert r.database.list('quote')==[]
        assert r.signals.all()==[]
        assert r.accounts.current is None
        assert r.api(4).snapshot('4.1').data['rows']==()
    finally:r.close()


def test_shared_selection_changes_all_tab_read_contexts(runtime):
    assert runtime.api(1).command('1.1','SELECT_PAIR',{'symbol':'USDJPY'}).status is CommandStatus.ACCEPTED
    for tab in runtime.tabs:
        assert runtime.api(tab.tab_id).snapshot(tab.subtabs[0].definition.subtab_id).data['symbol']=='USDJPY'


def test_scanner_declared_graph_is_acyclic_and_dirty_propagates():
    graph=scanner_graph()
    assert len(graph)==44
    assert sum(map(len,graph.values()))==130
    descendants=dirty_descendants('CTRADER_SOURCE')
    assert 'INGRESS_NORMALIZER' in descendants
    assert descendants.index('CTRADER_SOURCE')<descendants.index('INGRESS_NORMALIZER')


def test_closed_loop_checkpoint():
    result=run_checkpoint()
    assert result['ok'] and result['restart_reconciled']
    assert result['network_calls']==0 and result['real_broker_orders']==0


def test_consumer_switch_does_not_disable_reconciliation(runtime):
    api=runtime.api(2)
    assert api.command('2.1','SET_CONSUMER_SWITCH',{'consumer_id':'BROKER_RECONCILER','enabled':False}).status is CommandStatus.REJECTED
    assert api.command('2.1','SET_CONSUMER_SWITCH',{'consumer_id':'analysis.scanner','enabled':False}).status is CommandStatus.ACCEPTED
