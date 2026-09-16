#!/usr/bin/env python3
"""Convert one raw JSONL trace to review-only spec/replay artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.role_suite import build_spec  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-ineligible",
        action="store_true",
        help="write for review; remains non-scoreable",
    )
    args = parser.parse_args()
    try:
        events = [
            json.loads(line)
            for line in args.trace.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        spec, replay = build_spec(
            args.trace, events, allow_ineligible=args.allow_ineligible
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = spec["task_id"]
    spec_path = args.output_dir / f"{stem}.spec.json"
    replay_path = args.output_dir / f"{stem}.replay.jsonl"
    spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    replay_path.write_text(
        "".join(json.dumps(row) + "\n" for row in replay), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "spec": str(spec_path),
                "replay": str(replay_path),
                "role_id": spec["role_id"],
                "scoreable": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
