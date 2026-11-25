import importlib.util,sys,json,tempfile,unittest,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from apply_overlay import safe_target,git_blob,plan,apply
from activate_skills import activate
from compile_illustrator import compile_job
from media_audit import audit

class FilesystemTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_traversal(self):
  with self.assertRaises(ValueError):safe_target(self.root,'../bad')
 def test_absolute_path(self):
  with self.assertRaises(ValueError):safe_target(self.root,'/bad')
 def test_symlink(self):
  (self.root/'real').mkdir();(self.root/'link').symlink_to(self.root/'real',target_is_directory=True)
  with self.assertRaises(ValueError):safe_target(self.root,'link/a')
 def test_git_blob(self):self.assertEqual(git_blob(b''),'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
 def test_missing_migration_blocks(self):
  with self.assertRaisesRegex(ValueError,'Migration prerequisite'):plan(self.root)
 def test_dryrun_writes_nothing(self):
  r=apply(self.root,{'x.txt':b'new'});self.assertEqual(r['mode'],'dry-run');self.assertFalse((self.root/'x.txt').exists())
 def test_apply_addition_backup_and_idempotence(self):
  r=apply(self.root,{'x.txt':b'new'},enabled=True);self.assertEqual((self.root/'x.txt').read_bytes(),b'new');self.assertTrue(Path(r['backup']).is_dir());self.assertEqual(apply(self.root,{'x.txt':b'new'},enabled=True)['changed'],[]);shutil.rmtree(r['backup'])
 def test_drift_after_plan_rejected(self):
  (self.root/'x.txt').write_bytes(b'changed')
  with self.assertRaises(ValueError):apply(self.root,{'x.txt':b'new'},enabled=True)
 def test_skill_dry_run(self):
  p=self.root/'skills/pd-test';p.mkdir(parents=True);(p/'SKILL.md').write_text('test')
  self.assertEqual(activate(self.root,'codex')['copyCount'],1);self.assertFalse((self.root/'.agents').exists())
 def test_skill_apply_and_repeat(self):
  p=self.root/'skills/pd-test';p.mkdir(parents=True);(p/'SKILL.md').write_text('test')
  activate(self.root,'forge',True);self.assertEqual(activate(self.root,'forge',True)['copyCount'],0)
 def test_skill_conflict(self):
  p=self.root/'skills/pd-test';p.mkdir(parents=True);(p/'SKILL.md').write_text('test');q=self.root/'.agents/skills/pd-test';q.mkdir(parents=True);(q/'SKILL.md').write_text('other')
  with self.assertRaises(ValueError):activate(self.root,'codex',True)
 def test_illustrator_compiles(self):
  j=json.loads((ROOT/'examples/illustrator.job.json').read_text());s=compile_job(j,self.root);self.assertNotIn('__JOB_JSON__',s);self.assertIn('pd-vector-canary',s)
 def test_illustrator_rejects_id(self):
  j=json.loads((ROOT/'examples/illustrator.job.json').read_text());j['id']='../bad'
  with self.assertRaises(ValueError):compile_job(j,self.root)
 def test_illustrator_rejects_code_operations(self):
  j=json.loads((ROOT/'examples/illustrator.job.json').read_text());j['layers'][0]['shapes'][0]['kind']='execute'
  with self.assertRaises(ValueError):compile_job(j,self.root)
 def test_illustrator_bounds(self):
  j=json.loads((ROOT/'examples/illustrator.job.json').read_text());j['width']=float('inf')
  with self.assertRaises(ValueError):compile_job(j,self.root)
 def test_media_real_decode_and_contract(self):
  self.assertEqual(audit(ROOT/'evidence/synthetic-media-canary.mp4',width=320,height=180,duration=2,audio=True)['checks']['decode'],'PASS')
 def test_media_rejects_wrong_dimensions(self):
  with self.assertRaises(ValueError):audit(ROOT/'evidence/synthetic-media-canary.mp4',width=1)
 def test_media_rejects_wrong_duration(self):
  with self.assertRaises(ValueError):audit(ROOT/'evidence/synthetic-media-canary.mp4',duration=5)
 def test_media_rejects_missing_audio_contract(self):
  with self.assertRaises(ValueError):audit(ROOT/'evidence/synthetic-media-canary.mp4',audio=False)
 def test_media_rejects_truncated(self):
  p=self.root/'broken.mp4';p.write_bytes((ROOT/'evidence/synthetic-media-canary.mp4').read_bytes()[:128])
  with self.assertRaises(ValueError):audit(p)
if __name__=='__main__':unittest.main()
