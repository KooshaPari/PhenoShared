#!/usr/bin/env python3
"""post_ingest.py - POSTs collected rows to the job-collector Worker in batches
of 25. Token from ingest.tok (never printed). Rows: ghlist.json, ghmd-final.json,
ats-out.json. Dedupes across files by (company, title, url).

Failure handling: every failed batch is logged with its HTTP status and a body
snippet (Error 1102 / resource-limit 503s were previously swallowed, leaving
only an unexplained batches_failed_rows count). 503s get long backoff; three
consecutive failed batches trip a 5-minute circuit breaker so a degraded
Worker gets room to recover instead of 3x retry hammering."""
import json, os, sys, time, urllib.request, urllib.error

WORKER = 'https://job-collector.worker.example.com/ingest'
FILES = ('ghlist.json', 'ghmd-final.json', 'ats-out.json')
INTER_BATCH_SLEEP = 1.5
CIRCUIT_BREAKER_AFTER = 3
CIRCUIT_BREAKER_SLEEP = 300

def load_rows():
    rows, seen = [], set()
    for fn in FILES:
        if not os.path.exists(fn):
            continue
        for r in json.load(open(fn)):
            key = (r.get('company', '').lower(), r.get('title', '').lower(), r.get('official_url', ''))
            if key in seen:
                continue
            seen.add(key)
            rows.append(map_row(r))
    return rows

def map_row(r):
    return {
        'source': 'github-list',
        'url': r.get('official_url') or r.get('url') or '',
        'title': r.get('title', ''),
        'company': r.get('company', ''),
        'location': '; '.join(str(x) for x in (r.get('locations') or [])[:6]),
        'loc_rank': int(r.get('rank') or 0),
        'list': str(r.get('source') or '')[:80],
        'link_check': 'unverified',
    }

def send(batch, token):
    req = urllib.request.Request(WORKER, data=json.dumps({'rows': batch}).encode(),
        method='POST', headers={'Content-Type': 'application/json', 'User-Agent': 'koosha-jobs/1.0',
        'Accept': 'application/json', 'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def main():
    token = open('ingest.tok').read().strip()
    rows = load_rows()
    total = {'added': 0, 'upd': 0, 'dup': 0, 'bad': 0}
    failed = 0
    consecutive_failures = 0
    for i in range(0, len(rows), 25):
        batch = rows[i:i+25]
        batch_no = i // 25
        if i > 0:
            time.sleep(INTER_BATCH_SLEEP)
        if consecutive_failures >= CIRCUIT_BREAKER_AFTER:
            print(f'circuit breaker: {consecutive_failures} consecutive failed batches; '
                  f'sleeping {CIRCUIT_BREAKER_SLEEP}s before batch {batch_no}', flush=True)
            time.sleep(CIRCUIT_BREAKER_SLEEP)
            consecutive_failures = 0
        resp = None
        for attempt in range(4):
            try:
                resp = send(batch, token)
                break
            except urllib.error.HTTPError as e:
                body = e.read()[:200]
                print(f'batch {batch_no}: HTTP {e.code} attempt {attempt + 1}/4: {body!r}', flush=True)
                if attempt == 3:
                    failed += len(batch)
                elif e.code == 503:
                    time.sleep(30 * (attempt + 1))
                else:
                    time.sleep(5 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                print(f'batch {batch_no}: {type(e).__name__} {e} attempt {attempt + 1}/4', flush=True)
                if attempt == 3:
                    failed += len(batch)
                else:
                    time.sleep(10 * (attempt + 1))
        if resp is None:
            consecutive_failures += 1
            continue
        consecutive_failures = 0
        for k in total:
            total[k] += int(resp.get(k, 0) or 0)
        time.sleep(0.4)
    print(f'ingest: {len(rows)} rows; worker: {total}; batches_failed_rows: {failed}')

if __name__ == '__main__':
    main()
