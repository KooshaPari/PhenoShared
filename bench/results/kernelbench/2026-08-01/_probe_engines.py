#!/usr/bin/env python3
"""N12: confirm pheno-serve proxy upstream reachability using correct model aliases."""

import json
import urllib.request

OUT = {}

# correct model aliases per /v1/models
for alias in ("local/lfm2.5-8b-a1b", "local/lfm25-1.2b", "local"):
    payload = {
        "model": alias,
        "messages": [{"role": "user", "content": "Reply with the single word: pong"}],
        "max_tokens": 4,
        "temperature": 0.0,
    }
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:21080/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "User-Agent": "pheno-n12-probe",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with (
            urllib.request.urlopen(req, timeout=30) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            OUT[alias] = {
                "status": r.status,
                "body": r.read(3000).decode("utf-8", "replace")[:1500],
            }
    except urllib.error.HTTPError as e:
        OUT[alias] = {
            "status": e.code,
            "body": e.read(2000).decode("utf-8", "replace")[:1000],
        }
    except Exception as e:  # noqa: BLE001
        OUT[alias] = {"error": f"{type(e).__name__}: {e}"}

# readiness endpoint
for path in ("/readyz", "/admin/models", "/admin/routes/resolve"):
    try:
        if path == "/admin/routes/resolve":
            payload = {"model": "local/lfm2.5-8b-a1b"}
            req = urllib.request.Request(
                "http://127.0.0.1:21080" + path,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        else:
            req = urllib.request.Request("http://127.0.0.1:21080" + path, method="GET")
        with (
            urllib.request.urlopen(req, timeout=10) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            OUT[path] = {
                "status": r.status,
                "body": r.read(4000).decode("utf-8", "replace")[:2000],
            }
    except urllib.error.HTTPError as e:
        OUT[path] = {
            "status": e.code,
            "body": e.read(2000).decode("utf-8", "replace")[:1000],
        }
    except Exception as e:  # noqa: BLE001
        OUT[path] = {"error": f"{type(e).__name__}: {e}"}

print(json.dumps(OUT, indent=2))
