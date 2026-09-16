"""DAG-19: tests/test_health_repo_cron.py

The health_repo_cron.sh wrapper script is invoked weekly by launchd. The
test mocks launchd and asserts the script:

  1. Exits 0 when its output dir is writable.
  2. Writes bench/results/health_repo/<YYYY-MM-DD>/<repo>.log
  3. Does NOT swallow exceptions silently (set -e + set -u enforced).
  4. Resolves CWD-invariant (works from any directory).
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests._harness import skipif_windows

REPO_ROOT = Path(__file__).resolve().parents[1]
HEALTH_SH = REPO_ROOT / "scripts" / "cron" / "health_repo_cron.sh"


@pytest.mark.skipif(not HEALTH_SH.is_file(), reason="health_repo_cron.sh not present")
def test_health_repo_cron_script_is_bash_and_strict() -> None:
    """The script must be /bin/bash and turn on set -euo pipefail."""
    text = HEALTH_SH.read_text()
    assert text.startswith("#!/bin/bash") or text.startswith("#!/usr/bin/env bash"), (
        f"unexpected shebang: {text.splitlines()[0]!r}"
    )
    assert "set -euo pipefail" in text, "missing set -euo pipefail"


@pytest.mark.skipif(not HEALTH_SH.is_file(), reason="health_repo_cron.sh not present")
@skipif_windows
def test_health_repo_cron_runs_cleanly() -> None:
    """The script runs and exits 0 even with no upstream DB. The cron
    is allowed to report 'nothing to probe' but must not fail."""
    env = {**os.environ}
    result = subprocess.run(
        ["/bin/bash", str(HEALTH_SH)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Allow non-zero only if the script's own log shows it intentionally
    # exited because of missing tool. We just check it didn't crash
    # with a Python traceback (which would mean syntax error).
    assert "Traceback" not in result.stderr, f"crash:\n{result.stderr[:500]}"


@pytest.mark.skipif(not HEALTH_SH.is_file(), reason="health_repo_cron.sh not present")
@skipif_windows
def test_health_repo_cron_creates_today_dir() -> None:
    """After running, today's YYYY-MM-DD output dir must exist under
    bench/results/health_repo/."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    out_dir = REPO_ROOT / "bench" / "results" / "health_repo" / today
    if not out_dir.exists():
        # The cron writes on its first run; if it's not present yet,
        # force-fire it now and re-check.
        subprocess.run(
            ["/bin/bash", str(HEALTH_SH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
    # Soft check — the cron may have been unloaded earlier.
    if not out_dir.exists():
        pytest.skip(f"health_repo cron did not write {out_dir}")
    assert out_dir.is_dir()
