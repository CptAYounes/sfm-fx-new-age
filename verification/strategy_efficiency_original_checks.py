"""Original-observation parity and query-cost checks; no fixture imports or feed.

Requires the immutable acquisition root used by original_source_checks and the
preserved predecessor PublicProjectionService. Cutoff probes change read clocks,
not observations, timestamps, prices, volumes, identities or source evidence.
"""
from collections import Counter
from datetime import timedelta, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import statistics
import sys
import time
import unittest
from typing import Any

# The launcher explicitly pins this verification directory before any imports.
from original_source_checks import original_runtime, RUN, PACKAGE
from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES, instant
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.services.public_projections import PublicProjectionService

REFERENCE = Path(os.environ['SFM_PROJECTION_PREIMAGE']).resolve(strict=True)
EXPECTED_REFERENCE_SHA = os.environ['SFM_PROJECTION_PREIMAGE_SHA256']
if hashlib.sha256(REFERENCE.read_bytes()).hexdigest() != EXPECTED_REFERENCE_SHA:
    raise ValueError('Predecessor source hash mismatch')
spec = importlib.util.spec_from_file_location('preserved_projection_reference', REFERENCE)
if spec is None or spec.loader is None:
    raise ValueError('Preserved predecessor is not a loadable Python module')
reference_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference_module)
ReferenceService = reference_module.PublicProjectionService


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class OriginalProjectionEfficiency(unittest.TestCase):
    layers: list[dict[str, Any]]
    baseline_layers: list[dict[str, Any]]
    proof: dict[str, Any]
    @classmethod
    def setUpClass(cls):
        current_refresh = PublicProjectionService.refresh
        baseline = None
        try:
            PublicProjectionService.refresh = ReferenceService.refresh
            baseline, baseline_layers, _, baseline_receipt = original_runtime()
        finally:
            PublicProjectionService.refresh = current_refresh
        try:
            cls.r, cls.layers, _, cls.receipt = original_runtime()
            cls.baseline_layers = baseline_layers
            cls.baseline_receipt = baseline_receipt
        finally:
            if baseline is not None:
                baseline.close()
        cls.p = cls.r.analytics.projections
        cls.reference = ReferenceService(cls.r.database, cls.r.market, cls.r.consumers, cls.r.clock)
        cls.reference.methods = dict(cls.p.methods)
        cls.cutoff = cls.r.clock()
        cls.proof = dict(
            scope='UNCHANGED_ORIGINAL_OBSERVATIONS_REPLAY_NOT_NEW_LIVE_OPERATION',
            reference_path=str(REFERENCE), reference_sha256=EXPECTED_REFERENCE_SHA,
            input_row_sha256=cls.receipt['input_row_sha256'],
            baseline_geometry_sha256=digest(cls.baseline_receipt['geometry']),
            current_geometry_sha256=digest(cls.receipt['geometry']),
            baseline_full_layers_sha256=digest(cls.baseline_layers),
            current_full_layers_sha256=digest(cls.layers),
            source_matrix_rows=len(cls.layers), synthetic_observations=0,
            cutoffs_are_read_clock_probes_not_retimed_observations=True,
            full_requested_completion=False, measurements={},
            per_profile=[dict(strategy_id=m.key, input_kind=m.data_kind,
                states=dict(Counter(v['state'] for v in cls.layers if v['strategy_id']==m.key)),
                positive_geometry_rows=sum(v['state']=='READY' for v in cls.layers if v['strategy_id']==m.key))
                for m in METHODS])

    @classmethod
    def tearDownClass(cls):
        cls.proof['fixture_imports'] = [k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')]
        cls.proof['sdk_workers_started'] = bool(cls.r.connector.workers)
        cls.r.close()
        cls.proof['runtime_closed'] = cls.r.closed
        path = RUN / 'efficiency-receipt.json'
        with path.open('x') as stream:
            json.dump(cls.proof, stream, indent=2)
            stream.write('\n')
        path.chmod(0o444)

    def test_01_exact_original_geometry_fingerprints_and_clocks(self):
        self.assertEqual(self.baseline_receipt['input_row_sha256'], self.receipt['input_row_sha256'])
        self.assertEqual(self.baseline_receipt['geometry'], self.receipt['geometry'])
        self.assertEqual(self.baseline_layers, self.layers)
        self.assertEqual(len(self.layers), len(METHODS)*len(PAIRS)*len(FRAMES))
        self.assertFalse(any(v['state'] in {'ERROR', 'WARMUP'} for v in self.layers))

    def test_02_current_and_asof_exact_matrix_matches_predecessor(self):
        for symbol in PAIRS:
            for frame in FRAMES:
                cases: list[dict[str, Any]] = [{}, {'as_of': self.cutoff},
                               {'as_of': self.cutoff, 'apply_current_filters': True},
                               {'as_of': self.cutoff, 'dirty': True}, {'dirty': True}]
                for kwargs in cases:
                    self.assertEqual(self.p.read(symbol, frame, **kwargs),
                                     self.reference.read(symbol, frame, **kwargs), (symbol, frame, kwargs))

    def test_03_exact_cutoff_order_and_offset_equivalence(self):
        first = min((v['available_at'] for v in self.layers), key=instant)
        clocks = [instant(first)-timedelta(microseconds=1), instant(first), instant(self.cutoff),
                  instant(self.cutoff).astimezone(timezone(timedelta(hours=5, minutes=30)))]
        for clock in clocks:
            cutoff = clock.isoformat()
            self.assertEqual(self.p.read('EURUSD', 'H4', as_of=cutoff),
                             self.reference.read('EURUSD', 'H4', as_of=cutoff))
        canonical = self.r.database.connection.execute('SELECT projection_utc(?)', (self.cutoff,)).fetchone()[0]
        self.assertEqual(canonical, instant(self.cutoff).astimezone(timezone.utc).isoformat(timespec='microseconds'))

    def test_04_readtime_expiry_matches_without_resurrecting_old_rows(self):
        cutoffs = {v['valid_until'] for v in self.layers if v.get('valid_until')}
        self.assertTrue(cutoffs)
        for cutoff in sorted(cutoffs, key=instant):
            for clock in (cutoff, (instant(cutoff)+timedelta(microseconds=1)).isoformat()):
                self.assertEqual(self.p.read('EURUSD', 'H4', as_of=clock),
                                 self.reference.read('EURUSD', 'H4', as_of=clock))

    def test_05_switches_invalidate_without_a_persisted_read_cache(self):
        method = METHODS[0]
        args = dict(recipe_id=method.recipe_id, version=method.version)
        try:
            reply = self.r.api(3).command('3.1', 'ENABLE_RECIPE', dict(args, enabled=False))
            self.assertEqual(reply.status.value, 'ACCEPTED')
            self.assertNotIn(method.key, {v['strategy_id'] for v in self.p.read('EURUSD', 'H4')})
            self.assertIn(method.key, {v['strategy_id'] for v in self.p.read('EURUSD', 'H4', as_of=self.cutoff)})
            self.assertNotIn(method.key, {v['strategy_id'] for v in self.p.read('EURUSD', 'H4', as_of=self.cutoff, apply_current_filters=True)})
            self.assertEqual(self.p.read('EURUSD', 'H4'), self.reference.read('EURUSD', 'H4'))
        finally:
            self.r.api(3).command('3.1', 'ENABLE_RECIPE', dict(args, enabled=True))

    def test_06_disabled_methods_skip_all_feature_and_source_work(self):
        before = dict(self.p.runs), self.p.feature_builds
        try:
            for method in METHODS:
                self.r.api(3).command('3.1', 'ENABLE_RECIPE', dict(recipe_id=method.recipe_id, version=method.version, enabled=False))
            self.p.refresh({}, {})
            self.assertEqual((self.p.runs, self.p.feature_builds), before)
            self.assertEqual(self.p.read('EURUSD', 'H4'), [])
        finally:
            for method in METHODS:
                self.r.api(3).command('3.1', 'ENABLE_RECIPE', dict(recipe_id=method.recipe_id, version=method.version, enabled=True))

    def test_07_no_global_history_scan_or_read_side_write(self):
        db = self.r.database
        prior_list = db.list
        before = db.connection.total_changes
        def guarded_list(kind):
            if kind == 'strategy_projection':
                raise AssertionError('Global historical projection scan forbidden')
            return prior_list(kind)
        db.list = guarded_list
        try:
            for symbol in PAIRS:
                for frame in FRAMES:
                    self.assertEqual(len(self.p.read(symbol, frame, as_of=self.cutoff)), len(METHODS))
        finally:
            db.list = prior_list
        self.assertEqual(db.connection.total_changes, before)

    def test_08_bounded_queries_and_missing_source_isolation(self):
        db = self.r.database
        self.assertEqual(db.get_many('recipe_state', []), {})
        self.assertEqual(db.get_many('recipe_state', ['NO_SUCH_RECIPE']), {})
        with self.assertRaises(ValueError):
            db.get_many('recipe_state', ['x']*501)
        with self.assertRaises(ValueError):
            db.projection_history(scope='unknown', epoch='unknown', symbol='EURUSD', timeframe='H4', methods=['x']*501, cutoff=self.cutoff)
        authority = self.r.market.authority('EURUSD')
        assert authority is not None
        self.assertEqual(db.projection_history(scope=self.r.market.scope_id, epoch=authority['source_epoch']+'-absent',
            symbol='EURUSD', timeframe='H4', methods=[m.key for m in METHODS], cutoff=self.cutoff), {})

    def test_09_actual_sql_uses_exact_source_index_and_one_selected_revision(self):
        statements = []
        self.r.database.connection.set_trace_callback(statements.append)
        try:
            rows = self.p.read('EURUSD', 'H4', as_of=self.cutoff)
        finally:
            self.r.database.connection.set_trace_callback(None)
        sql = next(statement for statement in statements if statement.lstrip().startswith('WITH scoped AS'))
        plan = [row['detail'] for row in self.r.database.connection.execute('EXPLAIN QUERY PLAN '+sql)]
        self.assertTrue(any('public_projection_history_scope_idx' in item for item in plan), plan)
        self.assertEqual(len(rows), len(METHODS))
        self.assertEqual(len({v['strategy_id'] for v in rows}), len(METHODS))
        self.proof['historical_query_plan'] = plan

    def test_10_record_query_cost_and_wall_clock_without_math_changes(self):
        measurements = {}
        cases: list[tuple[str, dict[str, Any]]] = [('current', {}), ('historical', {'as_of': self.cutoff})]
        for name, kwargs in cases:
            mode = {}
            for label, service in (('predecessor', self.reference), ('optimized', self.p)):
                service.read('EURUSD', 'H4', **kwargs)
                timings = []
                for _ in range(5):
                    started = time.perf_counter()
                    result = service.read('EURUSD', 'H4', **kwargs)
                    timings.append(time.perf_counter()-started)
                statements = []
                self.r.database.connection.set_trace_callback(statements.append)
                try:
                    service.read('EURUSD', 'H4', **kwargs)
                finally:
                    self.r.database.connection.set_trace_callback(None)
                mode[label] = dict(seconds=timings, median_seconds=statistics.median(timings),
                    selected_rows=len(result), read_queries=sum(s.lstrip().startswith(('SELECT', 'WITH')) for s in statements))
            mode['measured_speedup'] = mode['predecessor']['median_seconds']/mode['optimized']['median_seconds']
            self.assertEqual(mode['predecessor']['selected_rows'], mode['optimized']['selected_rows'])
            if name == 'current':
                self.assertLess(mode['optimized']['read_queries'], mode['predecessor']['read_queries'])
            measurements[name] = mode
        self.proof['measurements'] = measurements

    def test_11_all_six_original_evidence_gates_preserved(self):
        blocked = {'volume_displacement', 'effort_result', 'volume_profile', 'vwap_bands', 'footprint_delta', 'dom_imbalance'}
        actual = {v['strategy_id'] for v in self.layers if v['state']=='DATA_UNAVAILABLE'}
        self.assertEqual(actual, blocked)
        self.assertTrue(all(not any(v[k] for k in ('series', 'zones', 'markers')) for v in self.layers if v['strategy_id'] in blocked))
        self.proof['original_input_blockers'] = sorted(blocked)

    def test_12_no_fixture_network_or_account_authentication(self):
        self.assertFalse([k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
        self.assertFalse(self.r.connector.workers)
        self.assertFalse(self.r.accounts.current.authenticated)
        self.assertFalse(self.r.fixture_mode)
        self.assertIsNone(self.r.connector.oauth)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalProjectionEfficiency))
    summary = dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        package_root=str(PACKAGE), synthetic_observations=0, result='PASS' if result.wasSuccessful() else 'FAIL')
    with (RUN/'efficiency-test-results.json').open('x') as stream:
        json.dump(summary, stream, indent=2)
        stream.write('\n')
    print(json.dumps(summary))
    raise SystemExit(0 if result.wasSuccessful() else 1)
