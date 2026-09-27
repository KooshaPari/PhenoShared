from __future__ import annotations
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import audit
import receipt_validator as rv

class ManifestTests(unittest.TestCase):
    def codes(self,path,text):
        return {x['code'] for x in audit.inspect_blob(path,text)}
    def test_multiple_project_flags(self):
        self.assertTrue(audit.repeated_projects('bun x tsc --noEmit -p a.json -p b.json'))
        self.assertTrue(audit.repeated_projects('tsgo --project=a --project=b'))
    def test_two_distinct_invocations_are_not_multiple_selection(self):
        self.assertFalse(audit.repeated_projects('tsc -p a.json && tsc -p b.json'))
        self.assertFalse(audit.repeated_projects('tsc -b a.json b.json'))
    def test_legacy_version_not_command_name(self):
        old=json.dumps({'devDependencies':{'typescript':'5.9.3'},'scripts':{'typecheck':'tsc --noEmit'}})
        new=json.dumps({'devDependencies':{'typescript':'7.0.2'},'scripts':{'typecheck':'tsc --noEmit'}})
        self.assertIn('TS_LEGACY_DECLARATION',self.codes('package.json',old))
        self.assertNotIn('TS_LEGACY_DECLARATION',self.codes('package.json',new))
    def test_noncanonical_runner_is_only_a_candidate(self):
        obs=audit.inspect_blob('package.json',json.dumps({'scripts':{'lint':'biome check .'}}))
        self.assertEqual(obs[0]['adjudication'],'needs_profile_and_evidence')
    def test_oxfmt_declaration(self):
        self.assertIn('FORMATTER_SOURCE_UNRESOLVED',self.codes('package.json',json.dumps({'scripts':{'format':'oxfmt .'}})))
        self.assertNotIn('FORMATTER_SOURCE_UNRESOLVED',self.codes('package.json',json.dumps({'scripts':{'format':'oxfmt .'},'devDependencies':{'oxfmt':'0.1.0'}})))
    def test_check_mutates(self):
        self.assertIn('CHECK_INVOKES_REPAIR',self.codes('package.json',json.dumps({'scripts':{'lint:stylelint':'bun run lint:stylelint:fix && stylelint .'}})))
        self.assertNotIn('CHECK_INVOKES_REPAIR',self.codes('package.json',json.dumps({'scripts':{'format:check':'oxfmt --check .'}})))
    def test_floating_inputs_not_automatic_failure(self):
        c=self.codes('package.json',json.dumps({'packageManager':'bun','devDependencies':{'typescript':'latest','x':'github:<REDACTED>/x'}}))
        self.assertTrue({'BUN_VERSION_UNDECLARED','FLOATING_DEPENDENCY_INPUT','DEPENDENCY_PLACEHOLDER'}<=c)
    def test_python_minimum_and_target_are_distinct(self):
        text='[project]\nrequires-python=">=3.14"\n[tool.ruff]\ntarget-version="py312"\n'
        self.assertIn('PYTHON_LINT_TARGET_MISMATCH',self.codes('python/pyproject.toml',text))
        self.assertIn('PYTHON_RUNTIME_NOT_PROVEN',self.codes('python/pyproject.toml',text))
    def test_size_profile_observation(self):
        self.assertIn('SIZE_ORIENTED_RELEASE_PROFILE',self.codes('Cargo.toml','[profile.release]\nopt-level="z"\n'))
    def test_workflow_ref(self):
        self.assertIn('WORKFLOW_MUTABLE_REF_CANDIDATE',self.codes('.github/workflows/ci.yml','jobs:\n  x:\n    uses: org/repo/.github/workflows/x.yml@main\n'))
        self.assertFalse(self.codes('.github/workflows/ci.yml','    uses: org/repo/.github/workflows/x.yml@'+'a'*40+'\n'))
    def test_history_is_not_live_adoption(self):
        self.assertNotEqual(audit.source_class('.archive/x/package.json'),'eligible_for_static_inspection_not_proven_active')
        self.assertNotEqual(audit.source_class('x/vendor/y/package.json'),'eligible_for_static_inspection_not_proven_active')
        self.assertNotEqual(audit.source_class('tests/fixtures/x/package.json'),'eligible_for_static_inspection_not_proven_active')
        self.assertEqual(audit.source_class('docs/package.json'),'eligible_for_static_inspection_not_proven_active')
    def test_malformed_manifest_not_silently_accepted(self):
        for text in ['{','[]','{"scripts":[]}','{"scripts":{"lint":4}}','{"dependencies":[]}']:
            with self.assertRaises(ValueError):audit.inspect_blob('package.json',text)

class GitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.repo=Path(self.tmp.name)
        self.g('init','-q');self.g('config','user.email','fixture@example.invalid');self.g('config','user.name','Fixture')
    def tearDown(self):self.tmp.cleanup()
    def g(self,*args):return subprocess.check_output(['git','-C',str(self.repo),*args],stderr=subprocess.STDOUT)
    def commit(self):self.g('add','.');self.g('commit','-qm','fixture')
    def test_reads_pinned_commit_not_dirty_worktree(self):
        p=self.repo/'package.json';p.write_text('{"scripts":{"typecheck":"tsc -p a -p b"}}');self.commit()
        p.write_text('{"scripts":{}}')
        r=audit.scan(self.repo)
        self.assertEqual(r['qualification'],'NOT_EVALUATED')
        self.assertEqual(r['collection_status'],'COMPLETED_STATIC_ONLY')
        self.assertIn('TS_MULTIPLE_PROJECT_FLAGS',{x['code'] for x in r['observations']})
    def test_bad_json_makes_collection_incomplete(self):
        (self.repo/'package.json').write_text('{');self.commit()
        self.assertEqual(audit.scan(self.repo)['collection_status'],'INCOMPLETE')
    def test_archives_and_symlinks_are_not_executed(self):
        (self.repo/'.archive').mkdir();(self.repo/'.archive/package.json').write_text('{')
        (self.repo/'package.json').symlink_to('/definitely/unavailable/elsewhere');self.commit()
        r=audit.scan(self.repo)
        self.assertEqual(r['counts']['non_regular_entries'],1)
        self.assertEqual(r['counts']['inspected_files'],0)
        self.assertEqual(r['qualification'],'NOT_EVALUATED')

class ReceiptTests(unittest.TestCase):
    def receipt(self):
        return {'source_commit':'a'*40,'evaluator_commit':'b'*40,'profile_id':'fixture',
            'tool_fingerprint':'fixture-tool','producer_id':'unauthenticated-fixture','artifact_digest':'fixture',
            'measurements':[{'family':f,'status':'executed','covered':100,'eligible':100,'failed':0,'exit_code':0,'evidence_ref':'fixture.json'} for f in rv.FLOORS]}
    def errs(self,r):return rv.validate(r,'a'*40,'b'*40)
    def test_good_structure_only(self):self.assertEqual(self.errs(self.receipt()),[])
    def test_wrong_revision(self):
        r=self.receipt();r['source_commit']='c'*40;self.assertTrue(self.errs(r))
    def test_empty_family_set(self):
        r=self.receipt();r['measurements']=[];self.assertEqual(len(self.errs(r)),6)
    def test_skipped_is_not_pass(self):
        r=self.receipt();r['measurements'][0]['status']='skipped';self.assertTrue(self.errs(r))
    def test_zero_denominator(self):
        r=self.receipt();r['measurements'][0]['eligible']=0;self.assertTrue(self.errs(r))
    def test_independent_floors_not_averaged(self):
        r=self.receipt();r['measurements'][0]['covered']=84;self.assertTrue(self.errs(r))
    def test_critical_requires_all(self):
        r=self.receipt();r['measurements'][-1]['covered']=99;self.assertTrue(self.errs(r))
    def test_missing_tool_and_failed_exit(self):
        r=self.receipt();r.pop('tool_fingerprint');r['measurements'][0]['exit_code']=2;self.assertTrue(self.errs(r))
    def test_nan_boolean_and_overcoverage_rejected(self):
        for val in (float('nan'),True,101,-1):
            r=self.receipt();r['measurements'][0]['covered']=val;self.assertTrue(self.errs(r))
    def test_duplicate_unknown_and_malformed_rows(self):
        r=self.receipt();r['measurements'] += [copy.deepcopy(r['measurements'][0]),{'family':'unknown'},None];self.assertTrue(self.errs(r))
        self.assertTrue(self.errs([]))
        r=self.receipt();r['measurements']={};self.assertTrue(self.errs(r))
    def test_missing_evidence_and_explicit_failed_behavior(self):
        r=self.receipt();r['measurements'][0]['evidence_ref']='';r['measurements'][1]['failed']=1;self.assertTrue(self.errs(r))
        for value in (None, False, 0.0, '0'):
            r=self.receipt();r['measurements'][0]['failed']=value;self.assertTrue(self.errs(r))


class CommandLineTests(unittest.TestCase):
    def test_receipt_cli_valid_and_invalid(self):
        from unittest.mock import patch
        import contextlib,io
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'receipt.json'
            path.write_text(json.dumps(ReceiptTests().receipt()))
            argv=['receipt_validator.py',str(path),'--expected-source','a'*40,'--expected-evaluator','b'*40]
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(rv.main(),0)
                self.assertIn('NOT_AUTHENTICATED',out.getvalue())
            path.write_text('{')
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(rv.main(),2)
    def test_collector_cli_output_and_error(self):
        from unittest.mock import patch
        import contextlib,io
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); subprocess.run(['git','init','-q',str(p)],check=True)
            subprocess.run(['git','-C',str(p),'config','user.email','fixture@example.invalid'],check=True)
            subprocess.run(['git','-C',str(p),'config','user.name','Fixture'],check=True)
            (p/'package.json').write_text('{}')
            subprocess.run(['git','-C',str(p),'add','.'],check=True)
            subprocess.run(['git','-C',str(p),'commit','-qm','fixture'],check=True)
            output=p/'reports/result.json'
            with patch.object(sys,'argv',['audit.py','--repo',str(p),'--output',str(output)]):self.assertEqual(audit.main(),0)
            self.assertEqual(json.loads(output.read_text())['qualification'],'NOT_EVALUATED')
            with patch.object(sys,'argv',['audit.py','--repo',str(p)]),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(audit.main(),0)
            with patch.object(sys,'argv',['audit.py','--repo',str(p),'--ref','does-not-exist']),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(audit.main(),2)

if __name__=='__main__':unittest.main()
