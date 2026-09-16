from __future__ import annotations
import copy,json,sys,unittest
from pathlib import Path
from graphlib import CycleError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from estimate_dag import estimate
from validate_package import validate_records
from reference_cases import ROOT

class Schedule(unittest.TestCase):
    def task(self,i,d=(),v=(1,1,1)):
        return {'id':i,'depends_on':list(d),'estimate_hours':dict(zip(('optimistic','most_likely','pessimistic'),v))}
    def test_real_unknown_not_fabricated(self):
        r=estimate(json.loads((ROOT/'work/tasks.json').read_text()));self.assertEqual(r['status'],'UNESTIMATED');self.assertIsNone(r['critical_path_hours'])
    def test_fork_join_and_slack(self):
        r=estimate([self.task('A'),self.task('B',['A'],(2,2,2)),self.task('C',['A']),self.task('D',['B','C'])])
        self.assertEqual(r['critical_path'],['A','B','D']);self.assertEqual(r['critical_path_hours'],4);self.assertEqual(r['tasks']['C']['slack_hours'],1)
    def test_missing_estimate(self):self.assertEqual(estimate([self.task('A',v=(None,None,None))])['status'],'UNESTIMATED')
    def test_cycle(self):
        with self.assertRaises(CycleError):estimate([self.task('A',['B']),self.task('B',['A'])])
    def test_unknown_dependency(self):
        with self.assertRaises(ValueError):estimate([self.task('A',['Z'])])
    def test_bad_estimates(self):
        with self.assertRaises(ValueError):estimate([self.task('A',v=(3,2,1))])
    def test_duplicate_tasks(self):
        with self.assertRaises(ValueError):estimate([self.task('A'),self.task('A')])
    def test_no_tasks(self):self.assertEqual(estimate([])['critical_path_hours'],0)

class Records(unittest.TestCase):
    def base(self):
        rd=lambda p:json.loads((ROOT/p).read_text())
        return [rd('records/requirements.json'),rd('work/tasks.json'),rd('records/traceability.json'),rd('records/products.json'),rd('portfolio/planning-roster.json'),{x['id'] for x in [json.loads(p.read_text()) for p in (ROOT/'specs').glob('*/meta.json')]}]
    def test_actual_records(self):self.assertEqual(validate_records(*self.base()),[])
    def test_duplicate(self):
        v=self.base();v[0].append(copy.deepcopy(v[0][0]));self.assertIn('duplicate requirement',validate_records(*v))
    def test_unknown_dep(self):
        v=self.base();v[1][0]['depends_on']=['WRONG'];self.assertTrue(validate_records(*v))
    def test_cycle(self):
        v=self.base();v[1][0]['depends_on']=[v[1][1]['id']];self.assertIn('task cycle',validate_records(*v))
    def test_fake_authority(self):
        v=self.base();v[1][0]['mutation_authorized']=True;self.assertTrue(validate_records(*v))
    def test_fake_evidence(self):
        v=self.base();v[2][0]['actual_product_evidence_ids']=['fabricated'];self.assertTrue(validate_records(*v))
    def test_capacity_mismatch(self):
        v=self.base();v[4]['product_session_capacity']=999;self.assertIn('seat count mismatch',validate_records(*v))
    def test_orphan(self):
        v=self.base();v[2][0]['work_ids']=[];self.assertTrue(validate_records(*v))
