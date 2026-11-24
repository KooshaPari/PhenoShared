#!/usr/bin/env python3
"""resume-bundle — multi-harness orchestration (E02). Group panes by cwd tree,
restore each bundle concurrently via the IPC daemon."""
import json, sys
from pathlib import Path
from collections import defaultdict

SNAPSHOT = Path.home() / '.local/share/resume-all/snapshot.jsonl'
HARNESS_ORDER = ['codex', 'cursor', 'forge', 'kilo', 'opencode', 'droid']

def build_bundles():
    by_cwd = defaultdict(list)
    for line in SNAPSHOT.read_text().strip().splitlines():
        if not line.strip(): continue
        try: r = json.loads(line)
        except json.JSONDecodeError: continue
        if r.get('dead'): continue
        h = r.get('harness', '')
        if h in ('shell', 'unknown', ''): continue
        cwd = r.get('cwd', '') or '/'
        parts = cwd.strip('/').split('/')
        prefix = '/' + '/'.join(parts[:3]) if len(parts) >= 3 else cwd
        by_cwd[prefix].append(r)

    bundles = []
    for prefix, rows in sorted(by_cwd.items()):
        merged = {}
        for r in rows:
            h = r.get('harness', '?')
            if h not in merged:
                merged[h] = r.get('session_id', '') or ''
        plan = [{'harness': h, 'session_id': merged[h], 'cwd': prefix}
                for h in HARNESS_ORDER if h in merged]
        if plan: bundles.append({'prefix': prefix, 'plan': plan})
    return bundles

def main():
    bundles = build_bundles()
    print(f"\n=== {len(bundles)} bundle(s) ===\n")
    for b in bundles:
        print(f"  {b['prefix']}")
        for step in b['plan']:
            sid = step['session_id'][:16] if step['session_id'] else '?'
            print(f"    {step['harness']:8s}  sid={sid}")

if __name__ == '__main__':
    main()
