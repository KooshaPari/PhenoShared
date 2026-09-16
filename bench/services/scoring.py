"""ScoringService — scoring and pass@1 computation.

Pure functions that operate on lists of task results; no I/O, no ports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoreSummary:
    """Aggregated scoring metrics for a set of task results."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    errored: int = 0
    pass_at_1: float = 0.0
    mean_latency_ms: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class ScoringService:
    """Compute aggregate scores from individual task outcomes."""

    @staticmethod
    def compute_pass_at_1(results: list[dict[str, Any]]) -> float:
        """Compute pass@1 from a list of result dicts (each must have 'passed' key)."""
        if not results:
            return 0.0
        ok = sum(1 for r in results if r.get("passed", False))
        return ok / len(results)

    @staticmethod
    def summarize(results: list[dict[str, Any]]) -> ScoreSummary:
        """Produce a :class:`ScoreSummary` from a list of result dicts."""
        total = len(results)
        passed = sum(1 for r in results if r.get("passed", False))
        failed = sum(
            1 for r in results if not r.get("passed", False) and r.get("error") is None
        )
        errored = sum(1 for r in results if r.get("error") is not None)
        pass_at_1 = passed / max(1, total)
        mean_lat = sum(r.get("latency_ms", 0.0) for r in results) / max(1, total)
        pt = sum(r.get("prompt_tokens", 0) for r in results)
        ct = sum(r.get("completion_tokens", 0) for r in results)
        return ScoreSummary(
            total=total,
            passed=passed,
            failed=failed,
            errored=errored,
            pass_at_1=pass_at_1,
            mean_latency_ms=mean_lat,
            total_prompt_tokens=pt,
            total_completion_tokens=ct,
        )
