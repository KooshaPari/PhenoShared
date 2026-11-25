import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from canonicalize import official_key,export
from collect import DB_SCHEMA

ROLE='00000000-0000-4000-8000-000000000000'

class CanonicalTests(unittest.TestCase):
    def test_whatnot_ashby_url_alias(self):
        a='https://www.whatnot.com/careers/roles/'+ROLE
        b='https://jobs.ashbyhq.com/whatnot/'+ROLE+'/application?embed=true'
        self.assertEqual(official_key(a),official_key(b))
    def test_greenhouse_variants(self):
        a='https://boards.greenhouse.io/ziprecruiter/jobs/8127108?gh_jid=8127108'
        b='https://job-boards.greenhouse.io/ziprecruiter/jobs/8127108'
        self.assertEqual(official_key(a),official_key(b))
    def test_titles_do_not_collapse_requisitions(self):
        self.assertNotEqual(
            official_key('https://jobs.ashbyhq.com/whatnot/'+ROLE),
            official_key('https://jobs.ashbyhq.com/whatnot/00000000-0000-4000-8000-000000000000'))
    def test_actual_merge_and_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); dbpath=root/'jobs.sqlite3'; db=sqlite3.connect(dbpath)
            db.executescript(DB_SCHEMA)
            db.execute('''INSERT INTO jobs(job_key,provider,employer,provider_id,title,location,official_url,description,
              content_hash,first_seen,last_seen,changed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(
              'ashby:whatnot:'+ROLE,'ashby','Whatnot',ROLE,'Software Engineer, 2027 New Grad','Los Angeles, CA',
              'https://jobs.ashbyhq.com/whatnot/'+ROLE,'', 'sig','2026-10-10','2026-10-12','2026-10-10'))
            db.commit();db.close()
            whatnot=root/'whatnot.json'
            whatnot.write_text(json.dumps({'verification_status':'discovered_unverified','engineering_roles':[
              {'id':ROLE,'title':'Software Engineer, 2027 New Grad',
               'locations':['Los Angeles, CA'], 'official_url':'https://www.whatnot.com/careers/roles/'+ROLE}]}))
            result=export(dbpath,whatnot,root/'canonical.json',now='2026-10-12T18:00:00Z')
            self.assertEqual(result['unique_canonical_jobs'],1)
            self.assertEqual(result['records'][0]['source_count'],2)
            self.assertEqual(result['records'][0]['verification_status'],'unverified')
            self.assertIsNone(result['verified_eligible_la'])

if __name__ == '__main__': unittest.main()
