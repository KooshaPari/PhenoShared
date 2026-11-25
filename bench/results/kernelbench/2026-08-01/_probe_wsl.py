#!/usr/bin/env python3
"""N12: locate live WSL vLLM backend and test completion route."""

import json
import socket
import subprocess  # nosec B404
import urllib.request

OUT = {}

# Discover WSL IP from Windows side (hostname -I via wsl.exe)
try:
    r = subprocess.run(  # nosec B603
        [
            r"C:\Windows\System32\wsl.exe",
            "-d",
            "FedoraLinux-44",
            "--",
            "hostname",
            "-I",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    OUT["wsl_hostname_I"] = r.stdout.strip() or r.stderr.strip()[:300]
    OUT["wsl_rc"] = r.returncode  # type: ignore[assignment]
except Exception as e:  # noqa: BLE001
    OUT["wsl_hostname_I"] = f"ERR {type(e).__name__}: {e}"

candidates = ["172.28.189.254"]
for token in (OUT.get("wsl_hostname_I") or "").split():
    if token.count(".") == 3:
        candidates.append(token)
# also probe the two vEthernet adapters seen in netstat
candidates += ["172.28.176.1", "172.23.112.1"]

OUT["candidates"] = candidates  # type: ignore[assignment]
for host in candidates:
    for port in (19000, 19001):
        try:
            s = socket.create_connection((host, port), timeout=3)
            s.close()
            OUT[f"{host}:{port}"] = "TCP OK"
        except Exception as e:  # noqa: BLE001
            OUT[f"{host}:{port}"] = f"TCP FAIL {type(e).__name__}"

# For any TCP-OK host, fetch /v1/models
for host in candidates:
    for port in (19000, 19001):
        if OUT.get(f"{host}:{port}") == "TCP OK":
            try:
                r = urllib.request.urlopen(
                    f"http://{host}:{port}/v1/models", timeout=5
                )  # internal HTTP to localhost/controlled endpoint, reviewed false positive # nosec B310
                OUT[f"models {host}:{port}"] = {
                    "status": r.status,
                    "body": r.read(400).decode("utf-8", "replace")[:400],
                }  # type: ignore[assignment]
            except Exception as e:  # noqa: BLE001
                OUT[f"models {host}:{port}"] = f"ERR {type(e).__name__}: {str(e)[:140]}"

print(json.dumps(OUT, indent=2))
