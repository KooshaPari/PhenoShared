#!/usr/bin/env python3
"""Read-only snapshot audit. Prints JSON; does not execute collected source code.

Run from any directory: python3 -B /absolute/path/to/inspect_snapshot.py
The only imported project implementation is rubric/scoring.py. Synthetic inputs
are supplied through mocked open(), so diagnostic probes do not modify files.
"""
import collections
import hashlib
import importlib.util
import io
import json
import platform
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def read(rel):
    return json.loads((ROOT / rel).read_text())


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    inventory = []
    groups = collections.defaultdict(lambda: {'files': 0, 'bytes': 0})
    for p in sorted(ROOT.rglob('*')):
        rel = p.relative_to(ROOT)
        if rel.parts[0] in ('audits', 'docs') or not p.is_file():
            continue
        stat = p.stat()
        row = {'path': str(rel), 'bytes': stat.st_size, 'sha256': digest(p)}
        inventory.append(row)
        groups[rel.parts[0]]['files'] += 1
        groups[rel.parts[0]]['bytes'] += stat.st_size
    rubric = read('rubric/rubric-v1.json')
    criteria = rubric['criteria']
    counts = collections.Counter(c['id'] for c in criteria)
    evidence = read('rubric/evidence-index.json')
    spec = importlib.util.spec_from_file_location('snapshot_scoring', ROOT / 'rubric/scoring.py')
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    cards = []
    for p in sorted((ROOT / 'scorecards').glob('*-audit.json')):
        data = json.loads(p.read_text())
        result = engine.score(str(ROOT / 'rubric/rubric-v1.json'), str(p))
        cards.append({'file': p.name, 'input_records': len(data.get('criteria', [])),
                      'unique_input_ids': len({c['id'] for c in data.get('criteria', [])}),
                      'scored': result['scored'], 'overall_pct': result['overall_pct'],
                      'grade': result['grade'], 'rubric_row_coverage_pct': round(100 * result['scored'] / len(criteria), 3)})

    def probe(rows, audit):
        docs = {'rubric': json.dumps({'criteria': rows}), 'audit': json.dumps({'criteria': audit})}
        try:
            with patch('builtins.open', side_effect=lambda p: io.StringIO(docs[p])):
                return engine.score('rubric', 'audit')
        except Exception as exc:
            return {'exception': type(exc).__name__, 'message': str(exc)}

    base = [{'id': 'AA-001', 'domain': 'one'}, {'id': 'BB-001', 'domain': 'two'}]
    probes = {
        'duplicate_rubric_id': probe([{'id': 'AA-001', 'domain': 'one'}, {'id': 'AA-001', 'domain': 'two'}], [{'id': 'AA-001', 'status': 'satisfied'}]),
        'unassessed_excluded': probe(base, [{'id': 'AA-001', 'status': 'satisfied'}]),
        'unknown_status': probe(base, [{'id': 'AA-001', 'status': 'typo'}]),
        'null_weight': probe(base, [{'id': 'AA-001', 'status': 'satisfied', 'weight': None}]),
        'negative_weight': probe(base, [{'id': 'AA-001', 'status': 'missing', 'weight': -1}, {'id': 'BB-001', 'status': 'satisfied', 'weight': 2}]),
        'duplicate_audit_last_wins': probe(base, [{'id': 'AA-001', 'status': 'missing'}, {'id': 'AA-001', 'status': 'satisfied'}]),
        'empty_audit': probe(base, []),
    }
    indexes = []
    for p in sorted((ROOT / 'chats').glob('*/session-index.tsv')):
        lines = p.read_text().splitlines()
        fields = [line.split('\t') for line in lines]
        indexes.append({'file': str(p.relative_to(ROOT)), 'lines': len(lines),
                        'field_counts': dict(collections.Counter(len(f) for f in fields)),
                        'duplicate_first_fields': len(fields) - len({f[0] for f in fields}),
                        'paths_resolving_relative_to_index': sum((p.parent / f[0]).is_file() for f in fields)})
    unresolved = []
    path_types = collections.Counter()
    for item in evidence['index']:
        value = item.get('resolved_path') or ''
        if value.startswith(('https://', 'http://')):
            path_types['url_not_live_verified'] += 1
        else:
            p = ROOT / value
            kind = 'file' if p.is_file() else 'directory' if p.is_dir() else 'missing'
            path_types[kind] += 1
            if kind == 'missing':
                unresolved.append({'id': item['id'], 'path': value})
    manifest = (ROOT / 'repos/MANIFEST.md').read_text()
    manifest_rows = re.findall(r'^\| (.+) \| ([0-9a-f]{12}) \|$', manifest, re.M)
    bad_manifest = []
    for rel, expected in manifest_rows:
        p = ROOT / 'repos' / rel
        if not p.is_file() or not digest(p).startswith(expected):
            bad_manifest.append(rel)
    archive = ROOT / 'chats/codex/sessions/01a0606a-b33a-7e52-934a-7774d75843a2.jsonl'
    original = Path('/Users/kooshapari/.codex/sessions/2026/09/01/rollout-2026-09-01T21-40-00-01a0606a-b33a-7e52-934a-7774d75843a2.jsonl')
    records = [json.loads(line) for line in archive.read_text().splitlines() if line.strip()]
    with zipfile.ZipFile(ROOT / 'windows/audit-collect.zip') as z:
        zip_check = {'entries': len(z.infolist()), 'first_bad_crc_entry': z.testzip()}
    report = {
        'captured_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
        'scope': str(ROOT), 'inventory_exclusions': ['audits/', 'docs/'],
        'inventory_groups': dict(groups), 'file_count': len(inventory),
        'rubric': {'rows': len(criteria), 'unique_ids': len(counts),
                   'duplicate_id_groups': sum(v > 1 for v in counts.values()),
                   'excess_rows_over_unique_ids': len(criteria) - len(counts),
                   'domains': len({c['domain'] for c in criteria}),
                   'invalid_id_pattern_rows': sum(not re.fullmatch(r'[A-Z]{2,4}-[0-9]{3,5}', c['id']) for c in criteria),
                   'status_counts': dict(collections.Counter(c['status'] for c in criteria)),
                   'duplicate_examples': [{'id': key, 'count': value} for key, value in counts.most_common(8)]},
        'evidence': {'resolution_counts': dict(collections.Counter(x['resolution'] for x in evidence['index'])),
                     'declared_resolved': evidence['summary']['resolved'],
                     'domain_resolved_sum': sum(v['resolved'] for v in evidence['summary']['by_domain'].values()),
                     'local_path_checks': dict(path_types), 'missing_paths': unresolved},
        'scorecards_recomputed': cards, 'diagnostic_probes': probes, 'session_indexes': indexes,
        'template_manifest': {'rows': len(manifest_rows), 'missing_or_hash_mismatch': bad_manifest},
        'windows_zip': zip_check,
        'preserved_session': {'records': len(records), 'first_timestamp': records[0].get('timestamp'),
                              'last_timestamp': records[-1].get('timestamp'), 'sha256': digest(archive),
                              'original_exists': original.is_file(), 'original_sha256': digest(original) if original.is_file() else None},
        'inventory': inventory,
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
