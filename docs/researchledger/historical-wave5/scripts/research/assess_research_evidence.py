#!/usr/bin/env python3
"""Offline evidence-admission checks; no fetching, code execution, or truth oracle.

States are separate assertions, not an automatic generated -> learned pipeline.
The examples are synthetic negative controls, not replayed OMNI-EPIC trajectories.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

CLAIMS = {'artifact_generated', 'task_learned', 'shared_policy_generalization', 'independent_reproduction'}
MODES = {'assumed_success', 'paper_report', 'observed_run', 'independent_run'}
COMPARISON_KEYS = ('task_revision', 'environment_revision', 'actuator_revision', 'observer_revision',
                   'evaluator_revision', 'budget_policy', 'selection_policy', 'timestep', 'precision')


def present(value):
    return isinstance(value, str) and bool(value.strip())


def assess(record: dict) -> dict:
    """Validate the submitted record. Admission is not independent verification."""
    if not isinstance(record, dict):
        return {'admitted': False, 'reasons': ['RECORD_INVALID']}
    reasons = []
    claim, mode = record.get('claim'), record.get('mode')
    if claim not in CLAIMS:
        reasons.append('CLAIM_INVALID')
    if mode not in MODES:
        reasons.append('MODE_INVALID')
    for field in ('source_locator', 'source_revision', 'task_revision'):
        if not present(record.get(field)):
            reasons.append('MISSING_' + field.upper())
    if record.get('generated') is not True:
        reasons.append('GENERATION_NOT_RECORDED')
    if claim in {'task_learned', 'shared_policy_generalization', 'independent_reproduction'}:
        if mode == 'assumed_success':
            reasons.append('ASSUMPTION_IS_NOT_LEARNING')
        if record.get('trained') is not True:
            reasons.append('TRAINING_NOT_RECORDED')
        for field in ('training_receipt', 'execution_receipt', 'success_receipt', 'evaluator_revision'):
            if not present(record.get(field)):
                reasons.append('MISSING_' + field.upper())
        if record.get('outcome') != 'success':
            reasons.append('SUCCESS_NOT_RECORDED')
    if claim == 'shared_policy_generalization':
        tasks, policies = record.get('evaluated_tasks'), record.get('evaluated_policies')
        if not isinstance(tasks, list) or not all(present(x) for x in tasks) or len(set(tasks)) < 2:
            reasons.append('MULTIPLE_TASKS_NOT_RECORDED')
        if not isinstance(policies, list) or len(policies) != 1 or not all(present(x) for x in policies):
            reasons.append('ONE_FIXED_POLICY_NOT_RECORDED')
        if record.get('adapted_during_evaluation') is not False:
            reasons.append('FIXED_POLICY_EVALUATION_NOT_ESTABLISHED')
    if claim == 'independent_reproduction':
        if mode != 'independent_run':
            reasons.append('NOT_AN_INDEPENDENT_RUN')
        if record.get('evaluator_independent_of_candidate') is not True:
            reasons.append('EVALUATOR_INDEPENDENCE_NOT_RECORDED')
        for field in ('reproduction_receipt', 'protocol_revision'):
            if not present(record.get(field)):
                reasons.append('MISSING_' + field.upper())
    return {'id': record.get('id'), 'claim': claim, 'admitted': not reasons, 'reasons': reasons,
            'limit': 'Checks record sufficiency only; a plausible or hashed receipt may still be false.'}


def comparison(a: dict, b: dict) -> dict:
    """Reject unknown or changed controls for a claimed controlled comparison."""
    missing, changed = [], []
    for key in COMPARISON_KEYS:
        x, y = a.get(key), b.get(key)
        valid = (lambda v: type(v) in {int, float} and math.isfinite(v) and v > 0) if key == 'timestep' else present
        if not valid(x) or not valid(y):
            missing.append(key)
        elif x != y:
            changed.append(key)
    return {'controlled': not missing and not changed, 'missing': missing, 'changed': changed,
            'limit': 'Different controls can be legitimate treatments, but not an unqualified topology-only comparison.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('fixtures', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    fixtures = json.loads(args.fixtures.read_text())
    results = []
    for case in fixtures['cases']:
        result = assess(case['record']) if case['kind'] == 'admission' else comparison(case['a'], case['b'])
        actual = result['admitted'] if case['kind'] == 'admission' else result['controlled']
        results.append({'case_id': case['id'], 'expected': case['expected'], 'actual': actual,
                        'matched_expectation': actual == case['expected'], 'detail': result})
    report = {'experiment': 'EG-W5-RECORD-ADMISSION', 'scope': 'synthetic negative-control fixtures only',
              'cases': len(results), 'passed': all(r['matched_expectation'] for r in results), 'results': results,
              'not_claimed': ['live agent benchmark', 'independent paper reproduction', 'automated source truth validation']}
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
