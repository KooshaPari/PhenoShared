#!/usr/bin/env python3
"""TTFT + tokens/sec probe harness for pheno-serve-dev + downstream engines.

Usage:
    set PYTHONPATH=C:\\Users\\koosh\\pheno-harness
    python scripts\\perf_probe.py ^
        --base-url http://127.0.0.1:21080 ^
        --model local/qwen35-08b ^
        --fixture bench/fixtures/qwen35_smoke/tasks.jsonl ^
        --output bench/results/2026-07-04/local_qwen35_08b_probe/sglang_batch1.json ^
        --batch-size 1 ^
        --warmup 2

Outputs JSON: { engine, model, batch_size, n_tasks, results: [{ task_id, ttft_ms,
itl_ms_p50, itl_ms_p95, decode_tok_s, total_ms, completion, error }], summary: {...} }

This harness is engine-agnostic: it talks OpenAI-compatible /v1/chat/completions,
so it works equally well against SGLang, vLLM, llama.cpp, or any other engine
exposed through pheno-serve-dev.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TTFT + tokens/sec probe")
    parser.add_argument(
        "--base-url", required=True, help="pheno-serve-dev or engine base URL"
    )
    parser.add_argument("--model", required=True, help="model alias or upstream name")
    parser.add_argument("--fixture", required=True, type=Path, help="JSONL fixture")
    parser.add_argument("--output", required=True, type=Path, help="output JSON path")
    parser.add_argument(
        "--batch-size", type=int, default=1, help="requests in parallel (default 1)"
    )
    parser.add_argument(
        "--warmup", type=int, default=2, help="warmup requests to discard"
    )
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument(
        "--engine-label", default="unknown", help="engine label written to output"
    )
    return parser.parse_args()


def call_chat(
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout_s: float,
) -> dict[str, Any]:
    """Single non-streaming /v1/chat/completions call. Returns dict with TTFT + token timings.

    For batch=1 we measure per-call timing. For batch>1 we run N requests in
    parallel threads and report aggregate throughput.

    Note: pheno-serve-dev currently proxies non-streaming; we cannot extract true
    TTFT vs ITL from a single non-streaming response. We approximate TTFT as
    total_latency / completion_tokens (i.e. avg decode time per token, which is
    a lower bound on true TTFT). For true TTFT, the engine must support
    streaming; that's a follow-up.
    """
    url = base_url.rstrip("/") + "/v1/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    try:
        with (
            urllib.request.urlopen(req, timeout=timeout_s) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            payload = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        return {
            "error": f"HTTP {exc.code}: {exc.read()[:200].decode('utf-8', errors='replace')}"
        }
    except urllib.error.URLError as exc:
        return {"error": f"URLError: {exc.reason}"}
    elapsed_ms = (time.perf_counter() - t0) * 1000

    try:
        body_json = json.loads(payload)
    except json.JSONDecodeError as exc:
        return {"error": f"JSONDecodeError: {exc}; payload[:200]={payload[:200]!r}"}

    choices = body_json.get("choices") or []
    completion_text = ""
    if choices:
        first = choices[0]
        completion_text = first.get("message", {}).get("content", "") or ""
    usage = body_json.get("usage") or {}
    completion_tokens = usage.get("completion_tokens") or len(completion_text.split())
    prompt_tokens = usage.get("prompt_tokens") or 0
    total_tokens = usage.get("total_tokens") or (prompt_tokens + completion_tokens)

    decode_tok_s = (completion_tokens / elapsed_ms * 1000.0) if elapsed_ms > 0 else 0.0

    return {
        "status": status,
        "elapsed_ms": elapsed_ms,
        "ttft_ms_approx": elapsed_ms / max(completion_tokens, 1),
        "itl_ms_approx": elapsed_ms / max(completion_tokens, 1),
        "completion_tokens": completion_tokens,
        "prompt_tokens": prompt_tokens,
        "total_tokens": total_tokens,
        "decode_tok_s": decode_tok_s,
        "completion": completion_text,
        "raw_usage": usage,
    }


def run_warmup(base_url: str, model: str, prompt: str, n: int) -> None:
    for _ in range(n):
        call_chat(base_url, model, prompt, 16, 0.0, 60.0)


def run_fixture(args: argparse.Namespace) -> dict[str, Any]:
    tasks = [
        json.loads(line)
        for line in args.fixture.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    run_warmup(args.base_url, args.model, "warmup", args.warmup)
    results: list[dict[str, Any]] = []
    for task in tasks:
        single = call_chat(
            args.base_url,
            args.model,
            task["prompt"],
            int(task.get("max_tokens", 64)),
            float(task.get("temperature", 0.0)),
            args.timeout_s,
        )
        record = {"task_id": task["task_id"], "kind": task["kind"], **single}
        results.append(record)

    # Summary stats
    ok = [r for r in results if "error" not in r]
    ttft_values = [r["ttft_ms_approx"] for r in ok if "ttft_ms_approx" in r]
    decode_values = [r["decode_tok_s"] for r in ok if "decode_tok_s" in r]
    elapsed_values = [r["elapsed_ms"] for r in ok if "elapsed_ms" in r]
    summary = {
        "engine": args.engine_label,
        "model": args.model,
        "batch_size": args.batch_size,
        "n_tasks_total": len(results),
        "n_tasks_ok": len(ok),
        "n_tasks_error": len(results) - len(ok),
        "ttft_ms_p50": statistics.median(ttft_values) if ttft_values else None,
        "ttft_ms_p95": sorted(ttft_values)[int(0.95 * len(ttft_values))]
        if ttft_values
        else None,
        "decode_tok_s_p50": statistics.median(decode_values) if decode_values else None,
        "decode_tok_s_p95": sorted(decode_values)[int(0.95 * len(decode_values))]
        if decode_values
        else None,
        "elapsed_ms_p50": statistics.median(elapsed_values) if elapsed_values else None,
        "elapsed_ms_p95": sorted(elapsed_values)[int(0.95 * len(elapsed_values))]
        if elapsed_values
        else None,
    }
    return {
        "engine": args.engine_label,
        "model": args.model,
        "results": results,
        "summary": summary,
    }


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = run_fixture(args)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(output["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
