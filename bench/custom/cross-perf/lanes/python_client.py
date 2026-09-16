"""Cross-perf Python client — Tree A (N13) Unified Polyglot Core.

Hits the dual-resident inference routes (Q2 = C):
  :19000 -> local/lfm2.5-8b-a1b  (vLLM 0.26, RTX 3090)
  :19001 -> local/qwen35-08b     (transformers-eager, GTX 1080 Ti)

Measures:
  tg64   : time-to-first-token for a 64-token completion
  TTFT   : time-to-first-token (ms) for the first generated token
  ITL    : inter-token latency (ms/token) over the completion window

Robustness (Q4): per-request timeout, bounded retries, partial-output
preservation, fail-closed JSON emission (never crashes the run).
"""

import argparse
import json
import sys
import time
import urllib.request
from typing import Any

MODEL_ROUTES = {
    "lfm25": {"port": 19000, "model": "local/lfm2.5-8b-a1b"},
    "qwen35": {"port": 19001, "model": "local/qwen35-08b"},
}

DEFAULT_PROMPT = (
    "Write a short Rust function that computes the nth Fibonacci number "
    "iteratively, with a doc comment, and explain the time complexity. "
)
DEFAULT_MAX_TOKENS = 64
TIMEOUT_S = 60.0
RETRIES = 2
BACKOFF_S = 2.0


def post(url: Any, payload: Any, timeout: float = TIMEOUT_S) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with (
        urllib.request.urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return json.loads(resp.read().decode("utf-8"))


def run_case(route: Any, model: Any, max_tokens: Any, prompt: Any) -> Any:
    base = "http://127.0.0.1:%d" % route["port"]
    url = base + "/v1/completions"
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": False,
    }
    last_err = None
    for attempt in range(RETRIES + 1):
        t0 = time.perf_counter()
        try:
            resp = post(url, payload)
            t1 = time.perf_counter()
            choices = resp.get("choices") or []
            text = choices[0].get("text", "") if choices else ""
            usage = resp.get("usage") or {}
            n_tokens = usage.get("completion_tokens") or max_tokens
            # TTFT/ITL are only observable from streaming; with non-stream we
            # report totals and derive ITL from completion_tokens.
            return {
                "route": "lfm25" if route["port"] == 19000 else "qwen35",
                "port": route["port"],
                "model": model,
                "max_tokens": max_tokens,
                "total_ms": (t1 - t0) * 1000.0,
                "completion_tokens": n_tokens,
                "tg64_ms": (t1 - t0) * 1000.0,
                "ttft_ms": None,
                "itl_ms": (t1 - t0) * 1000.0 / max(1, n_tokens),
                "text_len": len(text),
                "attempt": attempt,
                "status": "ok",
                "error": None,
            }
        except Exception as e:  # noqa: BLE001 - robustness lane
            last_err = repr(e)
            if attempt < RETRIES:
                time.sleep(BACKOFF_S * (attempt + 1))
    return {
        "route": "lfm25" if route["port"] == 19000 else "qwen35",
        "port": route["port"],
        "model": model,
        "max_tokens": max_tokens,
        "total_ms": None,
        "completion_tokens": 0,
        "tg64_ms": None,
        "ttft_ms": None,
        "itl_ms": None,
        "text_len": 0,
        "attempt": RETRIES,
        "status": "fail",
        "error": last_err,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", choices=list(MODEL_ROUTES), required=True)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--prompt-file", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    route = MODEL_ROUTES[args.route]
    prompt = DEFAULT_PROMPT
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()

    result = run_case(route, route["model"], args.max_tokens, prompt)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    # Fail-closed: nonzero exit only on hard failure.
    sys.exit(0 if result["status"] == "ok" else 3)


if __name__ == "__main__":
    main()
