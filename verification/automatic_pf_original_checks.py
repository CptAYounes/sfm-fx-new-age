"""Original-only automatic P&F checks; no generated/reflected market observations."""
from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR
import os,sys,json,sqlite3,hashlib,unittest
import subprocess
from typing import Any
PACKAGE=Path(os.environ['SFM_AUTO_PACKAGE_ROOT']).resolve();sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.tabs.tab3.public_point_figure_auto import automatic_point_figure,PROFILE
from sfm_fx_new_age.tabs.tab3.public_features import Features
from sfm_fx_new_age.tabs.tab3.public_genuine_data import evaluate_genuine
from sfm_fx_new_age.services.public_projections import PublicProjectionService
from sfm_fx_new_age.contracts.public_projection_inputs import ProjectionInputUnavailable
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.connector.native_feed_audit import protocol_capabilities,native_quote_health

OUT=Path(os.environ['SFM_AUTO_OUT']);OUT.mkdir(parents=True,exist_ok=False,mode=0o700)
DATABASE=Path(os.environ['SFM_AUTO_DATABASE']).resolve()

def load_original():
    c=sqlite3.connect(DATABASE.as_uri()+'?mode=ro&immutable=1',uri=True);c.execute('BEGIN');groups=defaultdict(list);specs={};authority={};raw=[]
    for kind,identity,body in c.execute("SELECT kind,id,body FROM records WHERE kind IN ('bar','spec','authority') ORDER BY kind,id"):
        row=json.loads(body);assert row['origin']=='LIVE_OBSERVED';raw.append((kind,identity,body))
        if kind=='bar':groups[(row['symbol'],row['timeframe'])].append(row)
        elif kind=='spec':specs[row['symbol']]=row
        else:authority[row['symbol']]=row
    c.close();lanes={}
    for (symbol,frame),bars in groups.items():
        bars.sort(key=lambda b:b['open_time']);cutoff=max(b['available_at'] for b in bars)
        inputs=dict(scope_id=bars[0]['scope_id'],authority=authority[symbol],symbol=symbol,frame=frame,spec=specs[symbol],_evaluation_at=cutoff,optional_evidence={})
        lanes[(symbol,frame)]=(bars,inputs)
    return lanes,hashlib.sha256(json.dumps(raw,separators=(',',':')).encode()).hexdigest()


def reference_columns(bars,box):
    """Independent grid traversal: add one integer box at a time from closes."""
    def grid(value,rounding):return int((Decimal(value)/box).to_integral_value(rounding=rounding))
    seed=bars[20]['close'];xs=[];direction=None;columns=[]
    for b in bars[21:]:
        rise=grid(b['close'],ROUND_FLOOR);fall=grid(b['close'],ROUND_CEILING)
        if direction is None:
            bottom=grid(seed,ROUND_FLOOR);top=grid(seed,ROUND_CEILING)
            if rise>bottom:direction='X';xs=list(range(bottom,rise+1))
            elif fall<top:direction='O';xs=list(range(top,fall-1,-1))
        elif direction=='X':
            if rise>xs[-1]:xs.extend(range(xs[-1]+1,rise+1))
            elif fall<=xs[-1]-3:columns.append(('X',min(xs),max(xs)));xs=list(range(xs[-1]-1,fall-1,-1));direction='O'
        else:
            if fall<xs[-1]:xs.extend(range(xs[-1]-1,fall-1,-1))
            elif rise>=xs[-1]+3:columns.append(('O',min(xs),max(xs)));xs=list(range(xs[-1]+1,rise+1));direction='X'
    return columns,((direction,min(xs),max(xs)) if direction else None)


class AutomaticOriginalChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lanes,cls.input_hash=load_original();cls.outputs={k:automatic_point_figure(Features(bars,()),inputs) for k,(bars,inputs) in cls.lanes.items()}
    @classmethod
    def tearDownClass(cls):
        proof:dict[str,Any]=dict(input_row_sha256=cls.input_hash,lanes={':'.join(k):v for k,v in cls.outputs.items()},synthetic_market_observations=0,fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')],product_modules={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)})
        assert not proof['fixture_imports'] and all(Path(p).is_relative_to(PACKAGE) for p in proof['product_modules'].values())
        (OUT/'geometry.json').write_text(json.dumps(proof,indent=2)+'\n')
    def test_28_original_lanes(self):self.assertEqual(len(self.lanes),28)
    def test_native_atr_seed_and_grid(self):
        for key,(bars,inputs) in self.lanes.items():
            tick=Decimal(inputs['spec']['tick_size']);ranges=[max(Decimal(bars[i]['high'])-Decimal(bars[i]['low']),abs(Decimal(bars[i]['high'])-Decimal(bars[i-1]['close'])),abs(Decimal(bars[i]['low'])-Decimal(bars[i-1]['close']))) for i in range(1,21)]
            atr=sum(ranges,Decimal(0))/20;expected=max(tick,(atr/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
            m=self.outputs[key]['metrics'];self.assertEqual(Decimal(m['seed_atr']),atr);self.assertEqual(Decimal(m['box_size']),expected);self.assertEqual(expected%tick,0);self.assertTrue(m['box_frozen']);self.assertEqual(m['profile'],PROFILE)
    def test_independent_integer_box_traversal(self):
        for key,(bars,_) in self.lanes.items():
            metrics=self.outputs[key]['metrics'];done,active=reference_columns(bars,Decimal(metrics['box_size']));actual=metrics['columns'];self.assertEqual(len(done),metrics['completed_columns'])
            self.assertEqual([(c['direction'],c['low'],c['high']) for c in actual if c['complete']],done[-63:]);self.assertEqual(next(((c['direction'],c['low'],c['high']) for c in actual if not c['complete']),None),active)
    def test_original_positive_and_both_directions(self):
        events=[e for v in self.outputs.values() for e in v['metrics']['events']];self.assertTrue(events);self.assertEqual({e['side'] for e in events},{'BUY','SELL'});self.assertTrue(any(v['zones'] for v in self.outputs.values()))
    def test_no_setup_is_not_missing_data(self):
        self.assertTrue(any(not v['markers'] and not v['zones'] and v['metrics']['profile']==PROFILE for v in self.outputs.values()))
    def test_five_column_extension_and_retirement(self):
        states=Counter()
        for key,out in self.outputs.items():
            metrics=out['metrics'];box=Decimal(metrics['box_size'])
            bars=self.lanes[key][0]
            for e in metrics['events']:
                states[e['state']]+=1;self.assertEqual(e['count_columns'],5);self.assertEqual(Decimal(e['extension']),box*15)
                expected=Decimal(e['boundary'])+(box*15 if e['side']=='BUY' else -box*15);self.assertEqual(Decimal(e['target']),expected)
                at=next(i for i,b in enumerate(bars) if b['close_time']==e['confirmed_at']);target=Decimal(e['target']);boundary=Decimal(e['boundary']);buy=e['side']=='BUY'
                seen=Decimal(bars[at]['high'])>=target if buy else Decimal(bars[at]['low'])<=target
                state='ALREADY_OBSERVED_BY_CONFIRMATION' if seen else 'ACTIVE';retired=None
                if not seen:
                    for b in bars[at+1:]:
                        reached=Decimal(b['high'])>=target if buy else Decimal(b['low'])<=target
                        invalid=Decimal(b['close'])<boundary if buy else Decimal(b['close'])>boundary
                        if reached or invalid:
                            state='REACHED_AND_INVALIDATED_SAME_BAR_NO_PATH_CLAIM' if reached and invalid else 'REACHED' if reached else 'INVALIDATED';retired=b['close_time'];break
                self.assertEqual(e['state'],state);self.assertEqual(e.get('retired_at'),retired)
            self.assertEqual(len(out['zones']),sum(e['state']=='ACTIVE' for e in metrics['events']))
        self.assertGreater(states['INVALIDATED'],0);self.assertGreater(states['ALREADY_OBSERVED_BY_CONFIRMATION'],0);self.assertGreater(states['ACTIVE'],0)
    def test_causal_prefix_frozen_seed_and_confirmations(self):
        for key,(bars,inputs) in self.lanes.items():
            # Prefixes preserve all original values and clocks; no market resampling.
            for n in (21, max(22,len(bars)//2),len(bars)-1):
                before=automatic_point_figure(Features(bars[:n],()),inputs);self.assertEqual(before['metrics']['box_size'],self.outputs[key]['metrics']['box_size'])
                for e in before['metrics']['events']:
                    after=next(v for v in self.outputs[key]['metrics']['events'] if v['confirmed_at']==e['confirmed_at'] and v['side']==e['side'])
                    for field in ('target','boundary','count_line','count_start','count_end','count_columns','extension'):self.assertEqual(e[field],after[field])
    def test_future_source_clock_rejected(self):
        bars,inputs=self.lanes[('GBPUSD','H4')]
        with self.assertRaises(ValueError):automatic_point_figure(Features(bars,()),dict(inputs,_evaluation_at=bars[20]['close_time']))
    def test_wrong_source_epoch_rejected(self):
        bars,inputs=self.lanes[('GBPUSD','H4')]
        with self.assertRaises(ValueError):automatic_point_figure(Features(bars,()),dict(inputs,authority=dict(inputs['authority'],source_epoch='WRONG_SOURCE')))
    def test_missing_native_grid_does_not_guess(self):
        bars,inputs=self.lanes[('GBPUSD','H4')]
        with self.assertRaises(ProjectionInputUnavailable):automatic_point_figure(Features(bars,()),dict(inputs,spec={}))
    def test_short_original_prefix_is_warmup(self):
        bars,inputs=self.lanes[('GBPUSD','H4')]
        with self.assertRaises(ProjectionInputUnavailable) as caught:automatic_point_figure(Features(bars[:20],()),inputs)
        self.assertEqual(caught.exception.state,'WARMUP')
    def test_real_production_dispatch_and_geometry_contract(self):
        for key,(bars,inputs) in self.lanes.items():
            out=evaluate_genuine('cause_effect',Features(bars,()),inputs,{});self.assertEqual(out,self.outputs[key]);body=dict(out,available_at=inputs['_evaluation_at']);PublicProjectionService._validate(body,inputs['_evaluation_at'])
    def test_native_protocol_does_not_claim_market_executions(self):
        caps=protocol_capabilities();self.assertEqual(caps['descriptor_fields']['ProtoOATickData'],['timestamp','tick']);self.assertFalse(caps['execution_print_feed_available']);self.assertFalse(caps['aggressor_print_feed_available']);self.assertFalse(caps['strict_sequenced_full_book_available'])
    def test_audit_cli_mixed_modes_refused_before_network_or_qt(self):
        code="import sys;sys.path.insert(0,sys.argv.pop(1));from sfm_fx_new_age.__main__ import main;raise SystemExit(main())"
        for options in (['--fixture-session'],['--capture-original-depth',str(OUT/'must-not-exist')],['--summary-json']):
            p=subprocess.run([sys.executable,'-I','-B','-c',code,str(PACKAGE),'--audit-native-feed',str(OUT/'must-not-exist'),*options],capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,2);self.assertFalse((OUT/'must-not-exist').exists())
    def test_audit_cli_existing_directory_refused_without_capture(self):
        code="import sys;sys.path.insert(0,sys.argv.pop(1));from sfm_fx_new_age.__main__ import main;raise SystemExit(main())"
        p=subprocess.run([sys.executable,'-I','-B','-c',code,str(PACKAGE),'--audit-native-feed',str(OUT)],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,2);self.assertFalse((OUT/'capture').exists());self.assertIn('ORIGINAL_INPUT_PREPARATION_FAILED',p.stdout)
    def test_original_zero_spread_and_stale_quote_diagnostics(self):
        root=Path(os.environ['SFM_AUTO_QUOTE_AUDIT']);cutoff=json.loads((root/'feed-audit.json').read_bytes())['observed_at']
        c=sqlite3.connect((root/'capture/state.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True)
        try:quotes=[json.loads(row[0]) for row in c.execute("SELECT body FROM records WHERE kind='quote'")]
        finally:c.close()
        locked=stale=0
        for q in quotes:
            self.assertEqual(q['origin'],'LIVE_OBSERVED');r=native_quote_health(q,cutoff)
            if q['bid']==q['ask']:
                locked+=1;self.assertTrue(r['coherent_bid_ask']);self.assertTrue(r['zero_spread'])
                if r['oldest_side_age_seconds']<=30:self.assertTrue(r['coherent_fresh_bid_ask'])
            if r['oldest_side_age_seconds']>30:stale+=1;self.assertFalse(r['coherent_fresh_bid_ask'])
        self.assertGreater(locked,0);self.assertGreater(stale,0)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AutomaticOriginalChecks))
    summary=dict(result='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),package_root=str(PACKAGE),database=str(DATABASE),synthetic_market_observations=0)
    (OUT/'test-results.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));raise SystemExit(0 if result.wasSuccessful() else 1)
