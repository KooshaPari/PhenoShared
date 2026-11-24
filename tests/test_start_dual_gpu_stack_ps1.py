"""DAG-89: tests/test_start_dual_gpu_stack_ps1.py

The start_dual_gpu_stack.ps1 script is the operator-side bootstrap for
the WSL/Fedora 44 dual-GPU lane (`docs/guides/WSL_FEDORA_44_DUAL_GPU.md`).
It launches a helper (llama-server on the 1080 Ti for port 8082) and a
primary runtime (vLLM or SGLang on the 3090 Ti for port 8000), plus the
pheno-serve-dev proxy on port 21080, with `CUDA_VISIBLE_DEVICES=1` so
the two GPUs are isolated.

The test asserts:

  1. The script file exists at scripts/start_dual_gpu_stack.ps1.
  2. The script has a PowerShell shebang-equivalent marker (a `param(...)`
     block, a `#Requires` directive, `$PSVersionTable`, or `$PSScriptRoot`).
  3. The script mentions both vllm and sglang (case-insensitive).
  4. The script mentions CUDA (case-insensitive) — required for GPU isolation.
  5. The script launches at least 2 separate engine processes via
     `Start-Process`, `Invoke-Expression`, or `& <engine>` call sites.
  6. The file is UTF-8 readable and has at least 10 lines.
  7. The script declares parameters via a `param(...)` block (optional
     guard — most production scripts do; skip gracefully if absent).

The script is NOT executed. PowerShell syntax validation is performed
via `pwsh -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw ...), [ref]$null)"`
which is parse-only; no engines are started.

On hosts without `pwsh` on PATH, the syntax check is skipped rather than
failing (the Apple Silicon dev workstation may not have PowerShell 7).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
START_PS1 = REPO_ROOT / "scripts" / "start_dual_gpu_stack.ps1"


def test_start_dual_gpu_stack_ps1_exists() -> None:
    """The dual-GPU stack launcher must exist at the canonical path."""
    assert START_PS1.is_file(), f"missing {START_PS1}"


def test_start_dual_gpu_stack_ps1_has_powershell_marker() -> None:
    """The script must carry a PowerShell shebang-equivalent marker.

    Accepted markers (any one of):
      - `param(...)` parameter block
      - `#Requires` directive
      - `$PSVersionTable` reference
      - `$PSScriptRoot` / `$PSCommandPath` reference
    """
    text = START_PS1.read_text()
    markers = (
        "param(",
        "#Requires",
        "$PSVersionTable",
        "$PSScriptRoot",
        "$PSCommandPath",
    )
    matched = [m for m in markers if m in text]
    assert matched, (
        "no PowerShell marker found (looked for: " + ", ".join(markers) + ")"
    )


def test_start_dual_gpu_stack_ps1_mentions_vllm_and_sglang() -> None:
    """The script must mention both vllm and sglang (case-insensitive)."""
    text = START_PS1.read_text()
    lowered = text.lower()
    assert "vllm" in lowered, "script does not mention 'vllm'"
    assert "sglang" in lowered, "script does not mention 'sglang'"


def test_start_dual_gpu_stack_ps1_mentions_cuda() -> None:
    """The script must mention CUDA (case-insensitive) for GPU isolation."""
    text = START_PS1.read_text()
    assert "cuda" in text.lower(), (
        "script does not mention 'cuda' (required for CUDA_VISIBLE_DEVICES "
        "or -dev CUDA<N> isolation)"
    )


def test_start_dual_gpu_stack_ps1_has_two_engine_starts() -> None:
    """The script must launch at least 2 separate engine processes.

    We count `Start-Process` invocations, `Invoke-Expression` calls, and
    `& <engine>` call-site operators. The helper (llama-server) + primary
    (vLLM or SGLang) + pheno-serve-dev proxy yields >= 3 Start-Process
    sites in the canonical implementation.
    """
    text = START_PS1.read_text()
    start_process = re.findall(r"\bStart-Process\b", text)
    invoke_expression = re.findall(r"\bInvoke-Expression\b", text)
    # `& <engine>` call operator: `& (Join-Path ...)` for the smoke
    # sub-script invocation is a common pattern.
    ampersand_call = re.findall(r"^\s*&\s+\S", text, flags=re.MULTILINE)
    total = len(start_process) + len(invoke_expression) + len(ampersand_call)
    assert total >= 2, (
        "expected >= 2 engine-start call sites; "
        f"Start-Process={len(start_process)}, "
        f"Invoke-Expression={len(invoke_expression)}, "
        f"&-call={len(ampersand_call)}"
    )


def test_start_dual_gpu_stack_ps1_is_readable_as_text() -> None:
    """The file must be UTF-8 readable and have at least 10 lines."""
    text = START_PS1.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) >= 10, f"script too short: {len(lines)} lines (need >= 10)"


@pytest.mark.skipif(
    shutil.which("pwsh") is None,
    reason="pwsh not on PATH; skipping PowerShell syntax check",
)
def test_start_dual_gpu_stack_ps1_passes_powershell_parser() -> None:
    """PowerShell's parser must accept the script.

    Uses `pwsh -NoProfile -Command` with `[System.Management.Automation.PSParser]::Tokenize`
    in parse-only mode (no execution). This mirrors the behavior of
    `bash -n` for sh scripts.
    """
    # Read the content and stringify it as a PowerShell here-string literal.
    content = START_PS1.read_text(encoding="utf-8")
    # Escape single quotes for the PowerShell single-quoted literal: '' is the
    # standard PS escape inside a single-quoted string.
    escaped = content.replace("'", "''")
    ps_command = (
        "$tokens = $null; "
        "$errors = $null; "
        f"$text = '{escaped}'; "
        "$null = [System.Management.Automation.PSParser]::Tokenize($text, [ref]$errors); "
        "if ($errors -and $errors.Count -gt 0) { "
        "  Write-Host 'PARSE_ERRORS:'; "
        "  $errors | ForEach-Object { Write-Host $_ }; "
        "  exit 1 "
        "} else { exit 0 }"
    )
    proc = subprocess.run(
        ["pwsh", "-NoProfile", "-Command", ps_command],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        "PowerShell syntax check failed:\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )


def test_start_dual_gpu_stack_ps1_has_param_block() -> None:
    """If the script declares parameters, they must be inside a `param(...)` block.

    The canonical implementation declares switches/strings/ints via
    `param(...)`; if a future revision drops the block, the test fails
    loudly so the contract is preserved.
    """
    text = START_PS1.read_text()
    assert re.search(r"(?m)^\s*param\s*\(", text), (
        "no `param(...)` block found at line start; the script should declare "
        "its switches (-SmokeOnly, -HelperOnly, etc.) via a parameter block"
    )


def test_start_dual_gpu_stack_ps1_isolates_cuda_visible_devices() -> None:
    """The script must set CUDA_VISIBLE_DEVICES for GPU isolation.

    The canonical implementation sets `CUDA_VISIBLE_DEVICES=1` for the
    llama-server helper and the vLLM/SGLang primary, so the 1080 Ti
    and 3090 Ti don't contend on the same physical GPU.
    """
    text = START_PS1.read_text()
    assert "CUDA_VISIBLE_DEVICES" in text, (
        "script does not set CUDA_VISIBLE_DEVICES; the dual-GPU lane "
        "requires explicit isolation between the 1080 Ti and 3090 Ti"
    )
