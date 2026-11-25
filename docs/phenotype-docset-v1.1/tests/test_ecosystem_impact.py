"""Structural negative controls, not native consumer verification."""
from __future__ import annotations
import copy, json, unittest
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[1]

class EcosystemImpactSchema(unittest.TestCase):
    def setUp(self):
        self.example=json.loads((ROOT/'examples/ecosystem-impact.json').read_text())
        self.validator=jsonschema.Draft202012Validator(json.loads((ROOT/'schemas/ecosystem-impact.schema.json').read_text()))
    def valid(self,record): return not list(self.validator.iter_errors(record))
    def test_synthetic_planned_example_valid(self): self.assertTrue(self.valid(self.example))
    def test_approval_cannot_be_granted(self):
        self.example['lifecycle_approval']=True; self.assertFalse(self.valid(self.example))
    def test_internal_reuse_search_required(self):
        del self.example['reuse']['internal_search']; self.assertFalse(self.valid(self.example))
    def test_external_reuse_search_required(self):
        del self.example['reuse']['external_search']; self.assertFalse(self.valid(self.example))
    def test_material_change_needs_consumer_entry(self):
        self.example['consumers']=[]; self.assertFalse(self.valid(self.example))
    def test_local_change_can_document_empty_consumer_set(self):
        self.example['materiality']='local-no-contract-impact';self.example['consumers']=[];self.assertTrue(self.valid(self.example))
    def test_consumer_tiers_are_explicit(self):
        self.example['consumers'][0]['tier']='everyone';self.assertFalse(self.valid(self.example))
    def test_consumer_constraints_required(self):
        self.example['consumers'][0]['constraints']=[];self.assertFalse(self.valid(self.example))
    def test_downstream_costs_required(self):
        del self.example['ecosystem_effects']['downstream_costs'];self.assertFalse(self.valid(self.example))
    def test_no_unsupported_measurement_state(self):
        self.example['ecosystem_effects']['measurement_status']='proven';self.assertFalse(self.valid(self.example))
    def test_actual_review_needs_evidence_reference(self):
        self.example['verification']['state']='evidence-ready-for-review';self.assertFalse(self.valid(self.example))
    def test_reference_is_not_authentication(self):
        self.example['verification']['state']='evidence-ready-for-review';self.example['verification']['evidence_refs']=['unverified-reference'];self.assertTrue(self.valid(self.example));self.assertFalse(self.example['lifecycle_approval'])
    def test_rollback_required(self):
        del self.example['coordination']['rollback'];self.assertFalse(self.valid(self.example))
    def test_bridge_exit_required(self):
        del self.example['coordination']['temporary_bridge_exit'];self.assertFalse(self.valid(self.example))
    def test_unknown_field_rejected(self):
        self.example['auto_merge']=True;self.assertFalse(self.valid(self.example))
    def test_blank_rationale_rejected(self):
        self.example['reuse']['rationale']='';self.assertFalse(self.valid(self.example))
    def test_baseline_requirements_and_trace_retained(self):
        req=json.loads((ROOT/'records/requirements.json').read_text()); trace=json.loads((ROOT/'records/traceability.json').read_text())
        ids={r['id'] for r in req};self.assertTrue({'REQ-06-01','REQ-06-08','REQ-06-09','REQ-06-20'}<=ids)
        for t in trace:
            if t['requirement_id'] in {f'REQ-06-{i:02d}' for i in range(9,21)}:
                self.assertIn('INT-003',t['intent_ids']);self.assertTrue(t['work_ids']);self.assertEqual(t['actual_product_evidence_ids'],[])
    def test_all_product_dossiers_reference_shared_policy(self):
        for p in (ROOT/'products').glob('*/DOSSIER.md'):
            with self.subTest(product=p.parent.name):self.assertIn('ECOSYSTEM-FIRST-EVOLUTION.md',p.read_text())

if __name__=='__main__':unittest.main()
