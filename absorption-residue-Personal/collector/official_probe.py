"""Bounded employer-controlled job checks; no automatic eligibility promotion."""
import argparse, datetime as dt, hashlib, html, json, re, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser

CAREER=re.compile(r'new grad|university grad|early career|entry.level|junior|associate|engineer i\b|engineer 1\b|software engineer',re.I)
SALARY=re.compile(r'\$\s?(\d{2,3}(?:,\d{3})?)\s*[kK]?\s*(?:-|–|—|to)\s*\$?\s?(\d{2,3}(?:,\d{3})?)\s*[kK]?',re.I)
GRAD=re.compile(r'graduat(?:e|ion|ing)[^.]{0,100}',re.I)
YOE=re.compile(r'.{0,80}\b\d+\s*(?:\+|-|to)?\s*\d*\s*years?\s+(?:of\s+)?(?:relevant\s+|professional\s+)?experience.{0,75}',re.I)
AUTH=re.compile(r'.{0,90}(?:US person|citizen|clearance|ITAR|work authorization|visa sponsor).{0,90}',re.I)
STRONG=['ZipRecruiter','Whatnot','First Resonance','Riot Games','MediaAlpha','Match Group','Otter','Freeform']

class HTMLText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.ignored=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.ignored+=1
    def handle_endtag(self,tag):
        if tag in ('script','style') and self.ignored:self.ignored-=1
    def handle_data(self,data):
        if not self.ignored:self.parts.append(data)
def plain(x):
    obj=HTMLText();obj.feed(html.unescape(str(x or '')))
    return re.sub(r'\s+',' ',' '.join(obj.parts)).strip()

def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'job-cockpit-source-verifier/0.1','Accept':'application/json,text/html'}),timeout=20) as response:
        raw=response.read(2_000_000).decode('utf-8',errors='replace')
        return response.status,raw

def official_check(row):
    canonical=row['canonical_id']
    kind,_,rest=canonical.partition(':')
    if kind=='greenhouse':
        slug,ident=rest.rsplit(':',1)
        url='https://boards-api.greenhouse.io/v1/boards/'+slug+'/jobs/'+ident+'?content=true'
        code,body=fetch(url)
        data=json.loads(body)
        if str(data.get('id'))!=ident:raise ValueError('Official Greenhouse job ID mismatch')
        description=plain(data.get('content',''))
        result='listed_on_official_ats'
    elif kind=='lever':
        slug,ident=rest.rsplit(':',1)
        url='https://api.lever.co/v0/postings/'+slug+'/'+ident+'?mode=json'
        code,body=fetch(url)
        data=json.loads(body)
        if str(data.get('id'))!=ident:raise ValueError('Official Lever job ID mismatch')
        description=plain(data.get('descriptionPlain') or data.get('description',''))
        result='listed_on_official_ats'
    elif kind=='ashby' and not canonical.startswith('ashby:whatnot:'):
        slug,ident=rest.rsplit(':',1)
        url='https://api.ashbyhq.com/posting-api/job-board/'+slug
        code,body=fetch(url)
        data=json.loads(body)
        job=next((x for x in data.get('jobs',[]) if x.get('id','').lower()==ident.lower()),None)
        if job is None:raise ValueError('Job not listed by official Ashby board')
        description=plain(job.get('descriptionPlain') or job.get('descriptionHtml',''))
        result='listed_on_official_ats'
    elif canonical.startswith('ashby:whatnot:'):
        # The official Whatnot catalog was independently fetched via Python.
        # Its existence does not prove that the direct application is accepting.
        return {'official_status':'catalog_observed_only','source_url':'https://www.whatnot.com/careers/discover',
            'description_signature':None,'signals':{},'verification_status':'unverified'}
    else:
        return {'official_status':'unsupported_direct_check','source_url':row['official_url'],
            'description_signature':None,'signals':{},'verification_status':'unverified'}
    def matches(rx):
        return list(dict.fromkeys(m.group(0).strip() for m in rx.finditer(description)))[:5]
    return {'official_status':result,'source_url':url,'http_status':code,
        'description_signature':hashlib.sha256(description.encode()).hexdigest(),
        'signals':{'graduation_excerpts':matches(GRAD),'experience_excerpts':matches(YOE),
            'authorization_excerpts':matches(AUTH),'salary_range_excerpts':matches(SALARY)},
        'verification_status':'unverified'}

def select_candidates(data,limit=30,per_employer=3):
    eligible=[r for r in data['records'] if r['region']=='la_metro' and
              not ('seniority_title' in r['review_flags'] or 'non_target_title' in r['review_flags'])
              and CAREER.search(r['title'])]
    def ranking(r):
        target=0 if any(t.lower() in r['title'].lower() for t in
          ['new grad','early career','entry','junior','associate','engineer i','engineer 1']) else 1
        favored=0 if r['company'] in STRONG else 1
        supported=0 if r['canonical_id'].split(':')[0] in ('greenhouse','lever','ashby') else 1
        return (target,favored,supported,r['company'].lower(),r['title'].lower())
    selected=[];counts={}
    for r in sorted(eligible,key=ranking):
        employer=r['company'].lower()
        if counts.get(employer,0)>=per_employer:continue
        selected.append(r);counts[employer]=counts.get(employer,0)+1
        if len(selected)>=limit:break
    return selected

def probe(src,out,limit=30,delay=0.5):
    data=json.loads(Path(src).read_text());selected=select_candidates(data,limit)
    results=[];stamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    for r in selected:
        item={'canonical_id':r['canonical_id'],'company':r['company'],'title':r['title'],
             'region':r['region'],'official_url':r['official_url'],'checked_at':stamp}
        try:item.update(official_check(r))
        except (HTTPError,URLError,ValueError,json.JSONDecodeError,TimeoutError) as exc:
            item.update(official_status='check_failed',error=str(exc)[:180],verification_status='unverified')
        results.append(item)
        if delay:time.sleep(delay)
    output={'checked_at':stamp,'kind':'official_source_probe_not_applicant_eligibility',
            'requested':len(selected),'official_ats_listed':sum(x.get('official_status')=='listed_on_official_ats' for x in results),
            'verified_eligible_la':None,'records':results}
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--canonical',required=True);p.add_argument('--out',required=True)
    p.add_argument('--limit',type=int,default=24);p.add_argument('--delay',type=float,default=0.5)
    a=p.parse_args()
    r=probe(a.canonical,a.out,min(max(a.limit,1),60),a.delay)
    print(json.dumps({k:r[k] for k in ('requested','official_ats_listed','verified_eligible_la')},indent=2))
