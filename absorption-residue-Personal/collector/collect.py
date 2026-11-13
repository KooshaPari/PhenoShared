#!/usr/bin/env python3
"""Read-only job discovery from public ATS feeds. Python 3.10+, stdlib only.

Discovery is NOT verification: never promote jobs to 'active_verified' automatically.
No applications, messaging, or authenticated scraping.
"""
import argparse
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import sqlite3
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path
from employer_policy import excluded_posting, excluded_keys

DB_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS jobs (
  job_key TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  employer TEXT NOT NULL,
  provider_id TEXT NOT NULL,
  title TEXT NOT NULL,
  location TEXT NOT NULL,
  official_url TEXT NOT NULL,
  description TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  changed_at TEXT NOT NULL,
  verification_status TEXT NOT NULL DEFAULT 'discovered',
  CHECK (verification_status IN ('discovered','needs_review','active_verified','ineligible','closed'))
);
CREATE TABLE IF NOT EXISTS observations (
  run_id TEXT NOT NULL, job_key TEXT NOT NULL, observed_at TEXT NOT NULL,
  change_type TEXT NOT NULL, PRIMARY KEY(run_id, job_key)
);
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT,
  source_ok INTEGER NOT NULL DEFAULT 0, source_failed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_jobs_seen ON jobs(last_seen);
CREATE INDEX IF NOT EXISTS idx_jobs_employer ON jobs(employer);
"""

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def plain(value):
    parser = TextExtractor()
    parser.feed(html.unescape(str(value or '')))
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')

def fetch_json(url):
    req = Request(url, headers={'User-Agent': 'job-cockpit-public-ats/0.1 (read-only)', 'Accept': 'application/json'})
    with urlopen(req, timeout=25) as response:
        return json.load(response)

def normalize(provider, employer, item):
    if excluded_posting(item, employer=employer):
        return None
    if provider == 'greenhouse':
        loc = (item.get('location') or {}).get('name') or ''
        fields = (item['id'], item.get('title'), loc, item.get('absolute_url'),
                  item.get('content', ''))
    elif provider == 'lever':
        categories = item.get('categories') or {}
        loc = categories.get('location') or ''
        fields = (item['id'], item.get('text'), loc, item.get('hostedUrl'),
                  item.get('descriptionPlain') or item.get('description', ''))
    elif provider == 'ashby':
        loc = item.get('location') or ''
        fields = (item['id'], item.get('title'), loc, item.get('jobUrl') or item.get('applyUrl'),
                  item.get('descriptionPlain') or item.get('descriptionHtml') or '')
    else:
        raise ValueError('unknown provider')
    ident, title, location, url, description = fields
    if not ident or not title or not url or not str(url).startswith('https://'):
        raise ValueError('missing id, title or official https URL')
    key = f'{provider}:{employer.lower().replace(" ", "-")}:{ident}'
    description = plain(description)
    signature = json.dumps([title, location, url, description], ensure_ascii=False)
    digest = hashlib.sha256(signature.encode()).hexdigest()
    return (key, provider, employer, str(ident), str(title), str(location), str(url), description, digest)

def endpoint(provider, slug):
    if provider == 'greenhouse':
        return f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true'
    if provider == 'lever':
        return f'https://api.lever.co/v0/postings/{slug}?mode=json'
    if provider == 'ashby':
        return f'https://api.ashbyhq.com/posting-api/job-board/{slug}'
    raise ValueError('unknown provider')

def extract(provider, payload):
    if provider == 'greenhouse':
        return payload['jobs']
    if provider == 'lever':
        return payload
    if provider == 'ashby':
        return [x for x in payload['jobs'] if x.get('isListed', True)]
    raise ValueError('unknown provider')

def discover(conn, config, limit=None, delay=0.4):
    started = now()
    run_id = started + ':' + hashlib.sha1(str(time.monotonic_ns()).encode()).hexdigest()[:10]
    conn.execute('INSERT INTO runs(run_id,started_at) VALUES (?,?)', (run_id, started))
    sources = config['sources'][:limit] if limit else config['sources']
    summary = {'run_id': run_id, 'sources_ok': 0, 'sources_failed': 0,
               'sources_excluded': 0, 'postings_excluded': 0,
               'new': 0, 'changed': 0, 'unchanged': 0, 'errors': []}
    blocked_keys = excluded_keys(conn)
    def retire(key, observed):
        conn.execute("UPDATE jobs SET verification_status='ineligible' WHERE job_key=?", (key,))
        conn.execute("INSERT INTO observations(run_id,job_key,observed_at,change_type) VALUES(?,?,?,'employer_excluded') ON CONFLICT(run_id,job_key) DO UPDATE SET change_type='employer_excluded'",
                     (run_id, key, observed))
        blocked_keys.add(key)
    # Preserve archived rows/provenance while removing excluded employers from active staging.
    with conn:
        for key, employer, url in conn.execute('SELECT job_key,employer,official_url FROM jobs').fetchall():
            if excluded_posting({'employer': employer, 'official_url': url}):
                retire(key, started)
    for source in sources:
        provider, slug, employer = (source[k] for k in ('provider','slug','employer'))
        if excluded_posting(employer=employer, slug=slug):
            summary['sources_excluded'] += 1
            continue
        try:
            records = extract(provider, fetch_json(endpoint(provider, slug)))
            normalized, excluded_ids = [], []
            for item in records:
                posting = normalize(provider, employer, item)
                if posting is None:
                    summary['postings_excluded'] += 1
                    if item.get('id') is not None:
                        excluded_ids.append(str(item['id']))
                else:
                    normalized.append(posting)
            observed = now()
            # Commit only after a full source fetch/parse. Failure must never close old jobs.
            with conn:
                for ident in excluded_ids:
                    retire(f'{provider}:{employer.lower().replace(" ", "-")}:{ident}', observed)
                for job in normalized:
                    if job[0] in blocked_keys:
                        summary['postings_excluded'] += 1
                        continue
                    existing = conn.execute('SELECT content_hash FROM jobs WHERE job_key=?', (job[0],)).fetchone()
                    change = 'new' if not existing else ('changed' if existing[0] != job[-1] else 'unchanged')
                    if not existing:
                        conn.execute('''INSERT INTO jobs(job_key,provider,employer,provider_id,title,location,official_url,
                          description,content_hash,first_seen,last_seen,changed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (*job, observed, observed, observed))
                    else:
                        conn.execute('''UPDATE jobs SET title=?, location=?, official_url=?, description=?,
                          content_hash=?, last_seen=?, changed_at=CASE WHEN content_hash<>? THEN ? ELSE changed_at END,
                          verification_status=CASE WHEN content_hash<>? THEN 'needs_review' ELSE verification_status END
                          WHERE job_key=?''',
                          (job[4], job[5], job[6], job[7], job[8], observed,
                           job[8], observed, job[8], job[0]))
                    conn.execute('INSERT INTO observations VALUES (?,?,?,?)', (run_id, job[0], observed, change))
                    summary[change] += 1
            summary['sources_ok'] += 1
        except (HTTPError, URLError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            summary['sources_failed'] += 1
            summary['errors'].append({'employer': employer, 'provider': provider, 'error': str(exc)[:180]})
        if delay:
            time.sleep(delay)
    with conn:
        conn.execute('''UPDATE runs SET completed_at=?, source_ok=?, source_failed=? WHERE run_id=?''',
                     (now(), summary['sources_ok'], summary['sources_failed'], run_id))
    return summary

TITLE = re.compile(r'\b(software|backend|back.end|full.stack|platform|developer|infrastructure|machine learning|ml engineer|ai engineer|devops|sre)\b', re.I)
EXCLUDE = re.compile(r'\b(senior|sr\.?|staff|principal|lead|manager|director|intern(ship)?|architect)\b', re.I)
LOCAL = re.compile(r'\b(los angeles|santa monica|culver city|marina del rey|el segundo|playa vista|hawthorne|burbank|pasadena|glendale|long beach|torrance|beverly hills|west hollywood|santa clarita)\b', re.I)

def triage(conn):
    """A queue, not a verified result set; ambiguous remote and eligibility stay unverified."""
    rows = conn.execute('SELECT job_key,employer,title,location,official_url,verification_status FROM jobs ORDER BY last_seen DESC').fetchall()
    blocked = excluded_keys(conn)
    result = []
    for key, employer, title, location, url, status in rows:
        if key in blocked or excluded_posting({'employer': employer, 'official_url': url}):
            continue
        if TITLE.search(title) and not EXCLUDE.search(title) and LOCAL.search(location):
            result.append({'employer': employer, 'title': title, 'location': location,
                           'official_url': url, 'verification_status': status})
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=str(Path(__file__).with_name('sources.json')))
    parser.add_argument('--db', default='jobs.sqlite3')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--triage-only', action='store_true')
    args = parser.parse_args()
    conn = sqlite3.connect(args.db)
    conn.executescript(DB_SCHEMA)
    if not args.triage_only:
        config = json.loads(Path(args.config).read_text())
        summary = discover(conn, config, args.limit)
        print(json.dumps(summary, indent=2))
    queue = triage(conn)
    print(json.dumps({'la_review_queue_count': len(queue), 'la_review_queue': queue}, indent=2))
    conn.close()

if __name__ == '__main__':
    main()
