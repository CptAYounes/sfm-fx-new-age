"""Original-data-only source/installed checks; never imports testing fixtures.

Requires an actual immutable native acquisition root in SFM_ORIGINAL_EVIDENCE.
The evaluation cutoff is an actual recorded timestamp, not invented market data.
These are recorded-source replays; connected capture is qualified separately.
"""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import hashlib,json,os,sqlite3,sys,time,unittest
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=Path(os.environ.get('SFM_ORIGINAL_PACKAGE_ROOT',str(ROOT/'src'))).resolve()
sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.core.runtime import ApplicationRuntime
from sfm_fx_new_age.contracts.domain import AccountContext,PAIRS,FRAMES,instant
from sfm_fx_new_age.contracts.public_strategies import METHODS
from sfm_fx_new_age.contracts.models import thaw
from sfm_fx_new_age.contracts.tab_data import DataRequest
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.connector.official_context import cot_records,fed_records

EVIDENCE=Path(os.environ['SFM_ORIGINAL_EVIDENCE']).resolve(strict=True)
RUN=Path(os.environ['SFM_ORIGINAL_CHECK_OUT']).resolve()
RUN.mkdir(exist_ok=False,parents=True,mode=0o700)
SOURCE=EVIDENCE/'fresh-broker-v5.sqlite3'
CONFIG=EVIDENCE/'connected-original-sources-v5.json'


def sha(data):return hashlib.sha256(data).hexdigest()


def original_runtime():
    source=sqlite3.connect(SOURCE.as_uri()+'?mode=ro',uri=True);source.execute('PRAGMA query_only=ON');source.execute('BEGIN')
    scope=json.loads(source.execute("SELECT body FROM records WHERE kind='setting' AND id='connector_remember'").fetchone()[0])['scope_id']
    selected=[];observed=[];raw_ticks=[]
    for kind,identity,body in source.execute("SELECT kind,id,body FROM records WHERE kind IN ('account_metadata','authority','spec','quote','bar','bar_revision','calendar','native_quote_history_received','native_quote_history_page','native_quote_history_decoded','native_quote_history_job','projection_current') ORDER BY kind,id"):
        v=json.loads(body)
        if kind=='native_quote_history_decoded':continue
        if v.get('scope_id')!=scope:continue
        if v.get('origin') not in (None,'LIVE_OBSERVED'):raise AssertionError('Nonoriginal observation refused')
        if kind=='projection_current':
            observed.append(v['available_at']);continue
        if kind=='quote':observed.extend(v[k] for k in ('available_at','bid_at','ask_at') if v.get(k))
        if v.get('available_at'):observed.append(v['available_at'])
        if kind=='native_quote_history_received':raw_ticks.append(v)
        selected.append((kind,identity,body))
    source.close();cutoff=max(observed,key=instant)
    runtime=ApplicationRuntime(clock=lambda:cutoff,supplemental_config=CONFIG)
    with runtime.database.transaction() as c:c.executemany('INSERT OR REPLACE INTO records VALUES(?,?,?)',selected)
    account=runtime.database.get('account_metadata',scope);assert account and account['authenticated'] is False
    runtime.accounts.select(AccountContext(**{k:v for k,v in account.items() if k!='scope_id'}))
    runtime.supplemental_ingress.poll(force=True)
    for method in METHODS:
        reply=runtime.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=method.recipe_id,version=method.version,enabled=True));assert reply.status.value=='ACCEPTED'
    started=time.monotonic();runtime.pump();elapsed=time.monotonic()-started
    layers=[v for symbol in PAIRS for frame in FRAMES for v in runtime.analytics.projections.read(symbol,frame)]
    return runtime,layers,raw_ticks,dict(scope='ORIGINAL_RECORDED_SOURCE_REPLAY_NOT_NEW_LIVE_CAPTURE',cutoff=cutoff,elapsed_seconds=elapsed,package_root=str(Path(__import__('sfm_fx_new_age').__file__).resolve().parent),input_row_sha256=sha('\n'.join(sha((k+'\0'+i+'\0'+b).encode()) for k,i,b in selected).encode()),matrix_rows=len(layers),states=dict(Counter(v['state'] for v in layers)),geometry={':'.join(v[k] for k in ('strategy_id','symbol','timeframe')):{k:v[k] for k in ('state','reason','series','zones','markers','metrics')} for v in layers},synthetic_observations=0,network_started=False)


class OriginalSourceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r,cls.layers,cls.raw_ticks,cls.receipt=original_runtime()
        cls.by_key={(v['strategy_id'],v['symbol'],v['timeframe']):v for v in cls.layers}
    @classmethod
    def tearDownClass(cls):
        cls.receipt['fixture_imports']=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')]
        cls.receipt['sdk_started']=bool(cls.r.connector.workers)
        cls.r.close();cls.receipt['runtime_closed']=cls.r.closed
        p=RUN/'replay-receipt.json'
        with p.open('x') as f:json.dump(cls.receipt,f,indent=2);f.write('\n')
        p.chmod(0o444)
    def test_independent_document_denominator_and_matrix(self):
        contract=json.loads((PACKAGE/'sfm_fx_new_age/contracts/data/public_document_requirements.json').read_bytes())
        self.assertEqual(set(contract['expected_catalogue_ids']),{m.key for m in METHODS});self.assertEqual(len(contract['requirements']),91)
        self.assertEqual(len(self.layers),83*7*4);self.assertFalse([v for v in self.layers if v['state'] in {'ERROR','WARMUP'}])
    def test_original_capture_did_not_leave_any_workers(self):
        receipt=json.loads((EVIDENCE/'fresh-broker-v5.json').read_bytes())
        self.assertTrue(receipt['sdk_processes_stopped']);self.assertTrue(receipt['auth_thread_stopped']);self.assertTrue(receipt['runtime_closed']);self.assertTrue(receipt['account_authenticated']);self.assertEqual(receipt['synthetic_observations'],0)
    def test_live_original_quote_was_evaluated_before_shutdown(self):
        rows=json.loads((EVIDENCE/'fresh-broker-v5.json').read_bytes())['live_quote_only_evaluations']
        self.assertEqual(len(rows),28);self.assertTrue(all(v['state'] in {'READY','NO_SETUP'} for v in rows));self.assertTrue(all(v['metrics'].get('forming_ohlc_reconstructed') is False for v in rows))
    def test_each_actual_recipe_command_withdraws_only_its_layer(self):
        for m in METHODS:
            before={v['strategy_id'] for v in self.r.analytics.projections.read('EURUSD','H4')}
            result=self.r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=False));self.assertEqual(result.status.value,'ACCEPTED')
            after={v['strategy_id'] for v in self.r.analytics.projections.read('EURUSD','H4')};self.assertEqual(before-after,{m.key});self.assertEqual(after,before-{m.key})
            result=self.r.api(3).command('3.1','ENABLE_RECIPE',dict(recipe_id=m.recipe_id,version=m.version,enabled=True));self.assertEqual(result.status.value,'ACCEPTED')
    def test_chart_api_does_not_leak_other_pairs_or_frames(self):
        self.r.pump()
        for symbol in PAIRS:
            for frame in FRAMES:
                body=thaw(self.r.api(1).query('1.4',DataRequest('chart',symbol=symbol,timeframe=frame,limit=5000)))
                self.assertEqual(len(body['strategy_layers']),83)
                self.assertTrue(all((v['symbol'],v['timeframe'],v['scope_id'],v['source_epoch'])==(symbol,frame,self.r.market.scope_id,self.r.market.authority(symbol)['source_epoch']) for v in body['strategy_layers']))
    def test_missing_trade_prints_and_book_remain_unavailable(self):
        missing={'volume_displacement','effort_result','volume_profile','vwap_bands','footprint_delta','dom_imbalance'}
        self.assertEqual({v['strategy_id'] for v in self.layers if v['state']=='DATA_UNAVAILABLE'},missing)
        self.assertTrue(all(not any(v[k] for k in ('series','zones','markers')) for v in self.layers if v['strategy_id'] in missing))
        automatic=[v for v in self.layers if v['strategy_id']=='cause_effect']
        self.assertEqual(len(automatic),28)
        self.assertTrue(all(v['state'] in {'READY','NO_SETUP'} and v['metrics']['profile']=='PNF_CLOSE_ATR20_FROZEN_3BOX_TRIPLE_V1' and v['metrics']['intrabar_sequence_inferred'] is False for v in automatic))
    def test_no_fixture_modules_or_authentication_restored(self):
        self.assertFalse([k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')]);self.assertFalse(self.r.fixture_mode);self.assertFalse(self.r.accounts.current.authenticated);self.assertFalse(self.r.connector.workers);self.assertIsNone(self.r.connector.oauth)
    def test_all_file_admissions_are_original_and_source_bound(self):
        providers=self.r.supplemental_ingress.status()['providers'];self.assertEqual(len(providers),3);self.assertTrue(all(p['origin']=='LIVE_OBSERVED' and p['state']=='ADMITTED' for p in providers))
    def test_raw_official_responses_match_acquisition_hashes(self):
        receipt=json.loads((EVIDENCE/'connected-official-v5/acquisition-receipt.json').read_bytes())
        for raw,source in zip(('cftc-original.raw','fed-board-original.raw'),receipt['responses']):self.assertEqual(sha((EVIDENCE/'connected-official-v5'/raw).read_bytes()),source['sha256']);self.assertTrue(source['tls_verification']);self.assertEqual(source['status'],200)
    def test_official_calendar_does_not_fabricate_importance_or_global_coverage(self):
        receipt=json.loads((EVIDENCE/'connected-official-v5/acquisition-receipt.json').read_bytes());data=json.loads((EVIDENCE/'connected-official-v5/fed-board-original.raw').read_bytes());rows,coverage=fed_records(data,receipt['responses'][1]['received_at'],receipt['fed_coverage']['month'])
        self.assertEqual(coverage,receipt['fed_coverage']);self.assertTrue(all(v['importance']=='UNSPECIFIED' for v in rows));self.assertFalse(coverage['no_news_guarantee']);self.assertTrue(coverage['excludes_other_agencies']);self.assertTrue(coverage['excludes_non_USD_events'])


def cot_check(symbol):
    def check(self):
        receipt=json.loads((EVIDENCE/'connected-official-v5/acquisition-receipt.json').read_bytes());raw=json.loads((EVIDENCE/'connected-official-v5/cftc-original.raw').read_bytes());source=cot_records(raw,receipt['responses'][0]['received_at'])[symbol]
        fraction=(Decimal(source['long'])-Decimal(source['short']))/Decimal(source['open_interest'])*(-1 if symbol.startswith('USD') else 1)
        for frame in FRAMES:
            row=self.by_key[('cot_macro',symbol,frame)];self.assertEqual(row['state'],'READY');self.assertEqual(Decimal(row['metrics']['mapped_net_fraction']),fraction);self.assertIsNone(row['metrics']['actual_release']);self.assertEqual(row['metrics']['first_verified_available_at'],source['time']);self.assertFalse(row['metrics']['spot_position_claim'])
    return check


def tick_check(symbol):
    def check(self):
        original=next(v for v in self.raw_ticks if v['symbol']==symbol);self.assertIs(original['payload']['hasMore'],False)
        envelope=json.loads((EVIDENCE/'connected-quotes-v5'/(symbol+'-tpo.json')).read_bytes());validate_wire_shape(SupplementalEvidence(**dict(envelope,records=tuple(envelope['records']))))
        timestamp=price=None;decoded=[]
        for row in original['payload']['tickData']:
            timestamp=int(row['timestamp']) if timestamp is None else timestamp+int(row['timestamp']);price=int(row['tick']) if price is None else price+int(row['tick']);decoded.append((timestamp,Decimal(price)/Decimal(100000)))
        decoded.sort();exported=sorted((int(instant(v['time']).timestamp()*1000),Decimal(v['price'])) for v in envelope['records']);self.assertEqual(decoded,exported)
        bars=self.r.market.bars(symbol,'H1',self.r.clock(),original['source_epoch']);native=next(b for b in bars if b.open_time==envelope['window_start'])
        self.assertEqual((decoded[0][1],max(p for t,p in decoded),min(p for t,p in decoded),decoded[-1][1]),(native.open,native.high,native.low,native.close))
        for frame in FRAMES:self.assertEqual(self.by_key[('profile_tpo',symbol,frame)]['state'],'READY')
    return check

for symbol in PAIRS:
    setattr(OriginalSourceChecks,'test_original_cftc_'+symbol,cot_check(symbol))
    setattr(OriginalSourceChecks,'test_original_ticks_and_tpo_'+symbol,tick_check(symbol))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalSourceChecks))
    summary=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),synthetic_observations=0,package_root=str(PACKAGE),result='PASS' if result.wasSuccessful() else 'FAIL')
    with (RUN/'test-results.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
    print(json.dumps(summary));raise SystemExit(0 if result.wasSuccessful() else 1)
