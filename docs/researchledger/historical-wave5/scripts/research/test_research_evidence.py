import copy
import unittest
from assess_research_evidence import assess, comparison, COMPARISON_KEYS
from build_evidence_cases import base, cases


class EvidenceTests(unittest.TestCase):
    def test_assumed_learning_rejected(self):
        r = base(); r['mode'] = 'assumed_success'
        self.assertFalse(assess(r)['admitted'])
    def test_generation_does_not_require_training(self):
        r = base(); r.update(claim='artifact_generated', mode='assumed_success', trained=False)
        self.assertTrue(assess(r)['admitted'])
    def test_report_not_reproduction(self):
        r = base(); r['claim'] = 'independent_reproduction'
        self.assertFalse(assess(r)['admitted'])
    def test_specialists_not_single_generalist(self):
        r = base(); r.update(claim='shared_policy_generalization', evaluated_tasks=['a','b'],
                             evaluated_policies=['pa','pb'], adapted_during_evaluation=False)
        self.assertFalse(assess(r)['admitted'])
    def test_no_mutation(self):
        r = base(); old = copy.deepcopy(r); assess(r); self.assertEqual(r, old)
    def test_truthy_strings_do_not_satisfy_flags(self):
        r = base(); r['trained'] = 'true'; self.assertFalse(assess(r)['admitted'])
    def test_unknown_outcome_not_success(self):
        r = base(); r['outcome'] = 'unknown'; self.assertFalse(assess(r)['admitted'])
    def test_unknown_control_not_equal(self):
        self.assertFalse(comparison({}, {})['controlled'])
    def test_timestep_is_treatment(self):
        a = {k: 'same' for k in COMPARISON_KEYS}; a['timestep'] = 0.1
        b = dict(a, timestep=0.01)
        self.assertEqual(comparison(a,b)['changed'], ['timestep'])
    def test_nan_invalid(self):
        a = {k: 'same' for k in COMPARISON_KEYS}; a['timestep'] = float('nan')
        self.assertIn('timestep', comparison(a,a)['missing'])
    def test_empty_policy_invalid(self):
        r = base(); r.update(claim='shared_policy_generalization', evaluated_tasks=['a','b'],
                             evaluated_policies=[''], adapted_during_evaluation=False)
        self.assertFalse(assess(r)['admitted'])
    def test_all_fixture_expectations(self):
        for case in cases()['cases']:
            with self.subTest(case=case['id']):
                value = assess(case['record'])['admitted'] if case['kind']=='admission' else comparison(case['a'],case['b'])['controlled']
                self.assertEqual(value, case['expected'])


if __name__ == '__main__':
    unittest.main()
