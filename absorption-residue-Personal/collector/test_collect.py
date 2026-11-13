"""Offline contract tests: python -m unittest discover -s collector -p 'test_*.py'."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('collect.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript(module.DB_SCHEMA)
        self.config = {'sources': [{'provider':'greenhouse','slug':'example','employer':'Example'}]}
        self.job = {'id':123,'title':'Software Engineer, New Grad',
                    'location':{'name':'Los Angeles, CA'},
                    'absolute_url':'https://job-boards.greenhouse.io/example/jobs/123',
                    'content':'<p>Build backend tools.</p>'}
    def tearDown(self):
        self.db.close()
    def test_normalization(self):
        record = module.normalize('greenhouse','Example',self.job)
        self.assertEqual(record[0], 'greenhouse:example:123')
        self.assertEqual(record[7], 'Build backend tools.')
        self.assertEqual(len(record[8]),64)
    def test_ashby_and_lever(self):
        ashby = module.normalize('ashby','Example',{'id':'abc','title':'Backend Engineer',
            'location':'Los Angeles','jobUrl':'https://jobs.ashbyhq.com/example/abc',
            'descriptionPlain':'Hello'})
        lever = module.normalize('lever','Example',{'id':'abc','text':'Backend Engineer',
            'categories':{'location':'Los Angeles'},'hostedUrl':'https://jobs.lever.co/example/abc',
            'descriptionPlain':'Hello'})
        self.assertNotEqual(ashby[0], lever[0])
        self.assertEqual(ashby[5],lever[5])
    def test_new_unchanged_changed(self):
        with patch.object(module,'fetch_json',return_value={'jobs':[self.job]}):
            first = module.discover(self.db,self.config,delay=0)
            second = module.discover(self.db,self.config,delay=0)
        self.assertEqual((first['new'],second['unchanged']),(1,1))
        self.assertEqual(len(module.triage(self.db)),1)
        changed = dict(self.job, content='<p>Build distributed backend tools.</p>')
        with patch.object(module,'fetch_json',return_value={'jobs':[changed]}):
            third = module.discover(self.db,self.config,delay=0)
        self.assertEqual(third['changed'],1)
        self.assertEqual(self.db.execute('SELECT verification_status FROM jobs').fetchone()[0],'needs_review')
    def test_failed_source_does_not_close_existing(self):
        with patch.object(module,'fetch_json',return_value={'jobs':[self.job]}):
            module.discover(self.db,self.config,delay=0)
        with patch.object(module,'fetch_json',side_effect=module.URLError('temporary')):
            summary=module.discover(self.db,self.config,delay=0)
        self.assertEqual(summary['sources_failed'],1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],1)
    def test_senior_and_intern_excluded(self):
        self.assertIsNotNone(module.EXCLUDE.search('Senior Software Engineer'))
        self.assertIsNotNone(module.EXCLUDE.search('Software Engineering Intern'))
        self.assertIsNone(module.EXCLUDE.search('Software Engineer, New Grad'))

if __name__ == '__main__':
    unittest.main()
