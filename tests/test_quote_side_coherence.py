"""One-sided native price coherence; synthetic frames, no network or broker writes."""
from decimal import Decimal
from test_connector_boundary import connected
from sfm_fx_new_age.connector.protocol import milliseconds
from sfm_fx_new_age.testing.fixtures import FIXTURE_NOW


def test_crossed_one_sided_update_invalidates_only_that_quote_and_can_recover(connected):
    r,event=connected;c=r.connector;account=r.accounts.current
    r.clock=lambda:'2026-11-05T12:00:00.003000Z'
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','bid':'110140','timestamp':milliseconds(FIXTURE_NOW)+1})
    assert r.accounts.current==account and c.native[('LIVE','123')]['connected']
    assert r.market.quote('123','EURUSD') is None
    assert 'EURUSD' in c.native[('LIVE','123')]['incoherent_quotes']
    event('ProtoOASpotEvent',{'ctidTraderAccountId':'123','symbolId':'1','ask':'110160','timestamp':milliseconds(FIXTURE_NOW)+2})
    q=r.market.quote('123','EURUSD')
    assert q.bid==Decimal('1.1014') and q.ask==Decimal('1.1016')
    assert q.bid_at!=q.ask_at and q.available_at==q.bid_at
    assert not c.native[('LIVE','123')]['incoherent_quotes']
    assert not r.database.orders()
