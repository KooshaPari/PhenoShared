"""StartupBench (2026-07) — long-horizon business-decision benchmark.

Models play the role of a newly-founded startup CEO over a 90-day simulated
period. Tasks cover: product positioning, hire/fire, fundraising, pricing,
roadmap prioritization, runway management. Adapted from Y Combinator
startup-simulation literature + recent paper "Long-Horizon Startup Planning
Benchmarks" (Stanford GSB, July 2026).

Reference: docs/superpowers/specs/2026-07-17-extend-benchmark-suites.md §7.
Default judge: DETERMINISTIC (multi-criterion rubric: runway, growth, decision coherence).
"""

from __future__ import annotations

import json
from typing import Any

from ._stub import BaseSuite, TaskSpec

SOURCE_URL = "specs/2026-07-17-extend-benchmark-suites.md §7"
VERSION = "2026-07"


def _startup_prompt(track: str, day_count: int) -> str:
    return (
        f"# StartupBench-{VERSION} ({track})\n\n"
        f"You are the founder/CEO of a {track} startup. You have "
        f"{day_count} simulated days to reach the following milestones:\n"
        f"- product_market_fit_score >= 7/10\n"
        f"- monthly_growth_rate >= 15%\n"
        f"- runway >= 12 months at end of period\n\n"
        f"Decisions (one per simulated day):\n"
        f"  HIRE <role>   FIRE <role>\n"
        f"  RAISE <amount_usd>\n"
        f"  SHIP <feature>\n"
        f"  PIVOT <direction>\n"
        f"  PRICING <model>\n\n"
        f"Reply with one decision per line in format: `DAY N: <ACTION>`\n"
        f"At end, reply with a JSON block:\n"
        f"```json\n"
        f'{{"product_market_fit_score": 0-10, "monthly_growth_rate": 0.0-1.0,'
        f' "runway_months": 0-36}}\n'
        f"```\n\n"
        f"Begin with: `DAY 1: HIRE cto`"
    )


def _parse_startup(text: str) -> dict[str, Any]:
    import re

    out = {
        "decisions": 0,
        "score": None,
        "valid_json": False,
        "trace": [],
    }

    decision_pattern = re.compile(r"DAY\s+(\d+)\s*:\s*(\w+(?:\s+[\w\-]+)?)", re.I)
    for m in decision_pattern.finditer(text):
        out["decisions"] += 1  # type: ignore[operator]
        out["trace"].append((int(m.group(1)), m.group(2).strip()))  # type: ignore[union-attr]

    json_block = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if json_block:
        try:
            j = json.loads(json_block.group(1))
            out["score"] = {  # type: ignore[assignment]
                "pmf": float(j.get("product_market_fit_score", 0.0)),
                "growth": float(j.get("monthly_growth_rate", 0.0)),
                "runway_months": float(j.get("runway_months", 0.0)),
            }
            out["valid_json"] = True
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return out


def _startup_score(parsed: dict[str, Any]) -> tuple[bool, str, float]:
    if not parsed["valid_json"] or parsed["score"] is None:
        return False, "invalid-json", 0.0
    s = parsed["score"]
    pmf_pass = s["pmf"] >= 7.0
    growth_pass = s["growth"] >= 0.15
    runway_pass = s["runway_months"] >= 12.0
    if pmf_pass and growth_pass and runway_pass:
        return True, "all-milestones-met", sum([pmf_pass, growth_pass, runway_pass])
    if pmf_pass or growth_pass or runway_pass:
        return False, "partial-milestones", sum([pmf_pass, growth_pass, runway_pass])
    return False, "no-milestones", 0.0


class StartupBench(BaseSuite):
    """Long-horizon startup-ops planning benchmark."""

    name = "startup-bench"
    domain = "long-horizon-planning"
    paper_metrics: tuple[str, ...] = (  # type: ignore[assignment]
        "milestones-met",
        "decision-coverage",
        "pmf",
        "growth-rate",
        "runway-months",
    )
    default_judge = "deterministic"
    source_url = SOURCE_URL
    notes = (
        "StartupBench (July 2026): 90-180 day startup CEO simulation. "
        "6 tracks: ai-saas, marketplace, fintech, healthtech, dev-tools, "
        "consumer. Score = number of milestones met (PMF, growth, runway). "
        "Multi-decision per day tests plan coherence + execution realism."
    )

    def __init__(self) -> None:
        self._tracks = [
            ("ai-saas", 90),
            ("marketplace", 90),
            ("fintech", 120),
            ("healthtech", 180),
            ("dev-tools", 90),
            ("consumer", 120),
        ]
        self._tasks = [
            TaskSpec(
                task_id=f"startup-bench-{track}",
                suite=self.name,
                prompt=_startup_prompt(track, days),
                reference=track,
                tags={"track": track, "days": days},  # type: ignore[arg-type]
            )
            for track, days in self._tracks
        ]

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return ``n`` deterministically sampled tasks for a benchmark run."""
        from bench.seeds import sample

        if n >= len(self._tasks):
            return list(self._tasks)
        idx = sample(self.name, seed, pool=list(range(len(self._tasks))), n=n)
        return [self._tasks[i] for i in idx.ordered_indices]

    def verify(self, task: TaskSpec, completion: str) -> tuple[bool, dict[str, Any]]:
        """Score the model completion against the expected startup-ops milestones."""

        parsed = _parse_startup(completion)
        passed, reason, milestones = _startup_score(parsed)
        return passed, {
            "judge": "startup-bench-validator",
            "reason": reason,
            "milestones_met": int(milestones),
            "pmf_score": parsed["score"]["pmf"] if parsed["score"] else None,
            "growth_rate": parsed["score"]["growth"] if parsed["score"] else None,
            "runway_months": parsed["score"]["runway_months"]
            if parsed["score"]
            else None,
            "decision_count": parsed["decisions"],
            "decision_coverage_pct": round(
                100 * parsed["decisions"] / task.tags["days"], 1  # type: ignore[call-overload]
            ),
        }


__all__ = ["StartupBench", "SOURCE_URL", "VERSION"]
