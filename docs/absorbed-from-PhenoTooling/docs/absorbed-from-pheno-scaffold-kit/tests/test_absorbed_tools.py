"""Tests for absorbed 2026-06-19: pheno-framework-lint, pheno-drift-detector, pheno-predict."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pheno_scaffold_kit as kit
from pheno_scaffold_kit import _drift_detector, _framework_lint, _predict


# ---------------------------------------------------------------------------
# __init__ / sub-library registration
# ---------------------------------------------------------------------------


def test_predict_reexported() -> None:
    assert "predict" in kit.SUB_LIBRARIES
    assert kit.SUB_LIBRARIES["predict"] is _predict


def test_framework_lint_reexported() -> None:
    assert "framework_lint" in kit.SUB_LIBRARIES
    assert kit.SUB_LIBRARIES["framework_lint"] is _framework_lint


def test_drift_detector_reexported() -> None:
    assert "drift_detector" in kit.SUB_LIBRARIES
    assert kit.SUB_LIBRARIES["drift_detector"] is _drift_detector


def test_seven_sub_libraries() -> None:
    """7 total: 4 legacy + 3 absorbed (L72/L73/L74)."""
    assert set(kit.SUB_LIBRARIES.keys()) == {
        "llms_txt",
        "prompt_test",
        "vibecoding_guard",
        "worklog_schema",
        "predict",
        "framework_lint",
        "drift_detector",
    }


# ---------------------------------------------------------------------------
# L73: framework-lint
# ---------------------------------------------------------------------------


def test_framework_lint_tier_inference() -> None:
    assert _framework_lint.infer_tier("pheno-config") == "pheno-*-lib"
    assert _framework_lint.infer_tier("phenotype-auth-ts") == "phenotype-*-sdk"
    assert _framework_lint.infer_tier("phenotype-bus-framework") == "phenotype-*-framework"
    # federated-service: matches `pheno-?PascalCase` (e.g. `phenoMCP` or `pheno-MCP`).
    assert _framework_lint.infer_tier("phenoMCP") == "federated-service"
    assert _framework_lint.infer_tier("pheno-MCP") == "federated-service"
    assert _framework_lint.infer_tier("not-a-substrate") == "unknown"


def test_framework_lint_pheno_lib_clean(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "lib.py").write_text("def hello():\n    return 1\n")
    violations, passed = _framework_lint.check_pheno_lib(tmp_path)
    assert "no-domain" in passed
    assert not any(v.rule == "pheno-lib/no-domain" for v in violations)


def test_framework_lint_pheno_lib_with_domain(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "foo.py").write_text("")
    violations, _ = _framework_lint.check_pheno_lib(tmp_path)
    assert any(v.rule == "pheno-lib/no-domain" for v in violations)


def test_framework_lint_help_via_cli() -> None:
    """E2E: ensure CLI registers the new subcommand groups."""
    result = subprocess.run(
        [sys.executable, "-m", "pheno_scaffold_kit.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "framework-lint" in result.stdout
    assert "drift-detector" in result.stdout
    assert "predict" in result.stdout


# ---------------------------------------------------------------------------
# L74: drift-detector
# ---------------------------------------------------------------------------


def test_drift_detector_smoke() -> None:
    """The detached CLI module imports + parses args without errors."""
    assert hasattr(_drift_detector, "cmd_scan")
    assert hasattr(_drift_detector, "cmd_validate")
    assert _drift_detector.DRIFT_THRESHOLD > 0


def test_drift_detector_buckets() -> None:
    assert _drift_detector.PAUSED_APPS == {"focalpoint", "QuadSGM", "WSM", "*fitness*"}
    assert "Dino" in _drift_detector.CONDITIONAL_APPS
    assert "AtomsBot" in _drift_detector.CAPSTONE_APPS


def test_drift_detector_no_candidates_on_empty(tmp_path: Path) -> None:
    """A root with no app-bucket repos produces 0 hits."""
    (tmp_path / "foo").mkdir()
    rc = _drift_detector.cmd_scan(
        _drift_detector.argparse.Namespace(root=str(tmp_path), format="json", out=None)
    )
    assert rc == 0


def test_drift_detector_help_via_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pheno_scaffold_kit.cli", "drift-detector", "scan", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--root" in result.stdout
    assert "--format" in result.stdout


# ---------------------------------------------------------------------------
# L72: predict
# ---------------------------------------------------------------------------


def test_predict_default_threshold() -> None:
    assert _predict.DEFAULT_THRESHOLD == 0.55
    assert _predict.SHINGLE_LEN == 5


def test_predict_tokenize_smoke() -> None:
    tokens = _predict.tokenize("def foo(x): return x + 1")
    # identifier + identifier + identifier + number = ["def", "foo", "x", "return", "x", "1"]
    assert "def" in tokens
    assert "foo" in tokens
    assert "1" in tokens


def test_predict_shingles_unique() -> None:
    tokens = ["a", "b", "c", "d", "e", "f", "g"]
    shingles = _predict.shingles(tokens, n=5)
    # 3 windows of 5 each: (a,b,c,d,e), (b,c,d,e,f), (c,d,e,f,g) — all distinct
    assert len(shingles) == 3


def test_predict_jaccard_self() -> None:
    tokens = ["a", "b", "c", "d", "e"]
    s = _predict.shingles(tokens, n=5)
    j, shared = _predict.jaccard(s, s)
    assert j == 1.0
    assert shared == 1


def test_predict_jaccard_disjoint() -> None:
    s1 = _predict.shingles(["a", "b", "c", "d", "e"], n=5)
    s2 = _predict.shingles(["v", "w", "x", "y", "z"], n=5)
    j, shared = _predict.jaccard(s1, s2)
    assert j == 0.0
    assert shared == 0


def test_predict_help_via_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pheno_scaffold_kit.cli", "predict", "scan", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--target" in result.stdout
    assert "--baseline" in result.stdout
    assert "--threshold" in result.stdout
