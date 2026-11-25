#!/usr/bin/env python3
"""Run a local streaming/concurrency performance sweep.

Real mode requires an already-running OpenAI-compatible local server. Synthetic
mode exercises scheduling and reporting only; it never calls a model.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from perf.resources import ResourceSampler  # noqa: E402
from perf.streaming import nonstream_chat, stream_chat  # noqa: E402
from perf.sweep import run_sweep  # noqa: E402
from pheno.model_policy import require_local_alias  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PhenoLM streaming concurrency profiler"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:21080")
    parser.add_argument("--model", default="local/qwen35-08b")
    parser.add_argument("--request-model", help="served model ID sent to the endpoint")
    parser.add_argument(
        "--transport", choices=("stream", "non-streaming"), default="stream"
    )
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--concurrency", default="1,2,4,8")
    parser.add_argument("--requests-per-level", type=int, default=8)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--engine-label", default="unknown")
    parser.add_argument("--api-key", help="Bearer token; defaults to PHENO_API_KEY")
    parser.add_argument("--resource-interval-s", type=float, default=0.5)
    parser.add_argument("--no-gpu-sampling", action="store_true")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument(
        "--thinking",
        action="store_true",
        help="Enable model reasoning during real requests",
    )
    return parser.parse_args()


def load_tasks(path: Path | None, count: int) -> list[dict[str, Any]]:
    if path is None:
        return [
            {
                "task_id": str(i),
                "prompt": "Return a short status line.",
                "max_tokens": 32,
                "temperature": 0.0,
            }
            for i in range(count)
        ]
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError(f"fixture is empty: {path}")
    return [rows[i % len(rows)] for i in range(count)]


def synthetic_call(task: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    time.sleep(0.001 + random.random() * 0.002)
    elapsed = (time.perf_counter() - started) * 1000.0
    return {
        "elapsed_ms": elapsed,
        "ttft_ms": elapsed / 2,
        "completion_tokens": 16,
        "decode_tok_s": 16 / (elapsed / 1000.0),
        "measurement_quality": "synthetic",
    }


def main() -> int:
    args = parse_args()
    if args.requests_per_level < 1 or args.warmup < 0:
        raise SystemExit("requests-per-level must be positive and warmup nonnegative")
    try:
        require_local_alias(args.model)
    except ValueError as exc:
        raise SystemExit(str(exc))
    levels = [int(item) for item in args.concurrency.split(",") if item.strip()]
    if not levels or any(level < 1 for level in levels):
        raise SystemExit("--concurrency must contain positive integers")
    tasks = load_tasks(args.fixture, args.requests_per_level)
    request_model = args.request_model or args.model
    transport = nonstream_chat if args.transport == "non-streaming" else stream_chat
    caller = (
        synthetic_call
        if args.synthetic
        else lambda task: transport(
            args.base_url,
            request_model,
            str(task.get("prompt", "")),
            int(task.get("max_tokens", 64)),
            float(task.get("temperature", 0.0)),
            args.timeout_s,
            args.api_key,
            args.thinking,
        )
    )
    include_gpu = not args.no_gpu_sampling
    overhead_sampler = ResourceSampler(
        interval=args.resource_interval_s, include_gpu=include_gpu
    )
    probe_overhead = overhead_sampler.measure_collect_overhead()
    sampler = ResourceSampler(
        interval=args.resource_interval_s, include_gpu=include_gpu
    )
    started = time.perf_counter()
    with sampler:
        sweep = run_sweep(caller, tasks, levels, args.warmup)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    payload = {
        "schema_version": "pheno.perf.v1",
        "engine": args.engine_label,
        "model": args.model,
        "request_model": request_model,
        "base_url": args.base_url if not args.synthetic else None,
        "synthetic": args.synthetic,
        "elapsed_ms": elapsed_ms,
        "warmup": sweep["warmup"],
        "transport": "synthetic" if args.synthetic else args.transport,
        "levels": sweep["levels"],
        "probe_overhead_ms": probe_overhead,
        "resources": sampler.summary(),
        "measurement_notes": [
            (
                "TTFT is time to first nonempty streamed content chunk; ITL is inter-SSE-chunk timing, "
                "not guaranteed one token per chunk."
            )
            if args.transport == "stream" and not args.synthetic
            else (
                "Total request latency is reported; TTFT/ITL are unavailable for non-streaming transport."
                if args.transport == "non-streaming" and not args.synthetic
                else "Synthetic mode measures harness scheduling only, not model inference."
            ),
            f"Thinking mode: {'enabled' if args.thinking else 'disabled'}.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "levels": len(payload["levels"]),
                "synthetic": args.synthetic,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
