"""V5 cell contract v0.2 pass-metric helpers.

Honest metrics: ``gen_ok`` is generation success (MLX/HTTP returned output).
``pass_at_1`` is dual-written as an alias for one release but is **not**
verified pass@1.  ``verified_pass_at_1`` stays 0.0 unless Harbor or another
verifier supplies a real score.
"""

from __future__ import annotations

from typing import Any, cast

EVIDENCE_REPORTED = "reported"
EVIDENCE_VERIFIED = "verified"
VALID_CELL_EVIDENCE_LABELS = frozenset({EVIDENCE_REPORTED, EVIDENCE_VERIFIED})


def cell_pass_fields(
    gen_success: bool,
    *,
    harbor_reward: float | None = None,
) -> dict[str, Any]:
    """Return v0.2 cell pass-metric fields with dual-write ``pass_at_1`` alias."""
    gen_ok = 1.0 if gen_success else 0.0

    if harbor_reward is not None:
        verified_pass_at_1 = float(harbor_reward)
        evidence_label = EVIDENCE_VERIFIED
    else:
        verified_pass_at_1 = 0.0
        evidence_label = EVIDENCE_REPORTED

    return {
        "gen_ok": gen_ok,
        # NOT verified pass@1 — dual-write alias of gen_ok for one release (PR1).
        "pass_at_1": gen_ok,
        "verified_pass_at_1": verified_pass_at_1,
        "evidence_label": evidence_label,
    }


def task_gen_ok(task: dict[str, Any]) -> float | None:
    """Read ``gen_ok`` from a contract ``task_result``; None when absent."""
    ap = task.get("additionalProperties") or {}
    if "gen_ok" in ap:
        return float(ap["gen_ok"])
    if "gen_ok" in task:
        return float(task["gen_ok"])
    return None


def suite_gen_ok_mean(suite: dict[str, Any]) -> float | None:
    """Mean ``gen_ok`` across ``task_results`` when any task carries the field."""
    values = [
        value
        for task in suite.get("task_results", [])
        if (value := task_gen_ok(task)) is not None
    ]
    if not values:
        return None
    n = suite.get("n", len(values))
    if n <= 0:
        return 0.0
    return cast(float, round(sum(values) / n, 4))


def effective_pass_at_1(suite: dict[str, Any]) -> float:
    """Prefer ``gen_ok`` mean for reported evidence; else legacy ``pass_at_1``."""
    gen_ok_mean = suite_gen_ok_mean(suite)
    if gen_ok_mean is not None:
        return gen_ok_mean
    return float(suite.get("pass_at_1", 0.0))
