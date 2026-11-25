"""File-backed daily quota counter for code-review providers.

Each provider's usage is stored in a per-day JSON file under
``{state_root}/quota-{provider_id}.{YYYY-MM-DD}.json``. The day boundary is
the local calendar date. Multi-process safety is NOT a goal — P1 is
single-process dry-run only; P3 will introduce flock() if multi-process
becomes necessary.

Source of truth: spec §6 D4 (quota rotation unit = per-day, per-provider).
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path


class QuotaExhaustedError(Exception):
    """Raised when consume() would push a provider past its daily limit."""

    def __init__(self, provider_id: str, limit: int, used: int) -> None:
        self.provider_id = provider_id
        self.limit = limit
        self.used = used
        super().__init__(
            f"Provider {provider_id!r} exhausted: {used}/{limit} used today"
        )


class QuotaStore:
    """Daily quota counter, one JSON file per (provider, day)."""

    def __init__(self, state_root: Path) -> None:
        self.state_root = Path(state_root)
        self.state_root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, provider_id: str, day: date | None = None) -> Path:
        day = day or date.today()
        safe_id = provider_id.replace("/", "_")
        return self.state_root / f"quota-{safe_id}.{day.isoformat()}.json"

    def _read(self, provider_id: str, day: date | None = None) -> dict:
        path = self._path_for(provider_id, day)
        if not path.exists():
            return {"provider": provider_id, "date": (day or date.today()).isoformat(), "used": 0}
        return json.loads(path.read_text())

    def usage(self, provider_id: str) -> int:
        """Return the number of times ``provider_id`` has been used today."""
        return int(self._read(provider_id).get("used", 0))

    def remaining(self, provider_id: str, limit: int | None) -> float:
        """Return remaining quota for today. ``None`` limit → +inf."""
        if limit is None:
            return math.inf
        return max(0, int(limit) - self.usage(provider_id))

    def record(self, provider_id: str) -> None:
        """Increment today's usage counter by 1 and persist to disk."""
        data = self._read(provider_id)
        data["used"] = int(data.get("used", 0)) + 1
        path = self._path_for(provider_id)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    def consume(self, provider_id: str, limit: int | None) -> None:
        """Atomically check + record one use.

        Raises:
            QuotaExhaustedError: if recording would exceed the daily limit.
        """
        if limit is None:
            self.record(provider_id)
            return
        used = self.usage(provider_id)
        if used >= int(limit):
            raise QuotaExhaustedError(provider_id, int(limit), used)
        self.record(provider_id)
