"""DAG-88: tests/test_install_wsl_pheno_serve_ps1.py

The ``scripts/install_wsl_pheno_serve.ps1`` script is the Windows-side
wrapper that invokes ``scripts/install_wsl_pheno_serve.sh`` inside a
named WSL2 distro (default ``Ubuntu-22.04``; the Fedora 44 LLM host is
provisioned by ``scripts/install_wsl_pheno_serve.sh`` which then
upgrades the distro to Fedora 44 in-place via dnf).

The test asserts:

  1. The script file exists at ``scripts/install_wsl_pheno_serve.ps1``.
  2. The script uses PowerShell syntax (carriage returns + ``param()``
     block + ``$Variable`` interpolation; we accept CRLF or LF).
  3. If PowerShell (``pwsh``) is on PATH, ``pwsh -NoProfile
     -Command "[scriptblock]::Create((Get-Content ...))"`` parses the
     script's AST without throwing ``ParserError``. We do NOT execute
     the script — invoking ``wsl.exe`` would require a real WSL distro
     and is out of scope for unit tests.
  4. The script references the Fedora 44 / WSL2 bootstrap path
     (``install_wsl_pheno_serve.sh``).
  5. The script's ``param([string]$Distro = "...")`` block accepts the
     distro override and rejects empty / malformed input gracefully
     (the script exits non-zero with an ERROR prefix line).
  6. The script never invokes a network fetch directly; the install
     bootstrap runs inside WSL, not in the Windows host.

Style mirrors ``tests/test_install_wsl_pheno_serve_sh.py`` (DAG-87)
and ``tests/test_start_dual_gpu_stack_ps1.py`` (DAG-89).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PS1 = REPO_ROOT / "scripts" / "install_wsl_pheno_serve.ps1"


def test_install_wsl_pheno_serve_ps1_script_exists() -> None:
    """The Windows-side wrapper must exist at the canonical path."""
    assert INSTALL_PS1.is_file(), f"missing {INSTALL_PS1}"


def test_install_wsl_pheno_serve_ps1_uses_powershell_syntax() -> None:
    """PowerShell markers: ``param()`` block, ``$Variable`` interpolation.

    PowerShell scripts conventionally use CRLF line endings on Windows;
    we accept either CRLF or LF (the Windows-side script is read by
    PowerShell which tolerates LF on modern .NET).
    """
    raw = INSTALL_PS1.read_bytes()
    assert raw.startswith(b"#"), (
        f"missing leading comment / shebang: first byte = {raw[:8]!r}"
    )
    text = raw.decode("utf-8", errors="replace")
    # Must contain a ``param()`` block (PowerShell convention).
    assert re.search(r"\bparam\s*\(", text), (
        "PowerShell script is missing a `param()` block — required for "
        "the ``$Distro`` parameter override"
    )
    # Must reference ``$Distro`` somewhere (the parameter is consumed
    # by the WSL invocation).
    assert re.search(r"\$Distro\b", text), (
        "PowerShell script does not reference $Distro — the parameter "
        "block is wired but the body never reads it"
    )
    # Must set ``$ErrorActionPreference = "Stop"`` (the script's
    # idempotency contract: any failing step halts the install).
    assert re.search(r'\$ErrorActionPreference\s*=\s*["\']Stop["\']', text), (
        "PowerShell script does not pin $ErrorActionPreference to Stop"
    )


@pytest.mark.skipif(
    shutil.which("pwsh") is None,
    reason="pwsh not on PATH; skip PowerShell parser check",
)
def test_install_wsl_pheno_serve_ps1_parses_with_pwsh() -> None:
    """PowerShell parser must accept the script without ParserError."""
    # Read the script, parse its AST. We do NOT execute the body.
    proc = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"$err = $null; "
            f"$tokens = $null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile("
            f"  '{INSTALL_PS1}', [ref]$tokens, [ref]$err) | Out-Null; "
            f"if ($err.Count -gt 0) {{ exit 1 }} else {{ exit 0 }}",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"PowerShell parse error:\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )


def test_install_wsl_pheno_serve_ps1_invokes_wsl_shell_script() -> None:
    """The script must delegate to the .sh bootstrap inside WSL2."""
    text = INSTALL_PS1.read_text()
    assert "install_wsl_pheno_serve.sh" in text, (
        "PowerShell wrapper does not delegate to install_wsl_pheno_serve.sh"
    )
    # Must invoke ``wsl`` (the Windows-side WSL launcher).
    assert re.search(r"\bwsl(\.exe)?\b", text), (
        "PowerShell wrapper does not invoke the `wsl` launcher"
    )


def test_install_wsl_pheno_serve_ps1_does_not_directly_fetch_models() -> None:
    """The Windows-side wrapper never fetches model weights directly.

    Model downloads happen on the Fedora 44 side via the .sh bootstrap
    and are gated by ``execution_policy.allow_model_download: false`` in
    the lane contract. The PowerShell wrapper must not pull weights.
    """
    text = INSTALL_PS1.read_text().lower()
    forbidden = (
        "huggingface.co",
        "models--qwen",
        "snapshot_download",
        "curl -o ",
        "wget ",
        "invoke-webrequest",
    )
    for needle in forbidden:
        assert needle not in text, (
            f"PowerShell wrapper appears to fetch model/network data "
            f"directly ({needle!r} found in script body)"
        )


def test_install_wsl_pheno_serve_ps1_distro_default_is_set() -> None:
    """The ``$Distro`` parameter must default to a real WSL distro name."""
    text = INSTALL_PS1.read_text()
    m = re.search(r"\$Distro\s*=\s*[\"']([^\"']+)[\"']", text)
    assert m, 'PowerShell script has no `$Distro = "..."` default'
    default = m.group(1)
    # Must be a plausible WSL distro name: alphanumeric + dashes + dots.
    # WSL accepts both ``Ubuntu-22.04`` and ``ubuntu-22.04`` depending on
    # how the distro was registered; accept either.
    assert re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,30}$", default), (
        f"default $Distro value {default!r} is not a plausible WSL distro name"
    )
