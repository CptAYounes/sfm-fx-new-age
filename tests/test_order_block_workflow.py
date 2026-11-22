"""Real shipped research algorithm on labelled synthetic bars; no broker network."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import pytest
from sfm_fx_new_age.contracts.domain import Bar,FRAMES,Origin,instant,record
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.testing.fixtures import fixture_runtime,FIXTURE_NOW,stamp
from sfm_fx_new_age.tabs.tab3.order_blocks import RECIPE_ID,METHOD,detect_structure

EPOCH='SYNTHETIC-ORDER-BLOCK-INPUTS-V1'
D=Decimal


def pattern(frame='H4',side='BUY',end=FIXTURE_NOW):
    duration={'W1':timedelta(weeks=1),'D1':timedelta(days=1),'H4':timedelta(hours=4),'H1':timedelta(hours=1)}[frame]
    rows=[('1.1000','1.1010','1.0990','1.1000')]*15+[
        ('1.1000','1.1050','1.0990','1.1010'),('1.1000','1.1015','1.0990','1.1000'),
        ('1.1000','1.1010','1.0990','1.1000'),('1.1000','1.1010','1.0985','1.0990'),
        ('1.0990','1.1090','1.0990','1.1080')]
    result=[]
    for i,values in enumerate(rows):
        o,h,l,c=map(D,values)
        if side=='SELL':o,h,l,c=D('2.2')-o,D('2.2')-l,D('2.2')-h,D('2.2')-c
        closed=instant(end)-duration*(len(rows)-i-1)
        result.append(Bar('EURUSD',frame,stamp(closed-duration),stamp(closed),stamp(closed),o,h,l,c,EPOCH,Origin.SYNTHETIC_FIXTURE))
    return result


def seeded(frame='H4',side='BUY',path=':memory:'):
    r=fixture_runtime(path)
    r.market.activate_source('EURUSD',EPOCH,Origin.SYNTHETIC_FIXTURE.value)
    for bar in pattern(frame,side):r.market.ingest(bar)
    r.pump();return r


def enable(r,value=True):
    result=r.api(3).command('3.1','ENABLE_RECIPE',{'recipe_id':RECIPE_ID,'version':1,'enabled':value})
    assert result.status.value=='ACCEPTED',result
    r.pump()


def levels(r,as_of=None):return thaw(r.api(1).query('1.6',DataRequest('chart',symbol='EURUSD',timeframe='H4',as_of=as_of)))['levels']


@pytest.mark.parametrize('frame',FRAMES)
@pytest.mark.parametrize('side',['BUY','SELL'])
def test_actual_producer_requires_switch_then_projects_confirmed_zone(frame,side):
    r=seeded(frame,side)
    try:
        assert not levels(r)
        assert RECIPE_ID in r.analytics.composers and 'ORDER_BLOCK' in r.analytics.scheduler.handlers
        enable(r)
        found=levels(r);assert len(found)==1
        level=found[0]
        assert level['kind']=='ORDER_BLOCK' and level['state']=='CONFIRMED' and level['side']==side
        assert level['lineage']['timeframe']==frame and level['lineage']['source_epoch']==EPOCH
        assert level['lineage']['method_version']==METHOD and level['lineage']['origin']=='SYNTHETIC_FIXTURE'
        assert not r.research.query('market_candidate',scope=r.market.scope_id,epoch=EPOCH,symbol='EURUSD',as_of=FIXTURE_NOW)
        assert not r.orders.transport.submissions
        runs=r.analytics.scheduler.runs['ORDER_BLOCK'];r.analytics.refresh('EURUSD')
        assert r.analytics.scheduler.runs['ORDER_BLOCK']==runs and levels(r)==found
        enable(r,False);assert not levels(r)
        # Historical data remains an immutable record, not current switch state.
        assert levels(r,FIXTURE_NOW)==found
        enable(r);assert levels(r)==found
    finally:r.close()


def test_confirmation_causal_and_wick_break_not_enough():
    from sfm_fx_new_age.services.scanner import confirmed_swings
    bars=[record(b) for b in pattern()]
    profile={'lookback':14,'body_fraction':'0.60','range_multiple':'1.00'}
    assert not detect_structure(bars[:-1],confirmed_swings(bars[:-1]),profile)
    assert len(detect_structure(bars,confirmed_swings(bars),profile))==1
    bars[-1]['close']='1.1040'
    assert not detect_structure(bars,confirmed_swings(bars),profile)


def test_touch_invalidation_revision_history_and_epoch_isolation():
    r=seeded();now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        enable(r);original=levels(r)[0]
        end=instant(FIXTURE_NOW)+timedelta(hours=4);now[0]=stamp(end)
        r.market.ingest(Bar('EURUSD','H4',FIXTURE_NOW,now[0],now[0],D('1.108'),D('1.109'),D('1.1005'),D('1.107'),EPOCH,Origin.SYNTHETIC_FIXTURE))
        r.pump();touched=levels(r)[0];assert touched['state']=='TOUCHED' and touched['revision']==2
        assert levels(r,FIXTURE_NOW)==[original]
        end+=timedelta(hours=4);old=now[0];now[0]=stamp(end)
        r.market.ingest(Bar('EURUSD','H4',old,now[0],now[0],D('1.107'),D('1.108'),D('1.095'),D('1.097'),EPOCH,Origin.SYNTHETIC_FIXTURE))
        r.pump();invalid=levels(r)[0];assert invalid['state']=='INVALIDATED' and invalid['revision']==3
        assert levels(r,FIXTURE_NOW)==[original]
        r.market.activate_source('EURUSD','ANOTHER-EPOCH','SYNTHETIC_FIXTURE');r.pump();assert not levels(r)
    finally:r.close()


def test_recipe_switch_survives_restart_but_does_not_restore_authentication(tmp_path):
    path=tmp_path/'state.sqlite3';r=seeded(path=path);enable(r);before=levels(r);r.close()
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    r=ApplicationRuntime(path,clock=lambda:FIXTURE_NOW)
    try:
        assert r.database.get('recipe_state',RECIPE_ID)['enabled']
        assert r.accounts.current is None and not r.connector.workers
        assert not levels(r)
    finally:r.close()


def test_tab3_real_checkbox_and_pending_cancel_dialog_are_reachable():
    from PySide6.QtWidgets import QApplication,QMessageBox
    from sfm_fx_new_age.app import create_main_window
    app=QApplication.instance() or QApplication([]);r=seeded();w=create_main_window(r);w.show();w.core_timer.stop();w.poll_timer.stop()
    def drain():
        for _ in range(4):r.pump();app.processEvents()
    try:
        r.api(3).navigate('3.1',r.api(3).inspect(symbol='EURUSD',timeframe='H4'));drain();p=w._active_panel()
        assert not p.strategy_enabled.isChecked();p.strategy_enabled.click();drain();assert levels(r)
        p.strategy_enabled.click();drain();assert not levels(r)
        # Separate labelled fixture signal: OB projection alone must not authorise Issue.

        r.market.activate_source('EURUSD','SYNTHETIC-FIXTURE-EPOCH-1','SYNTHETIC_FIXTURE');r.pump()
        assert r.api(4).command('4.1','ISSUE',{'signal_id':'FIXTURE-SIGNAL-1','revision':1,'user_initiated':True,'acknowledge_research':True}).status.value=='ACCEPTED'
        order=r.database.orders()[0]
        r.api(4).navigate('4.3',r.api(4).inspect(symbol='EURUSD',timeframe='H4',object_kind='order',object_id=order['id']));drain();p=w._active_panel()
        assert p.cancel_pending.isEnabled();p.cancel_pending.click();drain();box=p.findChild(QMessageBox,'confirmPendingCancellation')
        assert box and box.defaultButton()==box.button(QMessageBox.No)
        box.button(QMessageBox.No).click();drain();assert r.orders.transport.cancellations==0
        p.cancel_pending.click();drain();box=p.findChild(QMessageBox,'confirmPendingCancellation');box.button(QMessageBox.Yes).click();drain()
        assert r.database.order(order['id'])['state']=='CANCELED' and r.orders.transport.cancellations==1
        assert not p.cancel_pending.isEnabled()
    finally:w.close();r.close();app.processEvents()


def test_cancel_confirmation_hash_rejects_stale_record_and_scope(runtime):
    from sfm_fx_new_age.contracts.analytics import digest
    assert runtime.api(4).command('4.1','ISSUE',{'signal_id':'FIXTURE-SIGNAL-1','revision':1,'user_initiated':True,'acknowledge_research':True}).status.value=='ACCEPTED'
    order=runtime.database.orders()[0]
    for payload in ({'expected_order_hash':'not-current'},{'expected_scope_id':'OTHER'}):
        result=runtime.api(4).command('4.3','SEPARATE_BROKER_CANCEL',{'order_id':order['id'],'user_initiated':True,**payload})
        assert result.status.value=='REJECTED' and runtime.orders.transport.cancellations==0
    result=runtime.api(4).command('4.3','SEPARATE_BROKER_CANCEL',{'order_id':order['id'],'user_initiated':True,'expected_order_hash':digest(order),'expected_scope_id':order['scope_id']})
    assert result.status.value=='ACCEPTED' and runtime.orders.transport.cancellations==1


def test_corrected_away_break_invalidates_current_zone_without_rewriting_history():
    r=seeded();now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        enable(r);original=levels(r)[0];last=pattern()[-1]
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(minutes=1))
        r.market.ingest(replace(last,close=D('1.1040'),revision=2,available_at=now[0]));r.pump()
        assert levels(r)[0]['state']=='INVALIDATED' and levels(r)[0]['revision']==2
        assert levels(r,FIXTURE_NOW)==[original]
        r.analytics.refresh('EURUSD');assert levels(r)[0]['revision']==2
    finally:r.close()


def test_no_opposite_colour_or_weak_displacement_cannot_create_order_block():
    from sfm_fx_new_age.services.scanner import confirmed_swings
    rows=[record(b) for b in pattern()]
    profile={'lookback':14,'body_fraction':'0.60','range_multiple':'1.00'}
    rows[-1]['high']='1.1500' # Body/range too small, even though close breaks.
    assert not detect_structure(rows,confirmed_swings(rows),profile)
    r=seeded();now=[FIXTURE_NOW];r.clock=lambda:now[0];r.analytics.clock=lambda:now[0]
    try:
        now[0]=stamp(instant(FIXTURE_NOW)+timedelta(minutes=1))
        source=pattern()[-2]
        r.market.ingest(replace(source,close=D('1.1005'),revision=2,available_at=now[0]));r.pump()
        enable(r);assert not levels(r)
    finally:r.close()


def test_pending_cancel_dialog_rejects_selection_changed_during_confirmation(runtime):
    from PySide6.QtWidgets import QApplication,QMessageBox
    from sfm_fx_new_age.app import create_main_window
    app=QApplication.instance() or QApplication([]);w=create_main_window(runtime);w.show();w.core_timer.stop();w.poll_timer.stop()
    def drain():
        for _ in range(4):runtime.pump();app.processEvents()
    try:
        runtime.api(4).command('4.1','ISSUE',{'signal_id':'FIXTURE-SIGNAL-1','revision':1,'user_initiated':True,'acknowledge_research':True})
        order=runtime.database.orders()[0]
        runtime.api(4).navigate('4.3',runtime.api(4).inspect(symbol='EURUSD',object_kind='order',object_id=order['id']));drain();p=w._active_panel()
        p.cancel_pending.click();drain();box=p.findChild(QMessageBox,'confirmPendingCancellation');assert box
        runtime.database.update_order(order['id'],{'detail':'RECONCILED_DIFFERENT_CONTENT'})
        box.button(QMessageBox.Yes).click();drain()
        assert runtime.orders.transport.cancellations==0 and 'refused' in p.feedback.text().lower()
    finally:w.close();app.processEvents()


def test_warmup_and_disabled_scanner_do_not_reuse_current_order_blocks():
    r=seeded()
    try:
        enable(r);original=levels(r)
        r.api(2).command('2.1','SET_CONSUMER_SWITCH',{'consumer_id':'analysis.scanner','enabled':False});r.pump()
        assert not levels(r) and levels(r,FIXTURE_NOW)==original
        r.api(2).command('2.1','SET_CONSUMER_SWITCH',{'consumer_id':'analysis.scanner','enabled':True});r.pump()
        assert levels(r)==original
        r.market.activate_source('EURUSD','EMPTY_SOURCE','SYNTHETIC_FIXTURE');r.pump()
        assert not levels(r)
    finally:r.close()
