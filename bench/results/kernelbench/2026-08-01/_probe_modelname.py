#!/usr/bin/env python3
"""N12: confirm gateway 404 root cause — model-name passthrough to vLLM."""

import json
import urllib.request
from typing import Any

OUT = {}


def post(url: str, payload: dict[str, Any], timeout: int = 60) -> tuple[int | None, str]:
    req = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with (
            urllib.request.urlopen(req, timeout=timeout) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            return r.status, r.read(2000).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return getattr(e, "code", None), f"{type(e).__name__}: {e}"[:300]


msgs = [{"role": "user", "content": "hi"}]

# vLLM with the alias the gateway sends (expect 404 if name mapping missing)
st, body = post(
    "http://172.28.189.254:19000/v1/chat/completions",
    {"model": "local/lfm2.5-8b-a1b", "messages": msgs, "max_tokens": 4},
)
OUT["vllm_alias_name"] = {"status": st, "body": body}

# vLLM with the raw model id (expect 200)
st, body = post(
    "http://172.28.189.254:19000/v1/chat/completions",
    {"model": "LiquidAI/LFM2.5-8B-A1B", "messages": msgs, "max_tokens": 4},
)
OUT["vllm_raw_name"] = {"status": st, "body": body}

print(json.dumps(OUT, indent=2))
