#!/usr/bin/env python3
"""Probe TB2 route matrix: OmniRoute cloud, local llama-server, Main combo."""

from __future__ import annotations

import argparse
import json
import socket
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.harbor_util import omniroute_env
from pheno.paths import CONFIG_DIR, EVAL_RESULTS_DIR


def _tcp_ok(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _probe(url: str, key: str, model: str, timeout: int = 180) -> dict[str, Any]:
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
            "User-Agent": "pheno-harness/1.0 (route probe)",
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


def _host_port(url: str) -> tuple[str, int]:
    from urllib.parse import urlparse

    u = urlparse(url)
    host = u.hostname or "127.0.0.1"
    port = u.port or (443 if u.scheme == "https" else 80)
    return host, port


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    p.add_argument(
        "--timeout", type=int, default=180, help="HTTP probe timeout seconds"
    )
    p.add_argument(
        "--route-kind",
        help="Filter: omniroute_cloud | pheno_serve | local_direct | omniroute_combo",
    )
    args = p.parse_args()

    cfg = yaml.safe_load(
        (CONFIG_DIR / "harbor_tbench_routes.yaml").read_text(encoding="utf-8")
    )
    prov = cfg.get("provider") or {}
    omni = omniroute_env()
    omni_url = (
        prov.get("omniroute_base", "http://127.0.0.1:20128/v1").rstrip("/")
        + "/chat/completions"
    )
    local_key = prov.get("local_api_key", "local-no-key")

    entries = list(cfg.get("models", [])) + list(cfg.get("combo_reference", []))
    if args.route_kind:
        entries = [e for e in entries if e.get("route_kind") == args.route_kind]

    results = {"timestamp": datetime.now(UTC).isoformat(), "models": {}}
    any_ok = False
    for entry in entries:
        mid = entry["id"]
        kind = entry.get("route_kind", "omniroute_cloud")
        if kind in ("local_direct", "pheno_serve"):
            default_base = (
                "http://127.0.0.1:21080/v1"
                if kind == "pheno_serve"
                else "http://127.0.0.1:8080/v1"
            )
            base = entry.get("base_url", default_base).rstrip("/")
            url = base + "/chat/completions"
            api_model = entry.get("api_model", "local")
            host, port = _host_port(base)
            tcp = _tcp_ok(host, port)
            r = (
                _probe(url, local_key, api_model, timeout=args.timeout)
                if tcp
                else {
                    "ok": False,
                    "status": None,
                    "error": f"tcp refused {host}:{port}",
                }
            )
            harbor_model = f"openai/{api_model}"
        elif entry.get("combo"):
            host, port = _host_port(
                prov.get("omniroute_base", "http://127.0.0.1:20128/v1")
            )
            tcp = _tcp_ok(host, port)
            r = (
                _probe(
                    omni_url,
                    omni.get("OPENAI_API_KEY", ""),
                    "Main",
                    timeout=args.timeout,
                )
                if tcp
                else {
                    "ok": False,
                    "status": None,
                    "error": f"tcp refused {host}:{port}",
                }
            )
            harbor_model = "openai/Main"
        else:
            host, port = _host_port(
                prov.get("omniroute_base", "http://127.0.0.1:20128/v1")
            )
            tcp = _tcp_ok(host, port)
            r = (
                _probe(
                    omni_url, omni.get("OPENAI_API_KEY", ""), mid, timeout=args.timeout
                )
                if tcp
                else {
                    "ok": False,
                    "status": None,
                    "error": f"tcp refused {host}:{port}",
                }
            )
            harbor_model = f"openai/{mid}"

        ok = r["ok"]
        if ok:
            any_ok = True
        tcp_label = "tcp=OK" if tcp else "tcp=FAIL"
        http_label = "http=OK" if ok else "http=FAIL"
        results["models"][mid] = {
            "label": entry.get("label", mid),
            "route_kind": kind,
            "routing_policy": entry.get("routing_policy"),
            "tcp_ok": tcp,
            "probe": r,
            "route": kind if ok else None,
            "harbor_model": harbor_model,
        }
        print(
            f"{kind:<16} {entry.get('label', mid):<22} {tcp_label:<8} {http_label:<9} "
            f"route={kind if ok else 'NONE'}"
        )
        if tcp and not ok and r.get("error"):
            print(f"  -> {r['error'][:100]}")

    out = EVAL_RESULTS_DIR / "tbench_route_probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {out} — any route OK: {any_ok}")
    return 0 if any_ok or args.force else 1


if __name__ == "__main__":
    raise SystemExit(main())
