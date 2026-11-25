"""Unit tests for the Qwen MLX-versus-Pheno comparison matrix."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE.parent / "python" / "qwen_comparison_matrix.py"
SPEC = importlib.util.spec_from_file_location("qwen_comparison_matrix", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)


def test_matrix_covers_required_batch_and_context_variants() -> None:
    variants = matrix.build_variants(batches=[1, 8], contexts=[1, 128])

    assert {(row["batch"], row["context_tokens"]) for row in variants} == {
        (1, 1),
        (1, 128),
        (8, 1),
        (8, 128),
    }
    assert all(row["comparison_status"] == "not_comparable" for row in variants)
    assert all(
        row["pheno_metal"]["execution_status"] == "unsupported" for row in variants
    )


def test_validation_evidence_preserves_component_scope(tmp_path: Path) -> None:
    report_path = tmp_path / "validate.json"
    report_path.write_text(
        json.dumps(
            {
                "metal_available": True,
                "results": [
                    {
                        "name": "RMSNorm",
                        "passed": True,
                        "metal_available": True,
                        "mlx_ms": 0.5,
                        "metal_ms": 1.0,
                    },
                    {
                        "name": "end_to_end",
                        "passed": True,
                        "metal_available": False,
                        "mlx_ms": -1.0,
                        "metal_ms": None,
                    },
                ],
            }
        )
    )

    evidence = matrix.load_pheno_validation_evidence(report_path)

    assert evidence["report_status"] == "loaded"
    assert evidence["metal_available"] is True
    assert evidence["component_results"][0]["name"] == "RMSNorm"
    assert evidence["component_results"][1]["name"] == "end_to_end"
    assert evidence["comparison_caveat"] == matrix.PHENO_COMPARISON_CAVEAT


def test_markdown_reports_non_comparability_without_speedup_claims() -> None:
    report = matrix.make_report(
        variants=matrix.build_variants(batches=[1], contexts=[1]),
        mlx_rows=[
            {
                "batch": 1,
                "context_tokens": 1,
                "execution_status": "skipped",
                "reason": "checkpoint unavailable",
            }
        ],
        evidence={
            "report_status": "not_found",
            "report_path": "/tmp/validate.json",  # nosec B108 — fixed test scratch path (test-only artifact)
            "metal_available": None,
            "component_results": [],
            "comparison_caveat": matrix.PHENO_COMPARISON_CAVEAT,
        },
        methodology={
            "workload": "full forward",
            "stock_mlx_source": "mlx_lm",
            "batches": [1],
            "contexts": [1],
            "iters": 3,
            "warmup": 1,
            "weights": "real HF checkpoint required",
            "timing_boundary": "evaluated forwards",
        },
    )

    markdown = matrix.render_markdown(report)

    assert (
        "| 1 | 1 | skipped; checkpoint unavailable | unsupported | not comparable |"
        in markdown
    )
    assert "speedup" not in markdown.lower()
    assert matrix.PHENO_COMPARISON_CAVEAT in markdown
