from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "start_dual_gpu_stack.ps1"


def test_desktop_launcher_defaults_match_live_runtime_contract() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert '[string]$PrimaryRuntime = "vllm"' in source
    assert "[int]$HelperPort = 8082" in source
    assert "[int]$PrimaryPort = 8000" in source
    assert '"export CUDA_VISIBLE_DEVICES=1"' in source
    assert "CUDA_VISIBLE_DEVICES=1" in source


def test_desktop_launcher_preflights_ports_without_killing_listeners() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "function Test-PortAvailable" in source
    assert "Test-PortAvailable $HelperPort" in source
    assert "Test-PortAvailable $PrimaryPort" in source
    assert "Test-PortAvailable $PhenoPort" in source
    assert "no process will be stopped" in source


def test_desktop_launcher_keeps_sglang_explicit_and_vllm_default() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert '[ValidateSet("vllm", "sglang")]' in source
    assert '$PrimaryRuntime -eq "vllm"' in source
    assert "sglang.launch_server" in source


def test_desktop_launcher_has_an_explicit_no_launch_preflight_record_mode() -> None:
    """Preflight mode must emit the wrapper-consumable dual-device record."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert "[switch]$PreflightOnly" in source
    assert "[string]$PreflightOutput" in source
    assert 'schema_version = "pheno.desktop-preflight.v1"' in source
    assert "no_launch = $true" in source
    assert "physical_index" in source
    assert "contract = [ordered]@{" in source
    assert "sha256 = Get-ContractSha256" in source
    assert 'role = "helper"' in source
    assert 'role = "primary"' in source
    assert "Write-PreflightRecord" in source


def test_desktop_launcher_preflight_exits_before_any_server_start() -> None:
    """The observation-only branch must never reach a launch call site."""
    source = SCRIPT.read_text(encoding="utf-8")
    marker = "if ($PreflightOnly) {"
    start = source.index(marker)
    end = source.index("exit 0", start)
    preflight_branch = source[start:end]

    assert "Start-Process" not in preflight_branch
    assert "Wait-EndpointModel" not in preflight_branch
    assert "no process was launched or stopped" in preflight_branch


def test_desktop_launcher_preflight_normalizes_contract_line_endings() -> None:
    """The Windows producer must agree with the cross-platform consumer hash."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert "ReadAllBytes" in source
    assert "$source[$index] -eq 13" in source
    assert "$normalized.WriteByte(10)" in source


@pytest.mark.skipif(
    shutil.which("pwsh") is None,
    reason="pwsh not on PATH; skip launcher authority behavior check",
)
def test_desktop_launcher_refuses_unbound_window_before_hardware_or_server_actions() -> (
    None
):
    """A window ID is provenance, not enough authority to launch services."""
    completed = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(SCRIPT), "-WindowId", "arbitrary"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    # pwsh wraps long throw messages at ~67 columns and inserts ANSI colour
    # codes around the error context display (with pipe separators between
    # the original line and the wrapped message). Strip both before
    # checking the substring of the original throw message.
    stderr_normalized = re.sub(r"\x1b\[[0-9;]*m", "", completed.stderr)
    stderr_normalized = re.sub(r"\s+", " ", stderr_normalized)
    assert re.search(r"no\s+\|?\s*owner-issued desktop", stderr_normalized)
    assert re.search(r"authorization contract exists", stderr_normalized)
