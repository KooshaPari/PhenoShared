"""Tests for scripts/desk-unconfined-check.sh.

Proves the script's three outcomes and exit codes:
  - UNCONFINED  (exit 0) when the log shows sandbox_allow_unsandboxed_exec
                          or the phrase "no native OS wrapper"
  - CONFINED     (exit 1) when the log is readable but shows neither marker
  - UNKNOWN      (exit 2) when the log cannot be read
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "desk-unconfined-check.sh")


class DeskUnconfinedCheckTest(unittest.TestCase):
    """Contract tests for the desk unconfined-check probe."""

    def run_script(self, log_path: str) -> subprocess.CompletedProcess:
        """Invoke the script with the given log path."""
        return subprocess.run(
            ["bash", SCRIPT, log_path],
            capture_output=True,
            text=True,
            check=False,
        )

    def write_log(self, directory: str, name: str, body: str) -> str:
        """Write a temp fixture log and return its path."""
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        return path

    def test_unconfined_on_sandbox_allow_unsandboxed_exec(self) -> None:
        """sandbox_allow_unsandboxed_exec in the log yields UNCONFINED and exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self.write_log(
                tmp,
                "unconfined.log",
                "boot ok\n"
                "trace: sandbox_allow_unsandboxed_exec=true\n"
                "done\n",
            )
            result = self.run_script(log_path)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertTrue(
            result.stdout.startswith("UNCONFINED "),
            msg=f"expected UNCONFINED line, got: {result.stdout!r}",
        )
        self.assertIn("sandbox_allow_unsandboxed_exec", result.stdout)
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)

    def test_unconfined_on_no_native_os_wrapper_phrase(self) -> None:
        """The phrase 'no native OS wrapper' yields UNCONFINED and exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self.write_log(
                tmp,
                "wrapper.log",
                "launching agent\n"
                "no native OS wrapper detected on this host\n",
            )
            result = self.run_script(log_path)

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertTrue(
            result.stdout.startswith("UNCONFINED "),
            msg=f"expected UNCONFINED line, got: {result.stdout!r}",
        )
        self.assertIn("no native OS wrapper", result.stdout)
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)

    def test_confined_when_no_markers_present(self) -> None:
        """A readable log without either marker yields CONFINED and exit 1."""
        with tempfile.TemporaryDirectory() as tmp:
            log_path = self.write_log(
                tmp,
                "confined.log",
                "sandbox enabled\n"
                "OS wrapper active\n"
                "session finished cleanly\n",
            )
            result = self.run_script(log_path)

        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "CONFINED")
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)

    def test_unknown_when_log_missing(self) -> None:
        """A missing log yields UNKNOWN no-evidence and exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "does-not-exist.log")
            result = self.run_script(missing)

        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "UNKNOWN no-evidence")
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
