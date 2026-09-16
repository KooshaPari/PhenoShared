#!/usr/bin/env python3
"""Probe pheno-serve-dev profile endpoints without launching engines."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR


def _tcp_probe(base_url: str, timeout: float) -> dict[str, Any]:
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe pheno-serve-dev config")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg_path = CONFIG_DIR / "pheno_serve.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    profiles = cfg.get("profiles") or {}
    rows = []
    for alias, profile in profiles.items():
        base_url = profile.get("base_url")
        row = {
            "alias": alias,
            "engine": profile.get("engine"),
            "status": profile.get("status", "active"),
            "base_url": base_url,
        }
        if base_url:
            row["tcp"] = _tcp_probe(str(base_url), args.timeout)
        else:
            row["tcp"] = {"ok": False, "reason": "no base_url"}
        rows.append(row)

    out = {
        "server": cfg.get("server", {}),
        "profiles": rows,
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"pheno-serve config: {cfg_path}")
        for row in rows:
            tcp = row["tcp"]
            state = "up" if tcp.get("ok") else "down"
            print(
                f"{row['alias']:<28} {row['engine']:<14} {state:<5} {row.get('base_url')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
