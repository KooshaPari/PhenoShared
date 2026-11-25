#!/usr/bin/env python3
"""N12 probe: enumerate working completion routes on pheno-serve :21080."""

import json
import shutil
import subprocess  # nosec B404
import urllib.request

BASE = "http://127.0.0.1:21080"
OUT = {}

routes = [
    "/v1/completions",
    "/completions",
    "/generate",
    "/v1/chat/completions",
    "/v1/embeddings",
    "/api/v1/chat/completions",
    "/v1/chat/completions",
    "/v1/responses",
]

payloads = [
    {"model": "local/lfm2.5-8b-a1b", "prompt": "say pong", "max_tokens": 4},
    {"model": "lfm2.5-8b-a1b", "prompt": "say pong", "max_tokens": 4},
    {"model": "local/lfm25-1.2b", "prompt": "say pong", "max_tokens": 4},
]

for p in routes:
    for payload in payloads:
        key = f"{p} model={payload['model']}"
        try:
            req = urllib.request.Request(
                BASE + p,
                method="POST",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with (
                urllib.request.urlopen(req, timeout=20) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
            ):
                body = r.read(400).decode("utf-8", "replace")
                OUT[key] = {"status": r.status, "body": body[:300]}
        except Exception as e:  # noqa: BLE001
            OUT[key] = {"error": f"{type(e).__name__}: {e}"[:250]}

# nvidia-smi resolution: try known absolute paths then PATH
smi_candidates = [
    r"C:\Windows\System32\nvidia-smi.exe",
    r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    shutil.which("nvidia-smi"),
]
smi = None
for c in smi_candidates:
    if c and __import__("os").path.exists(c):
        smi = c
        break
if smi:
    r = subprocess.run(  # nosec B603
        [
            smi,
            "--query-gpu=index,name,memory.total,memory.used,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    OUT["nvidia_smi"] = {
        "rc": r.returncode,
        "stdout": r.stdout.strip(),
        "stderr": r.stderr.strip()[:300],
    }
    a = subprocess.run(  # nosec B603
        [
            smi,
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    OUT["compute_apps"] = {
        "rc": a.returncode,
        "stdout": a.stdout.strip(),
        "stderr": a.stderr.strip()[:300],
    }
else:
    OUT["nvidia_smi"] = {"error": "nvidia-smi not found on PATH or known locations"}

print(json.dumps(OUT, indent=2))
