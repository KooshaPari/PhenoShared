#!/usr/bin/env python3
"""Probe OmniRoute Main / cloud routes before TB2.0 matrix runs."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.harbor_util import fireworks_env, omniroute_env
from pheno.paths import CONFIG_DIR, EVAL_RESULTS_DIR


def _probe(url: str, key: str, model: str, timeout: int = 120) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "ok"}],
            "max_tokens": 3,
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "pheno-harness/1.0 (OmniRoute probe)",
        },
    )
    try:
        with (
            urllib.request.urlopen(req, timeout=timeout) as resp  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            return {"ok": resp.status == 200, "status": resp.status, "error": None}
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")[:200]
        return {"ok": False, "status": e.code, "error": err}
    except Exception as e:
        return {"ok": False, "status": None, "error": str(e)[:200]}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    cfg = yaml.safe_load(
        (CONFIG_DIR / "harbor_tbench_models.yaml").read_text(encoding="utf-8")
    )
    prov = cfg.get("provider", {})
    primary = prov.get("primary", "omniroute_main")
    omni = omniroute_env()
    omni_url = (
        prov.get("omniroute_base", "http://127.0.0.1:20128/v1").rstrip("/")
        + "/chat/completions"
    )
    fw = fireworks_env(
        prov.get("credential_id_firepass_sunset", "fireworks-ai-firepass")
    )
    fw_url = prov.get("direct_base", "https://api.fireworks.ai/inference/v1")
    if fw_url and not fw_url.startswith("http"):
        fw_url = "https://api.fireworks.ai/inference/v1"
    fw_url = fw_url.rstrip("/") + "/chat/completions"

    results = {
        "timestamp": datetime.now(UTC).isoformat(),
        "provider": primary,
        "models": {},
    }
    any_ok = False

    if primary == "omniroute_main":
        for entry in cfg.get("models", []):
            mid = entry["id"]
            r_omni = _probe(omni_url, omni.get("OPENAI_API_KEY", ""), mid)
            use = "omniroute_main" if r_omni["ok"] else None
            if use:
                any_ok = True
            results["models"][mid] = {
                "label": entry.get("label", mid),
                "omniroute": r_omni,
                "route": use,
                "harbor_model": f"openai/{mid}",
            }
            om = "OK" if r_omni["ok"] else "FAIL"
            print(f"{entry.get('label', mid):<20} omni={om:<4} route={use or 'NONE'}")
        for entry in cfg.get("models_sunset", []):
            results["models"][entry["id"]] = {
                "label": entry.get("label"),
                "sunset": True,
                "reason": entry.get("reason", "sunset"),
                "route": None,
            }
    else:
        # Legacy direct Fireworks path
        for entry in cfg.get("models", []):
            mid = entry["id"]
            direct = entry.get("direct_model", mid)
            r_direct = _probe(fw_url, fw.get("FIREWORKS_AI_API_KEY", ""), direct)
            use = "direct" if r_direct["ok"] else None
            if use:
                any_ok = True
            results["models"][mid] = {
                "label": entry.get("label", mid),
                "direct": r_direct,
                "route": use,
            }
            print(
                f"{entry.get('label', mid):<20} direct={'OK' if r_direct['ok'] else 'FAIL':<4} route={use or 'NONE'}"
            )

    out = EVAL_RESULTS_DIR / "tbench_model_probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {out} — any route OK: {any_ok}")
    return 0 if any_ok or args.force else 1


if __name__ == "__main__":
    raise SystemExit(main())
