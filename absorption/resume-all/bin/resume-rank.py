#!/usr/bin/env python3
"""resume-rank — rank panes by recency + activity (E06)."""
import json, os, sys, time
from pathlib import Path

SNAPSHOT = Path.home() / '.local/share/resume-all/snapshot.jsonl'
LOG_DIR = Path.home() / '.local/share/resume-all/pane-logs/'

WEIGHTS = {
    'forge': 1.0, 'codex': 0.8, 'cursor': 0.8,
    'kilo': 0.3, 'opencode': 0.3, 'droid': 0.3,
    'zmx': 0.5, 'sharecli-tray': 0.2,
}

def rank():
    now = time.time()
    ranked = []
    for line in SNAPSHOT.read_text().strip().splitlines():
        if not line.strip(): continue
        try: r = json.loads(line)
        except json.JSONDecodeError: continue
        if r.get('dead'): continue
        h = r.get('harness', '')
        if h in ('shell', 'unknown', ''): continue

        score = 1.0
        reasons = []
        ts = r.get('ts_epoch', 0) or 0
        age = now - ts if ts else float('inf')
        if age < 300: score += 2.0; reasons.append('active_now')
        elif age < 1800: score += 1.0; reasons.append('recent')
        elif age < 7200: score += 0.5; reasons.append('past_2h')

        sid = r.get('stable_id', '') or r.get('tty', '') or ''
        if sid:
            log = LOG_DIR / f'{sid}.log'
            if log.exists() and (now - log.stat().st_mtime) < 600:
                score += 0.5; reasons.append('log_recent')

        if r.get('session_id'):
            score += 0.5; reasons.append('has_session')

        score += WEIGHTS.get(h, 0.2)
        reasons.append(f"harness_{h}={WEIGHTS.get(h, 0.2)}")

        pid = r.get('pid')
        if pid:
            try: os.kill(pid, 0); score += 1.0; reasons.append('alive')
            except OSError: reasons.append('dead')

        ranked.append({
            'stable_id': sid[:20] if isinstance(sid, str) else '',
            'harness': h,
            'session_id': (r.get('session_id') or '')[:16],
            'cwd': (r.get('cwd') or '')[:40],
            'score': round(score, 2),
            'reasons': reasons[:5],
            'pid': pid,
            'age_seconds': int(age) if age != float('inf') else -1,
        })

    ranked.sort(key=lambda x: x['score'], reverse=True)
    return ranked

def main():
    items = rank()
    print(f"\n=== Pane Triage Ranking ({len(items)} panes) ===\n")
    for i, r in enumerate(items[:25], 1):
        status = '🟢' if 'alive' in r['reasons'] else '🔴' if 'dead' in r['reasons'] else '⚪'
        age_str = f"{r['age_seconds']}s" if 0 <= r['age_seconds'] < 3600 else f"{r['age_seconds']/3600:.1f}h" if r['age_seconds'] > 0 else '?'
        print(f"  {i:>2}. [{r['harness']:8s}] score={r['score']:5.2f} {status}  age={age_str:>6s}  sid={r['session_id']:16s}")
        print(f"      cwd={r['cwd']}")
        print(f"      reasons: {', '.join(r['reasons'])}")
        print()

if __name__ == '__main__':
    main()
