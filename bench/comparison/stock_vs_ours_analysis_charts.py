"""Task pool synthesis and visualization helpers for stock-vs-ours analysis.

This module contains the task pool generation functions for all benchmark
suites and the pick_25_tasks dispatch function.
"""

from __future__ import annotations

# Re-export pool functions from sub-module for backward compatibility.
from bench.comparison.stock_vs_ours_analysis_pools import (  # noqa: E402, F401
    _aider_polyglot_pool,
    _aime_pool,
    _arc_agi_2_pool,
    _bfcl_pool,
    _gpqa_diamond_pool,
    _livecodebench_pool,
    _mmlu_pro_pool,
    _swe_bench_pool,
    _swe_bench_pro_pool,
    _terminal_bench_pool,
)
from bench.types import TaskSpec


def pick_25_tasks(suite: str) -> list[TaskSpec]:
    """Dispatch to the canonical pool function for each of the 10 suites."""
    pool_fns = {
        "mmlu-pro": _mmlu_pro_pool,
        "gpqa-diamond": _gpqa_diamond_pool,
        "aime": _aime_pool,
        "arc-agi-2": _arc_agi_2_pool,
        "livecodebench": _livecodebench_pool,
        "aider-polyglot": _aider_polyglot_pool,
        "swe-bench": _swe_bench_pool,
        "swe-bench-pro": _swe_bench_pro_pool,
        "bfcl": _bfcl_pool,
        "terminal-bench": _terminal_bench_pool,
    }
    if suite not in pool_fns:
        raise ValueError(f"Unknown suite: {suite}")
    return pool_fns[suite]()
