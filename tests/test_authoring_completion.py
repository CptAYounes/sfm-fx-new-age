"""Actual product editor actions, not direct service substitutes."""
import os,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from sfm_fx_new_age.app import create_main_window
from sfm_fx_new_age.testing.fixtures import fixture_runtime


def test_actual_logictiles_gui_preview_save_activate_suspend_and_cas():
    app=QApplication.instance() or QApplication([]);r=fixture_runtime();w=create_main_window(r);w.show();w.core_timer.stop();w.poll_timer.stop()
    try:
        r.api(3).navigate('3.10',r.api(3).inspect(symbol='EURUSD'));app.processEvents();p=w._active_panel()
        p.rule_id.setText('GUI-ANALYTICAL-RULE');index=next(i for i in range(p.variable.count()) if p.variable.itemData(i)['key']=='fixture.d1_ready')
        p.variable.setCurrentIndex(index);p.operator.setCurrentText('EQ');p.literal.setText('true');p.add.click()
        assert p.tree.topLevelItem(0).childCount()==1
        before=r.database.connection.total_changes;p.actions['preview'].click();assert r.database.connection.total_changes==before
        assert 'TRUE' in p.feedback.text() and not r.database.get('rule','GUI-ANALYTICAL-RULE')
        p.actions['save'].click();row=r.database.get('rule','GUI-ANALYTICAL-RULE');assert row['state']=='DRAFT' and row['version']==1
        p.actions['activate'].click();assert r.database.get('rule','GUI-ANALYTICAL-RULE')['active_version']==1
        rule=json.loads(p.editor.toPlainText());rule['children'][0]['right']['value']=False;p.change(rule)
        p.actions['activate'].click();assert 'Save these edits' in p.feedback.text()
        p.actions['save'].click();assert r.database.get('rule','GUI-ANALYTICAL-RULE')['version']==2
        assert r.database.get('rule','GUI-ANALYTICAL-RULE')['active_version']==1
        # Polling preserves input and original CAS baseline, concurrent writer wins.
        r.catalogues.save_rule('GUI-ANALYTICAL-RULE',rule,expected_version=2);p.refresh();assert p._version==2
        p.actions['save'].click();assert 'conflict' in p.feedback.text().lower()
        assert r.database.get('rule','GUI-ANALYTICAL-RULE')['version']==3
        assert not r.orders.transport.submissions
    finally:w.close();r.close();app.processEvents()


def test_actual_parameter_editor_applies_typed_value_and_rejects_stale_version():
    app=QApplication.instance() or QApplication([]);r=fixture_runtime();w=create_main_window(r);w.show();w.core_timer.stop();w.poll_timer.stop()
    try:
        r.api(3).navigate('3.11',r.api(3).inspect(symbol='EURUSD'));app.processEvents();p=w._active_panel()
        p.choose.setCurrentIndex(p.choose.findData('order_block.lookback'));p.value.setText('12');p.apply.click()
        assert r.database.get('parameter','order_block.lookback')['value']==12
        assert r.database.get('parameter','order_block.lookback')['version']==1
        p.value.setText('true');p.apply.click();assert r.database.get('parameter','order_block.lookback')['value']==12
        p.value.setText('13');r.catalogues.set_parameter('order_block.lookback',14,expected_version=1);p.refresh()
        p.apply.click();assert 'conflict' in p.feedback.text().lower()
        assert p.value.text()=='13' and r.database.get('parameter','order_block.lookback')['value']==14
        assert not r.database.orders() and not r.connector.workers
    finally:w.close();r.close();app.processEvents()


def test_actual_capital_gui_has_currency_scope_cas_and_no_implicit_budget_approval():
    app=QApplication.instance() or QApplication([]);r=fixture_runtime();w=create_main_window(r);w.show();w.core_timer.stop();w.poll_timer.stop()
    try:
        r.api(4).navigate('4.7',r.api(4).inspect(symbol='EURUSD'));app.processEvents();p=w._active_panel()
        assert 'USD' in p.budget_label.text() and not p.details.isVisible()
        p.base.setCurrentText('BALANCE');p.budget.setText('100');p.apply.click()
        assert r.money.policy()['version']==1 and r.money.policy()['policy']['budget_money']=='100'
        assert 'NONE' in p.summary.text() and r.money.context()['approved_amount'] is None
        p.fraction.setText('45');p.apply.click();assert r.money.policy()['version']==1
        p.fraction.setText('0.45');p.budget.setText('101')
        r.money.set_policy(dict(r.money.policy()['policy'],budget_money='102'),expected_version=1);p.refresh();p.apply.click()
        assert 'conflict' in p.feedback.text().lower() and p.budget.text()=='101'
        assert r.money.policy()['policy']['budget_money']=='102' and not r.orders.transport.submissions
    finally:w.close();r.close();app.processEvents()
