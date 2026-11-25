"""Vending-Bench-v0 — 2-turn long-horizon business simulation (Andon Labs, 2025).

Tiny but infamous: models run a vending machine business across 50 simulated
days. Two variants: vending-bench-v0-100 (deterministic, 100-day horizon,
fixed $20 starting balance) and vending-bench-v0-200 (200-day, varied seed).

Spec reference: docs/superpowers/specs/2026-07-17-extend-benchmark-suites.md §6.
Source: github.com/andonll/vending-bench (paper: "Vending-Bench: A
Benchmark for Long-Term Coherence of LLM Agents", Andon Labs 2025).
Default judge: DETERMINISTIC (net assets - starting_balance == profit).
Output unit: USD profit.
"""

from __future__ import annotations

from typing import Any

from ._stub import BaseSuite, TaskSpec

SOURCE_URL = "github.com/andonll/vending-bench"
VERSION = "0.1"
STARTING_BALANCE_USD = 20.00
DAYS_HORIZON_100 = 100
DAYS_HORIZON_200 = 200


def _vending_prompt(variant: str, days_horizon: int) -> str:
    return (
        f"# Vending-Bench-v0 ({variant})\n\n"
        f"Scenario: You are the sole operator of a vending machine business "
        f"for {days_horizon} simulated days. Starting balance: "
        f"${STARTING_BALANCE_USD:.2f}. You must:\n"
        f"1. Order inventory at wholesale prices (varying by SKU)\n"
        f"2. Set retail prices per day per machine\n"
        f"3. Refill the machine, adjust stock, react to demand\n"
        f"4. Net profit = final_balance - starting_balance\n\n"
        f"On each simulated day, decide: keep_price, raise_price (amt),\n"
        f"lower_price (amt), order_sku, restock, abort.\n\n"
        f"Reply with one decision per line in format: `DAY N: <ACTION>`\n"
        f"Final line must be: `END_BALANCE=NNN.NN` (your final USD balance)\n\n"
        f"Start: `DAY 1: status`"
    )


def _parse_vending_response(text: str, days_horizon: int) -> dict[str, Any]:
    """Extract decision sequence and final balance from response."""
    import re

    out = {
        "decisions": 0,
        "end_balance": None,
        "valid_format": False,
        "trace": [],
    }

    decision_pattern = re.compile(r"DAY\s+(\d+)\s*:\s*(\w+(?:\s+[\w\.\-]+)?)", re.I)
    for m in decision_pattern.finditer(text):
        out["decisions"] += 1  # type: ignore[operator]
        out["trace"].append((int(m.group(1)), m.group(2).strip()))  # type: ignore[union-attr]

    end_match = re.search(r"END_BALANCE\s*=\s*(-?\d+\.?\d*)", text)
    if end_match:
        try:
            out["end_balance"] = float(end_match.group(1))  # type: ignore[assignment]
        except ValueError:
            pass

    # need >=50% day coverage
    out["valid_format"] = (
        out["decisions"] >= max(1, days_horizon * 0.5)  # type: ignore[arg-type, operator]
        and out["end_balance"] is not None
    )
    return out


def _vending_score(
    parsed: dict[str, Any], days_horizon: int
) -> tuple[bool, str, float]:
    if not parsed["valid_format"]:
        return False, "invalid-format", 0.0
    profit = parsed["end_balance"] - STARTING_BALANCE_USD
    if profit > 0:
        return True, "profitable", profit
    return False, "non-profitable", profit


class VendingBench(BaseSuite):
    """Long-horizon vending-machine operations benchmark."""

    name = "vending-bench"
    domain = "long-horizon-coherence"
    paper_metrics: tuple[str, ...] = ("profit-usd", "decision-coverage", "valid-format")  # type: ignore[assignment]
    default_judge = "deterministic"
    source_url = SOURCE_URL
    notes = (
        "Vending-Bench-v0 (Andon Labs, 2025): 50-100 day simulated vending "
        "machine business. 2 tasks: 100-day and 200-day variants. "
        "Score = final_balance - $20 starting balance. "
        "Editorial note: small benchmark, famous for exposing LLM "
        "incoherence on multi-day business decisions; many models "
        "go negative-balance by day 60."
    )

    def __init__(self) -> None:
        self._tasks = [
            TaskSpec(
                task_id="vending-bench-100",
                suite=self.name,
                prompt=_vending_prompt("v0-100", DAYS_HORIZON_100),
                reference="vending-bench-100",
                tags={"days": DAYS_HORIZON_100, "balance": STARTING_BALANCE_USD},  # type: ignore[arg-type]
            ),
            TaskSpec(
                task_id="vending-bench-200",
                suite=self.name,
                prompt=_vending_prompt("v0-200", DAYS_HORIZON_200),
                reference="vending-bench-200",
                tags={"days": DAYS_HORIZON_200, "balance": STARTING_BALANCE_USD},  # type: ignore[arg-type]
            ),
        ]

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Return ``n`` deterministically sampled tasks for a benchmark run."""
        from bench.seeds import sample

        if n >= len(self._tasks):
            return list(self._tasks)
        idx = sample(self.name, seed, pool=list(range(len(self._tasks))), n=n)
        return [self._tasks[i] for i in idx.ordered_indices]

    def verify(self, task: TaskSpec, completion: str) -> tuple[bool, dict[str, Any]]:
        """Score the model completion against the expected vending day plan."""

        days_horizon = task.tags["days"]  # type: ignore[call-overload]
        parsed = _parse_vending_response(completion, days_horizon)
        passed, reason, profit = _vending_score(parsed, days_horizon)
        return passed, {
            "judge": "vending-bench-validator",
            "reason": reason,
            "profit_usd": profit,
            "end_balance": parsed["end_balance"],
            "decision_count": parsed["decisions"],
            "decision_coverage_pct": round(100 * parsed["decisions"] / days_horizon, 1),
        }


__all__ = [
    "VendingBench",
    "STARTING_BALANCE_USD",
    "DAYS_HORIZON_100",
    "DAYS_HORIZON_200",
    "SOURCE_URL",
]
