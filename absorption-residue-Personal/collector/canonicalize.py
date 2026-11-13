"""Merge public ATS/Whatnot observations without claiming official eligibility.

Input files are produced by the existing read-only scheduled collectors.
Uses only standard-library Python. Canonical identity is conservative: same
title/company never establishes a duplicate; requisition ID does.
"""
import argparse, datetime as dt, json, re, sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from triage import region, TITLE, SENIOR, YOE5
from employer_policy import excluded_posting, excluded_keys

UUID = r"[0-9a-f-]{36}"

def official_key(raw):
    if not isinstance(raw,str) or not raw.startswith('https://'): return None
    parts=urlsplit(raw)
    hostname=parts.hostname.lower() if parts.hostname else ''
    path=parts.path.rstrip('/')
    match=None
    if hostname.endswith('greenhouse.io'):
        match=re.fullmatch(r"/([^/]+)/jobs/(\d+)",path,re.I)
        if match: return 'greenhouse:'+match[1].lower()+':'+match[2]
    if hostname=='jobs.ashbyhq.com':
        match=re.fullmatch(r"/([^/]+)/("+UUID+r")(?:/application)?",path,re.I)
        if match: return 'ashby:'+match[1].lower()+':'+match[2].lower()
    if hostname in ('whatnot.com','www.whatnot.com'):
        match=re.fullmatch(r"/careers/roles/("+UUID+r")",path,re.I)
        if match: return 'ashby:whatnot:'+match[1].lower()
    if hostname in ('jobs.lever.co','jobs.eu.lever.co'):
        match=re.fullmatch(r"/([^/]+)/("+UUID+r")",path,re.I)
        if match: return 'lever:'+match[1].lower()+':'+match[2].lower()
    if hostname.endswith('.myworkdayjobs.com'):
        match=re.search(r"_(R\d+(?:-\d+)?)$",path,re.I)
        if match: return 'workday:'+hostname+':'+match[1].lower()
    return 'url:'+urlunsplit(('https',hostname,path,'',''))

def export(db_path, whatnot_path, output_path, now=None):
    now=now or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    db=sqlite3.connect(str(db_path))
    rows=db.execute('SELECT job_key,employer,title,location,official_url,description,first_seen,last_seen,verification_status,content_hash FROM jobs').fetchall()
    blocked=excluded_keys(db)
    merged={}
    def absorb(key,company,title,location,url,first,last,source,ref,description='',content_hash=''):
        if not key or excluded_posting({'company': company, 'official_url': url}):return
        if key not in merged:
            merged[key]={'canonical_id':key,'company':company,'title':title,'official_url':url,
                'location':location,'region':region(location),'first_seen':first,'last_seen':last,
                'content_signature':content_hash or None,'source_observations':[],
                'verification_status':'unverified',
                'review_flags':[]}
        obj=merged[key]
        obj['first_seen']=min(obj['first_seen'],first)
        obj['last_seen']=max(obj['last_seen'],last)
        obj['source_observations'].append({'source':source,'ref':ref,'source_url':url})
        if obj['region']!='la_metro' and region(location)=='la_metro':
            obj['region']='la_metro';obj['location']=location
        if source=='whatnot-official':
            obj['official_url']=url;obj['company']=company
    for key,employer,title,location,url,description,first,last,status,hash_value in rows:
        if key in blocked:continue
        absorb(official_key(url),employer,title,location,url,first,last,'ats-collector',key,description,hash_value)
    data=json.loads(Path(whatnot_path).read_text())
    if data.get('verification_status')!='discovered_unverified' or not isinstance(data.get('engineering_roles'),list):
        raise ValueError('Unexpected Whatnot catalog structure')
    for r in data['engineering_roles']:
        if excluded_posting(r):continue
        loc=' | '.join(r.get('locations',[]))
        url=r.get('official_url')
        absorb(official_key(url),'Whatnot',r.get('title',''),loc,url,now,now,
            'whatnot-official',r.get('id',''))
    for record in merged.values():
        title=record['title']
        if not TITLE.search(title):record['review_flags'].append('non_target_title')
        if SENIOR.search(title):record['review_flags'].append('seniority_title')
        if record['region'] in ('remote_unconfirmed','unapproved_or_unknown'):
            record['review_flags'].append('location_not_approved')
        record['review_flags'].extend(['graduation_unchecked','experience_unchecked','official_page_unchecked'])
        record['source_count']=len(record['source_observations'])
    records=sorted(merged.values(),key=lambda x:(x['region']!='la_metro',x['company'].lower(),x['title'].lower(),x['canonical_id']))
    output={'generated_at':now,'kind':'canonical_discovery_not_eligibility','verified_eligible_la':None,
        'raw_ats_rows':len(rows),'whatnot_observations':len(data['engineering_roles']),
        'unique_canonical_jobs':len(records),
        'la_review_candidates':sum(x['region']=='la_metro' and 'seniority_title' not in x['review_flags'] for x in records),
        'records':records}
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    Path(output_path).write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    db.close()
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--db',required=True);p.add_argument('--whatnot',required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    out=export(a.db,a.whatnot,a.out)
    print(json.dumps({key:out[key] for key in ('raw_ats_rows','whatnot_observations','unique_canonical_jobs','la_review_candidates','verified_eligible_la')},indent=2))
