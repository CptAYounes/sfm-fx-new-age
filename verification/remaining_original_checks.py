"""Original-only remaining-source checks; no generated market observations."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
import hashlib,json,os,sqlite3,sys,unittest,subprocess
PACKAGE=Path(os.environ['SFM_REMAINING_PACKAGE_ROOT']).resolve();sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.services.point_figure_preparation import prepare_original_point_figure,verified_native_ticks
from sfm_fx_new_age.connector.depth_capture import decode_observed_levels
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.domain import AccountContext,instant
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.public_strategies import BY_KEY
from sfm_fx_new_age.core.runtime import ApplicationRuntime

EVIDENCE=Path(os.environ['SFM_REMAINING_EVIDENCE']);OUT=Path(os.environ['SFM_REMAINING_CHECK_OUT']);OUT.mkdir(parents=True,exist_ok=False,mode=0o700)
REQUEST=json.loads((EVIDENCE/'pf-research-request-v1.json').read_bytes());CAPTURE=Path(REQUEST['source_capture_directory']);CONFIG=json.loads((CAPTURE/'sources.json').read_bytes());BODY=json.loads((CAPTURE/'native-quotes/EURUSD-tpo.json').read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def request_file(name,changes=None):
    value=json.loads(json.dumps(REQUEST));value['output_directory']=str(OUT/name)
    if changes:
        for key,item in changes.items():value[key]=item
    p=OUT/(name+'-request.json');p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o444);return p

def create_runtime(prepared):
    value=json.loads((prepared/'sources.json').read_bytes());config=OUT/'combined-sources.json';config.write_text(json.dumps(dict(schema_version=1,providers=CONFIG['providers']+value['providers']),indent=2)+'\n')
    receipt=json.loads((prepared/'count-receipt.json').read_bytes());r=ApplicationRuntime(clock=lambda:receipt['available_at'],supplemental_config=config)
    c=sqlite3.connect((CAPTURE/'state.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True);c.execute('PRAGMA query_only=ON')
    try:rows=c.execute("SELECT kind,id,body FROM records WHERE kind IN ('account_metadata','authority','spec','quote','bar','bar_revision','calendar')").fetchall()
    finally:c.close()
    selected=[row for row in rows if json.loads(row[2]).get('scope_id')==BODY['scope_id']]
    with r.database.transaction() as c:c.executemany('INSERT OR REPLACE INTO records VALUES(?,?,?)',selected)
    metadata=r.database.get('account_metadata',BODY['scope_id']);assert metadata is not None;r.accounts.select(AccountContext(**{k:v for k,v in metadata.items() if k!='scope_id'}));r.supplemental_ingress.poll(force=True)
    return r,receipt

class OriginalRemainingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared=OUT/'prepared-research';p=request_file('prepared-research');cls.receipt=prepare_original_point_figure(p);cls.envelope=json.loads((cls.prepared/'EURUSD-point-figure.json').read_bytes())
    def test_raw_native_tick_decode_matches_all_seven_original_envelopes(self):
        manifest=json.loads((CAPTURE/'native-quotes/manifest.json').read_bytes());symbols=[]
        for entry in manifest['entries']:
            symbol=entry['file'].split('-')[0];body,tick=verified_native_ticks(str(CAPTURE),symbol,REQUEST['capture_receipt_sha256'],entry['sha256']);self.assertGreater(len(body['records']),0);self.assertGreater(Decimal(tick),0);symbols.append(symbol)
        self.assertEqual(len(set(symbols)),7)
    def test_original_observation_values_ids_and_clocks_unchanged(self):self.assertEqual(self.envelope['records'],BODY['records'])
    def test_no_source_epoch_or_expiry_renewal(self):
        self.assertEqual(self.envelope['source_epoch'],BODY['source_epoch']);self.assertEqual(self.envelope['valid_until'],BODY['valid_until']);self.assertGreaterEqual(instant(self.envelope['available_at']),instant(BODY['available_at']))
    def test_interpretation_settings_are_not_operator_approval(self):
        self.assertFalse(self.receipt['operator_approval_independently_authenticated']);self.assertFalse(self.receipt['settings_are_market_observations']);self.assertEqual(self.receipt['count_owner_label'],'EXPLICIT_SOFTWARE_VERIFICATION_SETTINGS_NOT_USER_ADOPTED')
    def test_positive_original_count_excludes_last_developing_column(self):
        self.assertEqual(self.receipt['completed_count_columns'],24);self.assertTrue(self.receipt['last_developing_column_excluded']);self.assertEqual(self.receipt['synthetic_observations'],0)
    def test_missing_side_count_line_and_owner_are_rejected_without_output(self):
        for index,field in enumerate(('side','count_line','count_start','count_end','box_size')):
            params=dict(REQUEST['parameters']);params.pop(field);p=request_file('missing'+str(index),{'parameters':params})
            with self.subTest(field=field),self.assertRaises(ValueError):prepare_original_point_figure(p)
            self.assertFalse((OUT/('missing'+str(index))).exists())
        p=request_file('missing-owner',{'count_owner_label':''})
        with self.assertRaises(ValueError):prepare_original_point_figure(p)
    def test_declared_parameter_rejections_do_not_change_observations(self):
        invalid=[dict(box_size='0.000001'),dict(count_line='1.0',reversal_boxes=1),dict(side='NEUTRAL'),dict(count_start='2026-11-10T00:00:00Z'),dict(box_size='NaN')]
        for index,delta in enumerate(invalid):
            p=request_file('invalid'+str(index),{'parameters':dict(REQUEST['parameters'],**delta)})
            with self.subTest(delta=delta),self.assertRaises((ValueError,ArithmeticError)):prepare_original_point_figure(p)
            self.assertFalse((OUT/('invalid'+str(index))).exists())
        self.assertEqual(sha(CAPTURE/'native-quotes/EURUSD-tpo.json'),REQUEST['source_envelope_sha256'])
    def test_wrong_or_normalized_hash_is_not_accepted(self):
        for index,change in enumerate(({'capture_receipt_sha256':'0'*64},{'source_envelope_sha256':REQUEST['source_envelope_sha256'].upper()},{'acknowledge_research_only':False})):
            p=request_file('identity'+str(index),change)
            with self.subTest(change=change),self.assertRaises(ValueError):prepare_original_point_figure(p)
    def test_existing_output_is_not_overwritten(self):
        p=OUT/'prepared-research-request.json'
        with self.assertRaises(ValueError):prepare_original_point_figure(p)
        self.assertEqual(json.loads((self.prepared/'EURUSD-point-figure.json').read_bytes()),self.envelope)
    def test_actual_broker_depth_decode_matches_original_receipt_no_sequence_fiction(self):
        raw=json.loads((EVIDENCE/'depth-source-v1/raw-depth.json').read_bytes());proof=json.loads((EVIDENCE/'depth-source-v1/depth-receipt.json').read_bytes());self.assertEqual(sha(EVIDENCE/'depth-source-v1/raw-depth.json'),proof['raw_sha256'])
        for symbol,events in raw['events'].items():
            result=decode_observed_levels(events)
            for key,value in result.items():self.assertEqual(value,proof['symbols'][symbol][key])
            self.assertTrue(events);self.assertFalse(result['native_sequence_available']);self.assertFalse(result['full_book_complete']);self.assertFalse(result['sequence_gap_detection_available'])
        self.assertFalse(proof['dom_strategy_admitted']);self.assertTrue(proof['sdk_processes_stopped']);self.assertTrue(proof['auth_thread_stopped']);self.assertEqual(proof['denied_broker_mutations'],0)
    def test_prepared_original_count_admits_through_real_file_ingress_and_paints_layer(self):
        r,receipt=create_runtime(self.prepared)
        try:
            method=BY_KEY['cause_effect'];response=r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=method.recipe_id,version=method.version,enabled=True));self.assertEqual(response.status.value,'ACCEPTED');r.pump()
            layers=[thaw(v) for v in r.analytics.projections.read('EURUSD','H4') if v['strategy_id']=='cause_effect'];self.assertEqual(len(layers),1);row=layers[0];self.assertEqual(row['state'],'READY');self.assertEqual(len(row['zones']),2);self.assertEqual(row['metrics']['completed_count_columns'],24)
            with (OUT/'pf-projection.json').open('x') as f:json.dump(thaw(row),f,indent=2);f.write('\n')
            self.assertFalse(r.connector.workers);self.assertEqual(row['source_epoch'],BODY['source_epoch']);self.assertEqual(row['origin'],'LIVE_OBSERVED')
        finally:r.close()
    def test_cli_rejects_fixture_and_mixed_acquisition_modes_before_gui(self):
        for options in (['--fixture-session'],['--capture-original-depth',str(OUT/'must-not-start')],['--summary-json']):
            command=[sys.executable,'-I','-B','-c',"import sys;sys.path.insert(0,sys.argv.pop(1));from sfm_fx_new_age.__main__ import main;raise SystemExit(main())",str(PACKAGE),'--prepare-original-point-figure',str(EVIDENCE/'pf-research-request-v1.json'),*options]
            result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15);self.assertEqual(result.returncode,2)
        self.assertFalse((OUT/'must-not-start').exists())

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(OriginalRemainingChecks);result=unittest.TextTestRunner(verbosity=2).run(suite);modules={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)}
    assert modules and all(Path(v).is_relative_to(PACKAGE) for v in modules.values()) and not any(k.startswith('sfm_fx_new_age.testing') for k in modules)
    receipt=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),synthetic_market_observations=0,research_settings_user_adopted=False,package_root=str(PACKAGE),all_modules_from_declared_root=True,product_modules=len(modules),network_started=False)
    with (OUT/'checks-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt,indent=2));raise SystemExit(not result.wasSuccessful())
