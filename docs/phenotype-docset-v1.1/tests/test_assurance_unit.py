from __future__ import annotations
import contextlib,copy,io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from assurance_check import evaluate,main,cell_key,digest_ids,ids
from reference_cases import fixture,vectors

class UnitAssurance(unittest.TestCase):
    def test_good_and_synthetic_denied(self):
        m,r=fixture();self.assertEqual(evaluate(m,r)['status'],'REJECTED')
        out=evaluate(m,r,True);self.assertEqual(out['status'],'RECORDS_CONSISTENT');self.assertFalse(out['lifecycle_approval']);self.assertFalse(out['authenticated_producer'])
    def test_exact_threshold(self):
        m,r=fixture();r['cells'][0]['covered_ids']=r['cells'][0]['eligible_ids'][:17]
        self.assertEqual(evaluate(m,r,True)['status'],'RECORDS_CONSISTENT')
    def test_native_record_not_authentication(self):
        m,r=fixture()
        for c in r['cells']:c['data_origin']='native'
        out=evaluate(m,r);self.assertEqual(out['status'],'RECORDS_CONSISTENT');self.assertFalse(out['authenticated_producer'])
    def test_null_input(self):self.assertEqual(evaluate(None,None)['status'],'REJECTED')
    def test_helpers(self):
        self.assertEqual(digest_ids(['b','a']),digest_ids(['a','b']))
        self.assertEqual(ids([], 'empty'),set())
        with self.assertRaises(ValueError):cell_key({})
    def test_cli_core_mocked_io(self):
        m,r=fixture()
        with patch('pathlib.Path.read_text',side_effect=[json.dumps(m),json.dumps(r)]),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['manifest','report','--allow-synthetic']),0)
        with patch('pathlib.Path.read_text',side_effect=[json.dumps(m),json.dumps(r)]),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['manifest','report']),1)
    def test_cli_read_error(self):
        with patch('pathlib.Path.read_text',side_effect=OSError('not found')),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(['m','r']),2)
    def test_cli_json_error(self):
        with patch('pathlib.Path.read_text',return_value='{'),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(['m','r']),2)

def make_case(mutator):
    def test(self):
        m,r=fixture();mutator(m,r);self.assertEqual(evaluate(m,r,True)['status'],'REJECTED')
    return test
for name,mutator in vectors():setattr(UnitAssurance,'test_negative_'+name,make_case(mutator))
