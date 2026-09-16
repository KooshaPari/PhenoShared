#!/usr/bin/env python3
"""Run a capacity-weighted heterogeneous-worker performance sweep."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from perf.heterogeneous import run_heterogeneous  # noqa: E402
from perf.streaming import stream_chat  # noqa: E402
from pheno.model_policy import require_local_alias  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--worker",
        action="append",
        required=True,
        help="worker-id=http://host:port (repeatable)",
    )
    parser.add_argument(
        "--capacity",
        action="append",
        default=[],
        help="worker-id=relative capacity weight (repeatable; measured tok/s ratio)",
    )
    parser.add_argument("--model", default="local/qwen35-08b")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require_local_alias(args.model)
    workers = []
    for value in args.worker:
        worker_id, separator, base_url = value.partition("=")
        if not separator or not worker_id or not base_url:
            raise SystemExit("--worker must be worker-id=base-url")
        workers.append({"id": worker_id, "base_url": base_url})
    capacities = {}
    for value in args.capacity:
        worker_id, separator, weight = value.partition("=")
        if not separator or not worker_id:
            raise SystemExit("--capacity must be worker-id=positive-weight")
        try:
            capacities[worker_id] = float(weight)
        except ValueError as exc:
            raise SystemExit("--capacity weight must be numeric") from exc
    for worker in workers:
        if worker["id"] in capacities:
            worker["capacity_weight"] = capacities[worker["id"]]
    tasks = [
        {
            "task_id": str(index),
            "prompt": "Return a short status line.",
            "max_tokens": args.max_tokens,
            "temperature": 0.0,
        }
        for index in range(args.requests)
    ]

    def caller(worker: dict[str, str], task: dict[str, Any]) -> dict[str, object]:
        result = stream_chat(
            worker["base_url"],
            args.model,
            str(task["prompt"]),
            int(task["max_tokens"] or 0),
            0.0,
            120.0,
        )
        return result

    payload = {
        "schema_version": "pheno.heterogeneous_perf.v1",
        "model": args.model,
        "workers": workers,
        "result": run_heterogeneous(workers, tasks, args.concurrency, caller),
        "measurement_notes": [
            "Workers are independent processes; no tensor parallelism is implied.",
            "Capacity weights are throughput priors, not semantic quality scores.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "success_count": payload["result"]["success_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
