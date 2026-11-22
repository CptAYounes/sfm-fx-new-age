"""Causal compute equivalence on retained originals; no feed or fixture setup.

Cutoff probes do not rewrite observations. Explicit nonmarket metadata controls
exercise equality/order boundaries without market prices or evidence admission.
"""
from pathlib import Path
from datetime import timedelta, timezone
import hashlib, importlib.util, json, os, sys, unittest
from typing import Any
from original_source_checks import original_runtime, RUN, PACKAGE
from sfm_fx_new_age.contracts.domain import PAIRS, FRAMES, instant, record
from sfm_fx_new_age.contracts.analytics import digest
from sfm_fx_new_age.services.scanner import confirmed_swings
from sfm_fx_new_age.tabs.tab3.public_features import Features
from sfm_fx_new_age.tabs.tab3 import public_algorithms as algorithms
from sfm_fx_new_age.tabs.tab3 import public_sequence_features as sequence

PREIMAGES=Path(os.environ['SFM_COMPUTE_PREIMAGES']).resolve(strict=True)
PINS={row['path']:row['sha256'] for row in json.loads(Path(os.environ['SFM_COMPUTE_BEFORE_LEDGER']).read_bytes())}


def reference(name):
    relative='src/sfm_fx_new_age/tabs/tab3/'+name+'.py'
    path=PREIMAGES/relative
    assert hashlib.sha256(path.read_bytes()).hexdigest()==PINS[relative]
    spec=importlib.util.spec_from_file_location('sfm_fx_new_age.tabs.tab3.preserved_'+name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


old_features=reference('public_features')
old_algorithms=reference('public_algorithms')
old_sequence=reference('public_sequence_features')


class OriginalComputeChecks(unittest.TestCase):
    proof:dict[str,Any]
    layers:list[dict[str,Any]]
    cases:list[tuple[str,str,list[dict[str,Any]],list[dict[str,Any]],dict[str,list[dict[str,Any]]]]]
    @classmethod
    def setUpClass(cls):
        cls.r,cls.layers,_,cls.proof=original_runtime()
        cls.cases=[]
        for pair in PAIRS:
            authority=cls.r.market.authority(pair)
            assert authority
            support={frame:[record(b) for b in cls.r.market.bars(pair,frame,cls.r.clock(),authority['source_epoch'])][-2048:] for frame in FRAMES}
            for frame in FRAMES:
                rows=support[frame];swings=confirmed_swings(rows)
                cls.cases.append((pair,frame,rows,swings,support))
        cls.proof.update(scope='ORIGINAL_COMPUTE_EQUIVALENCE_NOT_NEW_LIVE_ACCEPTANCE',metadata_controls_not_admitted=True)

    @classmethod
    def tearDownClass(cls):
        cls.proof['fixture_imports']=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')]
        cls.proof['sdk_workers_started']=bool(cls.r.connector.workers)
        cls.r.close();cls.proof['runtime_closed']=cls.r.closed
        with (RUN/'compute-receipt.json').open('x') as stream:json.dump(cls.proof,stream,indent=2);stream.write('\n')

    def test_01_every_original_prefix_keeps_exact_first_maximum_spelling(self):
        for pair,frame,rows,swings,support in self.cases:
            f=Features(rows,swings)
            for i,b in enumerate(rows):
                self.assertEqual(f.known_at(i),max((r['available_at'] for r in rows[:i+1]),key=instant),(pair,frame,i))
                for extra in (b['available_at'],rows[-1]['available_at']):
                    expected=max([r['available_at'] for r in rows[:i+1]]+[extra],key=instant)
                    self.assertEqual(f.known_at(i,extra),expected)

    def test_02_actual_open_close_boundaries_and_offset_equivalence(self):
        for pair,frame,rows,swings,support in self.cases:
            f=Features(rows,swings)
            for field,method in [('open_time',f.first_open_at_or_after),('close_time',f.first_close_at_or_after)]:
                clocks=[instant(b[field]) for b in rows]
                for i in sorted({0,len(rows)//2,len(rows)-1}):
                    for delta in (-1,0,1):
                        at=clocks[i]+timedelta(microseconds=delta)
                        expected=next((j for j,t in enumerate(clocks) if t>=at),None)
                        self.assertEqual(method(at),expected)
                        self.assertEqual(method(at.astimezone(timezone(timedelta(hours=5,minutes=30))).isoformat()),expected)

    def test_03_original_swing_filters_keep_input_order_and_strict_pivot_boundary(self):
        for pair,frame,rows,swings,support in self.cases:
            f=Features(rows,swings);old=old_features.Features(rows,swings)
            for i in range(len(rows)):
                for kind in (None,'LOW','HIGH'):
                    self.assertEqual(sequence.known_swings(f,i,kind),old_sequence.known_swings(old,i,kind))

    def test_04_latest_original_pivot_matches_stable_maximum(self):
        for pair,frame,rows,swings,support in self.cases:
            f=Features(rows,swings)
            for b in rows:
                at=instant(b['open_time'])
                for kind in ('LOW','HIGH','ABSENT_METADATA_KIND'):
                    eligible=[s for s in swings if s['kind']==kind and instant(s['available_at'])<=at]
                    expected=max(eligible,key=lambda s:instant(s['pivot_time'])) if eligible else None
                    self.assertIs(f.latest_swing_at(at,kind),expected)

    def test_05_causal_alternation_at_original_knowledge_boundaries(self):
        for pair,frame,rows,swings,support in self.cases:
            f=Features(rows,swings);old=old_features.Features(rows,swings)
            for at in {s['available_at'] for s in swings}:
                for delta in (-1,0,1):
                    cutoff=(instant(at)+timedelta(microseconds=delta)).isoformat()
                    self.assertEqual(sequence.alternating_at(f,cutoff),old_sequence.alternating_at(old,cutoff))

    def test_06_original_structure_events_and_pool_intervals_match_predecessor(self):
        for pair,frame,rows,swings,support in self.cases:
            f=Features(rows,swings);old=old_features.Features(rows,swings)
            self.assertEqual(algorithms.structure_events(f),old_algorithms.structure_events(old))
            account=self.r.accounts.current;assert account is not None
            spec=self.r.market.spec(account.account_id,pair);assert spec is not None
            inputs=dict(bars=support,spec=dict(tick_size=str(spec.tick_size)))
            self.assertEqual(sequence.pivot_pools(f,inputs),old_sequence.pivot_pools(old,inputs))
            self.assertEqual(sequence.prior_day_pools(f,inputs),old_sequence.prior_day_pools(old,inputs))

    def test_07_marker_zone_series_and_stage_bytes_match_original_rules(self):
        for pair,frame,rows,swings,support in self.cases:
            f=Features(rows,swings);old=old_features.Features(rows,swings)
            a=algorithms.blank();b=old_algorithms.blank()
            for i in (0,len(rows)//2,len(rows)-1):
                for module,feature,out in [(algorithms,f,a),(old_algorithms,old,b)]:
                    module.marker(out,feature,i,'COMPUTE_EQUIVALENCE','NEUTRAL')
                    module.zone(out,feature,i,float(rows[i]['low']),float(rows[i]['high']),'COMPUTE_EQUIVALENCE','NEUTRAL')
            algorithms.series(a,f,f.c,'ORIGINAL_CLOSES');old_algorithms.series(b,old,old.c,'ORIGINAL_CLOSES')
            self.assertEqual(a,b)
            items=[('COMPUTE_EQUIVALENCE',i) for i in (0,len(rows)//2,len(rows)-1)]
            self.assertEqual(sequence.stages(f,items),old_sequence.stages(old,items))

    def test_08_cache_is_lazy_frame_local_and_keeps_original_roots(self):
        pair,frame,rows,swings,support=self.cases[0]
        a=Features(rows,swings);b=Features(rows,swings)
        self.assertEqual(a.cache,{})
        for i in range(len(rows)):
            self.assertEqual(a.root_id(i),digest(rows[i]))
            self.assertIs(a.root_id(i),a.root_id(i))
        self.assertEqual(b.cache,{})
        self.assertEqual(len(a.cache['bar_root_ids']),len(rows))
        a.known_at(0);self.assertNotIn('bar_clocks',b.cache)

    def test_09_noncanonical_order_control_keeps_original_first_input_semantics(self):
        # Unmodified original records, reordered only in this unadmitted helper control.
        pair,frame,rows,swings,support=self.cases[0]
        reordered=list(reversed(rows));f=Features(reordered,swings)
        for field,method in [('open_time',f.first_open_at_or_after),('close_time',f.first_close_at_or_after)]:
            for at in (rows[0][field],rows[len(rows)//2][field],rows[-1][field]):
                expected=next((i for i,b in enumerate(reordered) if instant(b[field])>=instant(at)),None)
                self.assertEqual(method(at),expected)
        self.assertEqual(sequence.prior_day_pools(f,dict(bars=support)),old_sequence.prior_day_pools(old_features.Features(reordered,swings),dict(bars=support)))

    def test_10_empty_inputs_and_absent_kind_create_no_geometry_or_roots(self):
        f=Features((),())
        self.assertIsNone(f.first_open_at_or_after(self.r.clock()))
        self.assertIsNone(f.first_close_at_or_after(self.r.clock()))
        self.assertIsNone(f.latest_swing_at(self.r.clock(),'LOW'))
        self.assertEqual(sequence.alternating_at(f,self.r.clock()),[])
        self.assertEqual(algorithms.structure_events(f),[])
        self.assertNotIn('bar_root_ids',f.cache)

    def test_11_metadata_only_equal_pivot_tie_prefers_input_not_availability_order(self):
        # No price, quantity, evidence kind, id, source identity or admission path.
        rows=self.cases[0][2];early,late=rows[0]['open_time'],rows[-1]['open_time']
        first=dict(kind='METADATA_CONTROL_ONLY',available_at=late,pivot_time=early)
        second=dict(kind='METADATA_CONTROL_ONLY',available_at=early,pivot_time=early)
        f=Features(rows,(first,second))
        self.assertIs(f.latest_swing_at(early,'METADATA_CONTROL_ONLY'),second)
        self.assertIs(f.latest_swing_at(late,'METADATA_CONTROL_ONLY'),first)
        self.assertEqual(f.swings_at(late),[first,second])

    def test_12_equal_instant_offset_spelling_and_late_extra_stay_exact(self):
        # Scheduling-only controls reuse original prices without ever being admitted.
        rows=self.cases[0][2];at=instant(rows[0]['available_at'])
        utc=at.isoformat();offset=at.astimezone(timezone(timedelta(hours=5,minutes=30))).isoformat()
        controls=[dict(rows[0],available_at=offset),dict(rows[1],available_at=utc)]
        f=Features(controls,())
        self.assertEqual(f.known_at(1),offset)
        self.assertEqual(f.known_at(1,utc),offset)
        later=(at+timedelta(microseconds=1)).isoformat()
        self.assertEqual(f.known_at(1,later),later)

    def test_13_all_six_missing_original_source_gates_remain_closed(self):
        blocked={'volume_displacement','effort_result','volume_profile','vwap_bands','footprint_delta','dom_imbalance'}
        self.assertEqual({v['strategy_id'] for v in self.layers if v['state']=='DATA_UNAVAILABLE'},blocked)
        self.assertTrue(all(not any(v[k] for k in ('series','zones','markers')) for v in self.layers if v['strategy_id'] in blocked))

    def test_14_original_only_readonly_run_has_no_fixture_network_or_authentication(self):
        self.assertFalse([k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
        self.assertFalse(self.r.connector.workers)
        account=self.r.accounts.current;assert account is not None
        self.assertFalse(account.authenticated)
        self.assertIsNone(self.r.connector.oauth)
        self.assertFalse(self.r.fixture_mode)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalComputeChecks))
    summary=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),result='PASS' if result.wasSuccessful() else 'FAIL',new_market_observations=0,metadata_controls_are_not_market_evidence=True)
    with (RUN/'compute-test-results.json').open('x') as stream:json.dump(summary,stream,indent=2);stream.write('\n')
    print(json.dumps(summary));raise SystemExit(not result.wasSuccessful())
