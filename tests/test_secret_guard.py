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
    # core.hooksPath is emptied so a developer machine's global commit-message
    # hook cannot decide whether these fixture commits are allowed to exist.
    subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
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

    def baseline(self) -> None:
        """`--since-ref HEAD^` needs a parent commit to resolve against."""
        self.commit("registry/index.json", '{"version": 1}\n', "baseline")

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

    def test_documented_placeholder_values_are_ignored(self) -> None:
        # The three findings that turned main red on 2026-11-11, in the shapes
        # they appear in: the AWS documentation example key, two BytePort
        # link-handler fixtures, and a scanner spelling out the fakes it hunts.
        self.baseline()
        self.commit(
            "absorption/byteport/backend/byteport/routes/link_test.go",
            'const body = `{"accessKeyId": "AKIAIOSFODNN7EXAMPLE",'
            ' "apiKey": "sk-legacy-camelcase-key"}`\n'
            'const fakes = {"AKIAABCDEFGHIJKLMNOP",'
            ' "ghp_abcdefghijklmnopqrstuvwxyz0123456789"}\n',
            "placeholder fixtures",
        )

        result = self.run_guard("--since-ref", "HEAD^")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lookalike_keys_beside_placeholders_are_blocked(self) -> None:
        # Negative control: the allowlist is per value, so a credential that
        # merely shares a file with placeholders is still reported.
        self.baseline()
        self.commit(
            "absorption/byteport/backend/byteport/routes/link_test.go",
            'const body = `{"accessKeyId": "AKIAIOSFODNN7EXAMPLE",'
            ' "apiKey": "sk-Q7f3Lm2Xr9Tb4Vc1Nw8Z"}`\n',
            "placeholder plus a real-shaped key",
        )

        result = self.run_guard("--since-ref", "HEAD^")

        self.assertEqual(result.returncode, 1)
        self.assertIn("OpenAI key", result.stdout)
        self.assertNotIn("AWS access key", result.stdout)

    def test_env_template_is_scanned_rather_than_denied(self) -> None:
        # `.env.example` is a file a repository has to commit. It carries names
        # and local defaults, and no credential.
        self.baseline()
        self.commit(
            "absorption/byteport/.env.example",
            "# BytePort environment\n"
            "BYTEPORT_API_PORT=8081\n"
            "BYTEPORT_DATABASE_URL=sqlite:///data/byteport.db\n"
            "BYTEPORT_PASETO_KEY=\n"
            "WORKOS_CLIENT_SECRET=\n",
            "env template",
        )

        result = self.run_guard("--since-ref", "HEAD^")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("checked 1 changed file", result.stdout)

    def test_env_template_carrying_a_key_is_blocked(self) -> None:
        self.baseline()
        self.commit(
            "absorption/byteport/.env.example",
            "WORKOS_CLIENT_SECRET=sk-Q7f3Lm2Xr9Tb4Vc1Nw8Z\n",
            "template with a value",
        )

        result = self.run_guard("--since-ref", "HEAD^")

        self.assertEqual(result.returncode, 1)
        self.assertIn("potential secret pattern (OpenAI key)", result.stdout)

    def test_non_template_env_file_is_still_denied(self) -> None:
        # The template exception is three suffixes wide, not a hole in the rule.
        self.baseline()
        self.commit(
            "absorption/byteport/.env.local",
            "WORKOS_CLIENT_SECRET=\n",
            "local env file",
        )

        result = self.run_guard("--since-ref", "HEAD^")

        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked path for secrets/PII risk", result.stdout)


if __name__ == "__main__":
    unittest.main()
