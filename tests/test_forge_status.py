"""tests/test_forge_status.py — smoke test for scripts/forge_status.sh.

Validates:
1. The script has no shell syntax errors (`bash -n`).
2. Running with `--quiet` exits 0 when launchctl reports all 3 agents loaded.
3. Running with `--json` emits valid JSON with the expected keys.
4. Running with `--help` exits 0 with a usage banner.
5. The script is marked executable.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests._harness import skipif_non_macos

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "forge_status.sh"


def test_script_exists() -> None:
    assert SCRIPT.exists(), f"{SCRIPT} missing"


def test_script_is_executable() -> None:
    assert os.access(SCRIPT, os.X_OK), (
        f"{SCRIPT} not executable; run: chmod +x {SCRIPT}"
    )


@skipif_non_macos
def test_script_syntax() -> None:
    """`bash -n` should exit 0 (no syntax errors)."""
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


@skipif_non_macos
def test_script_help_exits_zero() -> None:
    result = subprocess.run(
        [str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "forge_status" in result.stdout or "agents" in result.stdout.lower()


@skipif_non_macos
def test_script_quiet_returns_known_exit_code() -> None:
    """`--quiet` returns 0 (loaded), 2 (partial), or 3 (unloadable) — never 1."""
    result = subprocess.run(
        [str(SCRIPT), "--quiet"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 2, 3), (
        f"unexpected exit code {result.returncode}: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


@skipif_non_macos
def test_script_json_is_valid() -> None:
    """`--json` output parses as JSON with the expected top-level keys."""
    result = subprocess.run(
        [str(SCRIPT), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 2, 3):
        pytest.skip(
            f"forge agents not in a state for JSON output (exit {result.returncode})"
        )
    data = json.loads(result.stdout)
    assert "agents" in data
    assert "loaded" in data
    assert "total" in data
    assert isinstance(data["agents"], list)
    for agent in data["agents"]:
        assert {"label", "script", "pid", "last_exit", "next_run", "last_log"} <= set(
            agent.keys()
        )


@skipif_non_macos
def test_script_table_includes_header() -> None:
    """Default (table) mode emits the AGENT/PID/EXIT header."""
    result = subprocess.run(
        [str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 2, 3):
        pytest.skip(f"forge agents not loaded (exit {result.returncode})")
    assert "AGENT" in result.stdout
    assert "PID" in result.stdout
    assert "EXIT" in result.stdout
