"""Indexed supplemental-source parity on retained original publications.

No networking, fixture imports or generated market observations. Separate SQL
metadata controls carry records=[] and never enter an evidence store/strategy.
Publication corruption controls alter only private test copies, not originals.
"""
from pathlib import Path
from datetime import timedelta, timezone
from collections import Counter
import hashlib, importlib.util, json, os, statistics, sys, time, unittest
from typing import Any, cast
from original_source_checks import original_runtime, RUN, PACKAGE
from sfm_fx_new_age.contracts.domain import PAIRS, instant
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.services.supplemental import SupplementalEvidenceStore
from sfm_fx_new_age.services.supplemental_files import SupplementalFileIngress
from sfm_fx_new_age.storage.database import Database, StateConflict

PREIMAGES=Path(os.environ['SFM_SUPPLEMENTAL_PREIMAGES']).resolve(strict=True)
PINS=json.loads(Path(os.environ['SFM_SUPPLEMENTAL_BEFORE']).read_bytes())['preimages']


def predecessor(name,relative):
    path=PREIMAGES/relative
    assert hashlib.sha256(path.read_bytes()).hexdigest()==PINS[relative]
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


old_store=predecessor('previous_supplemental','src/sfm_fx_new_age/services/supplemental.py')
old_ingress=predecessor('previous_file_ingress','src/sfm_fx_new_age/services/supplemental_files.py')


class SupplementalOriginalChecks(unittest.TestCase):
    proof:dict[str,Any]
    @classmethod
    def setUpClass(cls):
        cls.r,cls.layers,_,cls.original=original_runtime()
        cls.layers=cast(list[dict[str,Any]],cls.layers)
        cls.store=cls.r.analytics.supplemental
        cls.db=cls.r.database
        cls.rows=cls.db.list('supplemental_evidence')
        assert cls.rows and all(row['origin']=='LIVE_OBSERVED' for row in cls.rows)
        cls.reference=old_store.SupplementalEvidenceStore(cls.db,cls.r.market,cls.r.clock,lambda *args:None)
        cls.reference.providers=cls.store.providers
        cls.reference.admissions=cls.store.admissions
        cls.cutoff=cls.r.clock()
        cls.proof=dict(result='FAIL',scope='ORIGINAL_PUBLICATION_PARITY_WITH_SEPARATE_NONMARKET_SQL_CONTROLS',
            observations_generated=0,original_row_count=len(cls.rows),original_input_row_sha256=cls.original['input_row_sha256'],
            market_rows_or_clocks_modified=False,metadata_controls_not_market_observations=True,
            input_publication_sha256=digest(cls.rows),full_requested_completion=False,measurements={})

    @classmethod
    def tearDownClass(cls):
        cls.proof['fixture_imports']=[key for key in sys.modules if key.startswith('sfm_fx_new_age.testing')]
        cls.proof['sdk_workers_started']=bool(cls.r.connector.workers)
        cls.r.close();cls.proof['runtime_closed']=cls.r.closed
        with (RUN/'supplemental-receipt.json').open('x') as stream:json.dump(cls.proof,stream,indent=2);stream.write('\n')

    def test_01_original_snapshot_values_and_clocks_equal_reference(self):
        for pair in PAIRS:
            self.assertEqual(self.store.snapshot(pair,self.cutoff),self.reference.snapshot(pair,self.cutoff))
        self.assertEqual(digest(self.db.list('supplemental_evidence')),self.proof['input_publication_sha256'])

    def test_02_precise_cutoff_and_offset_equality(self):
        first=min((row['available_at'] for row in self.rows),key=instant)
        for at in ((instant(first)-timedelta(microseconds=1)).isoformat(),first,self.cutoff,
                   instant(self.cutoff).astimezone(timezone(timedelta(hours=-4))).isoformat()):
            for pair in PAIRS:self.assertEqual(self.store.snapshot(pair,at),self.reference.snapshot(pair,at))

    def test_03_actual_original_expiry_withdraws_at_same_boundary(self):
        for row in self.rows:
            for at in (row['valid_until'],(instant(row['valid_until'])+timedelta(microseconds=1)).isoformat()):
                self.assertEqual(self.store.snapshot(row['symbol'],at),self.reference.snapshot(row['symbol'],at))

    def test_04_no_whole_history_read_in_snapshot_or_file_poll(self):
        original=self.db.list
        def guarded(kind):
            if kind=='supplemental_evidence':raise AssertionError('Global supplemental history scan forbidden')
            return original(kind)
        self.db.list=guarded
        try:
            for pair in PAIRS:self.assertTrue(self.store.snapshot(pair,self.cutoff))
            self.r.supplemental_ingress.poll(force=True)
        finally:self.db.list=original
        self.assertEqual(digest(self.db.list('supplemental_evidence')),self.proof['input_publication_sha256'])

    def test_05_actual_query_uses_scoped_index_and_returns_only_selected_pair(self):
        statements=[];self.db.connection.set_trace_callback(statements.append)
        try:
            authority=self.r.market.authority('EURUSD');assert authority is not None
            rows=self.db.supplemental_candidates(scope=self.r.market.scope_id,epoch=authority['source_epoch'],symbol='EURUSD',
                origin=authority['origin'],providers=self.store.providers,cutoff=self.cutoff)
        finally:self.db.connection.set_trace_callback(None)
        self.assertTrue(rows)
        self.assertTrue(all((row['scope_id'],row['source_epoch'],row['symbol'])==(self.r.market.scope_id,authority['source_epoch'],'EURUSD') for row in rows))
        sql=next(statement for statement in statements if statement.lstrip().startswith('WITH scoped AS'))
        plan=[row['detail'] for row in self.db.connection.execute('EXPLAIN QUERY PLAN '+sql)]
        self.assertTrue(any('supplemental_interval_idx' in value for value in plan),plan)
        self.proof['snapshot_query_plan']=plan;self.proof['selected_original_rows_per_pair']=len(rows)

    def test_06_revision_lookup_returns_only_exact_interval_metadata(self):
        for row in self.rows:
            e=SupplementalEvidence(**dict(row,records=tuple(row['records'])))
            self.assertEqual(self.db.supplemental_revision(e),dict(revision=row['revision'],available_at=row['available_at']))
        row=self.rows[0];e=SupplementalEvidence(**dict(row,records=tuple(row['records']),provider_id='ABSENT_NONMARKET_CONTROL'))
        self.assertIsNone(self.db.supplemental_revision(e))

    def test_07_original_admission_and_idempotence_need_no_global_history(self):
        db=Database();events=[]
        store=SupplementalEvidenceStore(db,self.r.market,self.r.clock,lambda *args:events.append(args))
        for key,(kinds,origin) in self.store.providers.items():store.register_provider(key,kinds=kinds,origin=origin)
        e=[SupplementalEvidence(**dict(row,records=tuple(row['records']))) for row in self.rows]
        original=db.list
        def guarded(kind):
            if kind=='supplemental_evidence':raise AssertionError('Global history read during admission')
            return original(kind)
        db.list=guarded
        try:
            self.assertEqual(store.accept_many(e),len(e));self.assertEqual(store.accept_many(e),0)
            self.assertEqual(len(events),len(e))
            self.assertEqual(store.snapshot('EURUSD',self.cutoff),self.store.snapshot('EURUSD',self.cutoff))
        finally:db.close()

    def test_08_missing_provider_or_active_membership_cannot_resurrect(self):
        provider=self.rows[0]['provider_id'];registration=self.store.providers[provider]
        self.store.providers.pop(provider)
        try:self.assertEqual(self.store.snapshot('EURUSD',self.cutoff),self.reference.snapshot('EURUSD',self.cutoff))
        finally:self.store.providers[provider]=registration
        prior=self.store.admissions.get(provider);self.store.admissions[provider]=frozenset()
        try:
            self.assertEqual(self.store.snapshot('EURUSD',self.cutoff),self.reference.snapshot('EURUSD',self.cutoff))
            self.assertFalse(any(row['provider_id']==provider for row in self.store.snapshot('EURUSD',self.cutoff).values()))
        finally:
            if prior is None:self.store.admissions.pop(provider,None)
            else:self.store.admissions[provider]=prior

    def test_09_no_payload_is_rewritten_by_read_and_scope_mismatch_is_empty(self):
        changes=self.db.connection.total_changes;authority=self.r.market.authority('EURUSD');assert authority is not None
        for name,value in (('scope',self.r.market.scope_id+'-ABSENT'),('epoch',authority['source_epoch']+'-ABSENT'),('origin','REPLAY')):
            args=dict(scope=self.r.market.scope_id,epoch=authority['source_epoch'],symbol='EURUSD',origin=authority['origin'],providers=self.store.providers,cutoff=self.cutoff);args[name]=value
            self.assertEqual(self.db.supplemental_candidates(**args),[])
        self.assertEqual(self.db.connection.total_changes,changes)

    def test_10_file_admission_missing_corrupt_restored_on_original_copy(self):
        root=RUN/'private-original-publication';root.mkdir(mode=0o700)
        original_row=self.rows[0];payload=json.dumps(original_row,indent=2).encode();(root/'observations.json').write_bytes(payload)
        manifest=dict(schema_version=1,entries=[dict(file='observations.json',sha256=hashlib.sha256(payload).hexdigest())])
        (root/'manifest.json').write_text(json.dumps(manifest))
        configuration=dict(schema_version=1,providers=[dict(provider_id=original_row['provider_id'],origin=original_row['origin'],
            kinds=[original_row['kind']],manifest_path=str(root/'manifest.json'))]);(root/'sources.json').write_text(json.dumps(configuration))
        db=Database();store=SupplementalEvidenceStore(db,self.r.market,self.r.clock,lambda *args:None)
        ingress=SupplementalFileIngress(store,root/'sources.json')
        try:
            ingress.poll(force=True);self.assertEqual(cast(dict[str,Any],ingress.status())['providers'][0]['state'],'ADMITTED')
            before=store.snapshot(original_row['symbol'],self.cutoff);self.assertIn(original_row['kind'],before)
            (root/'manifest.json').rename(root/'missing-manifest.json');ingress.poll(force=True)
            self.assertEqual(cast(dict[str,Any],ingress.status())['providers'][0]['state'],'WAITING_INPUT');self.assertEqual(store.snapshot(original_row['symbol'],self.cutoff),{})
            (root/'missing-manifest.json').rename(root/'manifest.json');(root/'observations.json').write_bytes(payload+b' ')
            ingress.poll(force=True);self.assertEqual(cast(dict[str,Any],ingress.status())['providers'][0]['state'],'REJECTED');self.assertEqual(store.snapshot(original_row['symbol'],self.cutoff),{})
            (root/'observations.json').write_bytes(payload);ingress.poll(force=True)
            self.assertEqual(store.snapshot(original_row['symbol'],self.cutoff),before)
        finally:db.close()

    def test_11_metadata_only_sql_ties_rank_before_expiry_and_provider_filters(self):
        db=Database();self.addCleanup(db.close)
        # No market observations: this is a SQL ordering/control catalogue only.
        def metadata(identity,kind,provider,available,revision,until):
            return dict(scope_id='SQL_METADATA_ONLY',source_epoch='SQL_METADATA_ONLY',symbol='EURUSD',origin='LIVE_OBSERVED',
                kind=kind,provider_id=provider,available_at=available,revision=revision,valid_until=until,records=[],control_id=identity)
        at='2026-11-11T10:00:00.000001Z';later='2026-11-11T10:00:01Z';until='2026-11-11T11:00:00Z'
        rows=[metadata('old','CFTC_REPORT','P',at,1,until),metadata('new','CFTC_REPORT','P',later,2,later),
              metadata('tie-a','CFTC_REPORT','T',at,1,until),metadata('tie-b','CFTC_REPORT','T',at,1,until),
              metadata('unsupported','TRADED_PRINTS','P',until,99,until)]
        for i,row in enumerate(rows):db.put('supplemental_evidence',str(i),row)
        providers={'P':(frozenset({'CFTC_REPORT'}),'LIVE_OBSERVED'),'T':(frozenset({'CFTC_REPORT'}),'LIVE_OBSERVED')}
        result=db.supplemental_candidates(scope='SQL_METADATA_ONLY',epoch='SQL_METADATA_ONLY',symbol='EURUSD',origin='LIVE_OBSERVED',providers=providers,cutoff=until)
        self.assertEqual({row['control_id'] for row in result},{'new','tie-a','tie-b'})
        # Latest expired row is returned, never an older long-valid revision;
        # the unchanged store applies expiry and body-digest tie break later.
        self.assertEqual(max((r for r in result if r['provider_id']=='T'),key=digest),max(rows[2:4],key=digest))
        early=db.supplemental_candidates(scope='SQL_METADATA_ONLY',epoch='SQL_METADATA_ONLY',symbol='EURUSD',origin='LIVE_OBSERVED',providers=providers,cutoff=at)
        self.assertEqual({r['control_id'] for r in early},{'old','tie-a','tie-b'})

    def test_12_store_first_revision_and_immutability_rules_are_unchanged(self):
        db=Database();self.addCleanup(db.close)
        store=SupplementalEvidenceStore(db,self.r.market,self.r.clock,lambda *args:None)
        row=self.rows[0];store.register_provider(row['provider_id'],kinds=[row['kind']],origin=row['origin'])
        # Negative metadata controls preserve every original price/observation.
        e=SupplementalEvidence(**dict(row,records=tuple(row['records']),revision=2))
        with self.assertRaisesRegex(StateConflict,'First optional revision must be one'):store.accept(e)
        e=SupplementalEvidence(**dict(row,records=tuple(row['records'])))
        self.assertEqual(store.accept(e),1)
        corrupted=SupplementalEvidence(**dict(row,records=tuple(row['records']),source_ref='CORRUPTED_METADATA_CONTROL'))
        with self.assertRaisesRegex(StateConflict,'Optional evidence revisions are immutable'):store.accept(corrupted)
        self.assertEqual(store.snapshot(row['symbol'],self.cutoff)[row['kind']]['records'],row['records'])

    def test_13_record_measured_original_snapshot_and_poll_cost(self):
        reference_ingress=object.__new__(old_ingress.SupplementalFileIngress)
        reference_ingress.__dict__.update(self.r.supplemental_ingress.__dict__)
        reference_ingress.store=self.reference
        measures={}
        for operation in ('snapshot_all_pairs','poll_all_providers'):
            result={}
            for label,store,ingress in [('predecessor',self.reference,reference_ingress),('indexed',self.store,self.r.supplemental_ingress)]:
                def work():
                    if operation=='snapshot_all_pairs':return [store.snapshot(pair,self.cutoff) for pair in PAIRS]
                    return ingress.poll(force=True)
                work();samples=[]
                for _ in range(3):
                    started=time.perf_counter();work();samples.append(time.perf_counter()-started)
                result[label]=dict(seconds=samples,median_seconds=statistics.median(samples))
            result['measured_speedup']=result['predecessor']['median_seconds']/result['indexed']['median_seconds']
            measures[operation]=result
        self.proof['measurements']=measures

    def test_14_same_original_strategy_matrix_and_six_data_gates(self):
        missing={'volume_displacement','effort_result','volume_profile','vwap_bands','footprint_delta','dom_imbalance'}
        self.assertEqual({row['strategy_id'] for row in self.layers if row['state']=='DATA_UNAVAILABLE'},missing)
        self.assertEqual(len(self.layers),2324)
        self.assertFalse(any(row['state']=='ERROR' for row in self.layers))
        self.proof['original_matrix_states']=dict(Counter(row['state'] for row in self.layers))
        self.proof['matrix_geometry_sha256']=digest(self.original['geometry'])
        self.proof['fixture_free']=not any(key.startswith('sfm_fx_new_age.testing') for key in sys.modules)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SupplementalOriginalChecks))
    summary=dict(result='PASS_ORIGINAL_SOURCE_PARITY_AND_SEPARATE_METADATA_CONTROLS' if result.wasSuccessful() else 'FAIL',
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),synthetic_market_observations=0)
    with (RUN/'supplemental-test-results.json').open('x') as stream:json.dump(summary,stream,indent=2);stream.write('\n')
    print(json.dumps(summary,indent=2));raise SystemExit(0 if result.wasSuccessful() else 1)
