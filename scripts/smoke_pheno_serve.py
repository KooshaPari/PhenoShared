#!/usr/bin/env python3
"""Smoke test pheno-serve-dev without mutating repo state."""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.request import Request, urlopen


def _get(url: str) -> dict[str, Any]:
    with (
        urlopen(url, timeout=10) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return json.loads(resp.read().decode("utf-8"))


def _post(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with (
        urlopen(req, timeout=120) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test pheno-serve-dev")
    parser.add_argument("--base-url", default="http://127.0.0.1:21080")
    parser.add_argument("--model", default="local/qwen35-08b")
    parser.add_argument("--skip-completion", action="store_true")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    health = _get(base + "/healthz")
    models = _get(base + "/v1/models")
    completion = None
    if not args.skip_completion:
        completion = _post(
            base + "/v1/chat/completions",
            {
                "model": args.model,
                "messages": [
                    {"role": "user", "content": "Reply with exactly: pheno-serve-ok"}
                ],
                "temperature": 0,
                "max_tokens": 16,
            },
            headers={
                "X-Pheno-Run-Id": "smoke",
                "X-Pheno-Lane": "smoke",
                "X-Pheno-Role": "probe",
                "X-Pheno-Route-Kind": "pheno_serve",
                "X-Pheno-Eval-Suite": "smoke",
            },
        )
    print(
        json.dumps(
            {"health": health, "models": models, "completion": completion}, indent=2
        )[:4000]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
