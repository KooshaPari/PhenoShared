#!/usr/bin/env python3
"""resume-context — merge recent pane logs across harnesses (E03)."""
import json
from pathlib import Path
from collections import defaultdict

LOG_DIR = Path.home() / '.local/share/resume-all/pane-logs/'
SNAPSHOT = Path.home() / '.local/share/resume-all/snapshot.jsonl'

def tail_log(stable_id, n=5):
    log = LOG_DIR / f'{stable_id}.log'
    if not log.exists(): return []
    with open(log) as f:
        return [l.rstrip() for l in f if l.strip()][-n:]

def collect():
    events = []
    for line in SNAPSHOT.read_text().strip().splitlines():
        if not line.strip(): continue
        try: r = json.loads(line)
        except json.JSONDecodeError: continue
        if r.get('dead'): continue
        h = r.get('harness', '')
        if h in ('shell', 'unknown', ''): continue
        sid = r.get('stable_id', '') or r.get('tty', '') or ''
        if not sid: continue
        for line in tail_log(sid, 5):
            events.append({'ts': r.get('ts', ''), 'harness': h, 'line': line})
    events.sort(key=lambda e: e['ts'])
    return events

def main():
    ctx = collect()
    print(f"\n=== Reconstructed Context ({len(ctx)} events) ===\n")
    for e in ctx[:30]:
        print(f"  [{e['ts']}] [{e['harness']:8s}] {e['line'][:90]}")
    if len(ctx) > 30: print(f"  ... +{len(ctx)-30} more")

if __name__ == '__main__':
    main()
