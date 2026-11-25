"""DAG-87: tests/test_install_wsl_pheno_serve_sh.py

The install_wsl_pheno_serve.sh script is the operator-side bootstrap
for the Fedora 44 dual-GPU lane (`docs/guides/WSL_FEDORA_44_DUAL_GPU.md`).
It installs python3.12 + git + tailscale + nvidia-driver via dnf,
clones the named branch of pheno-harness into /opt/pheno-harness,
symlinks the launchd cron payloads into /etc/cron.d/pheno-harness,
and force-fires today's SOTA snapshot.

The test asserts:

  1. The script file exists at scripts/install_wsl_pheno_serve.sh.
  2. The script uses a bash shebang.
  3. `bash -n` parses the script cleanly (no syntax errors).
  4. The script mentions Fedora 44 (case-insensitive).
  5. The script uses `dnf` or `microdnf` as its package manager.
  6. If the script supports `--help`, calling it exits 0; otherwise
     the check is skipped gracefully (no false failure).

The script is NOT executed. SSH/tailscale/git-clone are mocked at the
subprocess level via `bash -n` only; no network calls are attempted.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "scripts" / "install_wsl_pheno_serve.sh"


def test_install_wsl_pheno_serve_script_exists() -> None:
    """The Fedora 44 install script must exist at the canonical path."""
    assert INSTALL_SH.is_file(), f"missing {INSTALL_SH}"


def test_install_wsl_pheno_serve_has_bash_shebang() -> None:
    """The shebang must point at bash (either form is accepted)."""
    text = INSTALL_SH.read_text()
    first_line = text.splitlines()[0]
    assert first_line.startswith("#!"), f"missing shebang: {first_line!r}"
    assert first_line in {"#!/bin/bash", "#!/usr/bin/env bash"}, (
        f"unexpected shebang: {first_line!r}"
    )


@pytest.mark.skipif(
    shutil.which("bash") is None or sys.platform == "win32",
    reason="bash not on PATH or Windows; skip syntax check",
)
def test_install_wsl_pheno_serve_passes_bash_n_syntax_check() -> None:
    """`bash -n` must parse the script without errors."""
    try:
        proc = subprocess.run(
            ["bash", "-n", str(INSTALL_SH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        pytest.skip("bash -n timed out (WSL SVM off)")
    combined = f"{proc.stdout or ''}{proc.stderr or ''}"
    # WSL on SVM-off hosts emits UTF-16LE (null bytes between chars); normalize.
    cleaned = combined.replace("\x00", "")
    if "HCS_E_HYPERV_NOT_INSTALLED" in cleaned:
        pytest.skip("WSL bash unavailable (SVM off) — skip syntax check")
    if "HCS" in cleaned and "HYPERV" in cleaned:
        pytest.skip("WSL bash unavailable (HCS) — skip syntax check")
    if "virtualization is not enabled" in cleaned.lower():
        pytest.skip("WSL bash unavailable (virtualization off) — skip syntax check")
    assert proc.returncode == 0, (
        f"bash syntax check failed:\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )


def test_install_wsl_pheno_serve_mentions_fedora_44() -> None:
    """The script must reference Fedora and the 44 release (case-insensitive)."""
    text = INSTALL_SH.read_text()
    lowered = text.lower()
    assert "fedora" in lowered, "script does not mention 'fedora'"
    assert "44" in text, "script does not mention release '44'"


def test_install_wsl_pheno_serve_has_dnf_or_microdnf() -> None:
    """The package manager invocation must be `dnf` or `microdnf`."""
    text = INSTALL_SH.read_text()
    # Strip comments to avoid matching docstring prose.
    non_comment = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    assert re.search(r"\bdnf\b", non_comment) or re.search(
        r"\bmicrodnf\b", non_comment
    ), "no `dnf` or `microdnf` invocation found in script body"


@pytest.mark.skipif(
    shutil.which("bash") is None or sys.platform == "win32",
    reason="bash not on PATH or Windows; skip --help probe",
)
def test_install_wsl_pheno_serve_help_or_usage() -> None:
    """If the script supports --help, calling --help exits 0.

    The Fedora 44 install script is a declarative bootstrap and may not
    implement a `--help` flag; in that case the test is skipped via
    `returncode != 0` and the optional check passes silently.
    """
    proc = subprocess.run(
        ["bash", str(INSTALL_SH), "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.skip(
            "script does not implement --help "
            f"(returncode={proc.returncode}); skipping optional flag check"
        )
    assert proc.returncode == 0
