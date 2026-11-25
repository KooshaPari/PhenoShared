#!/usr/bin/env python3
"""ats.py - direct ATS board sweep. Greenhouse/Lever/Ashby public APIs.
~55 boards. LA rank 3, SD/Chicago/Seattle/remote rank 1, else skipped.
SpaceX INCLUDED: dedupe vs already-submitted titles (SUBMITTED_TITLES) and
req ids (SUBMITTED_REQ_IDS); other SpaceX reqs stay in scope. Manager roles out.
Dedupe vs prior ats-out.json (rotated to ats-prev.json). Writes ats-out.json."""
import json, os, re, shutil, sys, time, urllib.request, urllib.error

UA = {'User-Agent': 'koosha-jobs/1.0'}

GREENHOUSE = ['spacex','airbnb','stripe','databricks','reddit','doordash','coinbase',
 'flexport','figure','benchling','gusto','brex','plaid','ramp','figma','scaleai','waymo',
 'openai','anthropic','discord','robinhood','datadog','mongodb','cloudflare','hashicorp',
 'confluent','rubrik','purestorage','box','dropbox','zoom','ziprecruiter','snap','riotgames',
 'tiktok','chime','affirm','toast','samsara','okta','duolingo','asana','twilio','lyft',
 'pinterest','houzz','headspace',' Hulu'.strip().lower(),'crunchyroll','playstation','fantasy',
 'relativityspace','virgingalactic','boom','astranis','vast','machina-labs','hadrian',
 'firstresonance','appfolio','service-titan','telesign','clutter',' fair'.strip().lower()]
LEVER = ['netlify','webflow','coursera','udacity','anduril-SKIPPED','vercel','linear',
 'retool','mercury','deel','sourcegraph','gitlab','elastic','kraken','gemini','opendoor',
 'thumbtack','nextdoor','yelp','quizlet','medium']
ASHBY = ['perplexity','anysphere','notion','ramp','watershed','substack','cognition',
 'mistral','xai','togetherai','replicate','modal','langchain','pinecone','weaviate']

EXCLUDE_COMPANIES = ('palantir', 'remitly', 'minimax', 'anduril', 'silvus')
# SpaceX already-submitted (receipt-verified Oct 8-12); do not re-surface.
SUBMITTED_TITLES = ('starship software engineer', 'starshield new grad security',
 'full stack software engineer, developer systems', 'starfall', 'security software engineer (new grad)',
 'applied ai')
SUBMITTED_REQ_IDS = set()  # populate when numeric greenhouse ids are confirmed

def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        return {'__error__': str(e)}

def rank(loc):
    ll = (loc or '').lower()
    if 'los angeles' in ll or 'hawthorne' in ll or 'santa monica' in ll or 'glendale' in ll \
       or 'culver city' in ll or 'el segundo' in ll or 'burbank' in ll or 'pasadena' in ll \
       or 'long beach' in ll or 'irvine' in ll or ll.strip() == 'la':
        return 3
    if any(k in ll for k in ('san diego', 'chicago', 'seattle', 'remote')):
        return 1
    return 0

def keep(company, title):
    cl, tl = company.lower(), title.lower()
    if any(x in cl for x in EXCLUDE_COMPANIES):
        return False
    if 'manager' in tl or 'intern' in tl or 'director' in tl or 'principal' in tl:
        return False
    if cl == 'spacex':
        if any(s in tl for s in SUBMITTED_TITLES):
            return False
    return True

def gh(slug):
    d = get_json(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs')
    for j in d.get('jobs', []):
        yield {'source': f'greenhouse:{slug}', 'id': str(j.get('id', '')),
               'title': j.get('title', ''), 'official_url': j.get('absolute_url', ''),
               'locations': [(j.get('location') or {}).get('name', '')],
               'company': slug, 'date_posted': j.get('updated_at', '')[:10]}

def lever(slug):
    d = get_json(f'https://api.lever.co/v0/postings/{slug}?mode=json')
    if isinstance(d, dict):
        return
    for j in d:
        cats = j.get('categories') or {}
        yield {'source': f'lever:{slug}', 'id': j.get('id', ''),
               'title': j.get('text', ''), 'official_url': j.get('hostedUrl', ''),
               'locations': [cats.get('location', '')], 'company': slug,
               'date_posted': ''}

def ashby(slug):
    d = get_json(f'https://api.ashbyhq.com/posting-api/job-board/{slug}')
    for j in d.get('jobs', []):
        yield {'source': f'ashby:{slug}', 'id': j.get('id', ''),
               'title': j.get('title', ''),
               'official_url': j.get('jobUrl') or j.get('applyUrl', ''),
               'locations': [j.get('location', '')], 'company': slug,
               'date_posted': j.get('publishedAt', '')[:10]}

def main():
    prev_ids = set()
    if os.path.exists('ats-out.json'):
        shutil.copyfile('ats-out.json', 'ats-prev.json')
        try:
            prev_ids = {r['id'] for r in json.load(open('ats-prev.json'))}
        except Exception:
            pass
    out, seen, errors = [], set(), 0
    for fn, slugs in ((gh, GREENHOUSE), (lever, LEVER), (ashby, ASHBY)):
        for slug in slugs:
            if '-SKIPPED' in slug or slug in ('palantir',):
                continue
            try:
                n0 = len(out)
                for row in fn(slug):
                    if not row['title'] or not row['official_url']:
                        continue
                    rk = rank(row['locations'][0] if row['locations'] else '')
                    if rk == 0:
                        continue
                    if not keep(row['company'], row['title']):
                        continue
                    uid = row['source'] + '|' + row['id']
                    if uid in seen:
                        continue
                    seen.add(uid)
                    row['rank'] = rk
                    row['new_vs_prev'] = uid not in prev_ids
                    out.append(row)
                time.sleep(0.3)  # polite crawl
            except Exception:
                errors += 1
    out.sort(key=lambda r: (-r['rank'], r['company'], r['title']))
    with open('ats-out.json', 'w') as f:
        json.dump(out, f, indent=1)
    new = sum(1 for r in out if r.get('new_vs_prev'))
    print(f'ats: {len(out)} rows -> ats-out.json ({new} new vs prev, {errors} board errors)')

if __name__ == '__main__':
    main()
