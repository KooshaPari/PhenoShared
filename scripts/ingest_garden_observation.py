#!/usr/bin/env python3
"""Ingest one completed local artifact into the append-only garden ledger."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.self_improvement.artifacts import observation_from_artifact  # noqa: E402
from scripts.gardener import _ledger_path, _load_policy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest a local performance/eval artifact"
    )
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--dry-run", action="store_true", help="print the observation without appending"
    )
    args = parser.parse_args()
    path = args.artifact.resolve()
    if not path.is_file():
        parser.error(f"artifact does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"invalid JSON artifact: {exc}")
    if not isinstance(payload, dict):
        parser.error("artifact root must be an object")
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        git_sha = "unknown"
    row = observation_from_artifact(payload, artifact=path, git_sha=git_sha)
    if args.dry_run:
        print(json.dumps(row, indent=2))
        return 0
    ledger = _ledger_path(_load_policy())
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(
        json.dumps(
            {"appended": True, "ledger": str(ledger), "scoreable": row["scoreable"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
