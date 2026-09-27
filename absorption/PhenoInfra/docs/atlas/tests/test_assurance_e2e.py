from __future__ import annotations
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from reference_cases import fixture,vectors,ROOT

class EndToEndAssurance(unittest.TestCase):
    def run_files(self,m,r,allow=True):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'manifest.json';b=Path(td)/'report.json';a.write_text(json.dumps(m));b.write_text(json.dumps(r))
            cmd=[sys.executable]
            dest=os.environ.get('QA_REFERENCE_COVERAGE_DIR')
            if dest:cmd+=['-m','coverage','run','--branch','--parallel-mode','--source=scripts','--data-file='+str(Path(dest)/'.coverage.e2e')]
            cmd+=[str(ROOT/'scripts/assurance_check.py'),str(a),str(b)]+(['--allow-synthetic'] if allow else [])
            c=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=20)
            return c.returncode,json.loads(c.stdout)
    def test_instantiated_cli(self):
        code,out=self.run_files(*fixture());self.assertEqual(code,0);self.assertFalse(out['product_tests_executed'])
    def test_synthetic_refused(self):self.assertEqual(self.run_files(*fixture(),allow=False)[0],1)
    def test_native_threshold(self):
        m,r=fixture()
        for c in r['cells']:c['data_origin']='native';c['covered_ids']=c['eligible_ids'][:17]
        self.assertEqual(self.run_files(m,r,False)[0],0)
    def test_null_document(self):self.assertEqual(self.run_files(None,None)[0],1)

def make_case(mutator):
    def test(self):
        m,r=fixture();mutator(m,r);code,result=self.run_files(m,r);self.assertEqual(code,1);self.assertEqual(result['status'],'REJECTED')
    return test
for name,mutator in vectors():setattr(EndToEndAssurance,'test_negative_'+name,make_case(mutator))
