"""Synthetic engineering controls for genuine-read corroboration; no networking."""
from dataclasses import replace
import pytest
from test_connector_boundary import connected
from sfm_fx_new_age.contracts.domain import record
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.connector.protocol import milliseconds


def captured_job(r,*,price_delta=0,extra=False):
    history=r.connector.quote_history
    identity=history.start('EURUSD','2026-11-05T10:00:00Z','2026-11-05T11:00:00Z')
    request=next(q for q in r.connector.requests.values() if (q.get('context') or {}).get('native_quote_history')==identity)
    rows=[dict(timestamp=milliseconds('2026-11-05T10:45:00Z'),tick=110100+price_delta),dict(timestamp=-1800000,tick=10)]
    if extra:rows.append(dict(timestamp=0,tick=0))
    history.page(request,dict(ctidTraderAccountId=r.accounts.current.account_id,hasMore=False,tickData=rows))
    assert r.database.get('native_quote_history_job',identity)['state']=='COMPLETE'
    return identity


def first_publication(r):
    job=captured_job(r);evidence=r.connector.quote_history.tpo_evidence(job,provider_id='CTRADER_CONNECTED_BID_TPO_V1',available_at=r.clock())
    store=r.analytics.supplemental;store.register_provider(evidence.provider_id,kinds=[evidence.kind],origin=evidence.origin)
    store.accept(evidence);store.admissions[evidence.provider_id]={digest(record(evidence))}
    return evidence


def advance(r,now='2026-11-05T12:01:00Z'):
    r.clock=lambda:now;r.analytics.supplemental.clock=r.clock


def test_reobserved_tpo_preserves_original_bytes_and_expiry(connected):
    r,_=connected;first=first_publication(r);advance(r)
    fresh=captured_job(r);second=r.connector.quote_history.tpo_evidence(fresh,provider_id=first.provider_id,available_at=r.clock())
    assert record(second)==record(first)
    assert second.available_at==first.available_at and second.valid_until==first.valid_until
    assert r.analytics.supplemental.accept(second)==0
    corroborations=r.database.list('native_quote_history_corroboration')
    assert len(corroborations)==1 and corroborations[0]['job_id']==fresh
    assert corroborations[0]['original_evidence_hash']==digest(record(first))


@pytest.mark.parametrize('change',['price','multiplicity'])
def test_changed_closed_interval_is_not_silently_reclassified_or_overwritten(connected,change):
    r,_=connected;first=first_publication(r);advance(r)
    fresh=captured_job(r,price_delta=1 if change=='price' else 0,extra=change=='multiplicity')
    with pytest.raises(ValueError,match='corroboration'):
        r.connector.quote_history.tpo_evidence(fresh,provider_id=first.provider_id,available_at=r.clock())
    assert len(r.database.list('supplemental_evidence'))==1
    assert record(first)==r.database.list('supplemental_evidence')[0]
    assert not r.database.list('native_quote_history_corroboration')


def test_expired_tpo_cannot_be_made_fresh_by_reobserving_old_window(connected):
    r,_=connected;first=first_publication(r);advance(r,'2026-11-06T01:00:00Z')
    fresh=captured_job(r)
    with pytest.raises(ValueError,match='expired'):
        r.connector.quote_history.tpo_evidence(fresh,provider_id=first.provider_id,available_at=r.clock())
    assert not r.analytics.supplemental.snapshot('EURUSD',r.clock())


def test_stored_tpo_is_not_returned_without_a_new_complete_capture(connected):
    r,_=connected;first=first_publication(r);advance(r)
    identity=r.connector.quote_history.start('EURUSD',first.window_start,first.window_end)
    with pytest.raises(ValueError,match='exhausted'):
        r.connector.quote_history.tpo_evidence(identity,provider_id=first.provider_id,available_at=r.clock())
    assert not r.database.list('native_quote_history_corroboration')


def test_corroboration_does_not_restore_ephemeral_provider_authority(connected):
    r,_=connected;first=first_publication(r);advance(r)
    store=r.analytics.supplemental;store.providers.clear();store.admissions.clear()
    fresh=captured_job(r);same=r.connector.quote_history.tpo_evidence(fresh,provider_id=first.provider_id,available_at=r.clock())
    assert record(same)==record(first)
    assert not store.providers and not store.snapshot('EURUSD',r.clock())


def test_different_provider_does_not_borrow_old_publication(connected):
    r,_=connected;first=first_publication(r);advance(r)
    fresh=captured_job(r);new=r.connector.quote_history.tpo_evidence(fresh,provider_id='DIFFERENT_CONTROL_PROVIDER',available_at=r.clock())
    assert new.provider_id!=first.provider_id and new.available_at==r.clock()
    assert not r.database.list('native_quote_history_corroboration')
