"""Append-only event logging for pheno-serve-dev."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EventLog:
    """Append-only JSONL event log for pheno-serve-dev."""

    def __init__(self, path: Path):
        self.path = path

    def append(self, event: dict[str, Any]) -> None:
        """Append one event dict to the log as a JSON line."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {"timestamp_utc": datetime.now(UTC).isoformat(), **event}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
