"""DAG-90: tests/test_run_dual_gpu_smoke_ps1.py

The ``scripts/run_dual_gpu_smoke.ps1`` script is the WSL/Fedora 44 dual-GPU
smoke lane: it invokes ``llama-bench.exe`` twice with isolated
``CUDA_VISIBLE_DEVICES`` so the 3090 Ti (primary) and the 1080 Ti
(helper) each run the same Qwen3.5-0.8B Q4_K_M prompt once. The
recorded ``tg64 tok/s`` values feed ``hardware_aware_placement.yaml``.

The test asserts:

  1. The script file exists at ``scripts/run_dual_gpu_smoke.ps1``.
  2. The script uses PowerShell syntax (``$ErrorActionPreference``,
     ``$Bench`` / ``$Model`` / ``$env:CUDA_VISIBLE_DEVICES``
     interpolation).
  3. If PowerShell (``pwsh``) is on PATH, ``pwsh`` parses the script's
     AST without throwing ``ParserError``. We do NOT execute the script
     because it shells out to ``llama-bench.exe`` (a Windows binary
     that requires a real CUDA driver + GGUF model on disk).
  4. The script runs the smoke lane exactly twice — once per GPU. A
     drift guard against accidentally running it once (only the
     primary) or three times (a typo'd extra call).
  5. The smoke lane isolates each GPU via ``CUDA_VISIBLE_DEVICES``
     (the load-bearing placement-policy invariant).
  6. The script surfaces the canonical ``tg64 tok/s`` collection
     marker that the placement-policy aggregator expects.
  7. The script never silently mutates ``hardware_aware_placement.yaml``
     directly — the operator copies the printed tok/s into the file
     by hand.

Style mirrors ``tests/test_install_wsl_pheno_serve_ps1.py`` (DAG-88)
and ``tests/test_start_dual_gpu_stack_ps1.py`` (DAG-89).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SMOKE_PS1 = REPO_ROOT / "scripts" / "run_dual_gpu_smoke.ps1"


def test_run_dual_gpu_smoke_ps1_script_exists() -> None:
    """The smoke lane script must exist at the canonical path."""
    assert RUN_SMOKE_PS1.is_file(), f"missing {RUN_SMOKE_PS1}"


def test_run_dual_gpu_smoke_ps1_uses_powershell_syntax() -> None:
    """PowerShell markers: ``$ErrorActionPreference = "Stop"``, env-var
    interpolation, ``Test-Path`` guard."""
    text = RUN_SMOKE_PS1.read_text()
    assert re.search(r'\$ErrorActionPreference\s*=\s*["\']Stop["\']', text), (
        "PowerShell script does not pin $ErrorActionPreference to Stop"
    )
    # The smoke lane must guard the binary + model paths with ``Test-Path``
    # before invoking ``llama-bench.exe`` (otherwise the script exits
    # with a cryptic FileNotFoundException).
    assert re.search(r"\bTest-Path\s+\$Bench\b", text), (
        "PowerShell script does not guard $Bench with Test-Path"
    )
    assert re.search(r"\bTest-Path\s+\$Model\b", text), (
        "PowerShell script does not guard $Model with Test-Path"
    )
    # Must reference ``CUDA_VISIBLE_DEVICES`` (the placement-policy
    # invariant the script enforces per GPU).
    assert "CUDA_VISIBLE_DEVICES" in text, (
        "PowerShell script does not reference CUDA_VISIBLE_DEVICES"
    )


def test_run_dual_gpu_smoke_ps1_requires_explicit_policy_and_window_before_bench() -> (
    None
):
    """Direct invocation must fail closed before the first llama-bench call."""
    text = RUN_SMOKE_PS1.read_text(encoding="utf-8")

    assert "[switch]$Execute" in text
    assert "[string]$WindowId" in text
    assert "config\\desktop_nvidia_qwen35_lane.yaml" in text
    assert "allow_model_inference" in text
    assert "allow_benchmark_execution" in text
    assert "MinimumFreeMiB" in text
    assert "nvidia-smi" in text
    assert "Assert-DesktopExecutionAuthority" in text
    assert "owner-issued desktop execution authorization" in text

    first_bench = text.index("& $Bench")
    for gate in ("$Execute", "$WindowId", "allow_model_inference", "nvidia-smi"):
        assert text.index(gate) < first_bench, f"{gate} must guard llama-bench"


@pytest.mark.skipif(
    shutil.which("pwsh") is None,
    reason="pwsh not on PATH; skip PowerShell authorization behavior check",
)
def test_run_dual_gpu_smoke_ps1_refuses_caller_window_without_owner_authorization() -> (
    None
):
    """A caller-provided window ID is provenance, never execution authority."""
    completed = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(RUN_SMOKE_PS1),
            "-Execute",
            "-WindowId",
            "arbitrary",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    # pwsh wraps the throw message at ~67 columns and embeds ANSI colour
    # codes; normalize before checking the substring.
    stderr_normalized = re.sub(r"\x1b\[[0-9;]*m", "", completed.stderr)
    stderr_normalized = re.sub(r"\s+", " ", stderr_normalized)
    assert completed.returncode != 0
    assert "no owner-issued desktop" in stderr_normalized
    assert "authorization contract exists" in stderr_normalized


@pytest.mark.skipif(
    shutil.which("pwsh") is None,
    reason="pwsh not on PATH; skip PowerShell parser check",
)
def test_run_dual_gpu_smoke_ps1_parses_with_pwsh() -> None:
    """PowerShell parser must accept the script without ParserError."""
    proc = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"$err = $null; "
            f"$tokens = $null; "
            f"[System.Management.Automation.Language.Parser]::ParseFile("
            f"  '{RUN_SMOKE_PS1}', [ref]$tokens, [ref]$err) | Out-Null; "
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


def test_run_dual_gpu_smoke_ps1_runs_smoke_exactly_twice() -> None:
    """The script must invoke the smoke lane exactly twice — once per GPU.

    The drift guard catches three classes of regression:
      * single-GPU smoke (only primary, helper untested) — the
        helper's tg64 tok/s would silently be missing.
      * triplicate smoke (a copy-paste typo) — would waste 8 minutes
        per run and inflate the SOTA snapshot's tok/s variance.

    We count *call sites* (statements that look like
    ``Invoke-GpuSmoke -Label ... -CudaVisible ...`` at the top level)
    rather than every textual occurrence — the function definition
    itself contains the identifier.
    """
    text = RUN_SMOKE_PS1.read_text()
    # Match top-level statements that invoke Invoke-GpuSmoke with a
    # -Label argument. The function definition uses ``function
    # Invoke-GpuSmoke`` (no -Label), so excluding ``-Label`` cleanly
    # separates the definition from call sites.
    call_sites = len(
        re.findall(
            r"^\s*Invoke-GpuSmoke\b[^\n]*-Label\b",
            text,
            flags=re.MULTILINE,
        )
    )
    assert call_sites == 2, (
        f"smoke lane must be invoked exactly twice (primary + helper); "
        f"found {call_sites} Invoke-GpuSmoke call sites"
    )


def test_run_dual_gpu_smoke_ps1_isolates_cuda_visible_devices_per_gpu() -> None:
    """Each smoke invocation must pass a different ``-CudaVisible`` value.

    The placement-policy invariant: 3090 Ti gets index 0, 1080 Ti gets
    index 1 (per the comment block at the top of the script). A
    regression that reuses the same CUDA index for both would let one
    GPU shadow the other and the recorded tg64 tok/s would be
    meaningless.

    The script binds ``$env:CUDA_VISIBLE_DEVICES = $CudaVisible``
    inside ``Invoke-GpuSmoke``; we assert the two ``-CudaVisible``
    arguments at the call sites are distinct and each ∈ {0, 1}.
    """
    text = RUN_SMOKE_PS1.read_text()
    # Find all ``-CudaVisible "<value>"`` arguments at Invoke-GpuSmoke call sites.
    cuda_args = re.findall(
        r'-CudaVisible\s+["\']([01])["\']',
        text,
    )
    assert sorted(cuda_args) == ["0", "1"], (
        f"CUDA_VISIBLE_DEVICES must isolate to {{0, 1}} via -CudaVisible "
        f"arguments; found {cuda_args!r}"
    )


def test_run_dual_gpu_smoke_ps1_surfaces_tg64_marker() -> None:
    """The script must print the ``tg64 tok/s`` collection marker.

    The placement-policy aggregator scrapes the operator's terminal
    for the ``tg64 tok/s`` line; the script's success-message comment
    is the canonical anchor.
    """
    text = RUN_SMOKE_PS1.read_text().lower()
    assert "tg64" in text, (
        "smoke lane does not reference tg64 tok/s — the placement-policy "
        "aggregator cannot parse the printed output"
    )
    assert "tok/s" in text, "smoke lane does not surface tok/s units"


def test_run_dual_gpu_smoke_ps1_does_not_silently_mutate_placement_yaml() -> None:
    """The script must not write to ``hardware_aware_placement.yaml``.

    The placement policy is operator-curated; the smoke lane prints the
    tok/s values for the operator to copy into the YAML by hand. A
    regression that auto-writes the YAML would silently drift the
    placement policy without operator review.

    References to ``hardware_aware_placement.yaml`` in comments are
    allowed (the script's tail comment names the file the operator is
    expected to edit). What is forbidden is any *write* to the file.
    """
    text = RUN_SMOKE_PS1.read_text().lower()
    # Strip comments — references in comments are documentation, not writes.
    code_only = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    # The forbidden write operations must not appear in non-comment code.
    forbidden = (
        "set-content",
        "add-content",
        "out-file",
        ">>",
    )
    for needle in forbidden:
        assert needle not in code_only, (
            f"smoke lane appears to write to disk ({needle!r}); "
            "smoke lane must be read-only with respect to repo state"
        )
    # Explicit guard: no assignment to hardware_aware_placement.yaml's
    # path. A regression that pipes tg64 tok/s into the YAML would
    # pass through this regex.
    assert not re.search(
        r"\b(?:set-content|add-content|out-file)\b[^\n]*hardware_aware_placement",
        code_only,
    ), (
        "smoke lane appears to write directly to "
        "hardware_aware_placement.yaml — the placement policy is "
        "operator-curated and must not be auto-mutated"
    )
