#!/usr/bin/env python3
"""resume-summarize — generate 1-sentence summary per active pane (E05)."""
import json, re, sys
from pathlib import Path

SNAPSHOT = Path.home() / '.local/share/resume-all/snapshot.jsonl'
LOG_DIR = Path.home() / '.local/share/resume-all/pane-logs/'

PATTERNS = {
    'forge': [
        (r'explain-this\s+([\w-]+)', 'was reviewing {}'),
        (r'--conversation-id\s+([\w-]+)', 'had a session {}'),
        (r'\b(refactor|implement|fix|add|update|remove|rename)\b', 'was modifying the codebase'),
        (r'Finished\s+(\w+)', 'finished {}'),
    ],
    'codex': [
        (r'resume\s+([\w-]+)', 'was in session {}'),
        (r'--search\s+(.*)', 'was searching for {}'),
        (r'\b(test|bench|evaluate|run|train)\b', 'was running {}'),
    ],
    'cursor': [
        (r'--resume\s+([\w-]+)', 'had session {}'),
        (r'\b(chat|ask|help)\b', 'was asking about {}'),
    ],
}

def tail_log(stable_id, n=20):
    log = LOG_DIR / f'{stable_id}.log'
    if not log.exists(): return []
    with open(log) as f:
        return [l.rstrip() for l in f if l.strip()][-n:]

def summarize(harness, lines):
    default = f'was running {harness} (no recent activity captured)'
    if not lines: return default
    for line in lines:
        for pat, fmt in PATTERNS.get(harness, []):
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                cap = m.group(1) if m.lastindex else ''
                what = fmt.format(cap) if cap else fmt
                return f'{harness} {what}' if not what.startswith(harness) else what
    return default

def main():
    rows = []
    for line in SNAPSHOT.read_text().strip().splitlines():
        if not line.strip(): continue
        try: r = json.loads(line)
        except json.JSONDecodeError: continue
        if r.get('dead'): continue
        h = r.get('harness', '')
        if h in ('shell', 'unknown', ''): continue
        sid = r.get('stable_id', '') or r.get('tty', '') or ''
        cwd = r.get('cwd', '')
        rows.append({'harness': h, 'session_id': r.get('session_id', '')[:16] if r.get('session_id') else '', 'cwd': cwd[:60], 'summary': summarize(h, tail_log(sid))})

    print(f"\n=== Session Summaries ({len(rows)} panes) ===\n")
    for r in rows:
        print(f"  [{r['harness']:8s}] {r['summary']}")
        if r['session_id'] or r['cwd']:
            print(f"            sid={r['session_id']} cwd={r['cwd']}")
        print()

if __name__ == '__main__':
    main()
