#!/usr/bin/env python3
"""Benchmark vLLM inference across WSL distros on RTX 3090 Ti."""

import json
import sys
import time
import urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
MODEL = "Qwen/Qwen3.5-0.8B"
URL = f"http://127.0.0.1:{PORT}"

PAYLOADS = [
    {
        "label": "short",
        "messages": [{"role": "user", "content": "Say hello in exactly 5 words."}],
        "max_tokens": 20,
    },
    {
        "label": "medium",
        "messages": [
            {
                "role": "user",
                "content": "Explain what a transformer model is in 3 sentences.",
            }
        ],
        "max_tokens": 100,
    },
    {
        "label": "long",
        "messages": [
            {
                "role": "user",
                "content": "Write a detailed comparison of Python vs Rust for systems programming, covering memory safety, performance, ecosystem, and learning curve.",
            }
        ],
        "max_tokens": 500,
    },
    {
        "label": "reasoning",
        "messages": [
            {
                "role": "user",
                "content": "What is 137 * 29? Show your work step by step.",
            }
        ],
        "max_tokens": 200,
    },
]


def chat_completion(payload):
    body = json.dumps(
        {
            "model": MODEL,
            "messages": payload["messages"],
            "max_tokens": payload["max_tokens"],
            "temperature": 0.0,
        }
    ).encode()
    req = urllib.request.Request(
        f"{URL}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    with (
        urllib.request.urlopen(req, timeout=300) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        data = json.loads(resp.read())
    elapsed = time.perf_counter() - t0
    usage = data.get("usage", {})
    content = data["choices"][0]["message"]["content"]
    return {
        "elapsed_s": round(elapsed, 3),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "tokens_per_s": round(usage.get("completion_tokens", 0) / elapsed, 1)
        if elapsed > 0
        else 0,
        "content_preview": content[:80],
    }


# Warmup
print(f"Benchmarking vLLM at {URL} with {MODEL}...")
try:
    urllib.request.urlopen(
        f"{URL}/v1/models", timeout=5
    )  # internal HTTP to localhost/controlled endpoint, reviewed false positive # nosec B310
except Exception as e:
    print(f"ERROR: Server not reachable at {URL}: {e}")
    sys.exit(1)

# Warmup request
chat_completion(PAYLOADS[0])
print("Warmup done.\n")

results = []
for p in PAYLOADS:
    r = chat_completion(p)
    r["label"] = p["label"]
    results.append(r)
    print(
        f"  {p['label']:12s}  {r['elapsed_s']:.3f}s  {r['completion_tokens']:3d} tokens  {r['tokens_per_s']:.1f} tok/s  | {r['content_preview']}"
    )

# Summary
total_tokens = sum(r["completion_tokens"] for r in results)
total_time = sum(r["elapsed_s"] for r in results)
avg_tps = total_tokens / total_time if total_time > 0 else 0
print(
    f"\n  TOTAL: {total_tokens} tokens in {total_time:.2f}s = {avg_tps:.1f} tok/s avg"
)
print(
    json.dumps(
        {
            "results": results,
            "total_tokens": total_tokens,
            "total_time_s": round(total_time, 2),
            "avg_tokens_per_s": round(avg_tps, 1),
        }
    )
)
