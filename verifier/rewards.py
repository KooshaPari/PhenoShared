"""RLVR-AF reward functions — verifiable signals only (Phase 3).

.. deprecated::
    This bespoke reward module is deprecated as of 2026-07-21. The
    canonical RLVR-AF composite reward is the
    ``harbor_pheno.rlvr_af.nested_l0_l1_l2_l3`` function in the
    ``harbor-pheno`` extension package
    (``portage/packages/harbor-pheno/src/harbor_pheno/rlvr_af.py``),
    with a registered plugin entry point. Pheno-harness remains for
    smoke tests only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from verifier.harness import VerifierResult


@dataclass
class RewardBreakdown:
    """Per-dimension reward with weighted total.

    Attributes:
        json_valid: Score for JSON validity (0/1).
        tool_valid: Score for tool-call structure (0/1).
        patch_applies: Score for patch applicability (0/1).
        tests_pass: Score for tests passing (0/1).
        output_under_cap: Ratio score for output tokens under cap.
        context_under_budget: Ratio score for context under budget.
        correct_escalation: Whether escalation was correct (0/1).
        tokens_saved: Fraction of baseline tokens saved.
        weights: Per-dimension weights applied to total.
        total: Weighted total reward.
        passed: Whether total exceeds threshold and verifier ok.

    """

    json_valid: float = 0.0
    tool_valid: float = 0.0
    patch_applies: float = 0.0
    tests_pass: float = 0.0
    output_under_cap: float = 0.0
    context_under_budget: float = 0.0
    correct_escalation: float = 0.0
    tokens_saved: float = 0.0
    weights: dict[str, float] = field(default_factory=dict)
    total: float = 0.0
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize the breakdown to a JSON-compatible dict.

        Returns:
            Dict with all reward dimensions and total.

        """
        return {
            "json_valid": self.json_valid,
            "tool_valid": self.tool_valid,
            "patch_applies": self.patch_applies,
            "tests_pass": self.tests_pass,
            "output_under_cap": self.output_under_cap,
            "context_under_budget": self.context_under_budget,
            "correct_escalation": self.correct_escalation,
            "tokens_saved": self.tokens_saved,
            "weights": self.weights,
            "total": self.total,
            "passed": self.passed,
        }


# Task 55 narrowing alias: Reward is the canonical typed reward.
Reward = RewardBreakdown


DEFAULT_WEIGHTS: dict[str, float] = {
    "json_valid": 0.10,
    "tool_valid": 0.10,
    "patch_applies": 0.20,
    "tests_pass": 0.25,
    "output_under_cap": 0.10,
    "context_under_budget": 0.10,
    "correct_escalation": 0.05,
    "tokens_saved": 0.10,
}


def _bool_score(ok: bool) -> float:
    """Convert a boolean check to a 0.0/1.0 score.

    Args:
        ok: Whether the check passed.

    Returns:
        1.0 if ok else 0.0.

    """
    return 1.0 if ok else 0.0


def _ratio_score(actual: int, limit: int) -> float:
    """Score whether ``actual`` is under ``limit`` with linear decay overage.

    Args:
        actual: Observed token count.
        limit: Allowed budget/cap.

    Returns:
        1.0 if under limit, otherwise ``max(0, 1 - over)`` where over is
        ``(actual - limit)/limit``.

    """
    if limit <= 0:
        return 1.0
    if actual <= limit:
        return 1.0
    over = (actual - limit) / max(limit, 1)
    return max(0.0, 1.0 - over)


def _tokens_saved_score(baseline: int, actual: int) -> float:
    """Score fraction of baseline tokens saved.

    Args:
        baseline: Baseline context tokens before reduction.
        actual: Actual context tokens used.

    Returns:
        ``min(1, saved/baseline)`` or 0 if baseline <= 0.

    """
    if baseline <= 0:
        return 0.0
    saved = max(0, baseline - actual)
    return min(1.0, saved / baseline)


def compute_rewards(
    result: VerifierResult,
    *,
    weights: dict[str, float] | None = None,
    pass_threshold: float = 0.75,
) -> RewardBreakdown:
    """Aggregate verifier checks into a scalar RLVR-AF reward.

    Args:
        result: ``VerifierResult`` (or ``Verdict``) from ``VerifierHarness``.
        weights: Optional override weights merged over ``DEFAULT_WEIGHTS``.
        pass_threshold: Threshold for ``passed`` flag (and must also have
            ``result.ok``).

    Returns:
        ``RewardBreakdown`` (alias ``Reward``) with weighted total.

    """
    w: dict[str, float] = {**DEFAULT_WEIGHTS, **(weights or {})}
    checks: dict[str, bool] = result.checks
    rb = RewardBreakdown(
        json_valid=_bool_score(checks.get("json_valid", False)),
        tool_valid=_bool_score(checks.get("tool_valid", False)),
        patch_applies=_bool_score(checks.get("patch_applies", False)),
        tests_pass=_bool_score(checks.get("tests_pass", False)),
        output_under_cap=_ratio_score(
            int(result.meta.get("output_tokens", 0)),
            int(result.meta.get("output_cap", 0)),
        ),
        context_under_budget=_ratio_score(
            int(result.meta.get("context_tokens", 0)),
            int(result.meta.get("context_budget", 0)),
        ),
        correct_escalation=_bool_score(checks.get("correct_escalation", True)),
        tokens_saved=_tokens_saved_score(
            int(result.meta.get("baseline_context_tokens", 0)),
            int(result.meta.get("context_tokens", 0)),
        ),
        weights=w,
    )
    rb.total = round(
        rb.json_valid * w["json_valid"]
        + rb.tool_valid * w["tool_valid"]
        + rb.patch_applies * w["patch_applies"]
        + rb.tests_pass * w["tests_pass"]
        + rb.output_under_cap * w["output_under_cap"]
        + rb.context_under_budget * w["context_under_budget"]
        + rb.correct_escalation * w["correct_escalation"]
        + rb.tokens_saved * w["tokens_saved"],
        4,
    )
    rb.passed = rb.total >= pass_threshold and result.ok
    return rb
