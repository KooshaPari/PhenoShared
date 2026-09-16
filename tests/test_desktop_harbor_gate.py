from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "harbor_cli" / "run_tbench_local.ps1"


def test_desktop_harbor_launcher_retains_future_authority_provenance_fields() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert '[string]$WindowId = ""' in source
    assert "-WindowId is required" in source
    assert "desktop_nvidia_qwen35_lane.yaml" in source
    assert "Get-FileHash" in source
    assert "PHENO_DESKTOP_WINDOW_ID" in source
    assert "PHENO_DESKTOP_AUTHORIZATION_PATH" in source
    assert "ConvertTo-Json" in source


def test_desktop_harbor_launcher_rejects_unbound_window_before_sidecar_or_execution() -> (
    None
):
    source = SCRIPT.read_text(encoding="utf-8")

    guard = 'throw "Desktop Harbor execution is blocked: no owner-issued execution authority is configured."'
    assert guard in source
    assert source.index(guard) < source.index("$authorizationDir =")
    assert source.index(guard) < source.index("Wait-LocalServer -TimeoutSec")
    assert source.index(guard) < source.index("Assert-Docker")


def test_desktop_harbor_launcher_verifies_canonical_model_before_docker() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "function Assert-CanonicalModel" in source
    assert "Qwen/Qwen3.5-0.8B" in source
    assert "local/qwen35-08b" in source
    assert "Assert-CanonicalModel" in source
    assert "Assert-Docker" in source
    assert "Assert-CanonicalModel\nAssert-Docker" in source


def test_desktop_harbor_launcher_normalizes_result_with_authorization_sidecar() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "normalize_harbor_trial.py" in source
    assert "--authorization-manifest" in source
    assert "pheno-normalized.json" in source
    assert "Resolve-LatestHarborJob" in source
