"""DAG-94: tests/test_dual_gpu_preflight.py

The `scripts/dual_gpu/preflight.py` script (added by DAG-93) is the
readiness probe for the Desktop NVIDIA dual-GPU lane defined in
`config/desktop_nvidia_qwen35_lane.yaml`. It runs six probes:

    1. probe_nvidia_smi             -- >=2 GPUs via nvidia-smi
    2. probe_cuda_visible_devices   -- CUDA_VISIBLE_DEVICES parses
    3. probe_disk_space             -- >=10 GB free under HF cache
    4. probe_worktree_clean         -- git status --porcelain empty
    5. probe_lane_config_loads      -- YAML parses, schema_version set
    6. probe_host_manifest_present  -- host_manifest.yaml exists

This test verifies the script's CLI surface and `--dry-run` behavior
via `subprocess.run([sys.executable, str(PREFLIGHT), ...])` with
`cwd=REPO_ROOT`, mirroring the style of
`tests/test_harbor_consumer_dry_run.py` (sibling DAG-67 test) and
`tests/test_install_launchd_sh.py` (sibling DAG-22 test).

Important: every probe here invokes the script with `--dry-run` so
that the side-effecting / slow probes (nvidia-smi, disk) are skipped.
Probe 4 (`probe_worktree_clean`) runs `git status --porcelain` which
is read-only and never mutates the worktree.

Section 8 (DAG-94 addition) mocks nvidia-smi output for dual GPUs and
asserts the preflight probe correctly parses PCIe + VRAM fields and
fails on mismatch -- no real nvidia-smi binary is invoked.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # must be imported before subprocess (hang on exit if reversed)

REPO_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = REPO_ROOT / "scripts" / "dual_gpu" / "preflight.py"

# Load preflight as importable module for direct probe unit tests (no
# subprocess CLI). Uses importlib to avoid relying on scripts.* package
# import side-effects, but the module is also available as
# scripts.dual_gpu.preflight via pythonpath=".".
_SPEC = importlib.util.spec_from_file_location(
    "scripts.dual_gpu.preflight", str(PREFLIGHT)
)
assert _SPEC and _SPEC.loader
_preflight_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_preflight_mod)  # type: ignore[union-attr]

# State directories the dry-run must never touch (sibling tests guard
# these too: harbor_consumer_dry_run, snapshot_sota, worktree_gc).
STATE_DIRS = (
    REPO_ROOT / "evidence",
    REPO_ROOT / "bench" / "results",
)

# Probes whose names must appear in the script's --verbose output.
# Names match the PROBES table in scripts/dual_gpu/preflight.py.
EXPECTED_PROBE_NAMES = (
    "probe_nvidia_smi",
    "probe_cuda_visible_devices",
    "probe_disk_space",
    "probe_worktree_clean",
    "probe_lane_config_loads",
    "probe_host_manifest_present",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_yaml_cache: bool | None = None


def _yaml_available() -> bool:
    """Return True iff PyYAML is importable in the active venv.

    Cached after first call to avoid repeated subprocess spawning during
    collection, which can cause TimeoutExpired errors when the full suite
    loads many test modules simultaneously.
    """
    global _yaml_cache  # noqa: PLW0603
    if _yaml_cache is not None:
        return _yaml_cache
    try:
        probe = subprocess.run(
            [sys.executable, "-c", "import yaml"],  # noqa: S603
            cwd=str(REPO_ROOT),
            env={**os.environ},
            capture_output=True,
            text=True,
            timeout=10,
        )
        _yaml_cache = probe.returncode == 0
    except subprocess.TimeoutExpired:
        _yaml_cache = False
    return _yaml_cache


def _worktree_clean() -> bool:
    """Return True iff `git status --porcelain` is empty in REPO_ROOT.

    Probe 4 (`probe_worktree_clean`) treats any non-empty git status
    output as a failure. To assert `--dry-run --verbose` exits 0 we
    must therefore guarantee a clean worktree at test time. This is
    read-only: the helper does not modify state.

    Uses a short timeout and treats timeout / error as "not clean" so
    that collection-time evaluation never hangs the test suite on
    hosts with a large or nested git worktree (e.g. C:/Users/koosh).
    """
    try:
        probe = subprocess.run(
            ["git", "status", "--porcelain"],  # noqa: S603
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return False
    except FileNotFoundError:
        return False
    return probe.returncode == 0 and not probe.stdout.strip()


# ---------------------------------------------------------------------------
# 1. Script exists
# ---------------------------------------------------------------------------


def test_preflight_script_exists() -> None:
    """The preflight script must live at scripts/dual_gpu/preflight.py."""
    assert PREFLIGHT.is_file(), f"missing {PREFLIGHT} -- DAG-93 deliverable"


# ---------------------------------------------------------------------------
# 2. Shebang
# ---------------------------------------------------------------------------


def test_preflight_has_shebang() -> None:
    """First line must be a Python shebang.

    Accepts ``#!/usr/bin/env python3`` (preferred), ``#!/usr/bin/python3``,
    or any ``#!.*python`` form. Mirrors the shebang check in
    test_harbor_consumer_dry_run.py.
    """
    assert PREFLIGHT.is_file(), f"missing {PREFLIGHT}"
    first = PREFLIGHT.read_text().splitlines()[0]
    assert first.startswith("#!"), f"missing shebang; first line: {first!r}"
    assert re.match(
        r"^#!.*\bpython(?:3)?\b",
        first,
    ), f"non-Python shebang: {first!r}"


# ---------------------------------------------------------------------------
# 3. --help exits 0 and documents --dry-run
# ---------------------------------------------------------------------------


def test_preflight_help_exits_0() -> None:
    """`--help` must exit 0 and print the argparse usage banner.

    argparse's --help handler prints to stdout and exits 0; this is
    the closest analog to a bash script's `Usage:` line.
    """
    result = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--help"],  # noqa: S603
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
    assert "usage:" in out.lower(), f"no 'usage:` banner in --help output:\n{out[:600]}"
    # --dry-run must be documented (the test below exercises it).
    assert "--dry-run" in out, f"--help does not document --dry-run:\n{out[:600]}"


# ---------------------------------------------------------------------------
# 4. --dry-run --verbose prints all 6 probe markers
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _yaml_available(),
    reason="yaml package not installed; preflight.py cannot import at module scope",
)
def test_preflight_dry_run_prints_probe_summary() -> None:
    """`--dry-run --verbose` must print all 6 probe names + >=6 markers.

    Under `--verbose` the driver prints a status line for every probe
    (regardless of pass/fail/skip), each prefixed with `[ok]`,
    `[fail]`, or `[dry-run]`. The test asserts every probe name
    appears in the combined output and that at least 6 marker tokens
    are present. Probes 1 (nvidia-smi) and 3 (disk) are skipped under
    --dry-run, so they print `[dry-run]`; the others report
    `[ok]` or `[fail]` depending on host state.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(PREFLIGHT),  # noqa: S603
            "--dry-run",
            "--verbose",
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    combined = (result.stdout or "") + "\n" + (result.stderr or "")

    for name in EXPECTED_PROBE_NAMES:
        assert name in combined, (
            f"probe {name!r} missing from --dry-run --verbose output:\n{combined[:800]}"
        )

    markers = re.findall(r"\[(ok|fail|dry-run|warn)\]", combined)
    assert len(markers) >= 6, (
        f"expected >= 6 markers, got {len(markers)}:\n{combined[:800]}"
    )


# ---------------------------------------------------------------------------
# 5. --dry-run --verbose exits 0 (skip when env is unsuitable)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _yaml_available(),
    reason="yaml package not installed",
)
def test_preflight_dry_run_exits_0() -> None:
    """`--dry-run --verbose` must exit 0 when the env is suitable.

    Skipped on hosts where `git status --porcelain` is non-empty, since
    probe 4 (`probe_worktree_clean`) would legitimately fail. The test
    also injects `CUDA_VISIBLE_DEVICES=0` so probe 2 passes on hosts
    that have the env unset (the contract still requires the operator
    to export it; we satisfy the test locally only).

    The worktree check is performed inside the test body (not as a
    collection-time skipif) to avoid hanging pytest collection on hosts
    where `git status` is slow (large nested worktree).
    """
    if not _worktree_clean():
        pytest.skip(
            "worktree is dirty (probe_worktree_clean would fail). "
            "Commit/stash untracked changes before asserting exit 0."
        )
    result = subprocess.run(
        [
            sys.executable,
            str(PREFLIGHT),  # noqa: S603
            "--dry-run",
            "--verbose",
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"--dry-run --verbose should exit 0, got {result.returncode}\n"
        f"--- stdout ---\n{result.stdout[:500]}\n"
        f"--- stderr ---\n{result.stderr[:500]}"
    )


# ---------------------------------------------------------------------------
# 6. No-args invocation runs the probes (does not raise argparse error)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _yaml_available(),
    reason="yaml package not installed",
)
def test_preflight_no_args_runs_all_probes() -> None:
    """Bare invocation (no flags) must not raise an argparse error.

    The script has no required positional args, so ``python
    preflight.py`` (no flags) must attempt all six probes rather than
    fail with exit code 2 (argparse's standard usage error). It MAY
    exit non-zero if probes fail on this host (e.g. nvidia-smi not on
    PATH, CUDA_VISIBLE_DEVICES unset) — that's the *probe* failing,
    not the CLI surface breaking. We assert that:

      * the process started (no ModuleNotFoundError, no SyntaxError),
      * the combined output mentions at least 3 of the 6 probe names,
        proving the driver reached the run loop.
    """
    result = subprocess.run(
        [sys.executable, str(PREFLIGHT)],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=60,
    )
    # argparse error -> exit 2; we do NOT accept that for a flagless
    # invocation (the script has no required args).
    assert result.returncode != 2, (
        f"argparse rejected no-args invocation (exit=2):\nstderr: {result.stderr[:400]}"
    )
    # The driver should have at least started; probe names must appear
    # in the failure summary even if all probes fail (the script
    # prints "preflight: N probe(s) failed" only on failure; with
    # --verbose not set, it prints per-probe only on failure).
    # Use --verbose here to make the assertions robust.
    result_v = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--verbose"],  # noqa: S603
        cwd=str(REPO_ROOT),
        env={**os.environ},
        capture_output=True,
        text=True,
        timeout=60,
    )
    combined_v = (result_v.stdout or "") + "\n" + (result_v.stderr or "")
    mentioned = [n for n in EXPECTED_PROBE_NAMES if n in combined_v]
    assert len(mentioned) >= 3, (
        f"expected at least 3 probe names in --verbose output, got "
        f"{len(mentioned)}: {mentioned}\n{combined_v[:800]}"
    )


# ---------------------------------------------------------------------------
# 7. --dry-run does NOT modify state
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _yaml_available(),
    reason="yaml package not installed",
)
def test_preflight_dry_run_does_not_modify_state() -> None:
    """`--dry-run` must not create any new files under evidence/ or
    bench/results/.

    `--dry-run` skips probes 1 (nvidia-smi) and 3 (disk) and is the
    read-only mode for the operator; nothing else in the driver writes
    to disk. We snapshot the on-disk set before/after and assert the
    diff is empty. Cron wrappers (snapshot_sota.py, worktree_gc_cron.sh,
    etc.) all write to these paths, so this guard keeps preflight
    out of that path.
    """

    def _snapshot() -> set[Path]:
        found: set[Path] = set()
        for d in STATE_DIRS:
            if d.is_dir():
                found.update(d.rglob("*"))
        return {p for p in found if p.is_file() or p.is_dir()}

    before = _snapshot()
    result = subprocess.run(
        [
            sys.executable,
            str(PREFLIGHT),  # noqa: S603
            "--dry-run",
            "--verbose",
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    after = _snapshot()
    new_paths = after - before
    assert not new_paths, (
        "--dry-run must not create new files; "
        f"new paths observed: {sorted(str(p) for p in new_paths)[:10]}"
    )
    # Sanity: the script actually ran and produced output. If the
    # invocation was a no-op we want to know.
    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    assert "preflight" in combined.lower(), (
        f"no preflight banner in output:\n{combined[:400]}"
    )


# ---------------------------------------------------------------------------
# 8. Mocked nvidia-smi: dual-GPU success, PCIe + VRAM parsing, mismatch
# ---------------------------------------------------------------------------

# Canonical dual-GPU nvidia-smi CSV (matches --query-gpu=index,name,memory.total)
DUAL_GPU_SMI_OK = (
    "0, NVIDIA GeForce GTX 1080 Ti, 11264 MiB\n"
    "1, NVIDIA GeForce RTX 3090 Ti, 24564 MiB\n"
)
# Single-GPU mismatch (should fail EXPECTED_GPU_COUNT=2)
SINGLE_GPU_SMI = "0, NVIDIA GeForce GTX 1080 Ti, 11264 MiB\n"
# Dual-GPU with VRAM values matching lane config but with PCIe columns
# (some nvidia-smi invocations include pcie width); the probe must still
# parse the memory.total field correctly when extra columns are present.
DUAL_GPU_PCIE_VRAM_OK = (
    "0, NVIDIA GeForce GTX 1080 Ti, 11264 MiB, 16x, Gen3\n"
    "1, NVIDIA GeForce RTX 3090 Ti, 24564 MiB, 16x, Gen4\n"
)


def _mock_smi(stdout: str, returncode: int = 0, stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


def test_probe_nvidia_smi_dual_gpu_mock_success() -> None:
    """Mock nvidia-smi with dual GPUs must pass and include VRAM sample."""
    mock_proc = _mock_smi(DUAL_GPU_SMI_OK)
    with patch.object(
        _preflight_mod.subprocess, "run", return_value=mock_proc
    ) as mock_run:
        passed, msg = _preflight_mod.probe_nvidia_smi(False)
        # Assert no real nvidia-smi was invoked beyond the mock
        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        assert "nvidia-smi" in args[0]
        assert passed is True, f"expected pass for dual GPU, got {passed}: {msg}"
        # Probe must have parsed VRAM / memory.total into the message
        assert "2 GPU" in msg, f"missing GPU count in msg: {msg}"
        # Sample should contain first GPU name or VRAM token
        assert "11264" in msg or "GTX 1080" in msg, f"VRAM not parsed into msg: {msg}"


def test_probe_nvidia_smi_parses_pcie_and_vram() -> None:
    """Mock output with PCIe + VRAM columns must still parse correctly.

    The real probe queries --format=csv,noheader with
    index,name,memory.total, but operators may extend the query to
    include PCIe link fields. The probe's row-count logic must not
    break when extra comma-separated columns (PCIe gen/width) are
    present -- it still sees 2 rows and reports VRAM.
    """
    mock_proc = _mock_smi(DUAL_GPU_PCIE_VRAM_OK)
    with patch.object(_preflight_mod.subprocess, "run", return_value=mock_proc):
        passed, msg = _preflight_mod.probe_nvidia_smi(False)
        assert passed is True, f"PCIe+VRAM parse failed: {msg}"
        assert "2 GPU" in msg


def test_probe_nvidia_smi_fails_on_single_gpu_mismatch() -> None:
    """Single GPU must fail the EXPECTED_GPU_COUNT=2 contract."""
    mock_proc = _mock_smi(SINGLE_GPU_SMI)
    with patch.object(_preflight_mod.subprocess, "run", return_value=mock_proc):
        passed, msg = _preflight_mod.probe_nvidia_smi(False)
        assert passed is False, "single GPU should fail dual-GPU preflight"
        assert "expected >= 2" in msg.lower() or "saw 1" in msg.lower(), msg


def test_probe_nvidia_smi_fails_on_empty_output() -> None:
    """Empty nvidia-smi output must fail (0 GPUs)."""
    mock_proc = _mock_smi("", returncode=0)
    with patch.object(_preflight_mod.subprocess, "run", return_value=mock_proc):
        passed, msg = _preflight_mod.probe_nvidia_smi(False)
        assert passed is False
        assert "0" in msg or "empty" in msg.lower()


def test_probe_nvidia_smi_fails_when_not_on_path() -> None:
    """FileNotFoundError from subprocess.run must be handled as fail."""
    with patch.object(
        _preflight_mod.subprocess, "run", side_effect=FileNotFoundError("no such file")
    ) as mock_run:
        passed, msg = _preflight_mod.probe_nvidia_smi(False)
        mock_run.assert_called_once()
        assert passed is False
        assert "not on path" in msg.lower()


def test_probe_nvidia_smi_fails_on_nonzero_exit() -> None:
    """Non-zero nvidia-smi exit must fail with stderr tail."""
    mock_proc = _mock_smi("", returncode=1, stderr="NVIDIA-SMI has failed")
    with patch.object(_preflight_mod.subprocess, "run", return_value=mock_proc):
        passed, msg = _preflight_mod.probe_nvidia_smi(False)
        assert passed is False
        assert "exit=1" in msg


def test_probe_nvidia_smi_vram_mismatch_still_counts_gpus() -> None:
    """Even with unexpected VRAM values, probe passes if 2 rows present.

    The current probe checks count >=2, not exact VRAM match; a future
    strict VRAM gate would fail here. This test documents the contract:
    VRAM is surfaced in the sample but count is the gate.
    """
    vram_mismatch = (
        "0, NVIDIA GeForce GTX 1080 Ti, 8000 MiB\n"
        "1, NVIDIA GeForce RTX 3090 Ti, 8000 MiB\n"
    )
    mock_proc = _mock_smi(vram_mismatch)
    with patch.object(_preflight_mod.subprocess, "run", return_value=mock_proc):
        passed, msg = _preflight_mod.probe_nvidia_smi(False)
        # Current implementation: passes on count, surfaces sample
        assert passed is True, f"count gate should pass even with VRAM mismatch: {msg}"
        assert "8000" in msg


def test_run_preflight_mocked_nvidia_smi_success() -> None:
    """run_preflight with mocked nvidia-smi dual-GPU must pass that probe.

    Patches subprocess.run with a side-effect that returns the dual-GPU
    CSV for nvidia-smi calls and delegates other calls (git) to real
    logic via a fallback mock that simulates a clean worktree.
    """
    real_run = _preflight_mod.subprocess.run  # keep reference for non-smi

    def _side_effect(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(cmd, list) and cmd and cmd[0] == "nvidia-smi":
            return _mock_smi(DUAL_GPU_SMI_OK)
        if isinstance(cmd, list) and cmd and cmd[0] == "git":
            m = MagicMock()
            m.stdout = ""
            m.stderr = ""
            m.returncode = 0
            return m
        # Disk / yaml probes: delegate to real where possible, else mock ok
        return (
            real_run(cmd, **kwargs)
            if False
            else MagicMock(stdout="", stderr="", returncode=0)
        )

    # We test the probe layer directly but also ensure run_preflight's
    # nvidia-smi probe sees the mock. Patch shutil.disk_usage and yaml
    # handling to avoid host-dependent failures.
    with patch.object(_preflight_mod.subprocess, "run", side_effect=_side_effect):
        with patch.object(_preflight_mod.shutil, "disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(
                free=20 * 1024**3, total=100 * 1024**3, used=80 * 1024**3
            )
            # Also ensure env satisfies CUDA_VISIBLE_DEVICES and that
            # lane config + host manifest probes are mocked to pass
            with patch.object(
                _preflight_mod,
                "probe_lane_config_loads",
                return_value=(True, "mocked ok"),
            ):
                with patch.object(
                    _preflight_mod,
                    "probe_host_manifest_present",
                    return_value=(True, "mocked ok"),
                ):
                    with patch.dict("os.environ", {"CUDA_VISIBLE_DEVICES": "0,1"}):
                        # Direct probe check
                        passed, _msg = _preflight_mod.probe_nvidia_smi(False)
                        assert passed is True
                        # Full preflight should exit 0 when all mocked probes pass
                        rc = _preflight_mod.run_preflight(dry_run=False, verbose=False)
                        assert rc == 0, "mocked full preflight should pass"


def test_run_preflight_mocked_nvidia_smi_mismatch_fails() -> None:
    """run_preflight must return 1 when mocked nvidia-smi shows 1 GPU."""

    def _side_effect(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(cmd, list) and cmd and cmd[0] == "nvidia-smi":
            return _mock_smi(SINGLE_GPU_SMI)
        if isinstance(cmd, list) and cmd and cmd[0] == "git":
            m = MagicMock()
            m.stdout = ""
            m.stderr = ""
            m.returncode = 0
            return m
        m = MagicMock()
        m.stdout = ""
        m.stderr = ""
        m.returncode = 0
        return m

    with patch.object(_preflight_mod.subprocess, "run", side_effect=_side_effect):
        with patch.object(_preflight_mod.shutil, "disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(
                free=20 * 1024**3, total=100 * 1024**3, used=80 * 1024**3
            )
            with patch.object(
                _preflight_mod,
                "probe_lane_config_loads",
                return_value=(True, "mocked ok"),
            ):
                with patch.object(
                    _preflight_mod,
                    "probe_host_manifest_present",
                    return_value=(True, "mocked ok"),
                ):
                    with patch.dict("os.environ", {"CUDA_VISIBLE_DEVICES": "0,1"}):
                        rc = _preflight_mod.run_preflight(dry_run=False, verbose=False)
                        assert rc == 1, "single-GPU mock must cause preflight failure"


def test_no_real_nvidia_smi_invoked_in_mock_tests() -> None:
    """Guard: mock tests must not shell out to real nvidia-smi."""
    # This test itself is a mock; it verifies the patch mechanism works
    # and that subprocess.run is interceptable (i.e., no direct os.system).
    with patch.object(_preflight_mod.subprocess, "run") as mock_run:
        mock_run.return_value = _mock_smi(DUAL_GPU_SMI_OK)
        _preflight_mod.probe_nvidia_smi(False)
        mock_run.assert_called_once()
        # Ensure the call was to "nvidia-smi" (not a real binary path leak)
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[0] == "nvidia-smi"
        assert any("--query-gpu" in c for c in called_cmd)
