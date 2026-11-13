"""Conservative geographic/eligibility triage. This never verifies a job."""
import argparse, json, re, sqlite3
from pathlib import Path
from employer_policy import excluded_posting, excluded_keys
REGIONS={
 'la_metro':'los angeles|santa monica|culver city|marina del rey|el segundo|playa vista|hawthorne|burbank|pasadena|glendale|long beach|torrance|beverly hills|west hollywood|santa clarita|venice|manhattan beach|redondo beach|hermosa beach|calabasas|malibu|woodland hills|sherman oaks|encino|studio city',
 'rest_socal':'irvine|anaheim|orange county|san diego|carlsbad|newport beach|costa mesa|riverside|ontario|ventura|oxnard',
 'bay_area':'san francisco|san jose|mountain view|palo alto|sunnyvale|redwood city|menlo park|oakland|berkeley|santa clara',
 'seattle':'seattle|bellevue|redmond|kirkland',
 'portland':'portland, or|beaverton|hillsboro',
 'chicago':'chicago|evanston',
 'nyc':'new york|brooklyn|manhattan|queens|jersey city'
}
TITLE=re.compile(r'\b(software|backend|back.end|full.stack|frontend|front.end|platform|infrastructure|developer|devtools|machine learning|ml engineer|applied ai|site reliability|sre)\b',re.I)
SENIOR=re.compile(r'\b(senior|sr\.?|staff|principal|lead|director|manager|architect|intern(ship)?)\b',re.I)
PM_TITLE=re.compile(r'\b(associate product manager|apm|product manager|technical program manager|tpm|program manager|product analyst)\b',re.I)
PM_SENIOR=re.compile(r'\b(senior|sr\.?|staff|principal|lead|director|group|distinguished|head of)\b',re.I)
CA_EXCLUDED=re.compile(r'\b(?:not eligible (?:to be hired )?in ca|excluding ca|excl\.? ca|no ca)\b',re.I)
ENTRY=re.compile(r'\b(new grad(?:uate)?|university grad(?:uate)?|entry.level|early career|associate|junior|engineer i|engineer 1|swe i|swe 1)\b',re.I)
YOE5=re.compile(r'\b(?:5|[6-9]|1\d)\s*\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?(?:software\s+)?(?:engineering\s+)?experience\b',re.I)

def region(location):
    location=(location or '').lower()
    for bucket,patterns in REGIONS.items():
        if re.search(r'\b(?:'+patterns+r')\b',location): return bucket
    return 'remote_unconfirmed' if re.search(r'\bremote\b',location) else 'unapproved_or_unknown'

def assess(row):
    employer,title,location,url,description,status=row
    if excluded_posting({'employer': employer, 'official_url': url}):
        return None
    flags=[]
    is_pm=bool(PM_TITLE.search(title))
    if not is_pm and not TITLE.search(title): flags.append('non_target_title')
    if is_pm:
        if PM_SENIOR.search(title): flags.append('seniority_or_internship')
    elif SENIOR.search(title): flags.append('seniority_or_internship')
    if YOE5.search(description): flags.append('5_plus_years')
    if not ENTRY.search(title): flags.append('experience_unverified')
    bucket=region(location)
    if bucket=='remote_unconfirmed': flags.append('california_remote_permission_unverified')
    if CA_EXCLUDED.search(location or ''): flags.append('california_excluded')
    if bucket=='unapproved_or_unknown': flags.append('geography_unapproved_or_unknown')
    flags.extend(('graduation_unverified','official_page_not_independently_rechecked'))
    return {'employer':employer,'title':title,'location':location,'region':bucket,'official_url':url,
      'discovery_status':status,'verification_status':'unverified','review_flags':flags}

def export(db_path,out):
    conn=sqlite3.connect(db_path)
    rows=conn.execute('SELECT job_key,employer,title,location,official_url,description,verification_status FROM jobs').fetchall()
    blocked=excluded_keys(conn)
    result={'schema_version':1,'total_discovered':len(rows),'verified_eligible_la':None,
      'warning':'Heuristic triage only. No job is marked verified by this exporter.',
      'candidates':[candidate for key,*row in rows if key not in blocked and (candidate := assess(row)) is not None]}
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(result,indent=2))
    conn.close()
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--db',required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    r=export(a.db,a.out)
    print(json.dumps({'discovered':r['total_discovered'],'verified_eligible_la':None}))
