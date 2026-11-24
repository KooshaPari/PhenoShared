#!/usr/bin/env python3
"""ghmd2.py - markdown lists tier, part 2. Filters ghmd-raw.json per standing
rules, rotates ghmd-final.json -> ghmd-prev.json, writes new ghmd-final.json
with a new_vs_prev flag for rows not present in the previous final."""
import json, os, shutil

EXCLUDE_COMPANIES = ('palantir', 'remitly', 'minimax', 'anduril', 'silvus')
TARGET_LOCS = ('los angeles', 'la', 'san diego', 'chicago', 'seattle', 'remote')

def rank(loc):
    ll = (loc or '').lower()
    if 'los angeles' in ll or ll.strip() == 'la':
        return 3
    if any(k in ll for k in ('san diego', 'chicago', 'seattle', 'remote')):
        return 1
    return 0

def main():
    rows = json.load(open('ghmd-raw.json'))
    prev_ids = set()
    if os.path.exists('ghmd-final.json'):
        shutil.copyfile('ghmd-final.json', 'ghmd-prev.json')
        try:
            prev_ids = {r['id'] for r in json.load(open('ghmd-prev.json'))}
        except Exception:
            prev_ids = set()
    out, seen = [], set()
    for r in rows:
        comp = (r.get('company') or '').replace('**', '').strip()
        cl = comp.lower()
        if any(x in cl for x in EXCLUDE_COMPANIES):
            continue
        title = (r.get('role') or '').strip()
        tl = title.lower()
        if 'manager' in tl or 'intern' in tl:
            continue
        url = r.get('apply_url') or ''
        if not url:
            continue
        loc = r.get('location') or ''
        rk = rank(loc)
        if rk == 0:
            continue
        uid = cl + '|' + tl + '|' + url
        if uid in seen:
            continue
        seen.add(uid)
        out.append({'source': 'simplify-md', 'id': uid[:180], 'title': title,
                    'company': comp, 'official_url': url, 'locations': [loc],
                    'rank': rk, 'date_posted': r.get('date_cell', ''),
                    'new_vs_prev': uid not in prev_ids})
    out.sort(key=lambda r: (-r['rank'], r['company'], r['title']))
    with open('ghmd-final.json', 'w') as f:
        json.dump(out, f, indent=1)
    new = sum(1 for r in out if r['new_vs_prev'])
    print(f'ghmd2: {len(out)} rows -> ghmd-final.json ({new} new vs prev)')

if __name__ == '__main__':
    main()
