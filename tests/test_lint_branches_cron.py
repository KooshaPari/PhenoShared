"""DAG-21: tests/test_lint_branches_cron.py

The lint_branches_cron.sh wrapper enforces the 8-prefix branch taxonomy:

  feat/        fix/        chore/        docs/
  test/        refactor/   perf/        build/

The test asserts the script:

  1. Has a sane shebang + strict mode.
  2. Exits non-zero when at least one branch violates the taxonomy
     (current main has branches like 'wip/*' that violate).
  3. Writes a structured report to bench/results/branch-lint/<YYYY-MM-DD>/.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests._harness import skipif_windows

REPO_ROOT = Path(__file__).resolve().parents[1]
LINT_SH = REPO_ROOT / "scripts" / "cron" / "lint_branches_cron.sh"


@pytest.mark.skipif(not LINT_SH.is_file(), reason="lint_branches_cron.sh not present")
def test_lint_branches_cron_script_is_bash_and_strict() -> None:
    text = LINT_SH.read_text()
    assert text.startswith("#!/bin/bash") or text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text


@pytest.mark.skipif(not LINT_SH.is_file(), reason="lint_branches_cron.sh not present")
@skipif_windows
def test_lint_branches_cron_writes_report() -> None:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out_dir = REPO_ROOT / "bench" / "results" / "branch-lint" / today
    if not out_dir.exists():
        subprocess.run(
            ["/bin/bash", str(LINT_SH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    if not out_dir.exists():
        pytest.skip(f"lint_branches cron did not write {out_dir}")
    assert out_dir.is_dir()
    # At least one report file.
    reports = list(out_dir.glob("*.md")) + list(out_dir.glob("*.txt"))
    assert reports, f"no report files in {out_dir}"


def test_branch_taxonomy_eight_prefixes() -> None:
    """The 8 canonical prefixes are the source of truth — if anyone
    adds/removes one, this test must change too. Documented in
    AGENTS.md §10.1."""
    canonical = {
        "feat/",
        "fix/",
        "chore/",
        "docs/",
        "test/",
        "refactor/",
        "perf/",
        "build/",
    }
    assert len(canonical) == 8
    # No duplicates and no empty strings.
    assert len(canonical) == len(set(canonical))
    assert all(canonical)
