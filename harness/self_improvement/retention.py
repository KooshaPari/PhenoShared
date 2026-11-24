"""Non-destructive retention helpers for the append-only garden ledger."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def retention_preview(
    path: Path, retention_days: int = 30, now: datetime | None = None
) -> dict[str, Any]:
    """Count fresh/eligible-for-archive rows without modifying the ledger."""
    if retention_days < 1:
        raise ValueError("retention_days must be positive")
    current = now or datetime.now(UTC)
    cutoff = current - timedelta(days=retention_days)
    total = fresh = archiveable = malformed = 0
    if not path.exists():
        return {
            "path": str(path),
            "total": 0,
            "fresh": 0,
            "archiveable": 0,
            "malformed": 0,
            "cutoff_utc": cutoff.isoformat(),
        }
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        try:
            row = json.loads(line)
            timestamp = datetime.fromisoformat(
                str(row["timestamp_utc"]).replace("Z", "+00:00")
            )
            if timestamp < cutoff:
                archiveable += 1
            else:
                fresh += 1
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            malformed += 1
    return {
        "path": str(path),
        "total": total,
        "fresh": fresh,
        "archiveable": archiveable,
        "malformed": malformed,
        "cutoff_utc": cutoff.isoformat(),
        "non_destructive": True,
    }


__all__ = ["retention_preview"]
