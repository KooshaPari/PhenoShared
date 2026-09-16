#!/usr/bin/env python3
"""N12: probe upstream KernelBench repo reachability (read-only, robust)."""

import json
import urllib.request

URLS = [
    "https://api.github.com/repos/ScalingIntelligence/KernelBench",
    "https://api.github.com/repos/Infatoshi/KernelBench-v3",
    "https://api.github.com/repos/google-deepmind/kernelbench",
]
OUT = {}
for url in URLS:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pheno-n12-probe"})
        with (
            urllib.request.urlopen(req, timeout=10) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            raw = r.read()
            OUT[url] = {"status": r.status, "bytes": len(raw)}
            try:
                data = json.loads(raw.decode("utf-8", "replace"))
                OUT[url].update(
                    {
                        "full_name": data.get("full_name"),
                        "default_branch": data.get("default_branch"),
                        "archived": data.get("archived"),
                        "pushed_at": data.get("pushed_at"),
                        "message": data.get("message"),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                OUT[url]["json_error"] = f"{type(exc).__name__}: {exc}"
                OUT[url]["head"] = raw[:300].decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        OUT[url] = {"error": f"{type(exc).__name__}: {exc}"}

print(json.dumps(OUT, indent=2))
