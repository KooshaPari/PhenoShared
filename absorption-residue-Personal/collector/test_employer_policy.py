"""Offline exclusion regressions for this repo's secondary collector and projections."""
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import collect
import canonicalize
import triage
import sync_to_worker
from employer_policy import excluded_posting

ROLE='00000000-0000-4000-8000-000000000000'


class EmployerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.executescript(collect.DB_SCHEMA)
        self.job={'id':1,'title':'Software Engineer I','location':{'name':'Los Angeles, CA'},
                  'absolute_url':'https://job-boards.greenhouse.io/example/jobs/1','content':'Build software.'}
        self.source={'provider':'greenhouse','slug':'example','employer':'Example'}

    def tearDown(self):
        self.db.close()

    def test_names_objects_urls_and_vendor_mentions(self):
        for row in [{'company':'PALANTIR Technologies'}, {'hiringOrganization':{'name':'Palantir'}},
                    {'url':'https://jobs.lever.co/palantir/'+ROLE},
                    {'url':'https://jobs.lever.co/pal%61ntir/'+ROLE},
                    {'url':'https://jobs.eu.lever.co/palantir/'+ROLE},
                    {'url':'https://jobs.ashbyhq.com/palantir/'+ROLE},
                    {'url':'https://careers.palantir.com/jobs/1'},
                    {'url':'https://palantir.wd5.myworkdayjobs.com/en-US/Careers/job/Engineer_R123'}]:
            with self.subTest(row=row):self.assertTrue(excluded_posting(row))
        self.assertFalse(excluded_posting({'company':'Example','title':'Palantir integrations engineer'}))
        self.assertFalse(excluded_posting({'url':'https://jobs.lever.co/example/'+ROLE+'?ref=palantir.com'}))

    def test_excluded_configured_source_is_never_fetched(self):
        for employer,slug in [('Palantir','alias'),('Legacy alias','palantir')]:
            with self.subTest(employer=employer,slug=slug):
                config={'sources':[{'provider':'lever','slug':slug,'employer':employer}]}
                with patch.object(collect,'fetch_json',side_effect=AssertionError('must not fetch')):
                    result=collect.discover(self.db,config,delay=0)
                self.assertEqual(result['sources_excluded'],1)
                self.assertEqual(result['sources_failed'],0)
                self.assertEqual(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0],0)

    def test_foreign_company_row_is_filtered_without_failing_the_healthy_source(self):
        blocked={**self.job,'id':2,'company':{'name':'Palantir Technologies'}}
        with patch.object(collect,'fetch_json',return_value={'jobs':[self.job,blocked]}):
            result=collect.discover(self.db,{'sources':[self.source]},delay=0)
        self.assertEqual(result['new'],1);self.assertEqual(result['postings_excluded'],1)
        self.assertEqual(result['sources_ok'],1);self.assertEqual(result['sources_failed'],0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0],1)

    def test_all_provider_normalizers_reject_company_or_url_exclusion(self):
        for provider in ('greenhouse','lever','ashby'):
            self.assertIsNone(collect.normalize(provider,'Palantir',self.job))
            self.assertIsNone(collect.normalize(provider,'Example',{**self.job,'companyName':'Palantir'}))
            self.assertIsNone(collect.normalize(provider,'Example',{**self.job,'official_url':'https://jobs.lever.co/palantir/'+ROLE}))

    def test_cached_foreign_role_is_retired_and_cannot_reopen_without_identity_review(self):
        with patch.object(collect,'fetch_json',return_value={'jobs':[self.job]}):
            collect.discover(self.db,{'sources':[self.source]},delay=0)
        before=self.db.execute('SELECT first_seen,last_seen,content_hash FROM jobs').fetchone()
        with patch.object(collect,'fetch_json',return_value={'jobs':[{**self.job,'company':'Palantir'}]}):
            collect.discover(self.db,{'sources':[self.source]},delay=0)
        with patch.object(collect,'fetch_json',return_value={'jobs':[self.job]}):
            collect.discover(self.db,{'sources':[self.source]},delay=0)
        self.assertEqual(self.db.execute('SELECT verification_status FROM jobs').fetchone()[0],'ineligible')
        self.assertEqual(self.db.execute('SELECT first_seen,last_seen,content_hash FROM jobs').fetchone(),before)
        self.assertEqual(collect.triage(self.db),[])
        self.assertIsNone(triage.assess(('Palantir','Software Engineer I','Los Angeles',
                                      'https://example.test/job','','discovered')))

    def test_existing_palantir_rows_retire_without_deleting_history(self):
        with patch.object(collect,'fetch_json',return_value={'jobs':[self.job]}):
            collect.discover(self.db,{'sources':[self.source]},delay=0)
        self.db.execute("UPDATE jobs SET employer='Palantir'");self.db.commit()
        result=collect.discover(self.db,{'sources':[]},delay=0)
        self.assertEqual(result['sources_failed'],0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT verification_status FROM jobs').fetchone()[0],'ineligible')
        self.assertEqual(collect.triage(self.db),[])

    def test_other_employers_ineligible_rows_keep_the_existing_refresh_behavior(self):
        with patch.object(collect,'fetch_json',return_value={'jobs':[self.job]}):
            collect.discover(self.db,{'sources':[self.source]},delay=0)
        self.db.execute("UPDATE jobs SET verification_status='ineligible'");self.db.commit()
        with patch.object(collect,'fetch_json',return_value={'jobs':[{**self.job,'content':'Changed requirements.'}]}):
            result=collect.discover(self.db,{'sources':[self.source]},delay=0)
        self.assertEqual(result['changed'],1)
        self.assertEqual(self.db.execute('SELECT verification_status FROM jobs').fetchone()[0],'needs_review')

    def test_readonly_triage_and_canonical_exports_exclude_unretired_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'jobs.sqlite3';db=sqlite3.connect(path);db.executescript(collect.DB_SCHEMA)
            with patch.object(collect,'fetch_json',return_value={'jobs':[self.job,{**self.job,'id':2}]}):
                collect.discover(db,{'sources':[self.source]},delay=0)
            db.execute("UPDATE jobs SET employer='Palantir' WHERE provider_id='2'");db.commit();db.close()
            whatnot=root/'whatnot.json';whatnot.write_text(json.dumps({'verification_status':'discovered_unverified',
                'engineering_roles':[{'id':ROLE,'company':'Palantir','title':'Software Engineer',
                'locations':['Los Angeles'],'official_url':'https://www.whatnot.com/careers/roles/'+ROLE}]}))
            queue=triage.export(path,root/'triage.json');self.assertEqual(len(queue['candidates']),1)
            merged=canonicalize.export(path,whatnot,root/'canonical.json')
            self.assertEqual(merged['raw_ats_rows'],2);self.assertEqual(merged['unique_canonical_jobs'],1)
            self.assertEqual(merged['records'][0]['company'],'Example')
            db=sqlite3.connect(path);self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],2);db.close()

    def test_whatnot_sync_filters_before_stripping_employer_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);row={'id':ROLE,'title':'Software Engineer','locations':['Los Angeles, CA'],
                               'official_url':'https://www.whatnot.com/careers/roles/'+ROLE}
            source=root/'whatnot.json';source.write_text(json.dumps({'verification_status':'discovered_unverified',
                'engineering_roles':[row]*20+[{**row,'company':'Palantir'}]}))
            with patch.object(sync_to_worker,'send',side_effect=AssertionError('no network writes')):
                report=sync_to_worker.sync(source,root/'report.json',execute=False)
            self.assertEqual(report['observations'],20);self.assertEqual(report['skipped_employer_excluded'],1)
            self.assertEqual(report['skipped_location_unresolved'],0);self.assertFalse(report['sent'])

    def test_direct_sender_refuses_excluded_rows_before_network_or_credentials(self):
        with patch.object(sync_to_worker,'urlopen',side_effect=AssertionError('no network calls')):
            with self.assertRaisesRegex(ValueError,'Excluded employer'):
                sync_to_worker.send([{'company':'Palantir'}],None)


if __name__=='__main__':unittest.main()
