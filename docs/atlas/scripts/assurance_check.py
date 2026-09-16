#!/usr/bin/env python3
"""Reference measurement-consistency checker; never grants product/lifecycle approval.

No product execution, native-report parsing, signature verification or credential checks
are performed. Synthetic fixtures are rejected unless deliberately enabled for testing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

KEY_FIELDS = ('component', 'language', 'platform', 'profile', 'family', 'metric')


def digest_ids(values: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(values), separators=(',', ':')).encode()).hexdigest()


def cell_key(value: dict[str, Any]) -> tuple[str, ...]:
    result = tuple(value.get(k) for k in KEY_FIELDS)
    if any(not isinstance(x, str) or not x.strip() for x in result):
        raise ValueError('Each required cell needs six nonempty identity fields')
    return result  # type: ignore[return-value]


def ids(value: Any, name: str, allow_empty: bool = True) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError(name + ' must be a list of nonempty strings')
    if len(value) != len(set(value)):
        raise ValueError(name + ' contains duplicate IDs')
    if not allow_empty and not value:
        raise ValueError(name + ' must not be empty')
    return set(value)


def evaluate(manifest: dict[str, Any], report: dict[str, Any], allow_synthetic: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    measurements: list[dict[str, Any]] = []
    try:
        if manifest.get('schema_version') != '1' or report.get('schema_version') != '1':
            raise ValueError('Unsupported schema version')
        for field in ('subject_id', 'revision', 'artifact_sha256'):
            if not isinstance(manifest.get(field), str) or not manifest[field]:
                raise ValueError('Missing expected ' + field)
        required = manifest.get('required_cells')
        cells = report.get('cells')
        if not isinstance(required, list) or not required:
            raise ValueError('No required measurement cells: no acceptance denominator')
        if not isinstance(cells, list):
            raise ValueError('Report cells must be a list')
        expected: dict[tuple[str, ...], dict[str, Any]] = {}
        for spec in required:
            k = cell_key(spec)
            if k in expected:
                raise ValueError('Duplicate required cell')
            eligible = ids(spec.get('eligible_ids'), 'expected eligible', False)
            critical = ids(spec.get('critical_ids'), 'expected critical')
            ids(spec.get('required_checks'), 'expected checks', False)
            if not critical <= eligible:
                raise ValueError('Expected critical IDs outside eligible inventory')
            floor = spec.get('minimum_percent')
            if type(floor) is not int or not 85 <= floor <= 100:
                raise ValueError('Required floor must be an integer from 85 to 100')
            if spec.get('denominator_sha256') != digest_ids(spec['eligible_ids']):
                raise ValueError('Expected denominator digest mismatch')
            expected[k] = spec
        observed: dict[tuple[str, ...], dict[str, Any]] = {}
        run_family: dict[str, str] = {}
        for cell in cells:
            k = cell_key(cell)
            if k in observed:
                raise ValueError('Duplicate reported cell')
            if k not in expected:
                raise ValueError('Unexpected cell not present in required profile')
            observed[k] = cell
            spec = expected[k]
            prefix = '/'.join(k) + ': '
            local: list[str] = []
            for field in ('subject_id', 'revision', 'artifact_sha256'):
                if cell.get(field) != manifest[field]:
                    local.append('wrong ' + field)
            origin = cell.get('data_origin')
            if origin not in ('native', 'synthetic'):
                local.append('unknown measurement origin')
            if origin == 'synthetic' and not allow_synthetic:
                local.append('synthetic evidence is not product proof')
            eligible = ids(cell.get('eligible_ids'), 'reported eligible', False)
            covered = ids(cell.get('covered_ids'), 'covered')
            critical = ids(cell.get('critical_ids'), 'critical')
            if eligible != set(spec['eligible_ids']):
                local.append('denominator inventory changed')
            if cell.get('denominator_sha256') != spec['denominator_sha256']:
                local.append('denominator digest mismatch')
            if critical != set(spec['critical_ids']):
                local.append('critical set changed')
            if not covered <= eligible:
                local.append('unknown covered item')
            if not critical <= covered:
                local.append('critical coverage incomplete')
            if 100 * len(covered) < spec['minimum_percent'] * len(eligible):
                local.append('below independent floor')
            if cell.get('run_status') != 'completed' or cell.get('outcome') != 'pass':
                local.append('run not completed and passing')
            if cell.get('accumulator_families') != [cell['family']]:
                local.append('mixed or wrong-family accumulator')
            run = cell.get('run_id')
            if not isinstance(run, str) or not run:
                local.append('missing run identity')
            elif run in run_family and run_family[run] != cell['family']:
                local.append('one run reused across independent families')
            else:
                run_family[run] = cell['family']
            checks = cell.get('checks')
            if not isinstance(checks, list) or not checks:
                local.append('no executed checks')
                checks = []
            check_ids = [c.get('id') for c in checks if isinstance(c, dict)]
            if len(check_ids) != len(checks) or any(not isinstance(x, str) or not x for x in check_ids):
                local.append('malformed checks')
            elif len(set(check_ids)) != len(check_ids):
                local.append('duplicate checks')
            passing = {c.get('id') for c in checks if isinstance(c, dict) and c.get('status') == 'pass'}
            if not set(spec['required_checks']) <= passing:
                local.append('required checks missing or nonpassing')
            if not isinstance(cell.get('evidence_refs'), list) or not cell['evidence_refs']:
                local.append('no evidence references')
            errors.extend(prefix + x for x in local)
            measurements.append({'cell': list(k), 'covered': len(covered), 'eligible': len(eligible),
                                 'percent': 100 * len(covered) / len(eligible), 'consistent': not local})
        for k in expected.keys() - observed.keys():
            errors.append('/'.join(k) + ': required cell missing')
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        errors.append('Malformed or inconsistent record: ' + str(exc))
    return {'status': 'REJECTED' if errors else 'RECORDS_CONSISTENT', 'errors': sorted(errors),
            'measurements': measurements, 'lifecycle_approval': False, 'authenticated_producer': False,
            'native_reports_parsed': False, 'product_tests_executed': False,
            'limitation': 'Record consistency only; no source truth, receipt authenticity, payload integrity or product acceptance is established.'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('--allow-synthetic', action='store_true', help='Only for reference fixture testing; never product approval')
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        report = json.loads(args.report.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'INPUT_ERROR', 'error': str(exc), 'lifecycle_approval': False}))
        return 2
    result = evaluate(manifest, report, args.allow_synthetic)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'RECORDS_CONSISTENT' else 1


if __name__ == '__main__':
    sys.exit(main())
