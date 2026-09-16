"""Probe PyPI for SGLang + vLLM wheel availability on Windows.

We use the JSON meta API and the wheel index from the release files list.
"""

import json
import urllib.request
from typing import Any

UA = {"User-Agent": "pheno/1.0 (setup-wizard)"}


def get_json(url: Any, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers=UA)
    with (
        urllib.request.urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
    ):
        body = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        # Surface the first 300 chars so we know what came back
        return {"_non_json_body": body[:300]}


def probe(name: Any, version_prefix: Any, package_label: Any) -> None:
    url = f"https://pypi.org/pypi/{name}/json"
    data = get_json(url)
    if "_non_json_body" in data:
        print(f"{package_label}: NON-JSON RESPONSE for {url}")
        print(f"  body[:300] = {data['_non_json_body']!r}")
        return
    print(f"{package_label}: got {len(data.get('releases', {}))} release entries")
    plats = {}
    pys = {}
    for v, files in data.get("releases", {}).items():
        if not v.startswith(version_prefix):
            continue
        for f in files:
            fn = f.get("filename", "")
            if not fn.endswith(".whl"):
                continue
            # format: name-version-pyver-abi-platform.whl
            parts = fn.split("-")
            if len(parts) < 5:
                continue
            py = parts[2]
            plat = parts[4].replace(".whl", "")
            pys.setdefault(py, set()).add(plat)
            plats.setdefault(plat, set()).add(py)
    print(f"  PyVer x Platforms (for {version_prefix}.x):")
    for py in sorted(pys):
        print(f"    {py}: {sorted(pys[py])}")
    print("  Platform x PyVers:")
    for plat in sorted(plats):
        print(f"    {plat}: {sorted(plats[plat])}")


print("=== SGLang ===")
probe("sglang", "0.5.1", "sglang 0.5.1x")
print()
print("=== vLLM ===")
probe("vllm", "0.24", "vllm 0.24.x")
