#!/usr/bin/env python3
"""cross-perf serving probe: POST to the :21080 gateway (model=local/qwen35-08b,
LIVE on the GTX 1080 Ti), max_tokens=8.

The gateway does NOT support SSE streaming (connection is closed on stream:true),
so TTFT/ITL are derived from the non-streaming total latency using the repo
convention `ttft_or_itl_from_nonstreaming_total_latency`
(pheno/capture_evidence_envelope.py). tg64 follows the llama-bench generation-
throughput convention (tok/s) computed at the measured completion length.

Emits one JSON object on stdout:
  {calls: N, per_call: [...], median: {wall_ms, ttft_ms, itl_ms, tg64_tok_s,
   completion_tokens, server_elapsed_ms}, model, endpoint, max_tokens,
   measurement_quality}
"""

import json
import statistics
import time
import urllib.request
from typing import Any

ENDPOINT = "http://127.0.0.1:21080/v1/chat/completions"
MODEL = "local/qwen35-08b"
PROMPT = "Reply with exactly: pong"
MAX_TOKENS = 8
CALLS = 5


def post_once() -> Any:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    with (
        urllib.request.urlopen(req, timeout=120) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        raw = r.read().decode("utf-8", "replace")
        wall_ms = (time.perf_counter() - t0) * 1000.0
        status = r.status
    data = json.loads(raw)
    usage = data.get("usage", {})
    pheno = data.get("pheno", {})
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    server_elapsed_s = float(pheno.get("elapsed_seconds", wall_ms / 1000.0) or 0.0)
    server_elapsed_ms = server_elapsed_s * 1000.0
    # Non-streaming proxies (gateway does not stream): TTFT ~= total latency,
    # ITL ~= total latency / completion_tokens.
    ttft_ms = server_elapsed_ms
    itl_ms = server_elapsed_ms / completion_tokens if completion_tokens > 0 else None
    tg64_tok_s = completion_tokens / server_elapsed_s if server_elapsed_s > 0 else None
    return {
        "status": status,
        "wall_ms": round(wall_ms, 2),
        "server_elapsed_ms": round(server_elapsed_ms, 2),
        "ttft_ms": round(ttft_ms, 2),
        "itl_ms": round(itl_ms, 2) if itl_ms is not None else None,
        "tg64_tok_s": round(tg64_tok_s, 2) if tg64_tok_s is not None else None,
        "completion_tokens": completion_tokens,
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion": data["choices"][0]["message"]["content"],
        "finish_reason": data["choices"][0].get("finish_reason"),
        "model_served": data.get("model"),
    }


def median(vals: Any) -> Any:
    real = [v for v in vals if v is not None]
    return round(statistics.median(real), 2) if real else None


def main() -> None:
    per_call = []
    for _ in range(CALLS):
        try:
            per_call.append(post_once())
        except Exception as exc:  # noqa: BLE001
            per_call.append({"error": f"{type(exc).__name__}: {exc}"[:300]})
        time.sleep(0.2)
    ok = [c for c in per_call if "error" not in c]
    out = {
        "model": MODEL,
        "endpoint": ENDPOINT,
        "max_tokens": MAX_TOKENS,
        "calls": len(per_call),
        "successful_calls": len(ok),
        "measurement_quality": "nonstreaming_total_latency_proxy",
        "per_call": per_call,
    }
    if ok:
        out["median"] = {
            "wall_ms": median([c["wall_ms"] for c in ok]),
            "server_elapsed_ms": median([c["server_elapsed_ms"] for c in ok]),
            "ttft_ms": median([c["ttft_ms"] for c in ok]),
            "itl_ms": median([c["itl_ms"] for c in ok]),
            "tg64_tok_s": median([c["tg64_tok_s"] for c in ok]),
            "completion_tokens": median([c["completion_tokens"] for c in ok]),
            "prompt_tokens": median([c["prompt_tokens"] for c in ok]),
        }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
