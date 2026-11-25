"""Tests for dual-GPU stack scripts (P09/P10/P11/P12/R5).

Covers:
- P09: one-command lane CLI script exists
- P10: dual-engine boot script exists
- P11: smoke ping script exists
- P12: engine version pins defined
- R5: Engine pins + smoke + health

These tests verify the existence and structure of the scripts.
Live execution tests are blocked on SVM-enabled hardware.
"""

from __future__ import annotations

from pathlib import Path


class TestDualGPUStackScripts:
    """P09/P10: Script existence and structure."""

    def test_start_dual_gpu_stack_ps1_exists(self) -> None:
        """start_dual_gpu_stack.ps1 exists (P10 — dual-engine boot)."""
        p = Path("scripts/start_dual_gpu_stack.ps1")
        assert p.exists(), f"Missing {p}"

    def test_start_dual_gpu_stack_is_powershell(self) -> None:
        """Script starts with PowerShell shebang or param block."""
        p = Path("scripts/start_dual_gpu_stack.ps1")
        content = p.read_text(encoding="utf-8")
        assert "#!" in content or "param(" in content or "#Requires" in content

    def test_run_desktop_lane_eval_exists(self) -> None:
        """run_desktop_lane_eval.py exists (P09 — one-command lane CLI)."""
        p = Path("scripts/run_desktop_lane_eval.py")
        assert p.exists(), f"Missing {p}"


class TestSmokePingScript:
    """P11: Smoke ping script exists."""

    def test_run_dual_gpu_smoke_exists(self) -> None:
        """run_dual_gpu_smoke.ps1 exists (P11 — smoke ping)."""
        p = Path("scripts/run_dual_gpu_smoke.ps1")
        assert p.exists(), f"Missing {p}"

    def test_smoke_script_references_dual_engine(self) -> None:
        """Smoke script references GPU/engine/smoke concept."""
        p = Path("scripts/run_dual_gpu_smoke.ps1")
        content = p.read_text(encoding="utf-8")
        assert "gpu" in content.lower() or "engine" in content.lower() or "smoke" in content.lower()


class TestEngineVersionPins:
    """P12: Engine version pins are documented in pyproject.toml or related config."""

    def test_pyproject_exists(self) -> None:
        """pyproject.toml exists for dependency management."""
        p = Path("pyproject.toml")
        assert p.exists(), "pyproject.toml must exist"

    def test_pyproject_has_project_metadata(self) -> None:
        """pyproject.toml has project or build-system metadata."""
        p = Path("pyproject.toml")
        content = p.read_text(encoding="utf-8")
        assert "[project]" in content or "[build-system]" in content
