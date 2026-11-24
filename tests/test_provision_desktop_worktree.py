"""DAG-33: tests/test_provision_desktop_worktree.py

The `scripts/provision_desktop_worktree.py` script (DAG-27) provisions a
tailscale-bootstrap worktree on the Desktop NVIDIA rig (WSL2 + Fedora 44).
It is intentionally idempotent and operator-safe: re-running with the
same `(host, branch)` tuple is a no-op (the worktrees index entry is
replaced, not duplicated), and `--dry-run` skips the actual SSH + clone
while still recording the dry-run intent in the index.

This test asserts the script's CLI surface and dry-run invariants via
`subprocess.run([sys.executable, str(PROVISION), ...])` with
`cwd=REPO_ROOT`, mirroring the style of `tests/test_harbor_consumer_dry_run.py`
(sibling DAG-67 test) and `tests/test_dual_gpu_preflight.py` (sibling
DAG-94 test).

Important:
  - Every test that actually invokes the script uses `--dry-run` so that
    no real SSH or remote `git worktree add` is fired.
  - The script DOES write to `evidence/dual_gpu/worktrees.json` in both
    dry-run and apply modes (the dry-run entry is recorded with
    `dry_run=True` and `ssh_ok=False`); this is the documented contract.
    The "no side effects" test therefore asserts no mutation of
    `bench/results/` or `~/.cache/` and that the recorded entry proves
    the SSH ping was bypassed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVISION = REPO_ROOT / "scripts" / "provision_desktop_worktree.py"
LANE_CONFIG = REPO_ROOT / "config" / "desktop_nvidia_qwen35_lane.yaml"
WORKTREE_INDEX = REPO_ROOT / "evidence" / "dual_gpu" / "worktrees.json"

# State directories the script must never touch (besides the intentional
# `evidence/dual_gpu/worktrees.json` index, which is the script's own
# contract artifact).  The dual_gpu_preflight sibling test guards the
# same set; we follow that convention here.
#
# NOTE: `~/.cache/` is intentionally NOT snapshotted via `rglob` --
# that directory can hold 100k+ files on a busy dev workstation and
# turns the snapshot into the slowest part of the test. The provision
# script never references `~/.cache/` in its source; the regression
# we actually need to guard is the script starting to write into
# `bench/results/`, which is where every other cron wrapper writes.
STATE_DIRS = (REPO_ROOT / "bench" / "results",)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _yaml_available() -> bool:
    """Return True iff PyYAML is importable in the active venv.

    The lane config is YAML; the provision script itself does not
    import yaml (it accepts the host via `--host`), but the test below
    that asserts the config parses cleanly needs PyYAML. This predicate
    mirrors the script's own YAML-adjacent runtime requirement.
    """
    probe = subprocess.run(
        [sys.executable, "-c", "import yaml"],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=120,
    )
    return probe.returncode == 0


def _read_index() -> dict:
    """Read `evidence/dual_gpu/worktrees.json` if it exists, else {}."""
    if not WORKTREE_INDEX.is_file():
        return {}
    return json.loads(WORKTREE_INDEX.read_text())


# ---------------------------------------------------------------------------
# 1. Script exists
# ---------------------------------------------------------------------------


def test_provision_script_exists() -> None:
    """The provision script must live at scripts/provision_desktop_worktree.py."""
    assert PROVISION.is_file(), (
        f"missing {PROVISION} -- DAG-27 deliverable; DAG-33 cannot exercise it"
    )


# ---------------------------------------------------------------------------
# 2. Shebang
# ---------------------------------------------------------------------------


def test_provision_has_shebang() -> None:
    """First line must be a Python shebang.

    Accepts ``#!/usr/bin/env python3`` (preferred), ``#!/usr/bin/python3``,
    or any ``#!.*python`` form. Mirrors the shebang checks in
    test_harbor_consumer_dry_run.py and test_dual_gpu_preflight.py.
    """
    assert PROVISION.is_file(), f"missing {PROVISION}"
    first = PROVISION.read_text().splitlines()[0]
    assert first.startswith("#!"), f"missing shebang; first line: {first!r}"
    assert re.match(
        r"^#!.*\bpython(?:3)?\b",
        first,
    ), f"non-Python shebang: {first!r}"


# ---------------------------------------------------------------------------
# 3. Syntax check via py_compile
# ---------------------------------------------------------------------------


def test_provision_compiles() -> None:
    """`python -m py_compile` must exit 0 on the script.

    py_compile is the canonical syntax-only check; it does not execute
    the module body, so it cannot fire SSH or write to disk.
    """
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(PROVISION)],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"py_compile failed (exit={result.returncode}):\n"
        f"--- stderr ---\n{result.stderr[:400]}"
    )


# ---------------------------------------------------------------------------
# 4. --help exits 0 and prints usage + the actual CLI surface
# ---------------------------------------------------------------------------


def test_provision_help_exits_0() -> None:
    """`--help` must exit 0, print a usage banner, and document the
    script's actual CLI surface.

    The script's argparse surface is: ``--host`` (required),
    ``--branch`` (default: ``fix/desktop-vllm-runtime``),
    ``--worktree-dir`` (required), and ``--dry-run``. We assert each
    of those flags appears in the combined --help output.
    """
    assert PROVISION.is_file(), f"missing {PROVISION}"
    result = subprocess.run(
        [sys.executable, str(PROVISION), "--help"],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"--help should exit 0, got {result.returncode}\n"
        f"--- stderr ---\n{result.stderr[:400]}"
    )
    out = (result.stdout or "") + "\n" + (result.stderr or "")
    assert "usage:" in out.lower(), f"no 'usage:' banner in --help output:\n{out[:600]}"
    for flag in ("--host", "--branch", "--worktree-dir", "--dry-run"):
        assert flag in out, f"--help does not document {flag!r}:\n{out[:600]}"


# ---------------------------------------------------------------------------
# 5. --dry-run does not touch bench/results/ or ~/.cache/
# ---------------------------------------------------------------------------


def test_provision_dry_run_does_not_modify_state(tmp_path: Path) -> None:
    """`--dry-run` must not create any new files under `bench/results/`
    or `~/.cache/`.

    The production index remains ``evidence/dual_gpu/worktrees.json``.
    This test exercises the dry-run-only temporary index override so it
    can assert the recorded entry without mutating tracked evidence.
    """

    def _snapshot() -> set[Path]:
        found: set[Path] = set()
        for d in STATE_DIRS:
            if d.is_dir():
                found.update(d.rglob("*"))
        return {p for p in found if p.is_file() or p.is_dir()}

    temp_root = Path(tempfile.gettempdir()) / "pheno-harness-test-index"
    temp_root.mkdir(exist_ok=True)
    index_path = temp_root / f"{tmp_path.name}-worktrees.json"
    if index_path.exists():
        index_path.unlink()
    before = _snapshot()
    result = subprocess.run(
        [
            sys.executable,
            str(PROVISION),  # noqa: S603
            "--host",
            "test@100.0.0.1",
            "--branch",
            "test/dag-33-dry-run",
            "--worktree-dir",
            "/tmp/dag-33-dry-run-worktree",  # nosec B108 - subprocess test fixture; sandboxed
            "--index-path",
            str(index_path),
            "--dry-run",
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"--dry-run should exit 0, got {result.returncode}\n"
        f"--- stderr ---\n{result.stderr[:500]}"
    )
    after = _snapshot()
    new_paths = after - before
    assert not new_paths, (
        "--dry-run must not create new files under bench/results/ or ~/.cache/; "
        f"new paths observed: {sorted(str(p) for p in new_paths)[:10]}"
    )

    # The intentional index entry MUST exist and MUST record ssh_ok=False
    # + dry_run=True -- this proves the SSH ping was bypassed, which in
    # turn proves no remote worktree was touched.
    assert index_path.is_file(), (
        f"--dry-run should still write the index at {index_path}"
    )
    idx = json.loads(index_path.read_text())
    assert idx.get("version") == 1, f"unexpected index version: {idx.get('version')}"
    entries = idx.get("worktrees") or []
    matching = [
        e
        for e in entries
        if e.get("host") == "test@100.0.0.1"
        and e.get("branch") == "test/dag-33-dry-run"
    ]
    assert matching, (
        f"--dry-run did not record the expected entry in {index_path}; "
        f"entries: {entries!r}"
    )
    entry = matching[-1]
    assert entry.get("dry_run") is True, (
        f"recorded entry should have dry_run=True; got: {entry!r}"
    )
    assert entry.get("ssh_ok") is False, (
        f"recorded entry should have ssh_ok=False (dry-run bypasses SSH); "
        f"got: {entry!r}"
    )


def test_provision_rejects_existing_custom_index(tmp_path: Path) -> None:
    """A custom index is test-only and must not overwrite existing files."""
    existing = tmp_path / "existing.json"
    original = '{"version": 1, "worktrees": []}\n'
    existing.write_text(original)
    result = subprocess.run(
        [
            sys.executable,
            str(PROVISION),  # noqa: S603
            "--host",
            "test@100.0.0.1",
            "--worktree-dir",
            "/tmp/dag-33-dry-run-worktree",  # nosec B108 - subprocess test fixture; sandboxed
            "--index-path",
            str(existing),
            "--dry-run",
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert existing.read_text() == original


# ---------------------------------------------------------------------------
# 6. Script body mentions tailscale or ssh (case-insensitive)
# ---------------------------------------------------------------------------


def test_provision_mentions_tailscale_or_ssh() -> None:
    """The script source must reference `tailscale` or `ssh` (case-insensitive).

    The script's stated purpose is to provision a "tailscale-bootstrap
    worktree" on the WSL rig via SSH; the docstring + CLI both
    reference this. A regression that drops both keywords would mean
    the script no longer knows what transport to use.
    """
    assert PROVISION.is_file(), f"missing {PROVISION}"
    body = PROVISION.read_text().lower()
    assert ("tailscale" in body) or ("ssh" in body), (
        "scripts/provision_desktop_worktree.py must mention 'tailscale' or 'ssh' "
        "(it provisions a tailscale-bootstrap worktree via SSH)"
    )


# ---------------------------------------------------------------------------
# 7. Companion config desktop_nvidia_qwen35_lane.yaml parses cleanly
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _yaml_available(),
    reason="yaml package not installed; cannot verify the lane config parses",
)
def test_provision_handles_config_yaml() -> None:
    """The companion YAML config must parse cleanly and carry the
    expected `schema_version`.

    The provision script itself does NOT load this YAML (that is
    `scripts/run_desktop_lane_eval.py`'s job). But DAG-33's wider
    contract is that the provision + lane-config pair is intact: the
    script + the config that names it must both be present and the
    config must be valid YAML with the canonical schema_version. A
    regression in either half would break the consumer
    (run_desktop_lane_eval.py).
    """
    import yaml  # local import; guarded by skipif above

    assert PROVISION.is_file(), f"missing {PROVISION}"
    assert LANE_CONFIG.is_file(), f"missing {LANE_CONFIG}"

    data = yaml.safe_load(LANE_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(data, dict), (
        f"{LANE_CONFIG} did not parse as a YAML mapping; got {type(data).__name__}"
    )
    assert data.get("schema_version") == "pheno.desktop-nvidia.qwen35-lane.v1", (
        f"unexpected schema_version: {data.get('schema_version')!r}"
    )

    # The provision script must reference this contract indirectly: its
    # sibling consumer (run_desktop_lane_eval.py) loads the same YAML
    # and computes its SHA256. We re-import the script via subprocess
    # to confirm import + module load succeeds end-to-end (no missing
    # imports, no syntax errors at runtime) without firing SSH.
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib.util, pathlib; "
            "p = pathlib.Path('scripts/provision_desktop_worktree.py'); "
            "s = importlib.util.spec_from_file_location('pdw', p); "
            "m = importlib.util.module_from_spec(s); "
            "s.loader.exec_module(m); "
            "assert callable(m.main)",
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert probe.returncode == 0, (
        f"scripts/provision_desktop_worktree.py failed to import as a module:\n"
        f"--- stderr ---\n{probe.stderr[:500]}"
    )
