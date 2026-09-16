#!/usr/bin/env python3
"""Evaluate garden gates over recent observations without mutating policy."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.self_improvement.gates import evaluate_gates  # noqa: E402
from harness.self_improvement.retention import retention_preview  # noqa: E402
from pheno.paths import CONFIG_DIR  # noqa: E402


def _read_rows(path: Path, cutoff: datetime) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            stamp = datetime.fromisoformat(
                str(row["timestamp_utc"]).replace("Z", "+00:00")
            )
            if stamp >= cutoff:
                rows.append(row)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate PhenoLM garden gates")
    parser.add_argument(
        "--dry-run", action="store_true", help="required: never write state"
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.dry_run:
        parser.error(
            "only --dry-run is implemented; promotion never mutates automatically"
        )
    if args.days < 1:
        parser.error("--days must be positive")
    policy = (
        yaml.safe_load((CONFIG_DIR / "garden_loop.yaml").read_text(encoding="utf-8"))
        or {}
    )
    ledger = ROOT / policy.get("ledger", {}).get("path", "state/garden/ledger.jsonl")
    now = datetime.now(UTC)
    rows = _read_rows(ledger, now - timedelta(days=args.days))
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_lane.setdefault(str(row.get("lane", "unknown")), []).append(row)
    reports = []
    for lane, lane_rows in sorted(by_lane.items()):
        latest = lane_rows[-1]
        metrics = latest.get("metrics", {})
        baseline = latest.get("baseline_metrics", {})
        gates = evaluate_gates(metrics, baseline, policy)
        reports.append({"lane": lane, "rows": len(lane_rows), "gates": gates})
    report = {
        "schema_version": "phenolm.garden.tick.v1",
        "dry_run": True,
        "window_days": args.days,
        "row_count": len(rows),
        "lanes": reports,
        "retention": retention_preview(
            ledger, int(policy.get("loop", {}).get("trace_retention_days", 30)), now
        ),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
