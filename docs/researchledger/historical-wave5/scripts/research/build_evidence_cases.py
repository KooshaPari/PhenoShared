"""Deterministic synthetic records. Nothing here is a paper's raw experiment data."""
from copy import deepcopy
from assess_research_evidence import COMPARISON_KEYS


def base():
    return {'id': 'synthetic', 'claim': 'task_learned', 'mode': 'paper_report',
            'source_locator': 'synthetic:section5', 'source_revision': 'v3', 'task_revision': 'task1',
            'generated': True, 'trained': True, 'training_receipt': 'synthetic:training',
            'execution_receipt': 'synthetic:execution', 'success_receipt': 'synthetic:success',
            'evaluator_revision': 'eval1', 'outcome': 'success'}


def cases():
    result = []
    def add(name, record, expected):
        result.append({'id': name, 'kind': 'admission', 'record': record, 'expected': expected})
    add('reported-learning', base(), True)
    r = base(); r.update(claim='artifact_generated', mode='assumed_success', trained=False)
    add('generated-is-admissible-as-generation', r, True)
    for field in ('source_locator', 'source_revision', 'task_revision', 'training_receipt',
                  'execution_receipt', 'success_receipt', 'evaluator_revision'):
        r = base(); r.pop(field); add('missing-' + field, r, False)
    for name, patch in [('simulated-learning', {'mode': 'assumed_success'}),
                        ('not-trained', {'trained': False}), ('claimed-success', {'outcome': 'unknown'}),
                        ('invalid-claim', {'claim': 'AGI'}), ('string-boolean', {'trained': 'true'})]:
        r = base(); r.update(patch); add(name, r, False)
    p = base(); p.update(claim='shared_policy_generalization', evaluated_tasks=['a','b'],
                         evaluated_policies=['p'], adapted_during_evaluation=False)
    add('fixed-policy-multiple-tasks', p, True)
    for name, patch in [('specialist-population', {'evaluated_policies': ['pa','pb']}),
                        ('adaptation-during-evaluation', {'adapted_during_evaluation': True}),
                        ('same-task-duplicated', {'evaluated_tasks': ['a','a']})]:
        r = deepcopy(p); r.update(patch); add(name, r, False)
    p = base(); p.update(claim='independent_reproduction', mode='independent_run',
                         evaluator_independent_of_candidate=True, reproduction_receipt='synthetic:repro',
                         protocol_revision='p1')
    add('independent-record', p, True)
    add('paper-not-reproduction', dict(p, mode='paper_report'), False)
    add('coupled-evaluator', dict(p, evaluator_independent_of_candidate=False), False)
    controls = {k: 'same' for k in COMPARISON_KEYS}; controls['timestep'] = 0.1
    result.append({'id': 'matched-controls', 'kind': 'comparison', 'a': controls, 'b': dict(controls), 'expected': True})
    for key in COMPARISON_KEYS:
        b = dict(controls); b[key] = 0.01 if key == 'timestep' else 'different'
        result.append({'id': 'changed-' + key, 'kind': 'comparison', 'a': controls, 'b': b, 'expected': False})
    result.append({'id': 'missing-controls', 'kind': 'comparison', 'a': {}, 'b': {}, 'expected': False})
    return {'scope': 'synthetic negative controls; no paper trajectories reproduced', 'cases': result}


if __name__ == '__main__':
    import json
    print(json.dumps(cases(), indent=2))
