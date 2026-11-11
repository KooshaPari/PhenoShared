"""Meaningful isolated installer checks; never touches canonical profiles or starts MCP servers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

INSTALL = Path(__file__).resolve().parents[1] / 'plugins/profile_install.py'

class Profiles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phinbox-harness-fixture-')
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def run_install(self, harness, profile, *extra, ok=True):
        result = subprocess.run(['python3', str(INSTALL), harness, '--profile-dir', str(profile),
            '--inbox-dir', str(self.root/'inbox'), '--binary', '/bin/false', *extra],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return result
    def test_dry_run_has_no_filesystem_effect(self):
        for harness in ['codex','jcode','forge','kcode']:
            profile=self.root/harness
            result=self.run_install(harness,profile)
            self.assertFalse(profile.exists())
            self.assertFalse(json.loads(result.stdout)['hooks_modified'])
    def test_json_profiles_preserve_other_servers_and_hooks_and_uninstall_owned_only(self):
        for harness,key,name in [('jcode','servers','mcp.json'),('kcode','servers','mcp.json'),('forge','mcpServers','.mcp.json')]:
            profile=self.root/harness;profile.mkdir()
            data={key:{'other':{'command':'existing-command','args':['keep']}}}
            (profile/name).write_text(json.dumps(data))
            hooks=b'{"hooks":{"PermissionRequest":["moshi","xirp"]}}'
            (profile/'hooks.json').write_bytes(hooks)
            self.run_install(harness,profile,'--apply')
            actual=json.loads((profile/name).read_text())
            self.assertEqual(actual[key]['other'],data[key]['other'])
            self.assertEqual(actual[key]['phinbox_mcp']['args'],[])
            self.assertEqual(actual[key]['phinbox_mcp']['env']['PHINBOX_INBOX_DIR'],str((self.root/'inbox').resolve()))
            self.assertEqual((profile/'hooks.json').read_bytes(),hooks)
            self.run_install(harness,profile,'--apply')
            self.run_install(harness,profile,'--apply','--uninstall')
            self.assertEqual(json.loads((profile/name).read_text()),data)
            self.assertEqual((profile/'hooks.json').read_bytes(),hooks)
    def test_changed_registration_cannot_be_uninstalled_or_overwritten(self):
        profile=self.root/'jcode';self.run_install('jcode',profile,'--apply')
        path=profile/'mcp.json';data=json.loads(path.read_text());data['servers']['phinbox_mcp']['args']=['operator-owned-change'];path.write_text(json.dumps(data))
        before=path.read_bytes()
        self.run_install('jcode',profile,'--apply','--uninstall',ok=False)
        self.run_install('jcode',profile,'--apply',ok=False)
        self.assertEqual(path.read_bytes(),before)
    def test_existing_unowned_registration_is_preserved(self):
        profile=self.root/'forge';profile.mkdir();path=profile/'.mcp.json'
        path.write_text(json.dumps({'mcpServers':{'phinbox_mcp':{'command':'operator-command'}}}))
        before=path.read_bytes();self.run_install('forge',profile,'--apply',ok=False);self.assertEqual(path.read_bytes(),before)
    def test_cross_harness_profile_reuse_is_refused(self):
        profile=self.root/'profile';self.run_install('jcode',profile,'--apply')
        self.run_install('kcode',profile,'--apply',ok=False)
        self.assertFalse((profile/'.mcp.json').exists())
    def test_canonical_profiles_and_symlink_escape_are_refused(self):
        self.run_install('codex',Path.home()/'.codex','--apply',ok=False)
        alias=self.root/'alias';alias.symlink_to(Path.home()/'.codex',target_is_directory=True)
        self.run_install('codex',alias,'--apply',ok=False)
        profile=self.root/'forge';profile.mkdir();external=self.root/'external';external.write_text('{}')
        (profile/'.mcp.json').symlink_to(external)
        self.run_install('forge',profile,'--apply',ok=False);self.assertEqual(external.read_text(),'{}')
    @unittest.skipUnless(shutil.which('codex'),'installed Codex CLI required for actual native profile check')
    def test_installed_codex_add_get_remove_uses_config_toml_and_preserves_hooks(self):
        profile=self.root/'codex';profile.mkdir();config=profile/'config.toml'
        config.write_text('model = "isolated-fixture"\n\n[mcp_servers.other]\ncommand = "/bin/false"\nargs = []\n')
        hooks=b'{"hooks":{"PermissionRequest":["moshi","xirp"]}}';(profile/'hooks.json').write_bytes(hooks)
        self.run_install('codex',profile,'--apply')
        self.assertIn('[mcp_servers.phinbox_mcp]',config.read_text());self.assertFalse((profile/'mcp.toml').exists())
        self.assertEqual((profile/'hooks.json').read_bytes(),hooks)
        self.run_install('codex',profile,'--apply')
        self.run_install('codex',profile,'--apply','--uninstall')
        self.assertNotIn('[mcp_servers.phinbox_mcp]',config.read_text());self.assertIn('[mcp_servers.other]',config.read_text())
        self.assertEqual((profile/'hooks.json').read_bytes(),hooks)

if __name__=='__main__':unittest.main()
