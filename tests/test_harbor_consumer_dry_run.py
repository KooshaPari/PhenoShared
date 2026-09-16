"""DAG-67: tests/test_harbor_consumer_dry_run.py

The `scripts/harbor_consumer_dry_run.py` script is the operator hook that
verifies the PyPI `harbor` package is importable (and, with
`--require-cli`, that the `harbor` console script is on PATH). It is
intentionally a dry-run boundary: it does not fork or vendor Harbor
framework code, and it never reaches out to a real Harbor API.

This test asserts the script:

  1. Exists at `scripts/harbor_consumer_dry_run.py` (note: Python, not
     bash — the script is `harbor_consumer_dry_run.py` per DAG-67, not a
     `*.sh` wrapper under `scripts/cron/`).
  2. Has a correct Python shebang (`#!/usr/bin/env python3`).
  3. Exits 0 when the `harbor` package is importable.
  4. Prints a recognizable `[harbor-dry-run]` marker on stdout.
  5. Does NOT create any new files under `evidence/` or `bench/results/`
     when run in default dry-run mode (i.e. it never writes to disk).
  6. Supports `--help` (argparse-style) and prints a usage banner.

Style mirrors `tests/test_install_launchd_sh.py`: subprocess via
`subprocess.run([...])` with `cwd=REPO_ROOT` and `text=True`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HARBOR_DRY_RUN = REPO_ROOT / "scripts" / "harbor_consumer_dry_run.py"

# Directories the script must never touch.  Sibling cron wrappers (e.g.
# health_repo_cron.sh, worktree_gc_cron.sh) all write per-day reports
# under these paths; the harbor_consumer dry-run explicitly does not.
STATE_DIRS = (
    REPO_ROOT / "evidence",
    REPO_ROOT / "bench" / "results",
)


# ---------------------------------------------------------------------------
# 1. Script exists
# ---------------------------------------------------------------------------


def test_harbor_consumer_dry_run_script_exists() -> None:
    """The dry-run script must live at scripts/harbor_consumer_dry_run.py."""
    assert HARBOR_DRY_RUN.is_file(), f"missing {HARBOR_DRY_RUN} — DAG-67 deliverable"


# ---------------------------------------------------------------------------
# 2. Shebang
# ---------------------------------------------------------------------------


def test_harbor_consumer_dry_run_has_shebang() -> None:
    """First line must be a Python shebang.

    Accepts:
      - `#!/usr/bin/env python3`     (preferred — portable)
      - `#!/usr/bin/env python`      (acceptable)
      - `#!/usr/bin/python3`         (acceptable)
      - `#!/bin/python3`             (acceptable)
    """
    assert HARBOR_DRY_RUN.is_file(), f"missing {HARBOR_DRY_RUN}"
    first = HARBOR_DRY_RUN.read_text().splitlines()[0]
    assert first.startswith("#!"), f"missing shebang; first line: {first!r}"
    assert re.match(
        r"^#!.*\bpython(?:3)?\b",
        first,
    ), f"non-Python shebang: {first!r}"


# ---------------------------------------------------------------------------
# 3. Dry-run mode exits 0 (skipped if harbor is not installed)
# ---------------------------------------------------------------------------


def _harbor_installed() -> bool:
    """Return True iff the `harbor` PyPI package is installed and importable.

    Mirrors the script's runtime check (``importlib.metadata.version('harbor')``
    followed by ``import harbor``) so the test skip predicate matches the
    script's runtime check. A bare ``import harbor`` is insufficient because
    the repo has a top-level ``harbor/`` directory (containing
    ``*.ps1`` scripts) that satisfies ``import`` but is not a real PyPI
    install — the script correctly rejects that case via
    ``PackageNotFoundError``. Conversely, a stale ``harbor-*.dist-info`` in
    site-packages without matching package code would let
    ``importlib.metadata.version`` succeed but ``import harbor`` fail.
    """
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (  # noqa: S603
                "import importlib.metadata as m\n"
                "m.version('harbor')\n"
                "import harbor  # noqa: F401\n"
            ),
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=30,
    )
    return probe.returncode == 0


@pytest.mark.skipif(
    not _harbor_installed(),
    reason="harbor package not installed; cannot exercise consumer dry-run",
)
def test_harbor_consumer_dry_run_in_dry_run_mode_exits_0() -> None:
    """`python scripts/harbor_consumer_dry_run.py` exits 0 when harbor imports."""
    result = subprocess.run(
        [sys.executable, str(HARBOR_DRY_RUN)],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"expected exit 0, got {result.returncode}\n"
        f"--- stdout ---\n{result.stdout[:500]}\n"
        f"--- stderr ---\n{result.stderr[:500]}"
    )


# ---------------------------------------------------------------------------
# 4. Prints a recognizable [harbor-dry-run] marker
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _harbor_installed(),
    reason="harbor package not installed; cannot exercise consumer dry-run",
)
def test_harbor_consumer_dry_run_prints_marker() -> None:
    """stdout must contain a `[harbor-dry-run]` marker line."""
    result = subprocess.run(
        [sys.executable, str(HARBOR_DRY_RUN)],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=60,
    )
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    assert "[harbor-dry-run]" in combined, (
        f"no [harbor-dry-run] marker in output:\n{combined[:600]}"
    )
    # Should also report a positive verdict (PASS / ok).
    assert ("PASS" in combined) or ("ok" in combined.lower()), (
        f"no positive verdict in output:\n{combined[:600]}"
    )


# ---------------------------------------------------------------------------
# 5. Does NOT modify state (no new files in evidence/ or bench/results/)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _harbor_installed(),
    reason="harbor package not installed; cannot exercise consumer dry-run",
)
def test_harbor_consumer_dry_run_does_not_modify_state() -> None:
    """The dry-run must not create any new files under evidence/ or
    bench/results/ (it is purely a probe — no side effects)."""

    # Snapshot the on-disk set BEFORE running.
    def _snapshot() -> set[Path]:
        found: set[Path] = set()
        for d in STATE_DIRS:
            if d.is_dir():
                found.update(d.rglob("*"))
        return {p for p in found if p.is_file() or p.is_dir()}

    before = _snapshot()
    result = subprocess.run(
        [sys.executable, str(HARBOR_DRY_RUN)],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"dry-run should exit 0; got {result.returncode}\nstderr: {result.stderr[:500]}"
    )
    after = _snapshot()
    new_paths = after - before
    assert not new_paths, (
        "harbor_consumer_dry_run.py must not create new files; "
        f"new paths observed: {sorted(str(p) for p in new_paths)[:10]}"
    )


# ---------------------------------------------------------------------------
# 6. --help / usage when called with no consumer args
# ---------------------------------------------------------------------------


def test_harbor_consumer_dry_run_help_or_usage_when_no_args() -> None:
    """`--help` (argparse) must exit 0 and print a usage banner.

    This is the closest analog to the no-args path on a bash script's
    `Usage: ...` line: argparse prints to stdout + exits 0 on `--help`.
    """
    assert HARBOR_DRY_RUN.is_file(), f"missing {HARBOR_DRY_RUN}"
    result = subprocess.run(
        [sys.executable, str(HARBOR_DRY_RUN), "--help"],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"--help should exit 0, got {result.returncode}\nstderr: {result.stderr[:400]}"
    )
    out = (result.stdout or "") + "\n" + (result.stderr or "")
    # argparse prints 'usage:' and a short program description
    assert "usage:" in out.lower(), f"no usage banner in --help output:\n{out[:400]}"
    assert "harbor" in out.lower(), (
        f"description should mention harbor; got:\n{out[:400]}"
    )
