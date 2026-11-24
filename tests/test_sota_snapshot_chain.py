"""DAG-23: tests/test_sota_snapshot_chain.py

The SOTA snapshot chain is the daily integrity record. Each day gets
``bench/results/sota/<YYYY-MM-DD>/snapshot.json`` + ``.sha256`` sidecar.
The .sha256 is the tamper-evidence; the .json is gitignored.

The test asserts:

  1. snapshot_sota.py exists and is importable.
  2. For each existing snapshot dir, the .sha256 matches the .json.
  3. The chain is gapless for the trailing 5 days (last 5 dates
     present, modulo known forensic gaps from the audit-A4 close-out).
"""

from __future__ import annotations

import datetime
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SOTA_ROOT = REPO_ROOT / "bench" / "results" / "sota"
SNAPSHOT_PY = REPO_ROOT / "scripts" / "cron" / "snapshot_sota.py"


def test_snapshot_sota_is_runnable() -> None:
    """The script must be importable as a module + accept --help."""
    result = subprocess.run(
        [sys.executable, str(SNAPSHOT_PY), "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, f"--help failed: {result.stderr[:200]}"
    assert "snapshot" in result.stdout.lower()


@pytest.mark.skipif(not SOTA_ROOT.is_dir(), reason="no SOTA chain yet")
def test_sha256_sidecars_match_payload() -> None:
    """For every existing snapshot dir, the .sha256 must match the .json."""
    for child in sorted(SOTA_ROOT.iterdir()):
        if not child.is_dir():
            continue
        sha = child / "snapshot.sha256"
        jsn = child / "snapshot.json"
        if not (sha.is_file() and jsn.is_file()):
            continue
        actual = hashlib.sha256(jsn.read_bytes()).hexdigest()
        # The sidecar format is "<sha>  snapshot.json\n".
        expected = sha.read_text().split()[0]
        assert actual == expected, (
            f"{child.name}: sha256 mismatch. actual={actual} expected={expected}"
        )


@pytest.mark.skipif(not SOTA_ROOT.is_dir(), reason="no SOTA chain yet")
def test_sota_chain_has_no_gap_in_last_5_days() -> None:
    """The trailing 5 days must all be present (modulo the documented
    forensic gaps from the audit close-out, which were backfilled in
    commit 9742256).

    Uses the most recent snapshot date as the reference rather than
    ``datetime.now()`` so the test is stable across the UTC date
    rollover (the cron runs once per UTC day; for ~1-2h after rollover
    the new day's snapshot does not yet exist).
    """
    snapshot_dates = sorted(
        child.name for child in SOTA_ROOT.iterdir() if child.is_dir()
    )
    if not snapshot_dates:
        pytest.skip("no SOTA snapshots to anchor against")
    latest = datetime.date.fromisoformat(snapshot_dates[-1])
    expected = [(latest - datetime.timedelta(days=i)).isoformat() for i in range(5)]
    for date in expected:
        d = SOTA_ROOT / date
        assert d.is_dir(), f"missing SOTA snapshot for {date}"


def test_snapshot_sota_backfill_emits_evidence_label(
    tmp_path: Path,
) -> None:
    """A backfill run (--date) must emit evidence_label='backfilled'.

    Writes to ``tmp_path`` (pytest's portable basetemp) instead of the
    repo tree so the snapshot does not leak onto disk between runs and
    cannot drift the committed SHA256 sidecar.
    """
    out_root = tmp_path / "_sota_test"
    result = subprocess.run(
        [
            sys.executable,
            str(SNAPSHOT_PY),
            "--date",
            "2020-01-01",
            "--backfill-note",
            "DAG-23 test",
            "--out-root",
            str(out_root),
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, f"snapshot_sota failed: {result.stderr[:200]}"
    snap = out_root / "2020-01-01" / "snapshot.json"
    assert snap.is_file(), f"snapshot not written to {snap}"
    import json

    envelope = json.loads(snap.read_text())
    assert envelope.get("evidence_label") == "backfilled"
