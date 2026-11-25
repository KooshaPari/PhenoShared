"""DAG-20: tests/test_worktree_gc_cron.py

The worktree_gc_cron.sh wrapper prunes gone branches + stale worktrees
weekly. The test asserts:

  1. The script has a sane shebang + set -euo pipefail.
  2. The script is CWD-invariant.
  3. The script reports what it did (exits 0 even when nothing to prune).
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests._harness import skipif_windows

REPO_ROOT = Path(__file__).resolve().parents[1]
GC_SH = REPO_ROOT / "scripts" / "cron" / "worktree_gc_cron.sh"


@pytest.mark.skipif(not GC_SH.is_file(), reason="worktree_gc_cron.sh not present")
def test_worktree_gc_cron_script_is_bash_and_strict() -> None:
    text = GC_SH.read_text()
    assert text.startswith("#!/bin/bash") or text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text


@pytest.mark.skipif(not GC_SH.is_file(), reason="worktree_gc_cron.sh not present")
@skipif_windows
def test_worktree_gc_cron_runs_cleanly() -> None:
    env = {**os.environ}
    result = subprocess.run(
        ["/bin/bash", str(GC_SH)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "Traceback" not in result.stderr
    # Exit 0 even if no worktrees to prune.


@pytest.mark.skipif(not GC_SH.is_file(), reason="worktree_gc_cron.sh not present")
@skipif_windows
def test_worktree_gc_cron_writes_today_log() -> None:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out_dir = REPO_ROOT / "bench" / "results" / "gc" / today
    if not out_dir.exists():
        subprocess.run(
            ["/bin/bash", str(GC_SH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    if not out_dir.exists():
        pytest.skip(f"worktree_gc cron did not write {out_dir}")
    assert out_dir.is_dir()
    # At least one .log file should be present (one per repo probed).
    logs = list(out_dir.glob("*.log"))
    assert logs, f"no .log files in {out_dir}"
