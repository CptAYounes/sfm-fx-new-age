"""FIX publication revision contract on unchanged original-price evidence.

No FIX market packet, execution tape, sequence history or book is fabricated.
The producer's actual AST expression is executed for transport metadata only;
a retained official vendor sequence is NOT treated as original market data.
The resulting envelope-revision value is tested through the real input store
using unchanged original INTRABAR_PRICES observations, never a made-up book.
This qualifies the metadata handoff, not an authenticated FIX/DOM stream.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import sys
import unittest

PACKAGE = Path(os.environ['SFM_FIX_PACKAGE_ROOT']).resolve(strict=True)
sys.path.insert(0, str(PACKAGE))
from sfm_fx_new_age.contracts.supplemental import SupplementalEvidence
from sfm_fx_new_age.contracts.supplemental_wire import validate_wire_shape
from sfm_fx_new_age.services.supplemental import SupplementalEvidenceStore
from sfm_fx_new_age.storage.database import Database, StateConflict

OUT = Path(os.environ['SFM_FIX_CHECK_OUT']).resolve()
OUT.mkdir(parents=True, exist_ok=False, mode=0o700)
ORIGINAL = Path(os.environ['SFM_ORIGINAL_TPO']).resolve(strict=True)
PRODUCER = Path(os.environ.get('SFM_FIX_PRODUCER', str(PACKAGE/'sfm_fx_new_age/connector/fix_capture.py'))).resolve(strict=True)
DOCUMENTS = Path(os.environ['SFM_FIX_EVIDENCE']).resolve(strict=True)
BODY = json.loads(ORIGINAL.read_bytes())
assert BODY['kind']=='INTRABAR_PRICES' and BODY['origin']=='LIVE_OBSERVED' and BODY.get('revision',1)==1
EXAMPLES = json.loads((DOCUMENTS/'research/published-fix-examples.json').read_bytes())
FULL = next(row for row in EXAMPLES if row['type']=='W' and '|271=' in row['text'])
NATIVE_SEQUENCE = int(next(field[3:] for field in FULL['text'].split('|') if field.startswith('34=')))
assert NATIVE_SEQUENCE > 1
TREE = ast.parse(PRODUCER.read_text())
FUNCTION = next(node for node in TREE.body if isinstance(node,ast.FunctionDef) and node.name=='snapshot_envelope')
CONSTRUCTOR = next(node.value for node in FUNCTION.body if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) and node.target.id=='body')
assert isinstance(CONSTRUCTOR,ast.Call)
REVISION = next(keyword.value for keyword in CONSTRUCTOR.keywords if keyword.arg=='revision')
RECORDS = next(keyword.value for keyword in CONSTRUCTOR.keywords if keyword.arg=='records')
assert isinstance(RECORDS,ast.List)
RECORD = RECORDS.elts[0]
assert isinstance(RECORD,ast.Call)
SEQUENCE = next(keyword.value for keyword in RECORD.keywords if keyword.arg=='sequence')
IDENTITY = next(keyword.value for keyword in RECORD.keywords if keyword.arg=='id')


def expression(node, sequence):
    return eval(compile(ast.Expression(node), str(PRODUCER), 'eval'), {'__builtins__': {'str':str}},
                dict(sequence=sequence, session_identity='SPECIFICATION_ONLY_METADATA_CONTROL', symbol=BODY['symbol']))


class OriginalMarket:
    scope_id = BODY['scope_id']
    def authority(self, symbol):
        if symbol != BODY['symbol']:
            return None
        return {key:BODY[key] for key in ('scope_id','source_epoch','symbol','origin')}


def make_store():
    database = Database()
    store = SupplementalEvidenceStore(database, OriginalMarket(), lambda:BODY['available_at'], lambda *args:None)
    store.register_provider(BODY['provider_id'], kinds=[BODY['kind']], origin=BODY['origin'])
    return database, store


def original_evidence(revision):
    return SupplementalEvidence(**dict(BODY, records=tuple(BODY['records']), revision=revision))


class FixPublicationOriginalChecks(unittest.TestCase):
    def test_first_publication_revision_matches_actual_store_on_original_prices(self):
        revision = expression(REVISION, NATIVE_SEQUENCE)
        database, store = make_store()
        try:
            # Exercise the producer-derived revision through the actual reader.
            count = store.accept(original_evidence(revision))
            self.assertEqual(count, 1)
            self.assertEqual(revision, 1)
            self.assertEqual(store.snapshot(BODY['symbol'],BODY['available_at'])[BODY['kind']]['records'], BODY['records'])
        finally:
            database.close()

    def test_envelope_revision_is_independent_of_session_sequence(self):
        for sequence in (NATIVE_SEQUENCE, NATIVE_SEQUENCE+1, 2147483647):
            self.assertEqual(expression(REVISION,sequence),1)
            self.assertEqual(expression(SEQUENCE,sequence),sequence)

    def test_native_record_identity_and_sequence_are_not_renumbered(self):
        identity = expression(IDENTITY,NATIVE_SEQUENCE)
        self.assertEqual(identity,'SPECIFICATION_ONLY_METADATA_CONTROL:'+str(NATIVE_SEQUENCE)+':'+BODY['symbol'])
        self.assertEqual(expression(SEQUENCE,NATIVE_SEQUENCE),NATIVE_SEQUENCE)

    def test_actual_store_still_rejects_nonone_initial_revision(self):
        database, store = make_store()
        try:
            with self.assertRaisesRegex(StateConflict, '^First optional revision must be one$'):
                store.accept(original_evidence(NATIVE_SEQUENCE))
            self.assertEqual(database.list('supplemental_evidence'),[])
        finally:
            database.close()

    def test_original_envelope_and_observation_bytes_are_not_modified(self):
        candidate = original_evidence(expression(REVISION,NATIVE_SEQUENCE))
        validate_wire_shape(candidate)
        self.assertEqual(list(candidate.records),BODY['records'])
        for key in ('scope_id','source_epoch','symbol','origin','source_ref','venue','instrument','price_domain','unit',
                    'window_start','window_end','available_at','valid_until','complete','parameters'):
            self.assertEqual(getattr(candidate,key),BODY[key])

    def test_repeated_same_original_publication_is_idempotent(self):
        database, store = make_store()
        try:
            evidence = original_evidence(expression(REVISION,NATIVE_SEQUENCE))
            self.assertEqual(store.accept(evidence),1)
            self.assertEqual(store.accept(evidence),0)
            self.assertEqual(len(database.list('supplemental_evidence')),1)
        finally:
            database.close()

    def test_optional_input_store_first_revision_rule_remains_source_owned(self):
        tree = ast.parse((PACKAGE/'sfm_fx_new_age/services/supplemental.py').read_text())
        source = ast.dump(tree,include_attributes=False)
        self.assertIn('First optional revision must be one',source)
        self.assertNotIn('sfm_fx_new_age.testing',sys.modules)


if __name__=='__main__':
    run = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FixPublicationOriginalChecks))
    receipt = dict(result='PASS_METADATA_HANDOFF_NOT_LIVE_FIX_DOM' if run.wasSuccessful() else 'FAIL',
        tests_run=run.testsRun,failures=len(run.failures),errors=len(run.errors),skipped=len(run.skipped),
        producer_sha256=hashlib.sha256(PRODUCER.read_bytes()).hexdigest(),
        input_sha256=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        exact_producer_ast_expression_executed=True, original_kind=BODY['kind'],
        market_observations_modified=False, synthetic_market_observations=0,
        specification_sequence_is_nonmarket_control=True, authenticated_fix_or_dom_proved=False,
        fixture_imports=[key for key in sys.modules if key.startswith('sfm_fx_new_age.testing')])
    with (OUT/'publication-checks.json').open('x') as stream:
        json.dump(receipt,stream,indent=2)
        stream.write('\n')
    print(json.dumps(receipt,indent=2))
    raise SystemExit(0 if run.wasSuccessful() else 1)
