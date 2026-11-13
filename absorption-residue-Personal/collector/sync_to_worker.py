#!/usr/bin/env python3
"""Explicit, authenticated publication of public Whatnot catalog observations.

Uses the EXISTING job-cockpit Worker ingest bearer credential.
No credential is written to repository artifacts or logs. Dry-run by default.
"""
import argparse, datetime as dt, json, os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from employer_policy import excluded_posting

WORKER = 'https://job-collector.worker.example.com/ingest'
WHATNOT = 'https://www.whatnot.com/careers/roles/'

def prepare(path):
    doc=json.loads(Path(path).read_text())
    if doc.get('verification_status')!='discovered_unverified':
        raise ValueError('Unexpected verification contract')
    observations=[]
    for row in doc.get('engineering_roles',[]):
        if excluded_posting(row):
            continue
        uid=row.get('id','')
        role_url=row.get('official_url','')
        title=row.get('title','')
        places=row.get('locations') or []
        if role_url!=WHATNOT+uid or len(uid)!=36 or not title or not isinstance(places,list):
            raise ValueError('Unexpected official Whatnot observation')
        # Preserve unresolved-location roles in the raw catalog, but do not import them.
        if not places:
            continue
        observations.append({'source':'whatnot-official','id':uid,'title':title,
                             'official_url':role_url,'locations':places})
    if not 15<=len(observations)<=100:
        raise ValueError('Unexpected official catalog size')
    return observations

def send(rows,token,endpoint=WORKER):
    if any(excluded_posting(row) for row in rows):
        raise ValueError('Excluded employer observation; no network write performed')
    if not token or len(token)<12:
        raise ValueError('A valid ingest credential is required')
    request=Request(endpoint,data=json.dumps({'rows':rows}).encode('utf-8'),
        method='POST',headers={'Content-Type':'application/json',
        'Accept':'application/json','Authorization':'Bearer '+token})
    with urlopen(request,timeout=30) as r:
        response=json.load(r)
        if r.status!=200 or not isinstance(response,dict) or 'added' not in response:
            raise ValueError('Unexpected Worker ingestion response')
        return {k:int(response.get(k,0)) for k in ('added','dup','bad')}

def sync(path,output,execute=False,token=None):
    rows=prepare(path)
    raw=json.loads(Path(path).read_text())['engineering_roles']
    result={'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
       'source':'whatnot-official','observations':len(rows),
       'skipped_employer_excluded':sum(excluded_posting(row) for row in raw),
       'skipped_location_unresolved':sum(not excluded_posting(row) and not row.get('locations') for row in raw),
       'configured':bool(token),
       'sent':False,'ingested':0,'duplicates':0,'rejected':0,
       'verification_status':'unverified'}
    if execute:
        if not token:raise RuntimeError('Missing JOB_COCKPIT_INGEST_TOKEN; no network write performed')
        for index in range(0,len(rows),100):
            response=send(rows[index:index+100],token)
            result['ingested']+=response['added']
            result['duplicates']+=response['dup']
            result['rejected']+=response['bad']
        result['sent']=True
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--whatnot',required=True);p.add_argument('--out',required=True)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args()
    report=sync(a.whatnot,a.out,a.execute,os.environ.get('JOB_COCKPIT_INGEST_TOKEN'))
    print(json.dumps(report,indent=2))
