"""Human-gated two-window promotion decisions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def promotion_decision(
    windows: Iterable[dict[str, Any]], human_approved: bool = False
) -> dict[str, Any]:
    rows = list(windows)
    last_two = rows[-2:]
    green = len(last_two) == 2 and all(row.get("status") == "green" for row in last_two)
    eligible = green and human_approved
    if not green:
        reason = "requires two consecutive green windows"
    elif not human_approved:
        reason = "human approval is required"
    else:
        reason = "eligible; caller must still apply an explicit reviewed change"
    return {
        "eligible": eligible,
        "green_windows": len(last_two) if green else 0,
        "human_approved": human_approved,
        "reason": reason,
        "mutated": False,
    }


__all__ = ["promotion_decision"]
