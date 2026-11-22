"""83 source→Tab4 pipelines. Synthetic tests are not connected-market proof."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from decimal import Decimal as D
from datetime import timedelta
import pytest
from sfm_fx_new_age.contracts.public_strategies import METHODS,BY_KEY
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.domain import Bar,Origin,instant
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW,stamp
from test_public_strategies import seed,enable,bars,EPOCH


def rows(r,frame='H4'):
    return thaw(r.api(4).query('4.1',DataRequest('strategy_signals',symbol='EURUSD',timeframe=frame,limit=5000)))['rows']


def test_exact_83_method_policies_and_no_missing_or_duplicate_pipeline():
    from sfm_fx_new_age.contracts.strategy_signals import POLICIES
    assert set(POLICIES)=={m.key for m in METHODS} and len(POLICIES)==83
    assert all(p.description and p.version==1 for p in POLICIES.values())


@pytest.mark.parametrize('method',METHODS,ids=lambda m:m.key)
def test_every_method_switch_reaches_tab4_with_truthful_status_and_no_orders(method):
    r=seed()
    try:
        before=rows(r);assert len(before)==83 and all(x['state']=='OFF' for x in before)
        enable(r,method.key)
        row=next(x for x in rows(r) if x['strategy_id']==method.key)
        assert row['enabled'] and row['state']!='OFF'
        assert row['policy_id'] and row['recipe_id']==method.recipe_id
        assert row['origin']=='SYNTHETIC_FIXTURE'
        assert row['state'] in {'NO_SETUP','WARMUP','DATA_UNAVAILABLE','WAITING','SIGNAL','BLOCKED','STALE','INVALIDATED','EXPIRED'}
        assert not r.orders.transport.submissions and not r.database.orders()
        enable(r,method.key,False)
        assert next(x for x in rows(r) if x['strategy_id']==method.key)['state']=='OFF'
    finally:r.close()


def test_engulfing_actual_algorithm_generates_source_bound_signal_without_binding():
    shape=[(1.1,1.101,1.099,1.1)]*60+[(1.1,1.101,1.09,1.095),(1.094,1.103,1.093,1.102)]
    r=seed(rows=bars(shape))
    try:
        enable(r,'engulfing');row=next(x for x in rows(r) if x['strategy_id']=='engulfing')
        assert row['opportunity_id'].startswith('strategy:') and row['side']=='BUY'
        assert D(row['entry'])<D('1.102') and D(row['stop'])<D(row['entry'])
        assert row['trigger']['root_ids'] and row['projection_fingerprint']
        assert row['source_epoch']==EPOCH and row['origin']=='SYNTHETIC_FIXTURE'
        assert row['state']=='STALE' and 'FRESH_TWO_SIDED_QUOTE' in row['blockers']
        assert not any(x.get('market_candidate_id')==row['opportunity_id'] for x in r.signals.all())
        assert not r.orders.transport.submissions
    finally:r.close()
