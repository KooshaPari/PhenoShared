#!/usr/bin/env python3
"""ghmd.py - markdown lists tier, part 1. Parses the SimplifyJobs
New-Grad-Positions README (HTML tables) into ghmd-raw.json."""
import json, re, urllib.request

README = 'https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md'

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'koosha-jobs/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')

def main():
    md = fetch(README)
    rows = []
    for tr in re.findall(r'<tr>(.*?)</tr>', md, re.S):
        tds = re.findall(r'<td>(.*?)</td>', tr, re.S)
        if len(tds) < 4:
            continue
        cm = re.search(r'<a href="https://simplify\.jobs/c/[^"]*">([^<]+)</a>', tds[0])
        company = cm.group(1).strip() if cm else re.sub(r'<[^>]+>', '', tds[0]).strip()
        role = re.sub(r'<[^>]+>', '', tds[1]).strip()
        loc_raw = tds[2]
        locs = [re.sub(r'<[^>]+>', '', x).strip() for x in re.split(r'</br>|<br/?>', loc_raw)]
        locs = [l for l in locs if l and 'location' not in l.lower()[:10]]
        # first non-simplify jobs link = apply url
        links = re.findall(r'href="(https?://[^"]+)"', tds[3])
        apply_url = next((u for u in links if 'simplify.jobs' not in u), '')
        rows.append({'company': company, 'role': role, 'location': '; '.join(locs),
                     'locations_list': locs, 'apply_url': apply_url,
                     'date_cell': re.sub(r'<[^>]+>', '', tds[4]).strip() if len(tds) > 4 else ''})
    with open('ghmd-raw.json', 'w') as f:
        json.dump(rows, f, indent=1)
    print(f'ghmd: {len(rows)} raw rows -> ghmd-raw.json')

if __name__ == '__main__':
    main()
