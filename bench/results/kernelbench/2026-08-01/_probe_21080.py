#!/usr/bin/env python3
"""N12 probe: check pheno-serve (21080) OpenAI-compat endpoints and GPU state."""

import json
import subprocess  # nosec B404
import urllib.request

OUT = {}

# --- Port-level probes -----------------------------------------------------
for path in ("/v1/models", "/health", "/v1/chat/completions", "/"):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:21080" + path,
            headers={"User-Agent": "pheno-n12-probe"},
        )
        with (
            urllib.request.urlopen(req, timeout=6) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            body = r.read(6000)
            text = body.decode("utf-8", "replace")
            OUT[path] = {"status": r.status, "body": text[:1000]}
    except Exception as e:  # noqa: BLE001
        OUT[path] = {"error": f"{type(e).__name__}: {e}"}

# --- Actual chat completion (tiny) -----------------------------------------
tiny_payload = {
    "model": "local",
    "messages": [{"role": "user", "content": "Reply with the single word: pong"}],
    "max_tokens": 8,
    "temperature": 0.0,
}
try:
    req = urllib.request.Request(
        "http://127.0.0.1:21080/v1/chat/completions",
        data=json.dumps(tiny_payload).encode("utf-8"),
        headers={"User-Agent": "pheno-n12-probe", "Content-Type": "application/json"},
        method="POST",
    )
    with (
        urllib.request.urlopen(req, timeout=60) as r  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        body = r.read(8000).decode("utf-8", "replace")
        OUT["chat_completion"] = {"status": r.status, "body": body[:2000]}
except Exception as e:  # noqa: BLE001
    OUT["chat_completion"] = {"error": f"{type(e).__name__}: {e}"}

# --- GPU state via nvidia-smi ----------------------------------------------
try:
    smi = subprocess.run(  # nosec B603 B607
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.total,memory.used,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    OUT["nvidia_smi"] = {
        "rc": smi.returncode,
        "stdout": smi.stdout.strip(),
        "stderr": smi.stderr.strip()[:500],
    }
except Exception as e:  # noqa: BLE001
    OUT["nvidia_smi"] = {"error": f"{type(e).__name__}: {e}"}

print(json.dumps(OUT, indent=2))
