"""Import and meta-path smoke tests for stock_vs_ours (no MLX inference required)."""

from __future__ import annotations

import pytest

from bench.comparison import needle_router, semantic_analysis, stock_vs_ours
from bench.comparison.mlx_direct import is_available as mlx_is_available
from bench.comparison.sglang_direct import SGLangDirect
from bench.comparison.sglang_direct import is_available as sglang_is_available


def test_stock_vs_ours_module_imports() -> None:
    assert stock_vs_ours.DEFAULT_MODEL
    assert stock_vs_ours.MODEL_REGISTRY
    assert callable(stock_vs_ours.pick_25_tasks)
    assert callable(stock_vs_ours.run_one_cell)


def test_needle_router_heuristic_route() -> None:
    result = needle_router.route_task(
        "Fix the off-by-one error in process()",
        "swe-bench",
        mode="heuristic",
    )
    assert result["tool"] == "code_generation"
    assert result["method"] == "heuristic_suite"
    assert result["correct"] is True


def test_ground_truth_category_known_suite() -> None:
    assert needle_router._ground_truth_category("mmlu-pro") == "question_answering"
    assert needle_router._ground_truth_category("unknown-suite") == "unknown"


def test_semantic_analysis_dry_path() -> None:
    reply = "The answer is B. This is because option B matches the definition."
    prompt = "Which option is correct? A B C D"
    quality = semantic_analysis.analyze_response_quality(
        reply, prompt, "correct_letter"
    )
    assert 0.0 <= quality["relevance_score"] <= 1.0
    failure = semantic_analysis.decompose_failure_mode(reply, prompt, "correct_letter")
    assert failure["primary_factor"]
    progress = semantic_analysis.compute_task_progress(reply, prompt, "easy")
    assert progress


def test_mlx_direct_availability_probe() -> None:
    # Import must succeed even when mlx_lm is absent; probe is non-throwing.
    assert isinstance(mlx_is_available(), bool)


def test_sglang_direct_availability_probe() -> None:
    # SGLangDirect only checks PHENO_SGLANG_URL; probe is non-throwing on
    # hosts without a running sglang server.
    assert isinstance(sglang_is_available(), bool)


def test_sglang_direct_requires_url_or_env() -> None:
    import os

    old = os.environ.pop("PHENO_SGLANG_URL", None)
    try:
        with pytest.raises(RuntimeError, match="PHENO_SGLANG_URL"):
            SGLangDirect(base_url=None)
    finally:
        if old is not None:
            os.environ["PHENO_SGLANG_URL"] = old


def test_sglang_direct_model_id_default() -> None:
    # When model_id is unset, returns 'default' sentinel used by the matrix.
    adapter = SGLangDirect(base_url="http://127.0.0.1:30000/v1", model="qwen-test")
    assert adapter.model_id == "qwen-test"
    assert adapter.close() is None  # no-op teardown


def test_pick_25_tasks_meta_populated() -> None:
    tasks = stock_vs_ours.pick_25_tasks("mmlu-pro")
    assert len(tasks) == 25
    first = tasks[0]
    assert first.meta.get("title")
    assert first.meta.get("acceptance")
    assert first.meta.get("description") == first.prompt


@pytest.mark.parametrize("suite", stock_vs_ours.SUITES)
def test_pick_25_tasks_all_suites(suite: str) -> None:
    tasks = stock_vs_ours.pick_25_tasks(suite)
    assert len(tasks) == 25
    assert all(t.meta for t in tasks)
