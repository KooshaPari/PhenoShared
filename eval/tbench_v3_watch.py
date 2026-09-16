"""Record TB3 compatibility-watch state without fetching a dataset."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pheno.paths import PHENO_ROOT


def record_status(output: Path | None = None) -> Path:
    """Append a TB3 watch-state record to the JSONL log.

    Reads the ``PHENO_ENABLE_TB3`` env var to mark the record. When
    unset, the status is ``"disabled"``. Network action is always
    ``"none"`` — this is a watch-only helper, not a fetcher.

    Args:
        output: Optional override for the JSONL output path. Defaults
            to ``bench/results/tbench/tb3_watch.jsonl``.

    Returns:
        Path to the JSONL file written to.
    """
    enabled = os.environ.get("PHENO_ENABLE_TB3") == "1"
    path = output or PHENO_ROOT / "bench" / "results" / "tbench" / "tb3_watch.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "suite": "terminal-bench@3.x",
        "status": "watch_enabled_pending_registry_check" if enabled else "disabled",
        "network_action": "none",
        "reason": "Set PHENO_ENABLE_TB3=1 only when an explicit registry check is approved.",
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return path
