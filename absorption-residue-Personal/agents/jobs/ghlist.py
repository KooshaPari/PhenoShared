#!/usr/bin/env python3
"""ghlist.py - Simplify JSON tier. Fetches SimplifyJobs/New-Grad-Positions
listings.json, filters per standing rules, writes ghlist.json rows for ingest.
Rules: $110k+ base signal when visible, new-grad/0-2 YOE tier (list is new-grad
by construction), LA first then SD/Chicago/Seattle/remote; Palantir excluded;
Remitly/MiniMax/Anduril dropped; Silvus skipped; manager roles out."""
import json, re, sys, urllib.request, datetime as dt

LISTINGS = 'https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json'
EXCLUDE_COMPANIES = {'palantir', 'remitly', 'minimax', 'anduril', 'silvus'}
LOC_RANK = {'los angeles': 3, 'la': 3, 'san diego': 1, 'chicago': 1, 'seattle': 1, 'remote': 1}

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'koosha-jobs/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def loc_rank(locs):
    best = 0
    for l in locs or []:
        ll = str(l).lower()
        for k, v in LOC_RANK.items():
            if k in ll:
                best = max(best, v)
    return best

def main():
    data = fetch(LISTINGS)
    rows, seen = [], set()
    today = dt.date.today().isoformat()
    for it in data:
        comp = (it.get('company_name') or '').strip()
        cl = comp.lower()
        if any(x in cl for x in EXCLUDE_COMPANIES):
            continue
        if not it.get('active', True):
            continue
        title = (it.get('title') or '').strip()
        tl = title.lower()
        if 'manager' in tl or 'intern' in tl:
            continue
        url = it.get('url') or ''
        if not url:
            continue
        locs = it.get('locations') or []
        rank = loc_rank(locs)
        if rank == 0:
            continue  # not in a target market
        uid = it.get('id') or (comp.lower() + '|' + tl + '|' + url)
        if uid in seen:
            continue
        seen.add(uid)
        rows.append({
            'source': 'simplify-json',
            'id': uid[:180],
            'title': title,
            'company': comp,
            'official_url': url,
            'locations': [str(l) for l in locs],
            'rank': rank,
            'salary': it.get('salary') or '',
            'date_posted': it.get('date_posted') or it.get('date_updated') or '',
            'scraped_at': today,
        })
    rows.sort(key=lambda r: (-r['rank'], r['company'], r['title']))
    with open('ghlist.json', 'w') as f:
        json.dump(rows, f, indent=1)
    print(f'ghlist: {len(rows)} rows -> ghlist.json')

if __name__ == '__main__':
    main()
