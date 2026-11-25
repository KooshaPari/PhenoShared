from __future__ import annotations
import hashlib,importlib.util,json,math,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
build=load('asset_build','scripts/build_asset.py');audit=load('asset_audit','scripts/audit_asset.py');sync=load('skill_sync','scripts/sync_skills.py');runner=load('blender_runner','scripts/run_blender.py')
class AssetTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model=build.build();cls.raw=build.glb_bytes(cls.model)
 def test_deterministic(self):self.assertEqual(self.raw,build.glb_bytes(build.build()))
 def test_checked_in_model_matches_generator(self):self.assertEqual(self.raw,(ROOT/'assets/concept-trainer.glb').read_bytes())
 def test_manifest_hashes(self):audit.audit_manifest(ROOT)
 def test_glb_consistency(self):self.assertGreater(audit.audit_glb(self.raw)['triangles'],10000)
 def test_reject_truncated(self):
  with self.assertRaises(ValueError):audit.audit_glb(self.raw[:-16])
 def test_reject_magic(self):
  with self.assertRaises(ValueError):audit.audit_glb(b'xxxx'+self.raw[4:])
 def test_reject_out_of_bounds_indices(self):
  bad=build.build();bad['parts'][0]['indices'][0]=9999999
  with self.assertRaises(ValueError):audit.audit_glb(build.glb_bytes(bad))
 def test_reject_duplicate_names(self):
  bad=build.build();bad['parts'][1]['name']=bad['parts'][0]['name']
  with self.assertRaises(ValueError):audit.audit_glb(build.glb_bytes(bad))
 def test_source_normals_finite(self):
  self.assertTrue(all(math.isfinite(n) for p in self.model['parts'] for n in p['normals']))
 def test_bounded_parts(self):
  self.assertLess(len(self.model['parts']),100);self.assertGreater(len(self.model['parts']),10)
 def test_held_axes(self):self.assertEqual(self.model['up'],'+Y');self.assertEqual(self.model['forward'],'+X')
class InstallTests(unittest.TestCase):
 def test_dry_plan_no_write(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);o=sync.plan(p,'codex',['fd3d-scroll-story']);self.assertEqual(o[0]['status'],'CREATE');self.assertFalse((p/'.agents').exists())
 def test_conflict(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);d=p/'.agents/skills/fd3d-scroll-story';d.mkdir(parents=True);(d/'SKILL.md').write_text('existing user rule');self.assertEqual(sync.plan(p,'codex',['fd3d-scroll-story'])[0]['status'],'CONFLICT');self.assertEqual((d/'SKILL.md').read_text(),'existing user rule')
 def test_identical(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);o=sync.plan(p,'forge',['fd3d-scroll-story'])[0];d=Path(o['destination']);d.parent.mkdir(parents=True);d.write_text(o['data']);self.assertEqual(sync.plan(p,'forge',['fd3d-scroll-story'])[0]['status'],'IDENTICAL')
 def test_reject_path_traversal(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):sync.plan(Path(t),'codex',['../../oops'])
 def test_reject_symlink(self):
  with tempfile.TemporaryDirectory() as t,tempfile.TemporaryDirectory() as external:
   p=Path(t)
   try:(p/'.agents').symlink_to(external,target_is_directory=True)
   except OSError:self.skipTest('OS disallows symlink creation')
   with self.assertRaises(ValueError):sync.plan(p,'codex',['fd3d-scroll-story'])
 def test_expanded_paths(self):
  with tempfile.TemporaryDirectory() as t:
   self.assertNotIn('{{KIT_ROOT}}',sync.plan(Path(t),'codex',['fd3d-scroll-story'])[0]['data'])
 def test_reject_nondirectory_parent(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'.agents').write_text('not a directory')
   with self.assertRaises(ValueError):sync.plan(p,'codex',['fd3d-scroll-story'])
 def test_apply_preserves_agents(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'AGENTS.md').write_text('user authority')
   r=subprocess.run([sys.executable,str(ROOT/'scripts/sync_skills.py'),'--project',t,'--harness','codex','--skills','fd3d-scroll-story','--apply'],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr);self.assertEqual((p/'AGENTS.md').read_text(),'user authority');self.assertTrue((p/'.agents/skills/fd3d-scroll-story/SKILL.md').is_file())
class PackagingTests(unittest.TestCase):
 def test_skill_frontmatter(self):
  files=sorted((ROOT/'skills').glob('*/SKILL.md'));self.assertEqual(len(files),18)
  for p in files:
   s=p.read_text();self.assertTrue(s.startswith('---\nname: '+p.parent.name+'\n'));self.assertIn('\ndescription:',s);self.assertLess(len(s.splitlines()),500)
 def test_source_catalog_unique(self):
  items=json.loads((ROOT/'resources/catalog.json').read_text())['items'];self.assertEqual(len(items),36);self.assertEqual(len({x['id'] for x in items}),len(items));self.assertEqual(sum(x['bundled'] for x in items),1)
 def test_upstream_blob(self):
  b=(ROOT/'upstream/anthropic/frontend-design/SKILL.md').read_bytes();sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();self.assertEqual(sha,'a5333457c414d20d625f307df945842c0952ecc3')
 def test_no_fonts(self):self.assertFalse([p for p in ROOT.rglob('*') if p.suffix.lower() in ('.ttf','.otf','.woff','.woff2')])
 def test_blender_argv_no_shell(self):
  cmd=runner.command('/path with space/blender',Path('/tmp/new job'),4,True);self.assertIn('--factory-startup',cmd);self.assertIn('--disable-autoexec',cmd);self.assertIn('--python-exit-code',cmd);self.assertEqual(cmd[0],'/path with space/blender')
 def test_standalone_has_no_external_resources(self):
  text=(ROOT/'demo-standalone.html').read_text();self.assertNotIn('<script src=',text);self.assertNotIn('<link rel="stylesheet"',text);self.assertIn('window.PRODUCT_MESH=',text);self.assertIn('data:image/svg+xml;base64,',text)
if __name__=='__main__':unittest.main()
