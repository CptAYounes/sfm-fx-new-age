"""FIX safety/specification controls, NOT genuine FIX market-data acceptance.

Uses retained original vendor documentation verbatim for structural checks only.
Published example bytes are not repaired, retimed, admitted as live evidence or
fed into a strategy. No mock market prices, logons or server responses are made.
"""
from pathlib import Path
from decimal import Decimal
import os,sys,json,unittest,subprocess,hashlib,xml.etree.ElementTree as ET
PACKAGE=Path(os.environ['SFM_FIX_PACKAGE_ROOT']).resolve();sys.path.insert(0,str(PACKAGE))
from sfm_fx_new_age.connector.fix_protocol import Decoder,QuoteBook,FixError,encode_quote,one,groups
from sfm_fx_new_age.connector.fix_capture import capture_fix_price,load_price_credentials,PriceSession
OUT=Path(os.environ['SFM_FIX_CHECK_OUT']);OUT.mkdir(parents=True,exist_ok=False,mode=0o700);EVIDENCE=Path(os.environ['SFM_FIX_EVIDENCE']);EXAMPLES=json.loads((EVIDENCE/'research/published-fix-examples.json').read_bytes())
def documented_fields(example):return tuple((int(token.partition('=')[0]),token.partition('=')[2]) for token in example['text'].rstrip('|').split('|'))
FULL=next(v for v in EXAMPLES if v['type']=='W' and '|271=' in v['text']);FULL_FIELDS=documented_fields(FULL)
REQUEST=next(v for v in EXAMPLES if v['type']=='V' and '|264=0|' in v['text']);REQUEST_FIELDS=documented_fields(REQUEST)
HEADER={8,9,35,49,56,50,57,34,52,10}

class FixControls(unittest.TestCase):
    def test_no_credential_attempt_writes_actual_zero_network_receipt(self):
        attempts=[]
        def audit(event,args):
            if event.startswith('socket.'):attempts.append(event);raise AssertionError('Unexpected FIX networking without credentials')
        sys.addaudithook(audit)
        r=capture_fix_price(Path.home()/'.local/share/sfm-fx-new-age/state.sqlite3',OUT/'no-secret.json',OUT/'missing-credential-attempt')
        self.assertEqual(r['result'],'FIX_PRICE_CREDENTIALS_MISSING');self.assertFalse(r['network_started']);self.assertFalse(r['socket_opened']);self.assertEqual(r['market_frames'],0);self.assertTrue(r['stream_closed']);self.assertEqual(attempts,[])
    def test_secret_loader_does_not_fall_back_to_oauth(self):
        with self.assertRaises((OSError,ValueError)):load_price_credentials(OUT/'never-written-price-secret.json')
    def test_outbound_order_and_trade_session_messages_denied(self):
        for kind in ('D','F','G','H','AF','AN'):
            with self.subTest(kind=kind),self.assertRaises(FixError):encode_quote(kind,1,'UNUSED','CSERVER')
    def test_administrative_wire_roundtrip_checksum_and_quote_routing(self):
        wire=encode_quote('0',1,'UNUSED','CSERVER');[(raw,fields)]=Decoder().feed(wire)
        self.assertEqual(raw,wire);self.assertEqual(one(fields,35),'0');self.assertEqual(one(fields,50),'QUOTE');self.assertEqual(one(fields,57),'QUOTE');self.assertNotIn(b'554=',wire)
    def test_fragmented_administrative_transport(self):
        wire=encode_quote('0',1,'UNUSED','CSERVER');d=Decoder();result=[]
        for byte in wire:result.extend(d.feed(bytes([byte])))
        self.assertEqual(len(result),1);self.assertEqual(result[0][0],wire);self.assertEqual(d.buffer,b'')
    def test_fullbook_request_preserves_only_supported_both_sides(self):
        fields=[(k,v) for k,v in REQUEST_FIELDS if k not in HEADER];wire=encode_quote('V',1,'UNUSED','CSERVER',fields);[(raw,decoded)]=Decoder().feed(wire)
        self.assertEqual([v for k,v in decoded if k==269],['0','1']);self.assertEqual(one(decoded,264),'0');self.assertEqual(one(decoded,265),'1')
    def test_request_cannot_subscribe_to_execution_type_or_write_field(self):
        original=[(k,v) for k,v in REQUEST_FIELDS if k not in HEADER]
        for fields in ([(k,'2' if k==269 and v=='1' else v) for k,v in original],original+[(38,'1000')]):
            with self.assertRaises(FixError):encode_quote('V',1,'UNUSED','CSERVER',fields)
    def test_vendor_generic_trade_enum_is_not_supported_subscription_evidence(self):
        xml=ET.fromstring((EVIDENCE/'research/FIX44-CSERVER.xml').read_bytes());fields=xml.find('fields');assert fields is not None;field=next(n for n in fields if n.get('name')=='MDEntryType');self.assertIn('2',{n.get('enum') for n in field})
        text=(EVIDENCE/'research/specification.txt').read_text();section=text.split('Market Data Request (MsgType(35)=V)')[1].split('Market Data Snapshot/Full Refresh')[0]
        self.assertIn('both bid and ask',section);self.assertIn('= Bid',section);self.assertIn('= Offer',section)
    def test_verbatim_published_examples_with_bad_lengths_are_not_repaired(self):
        rejected=0
        for row in EXAMPLES:
            if row['type'] not in {'V','W','X'}:continue
            raw=row['text'].replace('|','\x01').encode('ascii');start=raw.find(b'\x01',raw.find(b'9='))+1;end=raw.rfind(b'10=');declared=int(raw.split(b'\x01')[1][2:]);valid=declared==end-start and sum(raw[:end])%256==int(raw[end+3:end+6])
            if not valid:
                with self.subTest(type=row['type']),self.assertRaises(FixError):Decoder().feed(raw)
                rejected+=1
        self.assertGreater(rejected,0)
    def test_document_only_snapshot_structural_aggregation_not_wire_admission(self):
        book=QuoteBook({'1':'EURUSD'});self.assertEqual(book.apply(FULL_FIELDS),{'EURUSD'});levels=book.levels('EURUSD');self.assertIsNotNone(levels);assert levels is not None
        rows=groups(FULL_FIELDS,268,269,{269,299,270,271,278})
        for side,name in [('0','bids'),('1','asks')]:self.assertEqual(sum(Decimal(v[271]) for v in rows if v[269]==side),sum(Decimal(q) for p,q in levels[name]))
        self.assertFalse(list(OUT.glob('*-book.json')))
    def test_delta_cannot_initialize_full_book(self):
        delta=next(v for v in EXAMPLES if v['type']=='X');book=QuoteBook({'1':'EURUSD'})
        with self.assertRaises(FixError):book.apply(documented_fields(delta))
        self.assertTrue(book.failed);self.assertEqual(book.initialized,set())
    def test_spot_snapshot_without_native_id_quantity_is_refused(self):
        spot=next(v for v in EXAMPLES if v['type']=='W' and '|271=' not in v['text']);book=QuoteBook({'1':'EURUSD'})
        with self.assertRaises(FixError):book.apply(documented_fields(spot))
        self.assertTrue(book.failed)
    def test_explicit_invalidation_removes_snapshot_not_stale_visibility(self):
        book=QuoteBook({'1':'EURUSD'});book.apply(FULL_FIELDS);book.invalidate()
        with self.assertRaises(FixError):book.levels('EURUSD')
        self.assertEqual(book.books['EURUSD'],{})
    def test_scalar_duplicate_repeating_group_identity_is_not_flattened(self):
        with self.assertRaises(FixError):one(FULL_FIELDS,269)
        self.assertEqual(len(groups(FULL_FIELDS,268,269,{269,299,270,271,278})),int(one(FULL_FIELDS,268)))
    def test_cli_mixed_mode_refuses_before_fixture_or_network(self):
        bootstrap="import sys;sys.path.insert(0,sys.argv.pop(1));from sfm_fx_new_age.__main__ import main;raise SystemExit(main())"
        for args in (['--fixture-session'],['--summary-json'],['--capture-original-depth',str(OUT/'must-not-start')]):
            command=[sys.executable,'-I','-B','-c',bootstrap,str(PACKAGE),'--capture-fix-depth',str(OUT/'must-not-start'),*args];r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15);self.assertEqual(r.returncode,2)
        self.assertFalse((OUT/'must-not-start').exists())
    def test_empty_decoder_and_pre_snapshot_state_are_not_market_data(self):
        self.assertEqual(Decoder().feed(b''),[]);b=QuoteBook({'1':'EURUSD'})
        with self.assertRaises(FixError):b.levels('EURUSD')
    def test_protocol_only_admin_sequence_is_native_not_local_counter(self):
        class AdminOnly:
            def recv(self,n):return encode_quote('0',2,'CSERVER','UNUSED')
        session=PriceSession(dict(target_comp_id='CSERVER',sender_comp_id='UNUSED'),AdminOnly());session.logged_in=True
        with self.assertRaises(FixError):session.receive()
        self.assertEqual(session.incoming,1)
    def test_protocol_only_admin_contiguous_sequence_and_duplicate_rejection(self):
        class AdminOnly:
            def recv(self,n):return encode_quote('0',1,'CSERVER','UNUSED')
        session=PriceSession(dict(target_comp_id='CSERVER',sender_comp_id='UNUSED'),AdminOnly());session.logged_in=True
        frames=session.receive();self.assertEqual(len(frames),1);self.assertEqual(session.incoming,2)
        with self.assertRaises(FixError):session.receive()
    def test_protocol_only_admin_cannot_bypass_logon_state(self):
        class AdminOnly:
            def recv(self,n):return encode_quote('0',1,'CSERVER','UNUSED')
        session=PriceSession(dict(target_comp_id='CSERVER',sender_comp_id='UNUSED'),AdminOnly())
        with self.assertRaises(FixError):session.receive()
        self.assertFalse(session.logged_in)
    def test_protocol_only_admin_wrong_comp_identity_refused(self):
        class AdminOnly:
            def recv(self,n):return encode_quote('0',1,'WRONG','UNUSED')
        session=PriceSession(dict(target_comp_id='CSERVER',sender_comp_id='UNUSED'),AdminOnly());session.logged_in=True
        with self.assertRaises(FixError):session.receive()

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FixControls));modules={k:str(Path(str(v.__file__)).resolve()) for k,v in sys.modules.items() if k.startswith('sfm_fx_new_age') and getattr(v,'__file__',None)}
    assert modules and all(Path(v).is_relative_to(PACKAGE) for v in modules.values()) and not any(k.startswith('sfm_fx_new_age.testing') for k in modules)
    receipt=dict(result='PASS_CONTROLS_ONLY_NOT_LIVE_FIX_ACCEPTANCE' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),package_root=str(PACKAGE),all_product_modules_from_declared_root=True,fixture_imports=[],network_attempts=0,authenticated_FIX_session_proved=False,synthetic_market_observations_created=0,published_vendor_document_examples_not_admitted_as_observations=True,constructed_administrative_only_packets_not_market_observations=True)
    with (OUT/'controls-receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt,indent=2));raise SystemExit(not result.wasSuccessful())
