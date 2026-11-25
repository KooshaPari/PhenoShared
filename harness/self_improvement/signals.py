"""Deterministic aggregation of garden observations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from statistics import mean
from typing import Any


def aggregate_rows(
    rows: Iterable[dict[str, Any]], group_by: str | None = None
) -> dict[str, Any]:
    records = list(rows)
    if group_by:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in records:
            grouped[str(row.get(group_by, "unknown"))].append(row)
        return {key: aggregate_rows(value) for key, value in sorted(grouped.items())}
    numeric: dict[str, list[float]] = defaultdict(list)
    for row in records:
        for key, value in row.get("metrics", row).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric[key].append(float(value))
    return {
        key: {
            "count": len(values),
            "mean": mean(values),
            "min": min(values),
            "max": max(values),
        }
        for key, values in sorted(numeric.items())
    }


__all__ = ["aggregate_rows"]
