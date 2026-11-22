"""Execute the capture's exact MDReqID guard, not a simulated FIX session.

Only metadata controls and unchanged literal vendor documentation enter this
isolated guard. No market packets, prices, books or timestamps are fabricated,
repaired, admitted, rendered or labelled genuine. This is NOT live acceptance.
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
from sfm_fx_new_age.connector.fix_protocol import FixError, one

PRODUCER = Path(os.environ.get('SFM_FIX_PRODUCER', str(PACKAGE/'sfm_fx_new_age/connector/fix_capture.py'))).resolve(strict=True)
OUT = Path(os.environ['SFM_FIX_CHECK_OUT']).resolve()
OUT.mkdir(parents=True, exist_ok=False, mode=0o700)
EXAMPLES = Path(os.environ['SFM_FIX_EVIDENCE']).resolve(strict=True)/'research/published-fix-examples.json'
TREE = ast.parse(PRODUCER.read_bytes())
OWNER = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'capture_fix_price')
BRANCHES = [n for n in ast.walk(OWNER) if isinstance(n, ast.If)
            and isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name) and n.test.left.id == 'kind'
            and len(n.test.ops) == 1 and isinstance(n.test.ops[0], ast.In)
            and isinstance(n.test.comparators[0], ast.Set)
            and {getattr(v, 'value', None) for v in n.test.comparators[0].elts} == {'W', 'X'}]
assert len(BRANCHES) == 1
BRANCH = BRANCHES[0]
GUARDS = [n for n in BRANCH.body if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
          and isinstance(n.test.left, ast.Call) and isinstance(n.test.left.func, ast.Name)
          and n.test.left.func.id == 'one' and len(n.test.left.args) >= 2
          and isinstance(n.test.left.args[1], ast.Constant) and n.test.left.args[1].value == 262]
assert len(GUARDS) == 1
GUARD = GUARDS[0]
# Compile the existing statement unmodified; the test does not reimplement it.
CHECK = compile(ast.Module(body=[GUARD], type_ignores=[]), str(PRODUCER), 'exec')
REQUEST = 'NONMARKET_REQUEST_BINDING_A'
DOCUMENT_FIELDS = [tuple((int(v.partition('=')[0]), v.partition('=')[2])
                        for v in row['text'].rstrip('|').split('|'))
                   for row in json.loads(EXAMPLES.read_bytes()) if row['type'] in {'W', 'X'}]
assert DOCUMENT_FIELDS and all(not any(k == 262 for k, v in f) for f in DOCUMENT_FIELDS)


def check(fields, request_id=REQUEST):
    exec(CHECK, {'__builtins__': {}, 'one': one, 'FixError': FixError},
         dict(fields=fields, request_id=request_id))


class FixRequestBindingChecks(unittest.TestCase):
    def test_missing_request_metadata_is_not_defaulted_to_expected(self):
        with self.assertRaisesRegex(FixError, '^Missing/duplicate FIX scalar$'):
            check(())

    def test_exact_request_metadata_passes_this_guard_only(self):
        self.assertIsNone(check(((262, REQUEST),)))

    def test_wrong_request_metadata_is_refused(self):
        with self.assertRaisesRegex(FixError, '^Book request identity mismatch$'):
            check(((262, 'NONMARKET_REQUEST_BINDING_B'),))

    def test_duplicate_equal_request_metadata_is_refused(self):
        with self.assertRaisesRegex(FixError, '^Missing/duplicate FIX scalar$'):
            check(((262, REQUEST), (262, REQUEST)))

    def test_duplicate_mixed_request_metadata_is_refused(self):
        with self.assertRaisesRegex(FixError, '^Missing/duplicate FIX scalar$'):
            check(((262, REQUEST), (262, 'NONMARKET_REQUEST_BINDING_B')))

    def test_prefix_or_suffix_is_not_exact_request_identity(self):
        for token in (REQUEST+'-tail', 'head-'+REQUEST, REQUEST.lower()):
            with self.subTest(token=token), self.assertRaisesRegex(FixError, '^Book request identity mismatch$'):
                check(((262, token),))

    def test_unchanged_incomplete_document_examples_cannot_bypass_guard(self):
        for fields in DOCUMENT_FIELDS:
            with self.subTest(kind=one(fields, 35)), self.assertRaisesRegex(FixError, '^Missing/duplicate FIX scalar$'):
                check(fields)

    def test_actual_guard_precedes_book_changes_and_publication(self):
        guard_index = BRANCH.body.index(GUARD)
        apply_indexes = [i for i, n in enumerate(BRANCH.body) if any(isinstance(c, ast.Call)
                         and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name)
                         and c.func.value.id == 'book' and c.func.attr == 'apply' for c in ast.walk(n))]
        publication_indexes = [i for i, n in enumerate(BRANCH.body) if any(isinstance(c, ast.Call)
                               and isinstance(c.func, ast.Name) and c.func.id == 'snapshot_envelope' for c in ast.walk(n))]
        self.assertEqual(len(apply_indexes), 1)
        self.assertEqual(len(publication_indexes), 1)
        self.assertLess(guard_index, apply_indexes[0])
        self.assertLess(apply_indexes[0], publication_indexes[0])
        self.assertEqual(ast.dump(ast.parse(PRODUCER.read_bytes()), include_attributes=False), ast.dump(TREE, include_attributes=False))


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FixRequestBindingChecks))
    receipt = dict(result='PASS_REQUEST_METADATA_CONTROLS_NOT_LIVE_FIX' if result.wasSuccessful() else 'FAIL',
                   tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                   producer_sha256=hashlib.sha256(PRODUCER.read_bytes()).hexdigest(),
                   guard_ast_sha256=hashlib.sha256(ast.dump(GUARD, include_attributes=False).encode()).hexdigest(),
                   guard_source_span=[GUARD.lineno, GUARD.end_lineno], exact_production_guard_executed=True,
                   document_sha256=hashlib.sha256(EXAMPLES.read_bytes()).hexdigest(),
                   market_packets_constructed=0, market_observations_admitted=0, network_attempts=0,
                   genuine_fix_or_dom_qualified=False, document_examples_unchanged=True,
                   fixture_imports=[k for k in sys.modules if k.startswith('sfm_fx_new_age.testing')])
    with (OUT/'request-binding-checks.json').open('x') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    print(json.dumps(receipt, indent=2))
    raise SystemExit(not result.wasSuccessful())
