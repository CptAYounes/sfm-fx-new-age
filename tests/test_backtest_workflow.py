"""Explicit NONMARKET controls; never proof of profitable or executable strategy."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
import pytest
from sfm_fx_new_age.contracts.domain import Bar,Origin
from sfm_fx_new_age.contracts.models import thaw


def dataset(r,identity='NONMARKET-STUDY',n=42):
    start=datetime(2026,1,1,tzinfo=timezone.utc);bars=[]
    for i in range(n):
        t=start+timedelta(hours=i);o=D('1.1000') if i%2==0 else D('1.0990');c=D('1.0995') if i%2==0 else D('1.1010')
        bars.append(Bar('EURUSD','H1',t.isoformat(),(t+timedelta(hours=1)).isoformat(),(t+timedelta(hours=1)).isoformat(),o,max(o,c)+D('.0001'),min(o,c)-D('.0001'),c,'NONMARKET',Origin.SYNTHETIC_FIXTURE,scope_id='NONMARKET'))
    r.replay.import_dataset(identity,tuple(bars),source_ref='NONMARKET engineering only')
    return bars


def request(**kwargs):
    from sfm_fx_new_age.contracts.backtest import StudyRequest
    return StudyRequest(**(dict(study_id='NONMARKET-RUN',dataset_id='NONMARKET-STUDY',symbol='EURUSD',timeframe='H1',method_id='engulfing')|kwargs))


def test_actual_marker_study_persists_no_broker_authority(runtime):
    dataset(runtime);before=runtime.database.orders()
    result=thaw(runtime.api(3).run_research_study(request(train=16,test=8,holding_bars=2)))
    assert result['origin']=='HISTORICAL_REPLAY' and result['original_origin']=='SYNTHETIC_FIXTURE'
    assert result['execution_allowed'] is False and result['status']=='COMPLETE'
    assert result['backtest']['trades'] and result['walk_forward']['folds']
    assert runtime.database.get('research_study','NONMARKET-RUN')==result
    assert runtime.database.orders()==before and not runtime.orders.transport.submissions
    assert runtime.api(3).research_study('NONMARKET-RUN')['result_hash']==result['result_hash']


def test_study_identity_is_immutable_and_idempotent(runtime):
    dataset(runtime);a=runtime.api(3).run_research_study(request(train=16,test=8))
    assert runtime.api(3).run_research_study(request(train=16,test=8))==a
    with pytest.raises(ValueError,match='identity'):
        runtime.api(3).run_research_study(request(train=17,test=8))


@pytest.mark.parametrize('tab',[1,2,4])
def test_research_write_capability_is_research_only(runtime,tab):
    dataset(runtime)
    with pytest.raises(ValueError):runtime.api(tab).run_research_study(request())
    assert not runtime.database.list('research_study')


@pytest.mark.parametrize('kwargs',[{'train':True},{'test':0},{'holding_bars':101},{'stop_bps':('NaN',)},{'reward_r':('0',)},{'method_id':'footprint_delta'},{'stop_bps':tuple(str(i+1) for i in range(17))}])
def test_request_is_typed_bounded_and_does_not_imply_other_profiles(kwargs):
    from sfm_fx_new_age.contracts.backtest import StudyRequest
    with pytest.raises(ValueError):StudyRequest(**(dict(study_id='X',dataset_id='Y',symbol='EURUSD',timeframe='H1',method_id='engulfing')|kwargs))


def test_training_selection_never_observes_test_outcomes(runtime):
    bars=dataset(runtime,n=50);a=thaw(runtime.api(3).run_research_study(request(train=16,test=8)))
    from dataclasses import replace
    altered=tuple(b if i<24 else replace(b,open=b.open*2,high=b.high*2,low=b.low*2,close=b.close*2) for i,b in enumerate(bars))
    runtime.replay.import_dataset('CHANGED-FUTURE',altered,source_ref='NONMARKET changed future only')
    b=thaw(runtime.api(3).run_research_study(request(dataset_id='CHANGED-FUTURE',study_id='CHANGED-RUN',train=16,test=8)))
    assert a['walk_forward']['folds'][0]['training']==b['walk_forward']['folds'][0]['training']
    assert a['walk_forward']['folds'][0]['selected_parameters']==b['walk_forward']['folds'][0]['selected_parameters']


def test_ambiguity_is_unknown_not_invented_intrabar_profit(runtime):
    from dataclasses import replace
    bars=dataset(runtime)
    wide=tuple(replace(b,high=D('1.2'),low=D('1.0')) for b in bars)
    runtime.replay.import_dataset('WIDE',wide,source_ref='NONMARKET ambiguous OHLC')
    r=thaw(runtime.api(3).run_research_study(request(dataset_id='WIDE',study_id='WIDE-RUN',train=16,test=8)))
    assert r['backtest']['summary']['ambiguous']>0
    assert all(t['r_multiple'] is None for t in r['backtest']['trades'] if t['outcome']=='AMBIGUOUS_INTRABAR')


def test_no_future_open_is_used_before_original_availability(runtime):
    from dataclasses import replace
    bars=dataset(runtime);late=tuple(replace(b,available_at='2026-10-01T00:00:00Z') for b in bars)
    runtime.replay.import_dataset('LATE',late,source_ref='NONMARKET late batch')
    r=thaw(runtime.api(3).run_research_study(request(dataset_id='LATE',study_id='LATE-RUN',train=16,test=8)))
    assert not r['backtest']['trades'] and r['backtest']['summary']['signals_without_causal_entry']>0


def test_saved_study_is_queryable_through_research_dataset(runtime):
    from sfm_fx_new_age.contracts.tab_data import DataRequest
    dataset(runtime);runtime.api(3).run_research_study(request(train=16,test=8))
    d=runtime.api(3).query('3.12',DataRequest('research_studies'))
    assert d['total']==1 and d['rows'][0]['study_id']=='NONMARKET-RUN'
    assert 'backtest' not in d['rows'][0] # Bounded list metadata, explicit detail read.


def test_historical_close_assumption_is_explicit_and_never_changes_observations(runtime):
    from dataclasses import replace
    bars=dataset(runtime);late=tuple(replace(b,available_at='2026-10-01T00:00:00Z') for b in bars)
    runtime.replay.import_dataset('MODEL',late,source_ref='NONMARKET historical simulation')
    before=runtime.database.get('replay_dataset','MODEL')
    r=thaw(runtime.api(3).run_research_study(request(dataset_id='MODEL',study_id='MODEL-RUN',train=16,test=8,information_clock='HISTORICAL_CLOSE_ASSUMPTION')))
    assert r['backtest']['trades'] and r['walk_forward']['folds']
    assert r['original_availability_preserved'] is True and r['as_observed_execution_proof'] is False
    assert r['information_clock']=='HISTORICAL_CLOSE_ASSUMPTION'
    assert runtime.database.get('replay_dataset','MODEL')==before
    assert r['source_observation_hash']==before['dataset_hash']!=r['model_input_hash']


def test_report_widget_runs_and_reopens_persisted_result(runtime):
    from PySide6.QtWidgets import QApplication,QDialog
    from sfm_fx_new_age.app import create_main_window
    app=QApplication.instance() or QApplication([]);dataset(runtime)
    runtime.replay.create('NONMARKET-UI-RUN','NONMARKET-STUDY',{})
    window=create_main_window(runtime);window.resize(1000,720);window.show()
    try:
        context=runtime.api(3).inspect(symbol='EURUSD',timeframe='H1')
        runtime.api(3).navigate('3.12',context)
        for _ in range(3):runtime.pump();app.processEvents()
        panel=window._active_panel();panel.dataset.setCurrentIndex(panel.dataset.findData('replay_runs'));panel.refresh()
        panel.table.selectRow(next(i for i,r in enumerate(panel._rows) if r['run_id']=='NONMARKET-UI-RUN'))
        panel.study.method.setCurrentIndex(panel.study.method.findData('engulfing'));panel.study.train.setValue(16);panel.study.test.setValue(8)
        panel.study.run.click();app.processEvents()
        assert panel.study.last_result and panel.study.report.isEnabled()
        dialog=panel.findChild(QDialog,'researchStudyReport');assert dialog and dialog.isVisible()
        assert panel.study.run.geometry().right()<=panel.study.width()
        dialog.close();app.processEvents()
        panel.dataset.setCurrentIndex(panel.dataset.findData('research_studies'));panel.refresh();panel.table.selectRow(0)
        assert panel.study.last_result['study_id']==panel._rows[0]['study_id']
        assert not runtime.orders.transport.submissions
    finally:window.close();app.processEvents()


def test_result_integrity_is_checked_before_reuse(runtime):
    dataset(runtime);r=thaw(runtime.api(3).run_research_study(request(train=16,test=8)))
    r['markers']+=1;runtime.database.put('research_study',r['study_id'],r)
    with pytest.raises(ValueError,match='hash mismatch'):runtime.api(3).research_study(r['study_id'])
    with pytest.raises(ValueError,match='hash mismatch'):runtime.api(3).run_research_study(request(train=16,test=8))


def test_walk_forward_has_disjoint_test_windows_and_no_training_payoffs_from_future(runtime):
    dataset(runtime,n=60);r=thaw(runtime.api(3).run_research_study(request(train=16,test=8,holding_bars=3)))
    from sfm_fx_new_age.contracts.domain import instant
    windows=r['walk_forward']['folds']
    assert all(instant(a['window']['test_through'])<instant(b['window']['test_from']) for a,b in zip(windows,windows[1:]))
    for fold in windows:
        assert instant(fold['window']['train_through'])<instant(fold['window']['test_from'])
        assert all(t['exit_at'] is None or instant(t['exit_at'])<=instant(fold['window']['test_through']) for t in fold['test']['trades'])
        assert all(t['r_multiple'] is None for t in fold['test']['trades'] if t['outcome']=='OPEN_AT_PERIOD_END')


def test_result_and_configuration_survive_runtime_restart(tmp_path):
    from sfm_fx_new_age.core.runtime import ApplicationRuntime
    path=tmp_path/'research.sqlite';r=ApplicationRuntime(path)
    try:dataset(r);expected=thaw(r.api(3).run_research_study(request(train=16,test=8)))
    finally:r.close()
    r=ApplicationRuntime(path)
    try:
        assert thaw(r.api(3).research_study('NONMARKET-RUN'))==expected
        assert r.accounts.current is None and r.orders.transport is None
    finally:r.close()
