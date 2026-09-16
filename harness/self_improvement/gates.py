"""Required garden gates; evaluation only, never promotion or mutation."""

from __future__ import annotations

from typing import Any

_ALERT_RANK = {"green": 0, "yellow": 1, "red": 2, "blackout": 3}


def _decision(required: bool, passed: bool | None, reason: str) -> dict[str, Any]:
    status = (
        "green" if passed is True else "red" if passed is False else "not_evaluated"
    )
    return {"required": required, "status": status, "passed": passed, "reason": reason}


def evaluate_gates(
    metrics: dict[str, Any], baseline: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    gates = policy.get("gates", {})
    holdout_cfg = gates.get("holdout", {})
    holdout = metrics.get("holdout_score")
    base_holdout = baseline.get("holdout_score")
    holdout_pass = (
        None
        if holdout is None or base_holdout is None
        else float(holdout)
        >= float(base_holdout) + float(holdout_cfg.get("min_delta_vs_baseline", 0.0))
    )
    decisions = {
        "holdout": _decision(
            bool(holdout_cfg.get("required")),
            holdout_pass,
            "candidate holdout vs baseline",
        )
    }

    regression_cfg = gates.get("regression", {})
    regressions = metrics.get("new_regressions")
    decisions["regression"] = _decision(
        bool(regression_cfg.get("required")),
        None
        if regressions is None
        else int(regressions)
        <= int(regression_cfg.get("max_allowed_new_regressions", 0)),
        "new regression count",
    )

    safety_cfg = gates.get("safety", {})
    violations = metrics.get("high_severity_violations")
    decisions["safety"] = _decision(
        bool(safety_cfg.get("required")),
        None
        if violations is None
        else int(violations) <= int(safety_cfg.get("max_high_severity_violations", 0)),
        "high-severity safety violations",
    )

    budget_cfg = gates.get("budget", {})
    alert = str(metrics.get("budget_alert_level", ""))
    max_alert = str(budget_cfg.get("max_alert_level", "green"))
    decisions["budget"] = _decision(
        bool(budget_cfg.get("required")),
        None
        if alert not in _ALERT_RANK or max_alert not in _ALERT_RANK
        else _ALERT_RANK[alert] <= _ALERT_RANK[max_alert],
        f"alert={alert or 'missing'}, max={max_alert}",
    )

    replay_cfg = gates.get("reproducibility", {})
    replay = metrics.get("replay_equivalence")
    decisions["reproducibility"] = _decision(
        bool(replay_cfg.get("required")),
        None
        if replay is None
        else float(replay) >= float(replay_cfg.get("min_replay_equivalence", 0.90)),
        "replay equivalence",
    )

    serving_cfg = gates.get("serving_stability", {})
    crashes = metrics.get("crash_count")
    ttft_regression = metrics.get("p95_ttft_regression_pct")
    serving_pass = (
        None
        if crashes is None or ttft_regression is None
        else (
            int(crashes) <= int(serving_cfg.get("max_crash_count", 0))
            and float(ttft_regression)
            <= float(serving_cfg.get("max_p95_ttft_regression_pct", 10))
        )
    )
    decisions["serving_stability"] = _decision(
        bool(serving_cfg.get("required")),
        serving_pass,
        "crash count and p95 TTFT regression",
    )
    required_failures = [
        name
        for name, value in decisions.items()
        if value["required"] and value["status"] != "green"
    ]
    return {
        "status": "green" if not required_failures else "red",
        "decisions": decisions,
        "required_failures": required_failures,
    }


__all__ = ["evaluate_gates"]
