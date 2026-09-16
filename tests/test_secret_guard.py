"""Regression tests for the changed-content secret guard."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD = REPO_ROOT / "scripts" / "secret-guard.py"
BASELINE_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "secret_guard" / "unchanged-baseline.json"
)


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class SecretGuardChangedContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        run_git(self.repo, "init", "--quiet")
        run_git(self.repo, "config", "user.name", "Secret Guard Tests")
        run_git(self.repo, "config", "user.email", "secret-guard-tests@example.invalid")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_guard(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(GUARD), *args],
            cwd=self.repo,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def commit(self, relative_path: str, content: str, message: str) -> None:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        run_git(self.repo, "add", relative_path)
        run_git(self.repo, "commit", "--quiet", "-m", message)

    def test_unchanged_baseline_pattern_is_ignored(self) -> None:
        baseline = json.loads(BASELINE_FIXTURE.read_text(encoding="utf-8"))
        self.commit(
            "registry/index.json",
            json.dumps({"field": baseline["field"], "version": 1}, indent=2) + "\n",
            "baseline",
        )
        self.commit(
            "registry/index.json",
            json.dumps({"field": baseline["field"], "version": 2}, indent=2) + "\n",
            "unrelated update",
        )

        result = self.run_guard("--since-ref", "HEAD^")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("checked 1 changed file", result.stdout)

    def test_added_npm_token_is_blocked(self) -> None:
        self.commit("registry/index.json", '{"version": 1}\n', "baseline")
        token = "npm_" + ("A" * 20)
        self.commit(
            "registry/index.json",
            '{"version": 1, "token": "' + token + '"}\n',
            "add token fixture",
        )

        result = self.run_guard("--since-ref", "HEAD^")

        self.assertEqual(result.returncode, 1)
        self.assertIn("npm token", result.stdout)
        self.assertNotIn(token, result.stdout)

    def test_denied_path_is_blocked_even_without_secret_content(self) -> None:
        self.commit("docs/curated-prompts/example.txt", "safe\n", "baseline")
        self.commit("docs/curated-prompts/example.txt", "still safe\n", "update")

        result = self.run_guard("--since-ref", "HEAD^")

        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked path for secrets/PII risk", result.stdout)

    def test_option_like_revision_is_rejected(self) -> None:
        self.commit("registry/index.json", '{"version": 1}\n', "baseline")

        result = self.run_guard("--since-ref=-bad")

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid git revision", result.stderr)


if __name__ == "__main__":
    unittest.main()
