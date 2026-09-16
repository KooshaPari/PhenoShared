from __future__ import annotations
import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from assurance_check import main
from reference_cases import fixture,vectors

class IntegrationAssurance(unittest.TestCase):
    def run_files(self,m,r,allow=True):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'manifest.json';b=Path(td)/'report.json'
            a.write_text(json.dumps(m));b.write_text(json.dumps(r));o=io.StringIO()
            with contextlib.redirect_stdout(o):code=main([str(a),str(b)]+(['--allow-synthetic'] if allow else []))
            return code,json.loads(o.getvalue())
    def test_real_json_io(self):
        code,r=self.run_files(*fixture());self.assertEqual(code,0);self.assertFalse(r['lifecycle_approval'])
    def test_synthetic_refused(self):self.assertEqual(self.run_files(*fixture(),allow=False)[0],1)
    def test_missing_file(self):
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(['/no-such-manifest','/no-such-report']),2)
    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'broken';p.write_text('{')
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main([str(p),str(p)]),2)
    def test_native_and_threshold(self):
        m,r=fixture()
        for c in r['cells']:c['data_origin']='native';c['covered_ids']=c['eligible_ids'][:17]
        self.assertEqual(self.run_files(m,r,False)[0],0)
    def test_null_document(self):self.assertEqual(self.run_files(None,None)[0],1)

def make_case(mutator):
    def test(self):
        m,r=fixture();mutator(m,r);code,result=self.run_files(m,r);self.assertEqual(code,1);self.assertTrue(result['errors'])
    return test
for name,mutator in vectors():setattr(IntegrationAssurance,'test_negative_'+name,make_case(mutator))
