"""Tests for the pre-commit WORKLOG.md validator (validate_worklog.py).

Run: pytest tests/test_validate_worklog.py -v
or:  python -m unittest tests.test_validate_worklog
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

# Locate the validator script relative to this test file.
_VALIDATOR = Path(__file__).resolve().parent.parent / "validate_worklog.py"


V21_SAMPLE = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1-001 | 2026-06-15 | pheno | docs | refactor | abc1234 | #1 | done | koosha | macbook | sample |
"""

V20_SAMPLE = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1-001 | 2026-06-15 | pheno | docs | refactor | abc1234 | #1 | done | koosha | sample |
"""

V1P_SAMPLE = """| Date | Task ID | Layer | Action | Files | Notes | device |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-06-18 | T1.3 | L0 | docs | meta-bundle | chore: add files | macbook |
"""

V1_SAMPLE = """| Date | Task ID | Layer | Action | Files | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-06-18 | T1.3 | L0 | docs | meta-bundle | chore: add files |
"""

V21_INVALID_DEVICE = """| task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1-001 | 2026-06-15 | pheno | docs | refactor | abc1234 | #1 | done | koosha | toaster | sample |
"""

NOT_A_WORKLOG = """# Worklog

Active work tracking for parpour project.

---

## Current Sprint

| Item | Status |
|------|--------|
| Documentation updates | In Progress |
"""


def _run_validator(path: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke validate_worklog.py as a subprocess (matches pre-commit use)."""
    return subprocess.run(
        ["python3", str(_VALIDATOR), str(path), *args],
        capture_output=True, text=True, timeout=30,
    )


class TestValidate(unittest.TestCase):
    def test_v21_canonical_passes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(V21_SAMPLE)
            path = Path(f.name)
        try:
            result = _run_validator(path)
            self.assertEqual(result.returncode, 0,
                             f"stderr={result.stderr}\nstdout={result.stdout}")
        finally:
            path.unlink()

    def test_v20_legacy_warns_by_default(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(V20_SAMPLE)
            path = Path(f.name)
        try:
            result = _run_validator(path)
            # Legacy v2.0 of an untracked file → FAIL (new file)
            # But the test path isn't in a git repo, so _is_new_file returns
            # False (conservative), so it's WARN with exit 0.
            self.assertIn("legacy format 'v20'", result.stderr)
        finally:
            path.unlink()

    def test_v1p_legacy_warns(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(V1P_SAMPLE)
            path = Path(f.name)
        try:
            result = _run_validator(path)
            self.assertIn("legacy format 'v1p'", result.stderr)
        finally:
            path.unlink()

    def test_v1_legacy_warns(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(V1_SAMPLE)
            path = Path(f.name)
        try:
            result = _run_validator(path)
            self.assertIn("legacy format 'v1'", result.stderr)
        finally:
            path.unlink()

    def test_v21_invalid_device_fails(self):
        """A canonical v2.1 file with a non-canonical device value must FAIL."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(V21_INVALID_DEVICE)
            path = Path(f.name)
        try:
            result = _run_validator(path)
            self.assertEqual(result.returncode, 1,
                             f"expected FAIL on invalid device; stderr={result.stderr}")
            self.assertIn("toaster", result.stderr)
            self.assertIn("CANONICAL_DEVICES", result.stderr)
        finally:
            path.unlink()

    def test_not_a_worklog_passes(self):
        """Files that aren't worklogs (no recognized header) should pass."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(NOT_A_WORKLOG)
            path = Path(f.name)
        try:
            result = _run_validator(path)
            self.assertEqual(result.returncode, 0)
        finally:
            path.unlink()

    def test_strict_flag_fails_on_legacy(self):
        """The --strict flag should fail even on legacy formats in temp files."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(V20_SAMPLE)
            path = Path(f.name)
        try:
            result = _run_validator(path, "--strict")
            self.assertEqual(result.returncode, 1)
            self.assertIn("legacy format 'v20'", result.stderr)
        finally:
            path.unlink()

    def test_warn_only_never_fails(self):
        """The --warn-only flag should never fail, even on invalid v2.1."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(V21_INVALID_DEVICE)
            path = Path(f.name)
        try:
            result = _run_validator(path, "--warn-only")
            self.assertEqual(result.returncode, 0,
                             f"expected WARN-only exit 0; stderr={result.stderr}")
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
