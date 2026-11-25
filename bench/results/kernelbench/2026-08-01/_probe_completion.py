#!/usr/bin/env python3
"""N12: re-test pheno-serve :21080 completion path now that WSL vLLM is confirmed up."""

import json
import urllib.request
from typing import Any

OUT = {}


def post(url: str, payload: dict[str, Any], timeout: int = 90) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with (
        urllib.request.urlopen(req, timeout=timeout) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return r.status, r.read(6000).decode("utf-8", "replace")


# 1. Direct to WSL vLLM
try:
    st, body = post(
        "http://172.28.189.254:19000/v1/chat/completions",
        {
            "model": "LiquidAI/LFM2.5-8B-A1B",
            "messages": [{"role": "user", "content": "Reply with exactly: pong"}],
            "max_tokens": 8,
            "temperature": 0.0,
        },
    )
    OUT["direct_wsl_chat"] = {"status": st, "body": body[:800]}
except Exception as e:  # noqa: BLE001
    OUT["direct_wsl_chat"] = {"error": f"{type(e).__name__}: {e}"[:300]}

# 2. Through gateway (as KernelBench harness would)
try:
    st, body = post(
        "http://127.0.0.1:21080/v1/chat/completions",
        {
            "model": "local/lfm2.5-8b-a1b",
            "messages": [{"role": "user", "content": "Reply with exactly: pong"}],
            "max_tokens": 8,
            "temperature": 0.0,
        },
    )
    OUT["gateway_chat"] = {"status": st, "body": body[:800]}
except Exception as e:  # noqa: BLE001
    OUT["gateway_chat"] = {"error": f"{type(e).__name__}: {e}"[:300]}

# 3. admin route resolution
try:
    st, body = post(
        "http://127.0.0.1:21080/admin/routes/resolve",
        {"model": "local/lfm2.5-8b-a1b"},
    )
    OUT["resolve"] = {"status": st, "body": body[:500]}
except Exception as e:  # noqa: BLE001
    OUT["resolve"] = {"error": f"{type(e).__name__}: {e}"[:300]}

print(json.dumps(OUT, indent=2))
