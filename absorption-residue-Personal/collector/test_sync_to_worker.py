import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import sync_to_worker as w

ROLE='00000000-0000-4000-8000-000000000000'
class SyncTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.root=Path(self.tmp.name)
  self.file=self.root/'whatnot.json'
  self.file.write_text(json.dumps({'verification_status':'discovered_unverified',
   'engineering_roles':[{'id':ROLE,'title':'Software Engineer, New Grad',
   'official_url':'https://www.whatnot.com/careers/roles/'+ROLE,
   'locations':['Los Angeles, CA']}] * 20}))
 def tearDown(self):self.tmp.cleanup()
 def test_dry_run_never_sends(self):
  with patch.object(w,'send',side_effect=AssertionError('Unexpected network write')):
   report=w.sync(self.file,self.root/'report.json',execute=False)
  self.assertEqual(report['sent'],False)
  self.assertEqual(report['ingested'],0)
 def test_null_locations_skipped_not_fatal(self):
  doc=json.loads(self.file.read_text())
  doc['engineering_roles'].append({'id':'00000000-0000-4000-8000-000000000000','title':'Staff Engineer - Japan',
   'official_url':'https://www.whatnot.com/careers/roles/00000000-0000-4000-8000-000000000000','locations':None})
  self.file.write_text(json.dumps(doc))
  rows=w.prepare(self.file)
  self.assertEqual(len(rows),20)
 def test_execute_requires_token(self):
  with self.assertRaises(RuntimeError):
   w.sync(self.file,self.root/'report.json',execute=True,token=None)
 def test_authenticated_response_accounting(self):
  with patch.object(w,'send',return_value={'added':19,'dup':1,'bad':0}) as send:
   report=w.sync(self.file,self.root/'report.json',execute=True,token='unittest-secret-not-real')
  self.assertTrue(report['sent'])
  self.assertEqual(report['ingested'],19)
  self.assertEqual(report['duplicates'],1)
  self.assertEqual(send.call_count,1)
 def test_unresolved_location_roles_are_skipped(self):
  doc=json.loads(self.file.read_text())
  doc['engineering_roles'].append({'id':'00000000-0000-4000-8000-000000000000',
    'title':'Staff Software Engineer - Japan',
    'official_url':'https://www.whatnot.com/careers/roles/00000000-0000-4000-8000-000000000000'})
  self.file.write_text(json.dumps(doc))
  result=w.sync(self.file,self.root/'report.json',execute=False)
  self.assertEqual(result['observations'],20)
  self.assertEqual(result['skipped_location_unresolved'],1)
 def test_rejects_unverified_source_shape(self):
  self.file.write_text('{}')
  with self.assertRaises(ValueError):w.prepare(self.file)

if __name__=='__main__':unittest.main()
