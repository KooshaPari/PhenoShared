#!/usr/bin/env python3
"""N12: verify vLLM backend absence on canonical ports + record topology."""

import json
import urllib.request

OUT = {}
ports = [19000, 19001, 47984, 47989, 47990, 48010, 8081, 21080]
for port in ports:
    for path in ["/health", "/v1/models"]:
        try:
            r = urllib.request.urlopen(
                f"http://127.0.0.1:{port}{path}", timeout=4
            )  # internal HTTP to localhost/controlled endpoint, reviewed false positive # nosec B310
            OUT[f"{port}{path}"] = {
                "status": r.status,
                "body": r.read(250).decode("utf-8", "replace")[:250],
            }
        except Exception as e:  # noqa: BLE001
            OUT[f"{port}{path}"] = {"error": f"{type(e).__name__}: {str(e)[:140]}"}

# Confirm what owns 47984 (should be sunshine, not vllm)
import subprocess  # nosec B404

r = subprocess.run(  # nosec B603
    [r"C:\Windows\System32\netstat.exe", "-ano"],
    capture_output=True,
    text=True,
    timeout=30,
)
lines = [
    l.strip()
    for l in r.stdout.splitlines()
    if ":47984" in l or ":19000" in l or ":19001" in l or ":21080" in l
]
OUT["netstat_hits"] = lines[:20]  # type: ignore[assignment]

print(json.dumps(OUT, indent=2))
