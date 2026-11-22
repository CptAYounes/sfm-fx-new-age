"""Nonmarket upgrade/restart controls; old immutable recipe bytes stay intact."""
import json
import pytest
from sfm_fx_new_age.contracts.analytics import Recipe
from sfm_fx_new_age.contracts.domain import record
from sfm_fx_new_age.contracts.public_strategies import BY_KEY, METHODS
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.services.research import ResearchStore
from sfm_fx_new_age.storage.database import Database


@pytest.mark.parametrize('saved', [None, False, True, 'MALFORMED', 'UNKNOWN_VERSION'])
def test_dom_upgrade_preserves_explicit_switch_history_and_restart(tmp_path, saved):
    path = tmp_path / 'labelled-metadata-only.sqlite3'
    definition = BY_KEY['dom_imbalance']
    assert definition.version == 2 and definition.method_version == 'PUBLIC_FOREX_DOM_IMBALANCE_V2'
    assert definition.recipe_id == 'public.forex.dom_imbalance.v1'
    legacy = Recipe(definition.recipe_id, 1, 'LABELLED_LEGACY_RECIPE_METADATA',
        ('FEATURE_CACHE',), 'fixture://nonmarket-recipe-metadata-not-live-observations', '0'*64)
    old_key = json.dumps(['GLOBAL_RESEARCH', 'GLOBAL_RESEARCH', legacy.recipe_id, 1], separators=(',', ':'))
    db = Database(path)
    try:
        ResearchStore(db, lambda *args: None).publish(legacy)
        state = None
        if saved is not None:
            state = dict(recipe_id=legacy.recipe_id, version=7 if saved == 'UNKNOWN_VERSION' else 1,
                enabled='NOT_A_BOOLEAN' if saved == 'MALFORMED' else saved is True)
            db.put('recipe_state', legacy.recipe_id, state)
        before = db.get('recipe', old_key)
    finally:
        db.close()
    for restart in range(2):
        r = ApplicationRuntime(path)
        try:
            assert r.database.get('recipe', old_key) == before == record(legacy)
            history = [v for v in r.research.recipes(history=True) if v['recipe_id'] == legacy.recipe_id]
            current = [v for v in r.research.recipes() if v['recipe_id'] == legacy.recipe_id]
            assert sorted(v['version'] for v in history) == [1, 2]
            assert len(current) == 1 and current[0]['version'] == 2
            actual = r.database.get('recipe_state', legacy.recipe_id)
            if saved is False or saved is True:
                assert actual == dict(state, version=2)
                assert r.analytics.projections.enabled(definition) is saved
            else:
                assert actual == state
                assert not r.analytics.projections.enabled(definition)
            assert len(METHODS) == len(r.analytics.projections.methods) == 83
            assert not r.connector.workers and not r.database.orders()
            result = r.api(3).command('3.1', 'ENABLE_RECIPE',
                dict(recipe_id=legacy.recipe_id, version=1, enabled=True))
            assert result.status.value == 'REJECTED'
            assert r.database.get('recipe_state', legacy.recipe_id) == actual
        finally:
            r.close()
