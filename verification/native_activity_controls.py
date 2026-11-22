"""Original-observation replay plus explicit NONMARKET lifecycle negatives.
No fabricated observations count toward native source acceptance.
"""
from pathlib import Path
from datetime import timedelta
from dataclasses import replace
from copy import deepcopy
import ast,json,os,sqlite3,sys,unittest
from typing import Any
PACKAGE=Path(os.environ['SFM_NATIVE_PACKAGE']).resolve(strict=True);sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.domain import AccountContext,PAIRS,instant,record
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from sfm_fx_new_age.connector.broker_depth import ConnectedBrokerDepth,PROVIDER
from sfm_fx_new_age.tabs.tab3.public_activity_alternatives import ACTIVITY_NAMES,evaluate_activity
from sfm_fx_new_age.tabs.tab3.public_genuine_data import evaluate_genuine
from sfm_fx_new_age.tabs.tab3.public_features import Features
CAPTURE=Path(os.environ['SFM_NATIVE_CAPTURE']).resolve(strict=True)
OUT=Path(os.environ['SFM_NATIVE_OUT']);OUT.mkdir(mode=0o700,parents=True,exist_ok=False)
C=sqlite3.connect((CAPTURE/'state.sqlite3').as_uri()+'?mode=ro',uri=True)
try:
    C.execute('PRAGMA query_only=ON');ORIGINAL_ROWS=C.execute("SELECT kind,id,body FROM records WHERE kind IN ('account_metadata','authority','spec','bar')").fetchall()
    ORIGINAL_EVIDENCE=[json.loads(b) for b, in C.execute("SELECT body FROM records WHERE kind='supplemental_evidence' AND json_extract(body,'$.kind')='INTRABAR_PRICES'")]
finally:C.close()
DEPTH=json.loads((CAPTURE/'broker-depth-envelopes.json').read_bytes());EVENTS=json.loads((CAPTURE/'original-depth-events.json').read_bytes())


class ActivityControls(unittest.TestCase):
    inputs:dict[str,Any]
    def setUp(self):
        self.e=SupplementalEvidence(**dict(DEPTH['EURUSD'],records=tuple(DEPTH['EURUSD']['records'])))
        self.cutoff=self.e.available_at;self.r=ApplicationRuntime(clock=lambda:self.cutoff,native_analytical_feed=True,activity_alternatives=True)
        with self.r.database.transaction() as c:c.executemany('INSERT INTO records VALUES(?,?,?)',ORIGINAL_ROWS)
        account=self.r.database.get('account_metadata',self.e.scope_id);assert account
        self.account=AccountContext(**{k:v for k,v in account.items() if k!='scope_id'});self.r.accounts.select(self.account)
        assert self.r.connector.analytical_feed is not None;self.depth=self.r.connector.analytical_feed.depth
        self.calls=[]
        def request(endpoint,name,payload,context=None):self.calls.append(dict(endpoint=endpoint,name=name,payload=payload,context=context));return 'NONMARKET_READ_REQUEST'
        self.r.connector.request=request
        authorities={s:self.r.market.authority(s) for s in PAIRS};assert all(authorities.values())
        self.identity=(self.account.scope_id,tuple((s,(authorities[s] or {})['source_epoch']) for s in PAIRS))
        self.inputs=dict(scope_id=self.account.scope_id,authority=self.r.market.authority('EURUSD'),symbol='EURUSD',frame='H4',activity_alternatives=True,
            _evaluation_at=self.cutoff,spec=record(self.r.market.spec(self.account.account_id,'EURUSD')),optional_evidence={'BROKER_DEPTH':record(self.e)})
        q=next(v for v in ORIGINAL_EVIDENCE if v['symbol']=='EURUSD');self.inputs['optional_evidence']['INTRABAR_PRICES']=q
        bars=self.r.market.bars('EURUSD','H4',self.cutoff,self.e.source_epoch);self.f=Features([record(b) for b in bars],())
    def tearDown(self):self.r.close()
    def _book(self,ack=True):
        self.depth.poll(self.identity)
        request=dict(context={'binding':self.depth.binding})
        if ack:self.depth.handle(self.account.endpoint_class,'ProtoOASubscribeDepthQuotesRes',{'ctidTraderAccountId':self.account.account_id},request)
        for event in EVENTS:
            if event['symbol']!='EURUSD' or instant(event['received_at'])>instant(self.e.records[0]['time']):continue
            self.cutoff=event['received_at'];self.depth.handle(self.account.endpoint_class,'ProtoOADepthEvent',event['payload'],None)
        self.cutoff=self.e.available_at
    def test_all_six_original_alternatives_declare_their_different_semantics(self):
        for key in ACTIVITY_NAMES:
            out=evaluate_genuine(key,self.f,self.inputs,{})
            self.assertTrue(out['metrics']['alternative']);self.assertFalse(out['metrics']['executed_volume']);self.assertFalse(out['metrics']['known_aggressors'])
            self.assertEqual(out['metrics']['interpretation_name'],ACTIVITY_NAMES[key])
    def test_strict_mode_never_accepts_proxy_inputs(self):
        self.inputs['activity_alternatives']=False
        for key in ACTIVITY_NAMES:
            with self.assertRaises(ProjectionInputUnavailable):evaluate_genuine(key,self.f,self.inputs,{})
    def test_present_but_invalid_strict_source_is_not_masked_by_alternative(self):
        self.inputs['optional_evidence']['TRADED_PRINTS']={'kind':'TRADED_PRINTS'}
        with self.assertRaises((ValueError,TypeError,KeyError)):evaluate_genuine('vwap_bands',self.f,self.inputs,{})
    def test_quote_direction_first_quote_is_unclassified_not_an_aggressor(self):
        out=evaluate_activity('footprint_delta',self.f,self.inputs)['metrics']
        total=sum(out[k] for k in ('up_quote_changes','down_quote_changes','unchanged_quotes','unclassified_quotes'))
        self.assertEqual(total,len(self.inputs['optional_evidence']['INTRABAR_PRICES']['records']));self.assertFalse(out['aggressor_inferred']);self.assertEqual(out['unclassified_quotes'],1)
    def test_activity_refuses_wrong_source_and_expired_actual_evidence(self):
        wrong=deepcopy(self.inputs);wrong['authority']['source_epoch']='NONMARKET_WRONG_EPOCH'
        with self.assertRaisesRegex(ValueError,'source mismatch'):evaluate_activity('dom_imbalance',self.f,wrong)
        wrong=deepcopy(self.inputs);wrong['_evaluation_at']=(instant(self.e.valid_until)+timedelta(microseconds=1)).isoformat()
        with self.assertRaises(ProjectionInputUnavailable):evaluate_activity('dom_imbalance',self.f,wrong)
    def test_observed_book_cannot_claim_native_sequence_or_completeness(self):
        for field in ('native_sequence','full_book_complete'):
            with self.assertRaises(ValueError):validate_wire_shape(replace(self.e,parameters=dict(self.e.parameters,**{field:True})))
        with self.assertRaises(ValueError):validate_wire_shape(replace(self.e,records=(dict(self.e.records[0],sequence=1),)))
    def test_subscription_is_once_per_binding_and_no_orders(self):
        self.depth.poll(self.identity);self.depth.poll(self.identity)
        self.assertEqual([v['name'] for v in self.calls],['ProtoOASubscribeDepthQuotesReq']);self.assertFalse(self.r.connector.workers)
    def test_actual_depth_needs_acknowledgement_before_admission(self):
        self._book(ack=False);self.depth.poll(self.identity)
        self.assertNotIn(PROVIDER,self.r.analytics.supplemental.providers)
    def test_original_depth_reconstruction_and_actual_receipt_clocks(self):
        self._book();self.depth.publish('EURUSD')
        got=self.r.analytics.supplemental.snapshot('EURUSD',self.cutoff)['BROKER_DEPTH']
        self.assertEqual(got['records'][0]['bids'],self.e.records[0]['bids']);self.assertEqual(got['records'][0]['asks'],self.e.records[0]['asks'])
        self.assertEqual(got['records'][0]['time'],self.e.records[0]['time']);self.assertEqual(got['available_at'],self.e.available_at)
    def test_idle_and_disconnect_never_refresh_original_clock_or_restore_authority(self):
        self._book();self.depth.publish('EURUSD');before=self.r.database.list('supplemental_evidence')
        self.cutoff=(instant(self.e.valid_until)+timedelta(seconds=1)).isoformat();self.depth.poll(self.identity)
        status:Any=self.depth.status();self.assertFalse(self.r.analytics.supplemental.snapshot('EURUSD',self.cutoff));self.assertEqual(status['pairs']['EURUSD'],'STALE_RECEIPT')
        self.depth.disconnect();self.assertNotIn(PROVIDER,self.r.analytics.supplemental.providers);self.assertEqual(before,self.r.database.list('supplemental_evidence'))
    def test_reconnect_rebind_clears_original_book_and_requires_new_ack(self):
        self._book();self.depth.publish('EURUSD');session=self.depth.session
        self.depth.poll(('NONMARKET_CHANGED_BINDING',self.identity[1]));self.assertNotEqual(session,self.depth.session)
        self.assertFalse(self.depth.ack);self.assertFalse(any(self.depth.books.values()));self.assertNotIn(PROVIDER,self.r.analytics.supplemental.providers)
        self.assertEqual(sum(v['name']=='ProtoOASubscribeDepthQuotesReq' for v in self.calls),2)
    def test_failed_subscribe_withdraws_without_blind_retry(self):
        self._book();self.depth.publish('EURUSD');self.depth.fail({'context':{'broker_depth':'SUBSCRIBE'}});before=len(self.calls)
        self.depth.poll(self.identity);self.assertEqual(len(self.calls),before);self.assertFalse(self.depth.ack);self.assertNotIn(PROVIDER,self.r.analytics.supplemental.providers)
    def test_explicit_local_broker_depth_provider_excludes_automatic_subscription(self):
        d=ConnectedBrokerDepth(self.r.connector,excluded=True);d.poll(self.identity);self.assertFalse(self.calls);self.assertFalse(d.binding)
    def test_entrypoint_exposes_strict_mode_and_keeps_it_out_of_headless_network(self):
        tree=ast.parse((PACKAGE/'sfm_fx_new_age/__main__.py').read_bytes())
        flags=[n for n in ast.walk(tree) if isinstance(n,ast.Constant) and n.value=='--strict-genuine-data'];self.assertEqual(len(flags),1)
        r=ApplicationRuntime(activity_alternatives=True)
        try:self.assertIsNone(r.connector.analytical_feed);self.assertFalse(r.connector.workers)
        finally:r.close()


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ActivityControls))
    origins={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)}
    assert all(Path(p).is_relative_to(PACKAGE) for p in origins.values())
    summary=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),result='PASS' if result.wasSuccessful() else 'FAIL',scope='ORIGINAL_REPLAY_AND_EXPLICIT_NONMARKET_LIFECYCLE_CONTROLS',fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')],product_module_origins=origins)
    with (OUT/'controls.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='product_module_origins'}));raise SystemExit(not result.wasSuccessful())
