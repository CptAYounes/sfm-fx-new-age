"""Offline lifecycle controls using the real retained connected acquisition.

These are source-replay and nonmarket lifecycle controls, not fresh feed proof.
"""
from pathlib import Path
from dataclasses import replace
from threading import Thread
from time import monotonic
import ast,json,os,sqlite3,sys,unittest
from typing import Any
PACKAGE=Path(os.environ['SFM_FEED_PACKAGE']).resolve(strict=True);sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.domain import AccountContext,PAIRS,instant
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.connector.analytical_feed import ConnectedAnalyticalFeed,TPO,COT,CALENDAR
from sfm_fx_new_age.contracts.models import thaw
CAPTURE=Path(os.environ['SFM_FEED_CAPTURE']).resolve(strict=True)
OUT=Path(os.environ['SFM_FEED_OUT']);OUT.mkdir(mode=0o700,parents=True,exist_ok=False)


class FeedControls(unittest.TestCase):
    feed:ConnectedAnalyticalFeed
    def setUp(self):
        c=sqlite3.connect((CAPTURE/'state.sqlite3').as_uri()+'?mode=ro',uri=True)
        try:
            c.execute('PRAGMA query_only=ON');allrows=c.execute('SELECT kind,id,body FROM records').fetchall()
        finally:c.close()
        evidence=[json.loads(b) for k,i,b in allrows if k=='supplemental_evidence'];assert len(evidence)==21
        self.evidence=[SupplementalEvidence(**dict(v,records=tuple(v['records']))) for v in evidence]
        self.cutoff=max((v.available_at for v in self.evidence),key=instant)
        scope=self.evidence[0].scope_id
        selected=[(k,i,b) for k,i,b in allrows if k in {'account_metadata','authority','spec','native_quote_history_job','native_quote_history_decoded'} and (json.loads(b).get('scope_id')==scope or k=='native_quote_history_decoded')]
        self.r=ApplicationRuntime(clock=lambda:self.cutoff,native_analytical_feed=True)
        with self.r.database.transaction() as conn:conn.executemany('INSERT INTO records VALUES(?,?,?)',selected)
        account=self.r.database.get('account_metadata',scope);assert account
        self.r.accounts.select(AccountContext(**{k:v for k,v in account.items() if k!='scope_id'}))
        feed=self.r.connector.analytical_feed;assert feed is not None;self.feed=feed
    def tearDown(self):self.r.close()
    def test_constructor_and_unauthed_poll_do_not_network_or_restore_provider_authority(self):
        self.assertFalse(self.r.connector.workers);self.assertFalse(self.r.analytics.supplemental.providers)
        self.feed.poll();self.assertFalse(self.r.connector.workers);self.assertFalse(self.r.analytics.supplemental.providers)
    def test_core_default_and_headless_checks_stay_inert(self):
        r=ApplicationRuntime()
        try:self.assertIsNone(r.connector.analytical_feed);self.assertFalse(r.connector.workers)
        finally:r.close()
    def test_normal_entrypoint_explicitly_enables_connected_source_owner(self):
        tree=ast.parse((PACKAGE/'sfm_fx_new_age/__main__.py').read_bytes())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and any(k.arg=='native_analytical_feed' and isinstance(k.value,ast.Constant) and k.value.value is True for k in n.keywords)]
        self.assertEqual(len(calls),1)
        self.assertIsInstance(calls[0].func,ast.Name)
        assert isinstance(calls[0].func,ast.Name)
        self.assertEqual(calls[0].func.id,'ApplicationRuntime')
    def test_original_admission_is_idempotent_and_exact_source_scoped(self):
        for v in self.evidence:self.feed._admit(v.provider_id,[v])
        first=self.r.database.list('supplemental_evidence')
        for v in self.evidence:self.feed._admit(v.provider_id,[v])
        self.assertEqual(self.r.database.list('supplemental_evidence'),first)
        for symbol in PAIRS:self.assertEqual(set(self.r.analytics.supplemental.snapshot(symbol,self.cutoff)),{'INTRABAR_PRICES','CFTC_REPORT','OFFICIAL_CALENDAR'})
    def test_disconnect_withdraws_all_owned_inputs_without_deleting_history(self):
        for v in self.evidence:self.feed._admit(v.provider_id,[v])
        self.feed.disconnect()
        self.assertFalse(self.r.analytics.supplemental.snapshot('EURUSD',self.cutoff))
        self.assertEqual(len(self.r.database.list('supplemental_evidence')),21)
    def test_wrong_epoch_original_envelope_refuses_and_does_not_register(self):
        v=self.evidence[0]
        with self.assertRaisesRegex(ValueError,'scope / epoch'):self.feed._admit(v.provider_id,[replace(v,source_epoch=v.source_epoch+'-NONMARKET_MISMATCH')])
        self.assertNotIn(v.provider_id,self.r.analytics.supplemental.providers)
        self.assertFalse(self.r.database.list('supplemental_evidence'))
    def test_explicit_file_kind_is_not_shadowed_by_automatic_producer(self):
        feed=ConnectedAnalyticalFeed(self.r.connector,excluded_kinds={'INTRABAR_PRICES'})
        v=next(v for v in self.evidence if v.kind=='INTRABAR_PRICES')
        feed._admit(v.provider_id,[v]);self.assertNotIn(v.provider_id,self.r.analytics.supplemental.providers);feed.close()
    def test_missing_authenticated_session_withdraws_previous_registration_on_poll(self):
        for v in self.evidence:self.feed._admit(v.provider_id,[v])
        self.feed.binding=('NONMARKET_OLD_SCOPE',())
        self.feed.poll()
        self.assertIsNone(self.feed.binding);self.assertFalse(self.r.analytics.supplemental.providers)
    def test_stale_completed_http_result_cannot_cross_source_binding(self):
        self.feed.binding=('NONMARKET_NEW_SCOPE',())
        worker=Thread(target=lambda:None);worker.start();worker.join();self.feed.worker=worker
        self.feed.results.put((('NONMARKET_OLD_SCOPE',()),Path('not-read'),None,None))
        self.feed._finish_context();self.assertIsNone(self.feed.worker)
        self.assertFalse(self.r.analytics.supplemental.providers)
    def test_close_joins_owned_nonnetwork_lifecycle_worker(self):
        worker=Thread(target=lambda:None);worker.start();self.feed.worker=worker
        self.feed.close();self.assertFalse(worker.is_alive());self.assertIsNone(self.feed.worker)
    def test_timeout_marks_original_job_failed_instead_of_running_forever(self):
        job=next(j for j in self.r.database.list('native_quote_history_job') if j['state']=='COMPLETE')
        job=dict(job,state='RUNNING');self.r.database.put('native_quote_history_job',job['id'],job)
        request_id='NONMARKET_TIMEOUT_CONTROL'
        self.r.connector.requests[request_id]=dict(sent=monotonic()-31,name='ProtoOAGetTickDataReq',endpoint=job['endpoint'],payload={},context={'native_quote_history':job['id']})
        self.r.connector.poll()
        stored=self.r.database.get('native_quote_history_job',job['id']);assert stored is not None
        self.assertEqual(stored['state'],'REQUEST_FAILED')
    def test_retained_quote_decoder_preserves_original_observation_ids_prices_and_clocks(self):
        for v in self.evidence:
            if v.kind!='INTRABAR_PRICES':continue
            jobs=[j for j in self.r.database.list('native_quote_history_job') if j['symbol']==v.symbol]
            self.assertEqual(len(jobs),1)
            rebuilt=self.r.connector.quote_history.tpo_evidence(jobs[0]['id'],provider_id=TPO,available_at=v.available_at)
            self.assertEqual(thaw(rebuilt.records),thaw(v.records));self.assertEqual(rebuilt.window_start,v.window_start);self.assertEqual(rebuilt.window_end,v.window_end)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FeedControls))
    summary=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),scope='ORIGINAL_REPLAY_PLUS_NONMARKET_LIFECYCLE_CONTROLS',result='PASS' if result.wasSuccessful() else 'FAIL',fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
    with (OUT/'controls.json').open('x') as stream:json.dump(summary,stream,indent=2);stream.write('\n')
    print(json.dumps(summary));raise SystemExit(not result.wasSuccessful())
