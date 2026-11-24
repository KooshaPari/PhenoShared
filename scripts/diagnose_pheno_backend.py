#!/usr/bin/env python3
"""Diagnose which API mode a configured local backend supports.

Default mode checks lightweight health/model endpoints and method availability.
It does not request text generation unless --completion is passed.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR


def _tcp(base_url: str, timeout: float) -> dict[str, Any]:
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}


def _request(method: str, url: str, payload: dict | None, timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with (
            urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            body = resp.read(500).decode("utf-8", errors="replace")
            return {"ok": True, "status": resp.status, "body_sample": body}
    except HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "body_sample": body}
    except (URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _profile(alias: str) -> dict[str, Any]:
    cfg = (
        yaml.safe_load((CONFIG_DIR / "pheno_serve.yaml").read_text(encoding="utf-8"))
        or {}
    )
    profiles = cfg.get("profiles") or {}
    if alias not in profiles:
        raise SystemExit(f"unknown alias {alias}; known: {', '.join(sorted(profiles))}")
    return profiles[alias]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose pheno-serve backend API mode"
    )
    parser.add_argument("--alias", default="local/qwen35-08b")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument(
        "--completion", action="store_true", help="Also send tiny completion requests"
    )
    args = parser.parse_args()

    profile = _profile(args.alias)
    base = str(profile.get("base_url") or "").rstrip("/")
    legacy = str(profile.get("legacy_completion_url") or "")
    payload_chat = {
        "model": args.alias,
        "messages": [{"role": "user", "content": "Say ok."}],
        "max_tokens": 2,
        "temperature": 0,
    }
    payload_completion = {
        "model": args.alias,
        "prompt": "Say ok.",
        "max_tokens": 2,
        "temperature": 0,
    }
    result = {
        "alias": args.alias,
        "engine": profile.get("engine"),
        "configured_backend_mode": profile.get("backend_mode", "auto"),
        "base_url": base,
        "tcp": _tcp(base, args.timeout)
        if base
        else {"ok": False, "reason": "no base_url"},
        "checks": {},
    }
    if base:
        result["checks"]["GET /v1/models"] = _request(
            "GET", base + "/models", None, args.timeout
        )
        if args.completion:
            result["checks"]["POST /v1/chat/completions"] = _request(
                "POST", base + "/chat/completions", payload_chat, args.timeout
            )
            result["checks"]["POST /v1/completions"] = _request(
                "POST", base + "/completions", payload_completion, args.timeout
            )
    if legacy and args.completion:
        result["checks"]["POST legacy /completion"] = _request(
            "POST", legacy, {"prompt": "Say ok.", "n_predict": 2}, args.timeout
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
