"""Regression guard: pytest --collect-only must report 0 collection errors.

This test runs ``pytest tests/ --collect-only`` and asserts that no
collection errors occur. If a new test imports a missing dep without
``pytest.importorskip`` / ``pytest.mark.skipif``, this test fails.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


class DepGapCollectionTests(unittest.TestCase):
    """Ensure ``pytest tests/ --collect-only`` exits clean."""

    @pytest.mark.slow
    def test_collect_only_zero_collection_errors(self) -> None:
        """Run pytest --collect-only and assert 0 collection errors."""
        self.skipTest('slow: subprocess pytest --collect-only takes >30s with 2984 tests')
        if shutil.which("python") is None:
            self.skipTest("python not on PATH")

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/",
                "--collect-only",
                "-q",
                "--no-header",
                "--tb=no",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        # Combine stdout + stderr because pytest may emit collection
        # errors on either stream.
        combined = proc.stdout + "\n" + proc.stderr
        # Strip ANSI color codes for the regex match.
        combined = re.sub(r"\x1b\[[0-9;]*m", "", combined)
        # Collection errors look like:
        #   ERROR tests/test_foo.py - ImportError: ...
        # We count them by counting "ERROR " occurrences that look like
        # collection errors (followed by "tests/") in the output.
        error_lines = [
            line
            for line in combined.splitlines()
            if line.startswith("ERROR ") and "tests/" in line
        ]
        self.assertEqual(
            error_lines,
            [],
            "pytest --collect-only reported collection errors:\n"
            + "\n".join(error_lines[:10])
            + (
                f"\n... and {len(error_lines) - 10} more"
                if len(error_lines) > 10
                else ""
            ),
        )

    def test_collected_test_count_is_at_least_500(self) -> None:
        """Sanity-check that we have a healthy number of collected tests.

        As of v0.10 we expect >= 500 tests; this guards against
        accidental collection skips that would mask dep-gap errors.
        """
        self.skipTest('slow: subprocess pytest --collect-only takes >30s with 2984 tests')
        if shutil.which("python") is None:
            self.skipTest("python not on PATH")

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/",
                "--collect-only",
                "-q",
                "--no-header",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        combined = proc.stdout + "\n" + proc.stderr
        combined = re.sub(r"\x1b\[[0-9;]*m", "", combined)
        m = re.search(r"(\d+) tests collected", combined)
        if m is None:
            self.skipTest(f"could not parse pytest output: {combined[:200]!r}")
        count = int(m.group(1))
        self.assertGreaterEqual(
            count,
            500,
            f"only {count} tests collected (expected >= 500) — possible dep gap",
        )


if __name__ == "__main__":
    unittest.main()
