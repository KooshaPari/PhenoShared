"""Regression tests for the Lefthook CI install and PR-title shell boundary.

Run with Python + PyYAML. Set LEFTHOOK_TEST_BINARY to a verified native Lefthook
2.1.12 binary to additionally exercise the real commit-msg hook.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/lefthook-check.yml").read_text())
JOBS = WORKFLOW["jobs"]
INSTALLS = [
    step["run"]
    for job in JOBS.values()
    for step in job["steps"]
    if step["name"] == "Install lefthook"
]
TITLE_STEP = JOBS["commit-msg-check"]["steps"][-1]


class LefthookWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="lefthook-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Ubuntu provides GNU sha256sum. macOS may provide a BSD variant.
        if shutil.which("gsha256sum"):
            (self.bin / "sha256sum").symlink_to(shutil.which("gsha256sum"))
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}")
        self.env.update({key: str(value) for key, value in WORKFLOW["env"].items()})
        self.env.update(RUNNER_TEMP=str(self.root), GITHUB_PATH=str(self.root / "path"))

    def executable(self, name: str, source: str) -> Path:
        path = self.bin / name
        path.write_text("#!/bin/bash\nset -euo pipefail\n" + source)
        path.chmod(0o755)
        return path

    def run_shell(self, script: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-euo", "pipefail", "-c", script], cwd=self.root,
            env=self.env, capture_output=True, text=True, check=False,
        )

    def fake_download(self) -> None:
        artifact = self.root / "artifact"
        artifact.write_text('#!/bin/sh\nprintf "2.1.12\\n"\n')
        self.env["ARTIFACT"] = str(artifact)
        self.env["LEFTHOOK_SHA256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        self.executable("uname", 'printf "Linux x86_64\\n"\n')
        self.executable("curl", 'while [ "$1" != "--output" ]; do shift; done\ncp "$ARTIFACT" "$2"\n')

    def test_both_install_sites_share_pinned_verified_recipe(self) -> None:
        self.assertEqual(len(INSTALLS), 2)
        self.assertEqual(INSTALLS[0], INSTALLS[1])
        self.assertEqual(str(WORKFLOW["env"]["LEFTHOOK_VERSION"]), "2.1.12")
        self.assertEqual(WORKFLOW["env"]["LEFTHOOK_SHA256"],
                         "22ff1ad48d1a0f4dca8d6b7e920056c6a9015f9204e5b693858ed9c2db759a16")
        for script in INSTALLS:
            self.assertLess(script.index("sha256sum"), script.index("chmod"))
            self.assertNotIn("install.sh", script)
            self.assertNotIn("cargo", script)

    def test_install_success_exports_only_verified_binary(self) -> None:
        self.fake_download()
        result = self.run_shell(INSTALLS[0])
        self.assertEqual(result.returncode, 0, result.stderr)
        path = Path(self.env["GITHUB_PATH"]).read_text().strip()
        self.assertTrue(os.access(Path(path) / "lefthook", os.X_OK))

    def test_checksum_mismatch_does_not_execute_or_export(self) -> None:
        self.fake_download()
        self.env["LEFTHOOK_SHA256"] = "0" * 64
        result = self.run_shell(INSTALLS[0])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(Path(self.env["GITHUB_PATH"]).exists())
        self.assertFalse(os.access(next(self.root.glob("lefthook.*/lefthook")), os.X_OK))

    def test_download_failure_does_not_export(self) -> None:
        self.fake_download()
        self.executable("curl", "exit 22\n")
        self.assertNotEqual(self.run_shell(INSTALLS[0]).returncode, 0)
        self.assertFalse(Path(self.env["GITHUB_PATH"]).exists())

    def test_wrong_architecture_stops_before_download(self) -> None:
        self.fake_download()
        self.executable("uname", 'printf "Darwin arm64\\n"\n')
        self.assertNotEqual(self.run_shell(INSTALLS[0]).returncode, 0)
        self.assertEqual(list(self.root.glob("lefthook.*")), [])

    def test_title_is_data_not_executable_shell(self) -> None:
        (self.root / ".git").mkdir()
        self.executable("lefthook", 'test "$1" = run\ntest "$2" = commit-msg\n')
        self.assertEqual(TITLE_STEP["env"]["PR_TITLE"], "${{ github.event.pull_request.title }}")
        self.assertNotIn("${{", TITLE_STEP["run"])
        for title in ['ci: $(touch PWNED)', 'ci: `touch PWNED`',
                      'ci: "; touch PWNED; #', '-n', 'ci: back\\slash', '',
                      'ci: first\n$(touch PWNED)']:
            with self.subTest(title=title):
                self.env["PR_TITLE"] = title
                result = self.run_shell(TITLE_STEP["run"])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((self.root / ".git/COMMIT_MSG_TEMP").read_text(), title + "\n")
                self.assertFalse((self.root / "PWNED").exists())

    @unittest.skipUnless(os.environ.get("LEFTHOOK_TEST_BINARY"), "Set verified native binary path")
    def test_real_commit_message_validation(self) -> None:
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        shutil.copy(ROOT / "lefthook.yml", self.root / "lefthook.yml")
        self.executable("lefthook", 'exec "$LEFTHOOK_TEST_BINARY" "$@"\n')
        for title, valid in [("ci: repair installation", True), ("invalid title", False),
                             ("ci: $(touch PWNED)", True), ("", False)]:
            with self.subTest(title=title):
                self.env["PR_TITLE"] = title
                result = self.run_shell(TITLE_STEP["run"])
                self.assertEqual(result.returncode == 0, valid, result.stdout + result.stderr)
                self.assertFalse((self.root / "PWNED").exists())
                self.assertFalse((self.root / ".git/hooks/pre-commit").exists())


if __name__ == "__main__":
    unittest.main()
