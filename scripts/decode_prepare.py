#!/usr/bin/env python3
"""Decode acceleration prep: DFlash, speculative, diffusion-draft status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR, EVAL_RESULTS_DIR


def _load_matrix() -> dict[str, Any]:
    return yaml.safe_load(
        (CONFIG_DIR / "decode_acceleration_matrix.yaml").read_text(encoding="utf-8")
    )


def _dflash_map(matrix: dict[str, Any]) -> dict[str, dict]:
    return {row["target_id"]: row for row in matrix.get("dflash_checkpoints", [])}


def cmd_list() -> int:
    m = _load_matrix()
    print("Decode acceleration categories:")
    for cat, body in m.get("categories", {}).items():
        print(f"\n  [{cat}]")
        for _key, method in (body.get("methods") or {}).items():
            mid = method.get("id", _key)
            status = method.get("status", "?")
            print(f"    - {mid} ({status})")
    print("\nDFlash target map:")
    for row in m.get("dflash_checkpoints", []):
        proxy = " proxy" if row.get("proxy") else ""
        dflash = row.get("dflash_hf") or "MISSING"
        print(f"  {row['target_id']}{proxy}: {dflash}")
    return 0


def cmd_check(target: str, method: str) -> int:
    m = _load_matrix()
    row = _dflash_map(m).get(target)
    if method == "dflash":
        if not row:
            print(f"No DFlash mapping for target: {target}")
            return 1
        print(f"Target: {target}")
        print(f"  Target HF: {row.get('target_hf')}")
        print(f"  DFlash HF: {row.get('dflash_hf') or 'NONE — train or wait'}")
        if row.get("proxy"):
            print(
                "  WARNING: using proxy DFlash ckpt — train target-specific draft for production"
            )
        if row.get("requires"):
            print(f"  Requires first: {row['requires']}")
        gates = m.get("eval_gates", {}).get("before_promotion", [])
        print("\n  Promotion gates:")
        for g in gates:
            print(f"    - {g}")
        return 0 if row.get("dflash_hf") else 2

    # generic method lookup
    for body in m.get("categories", {}).values():
        for _key, rec in (body.get("methods") or {}).items():
            if rec.get("id") == method or _key == method:
                print(f"Method: {rec.get('id', _key)}")
                print(f"  Status: {rec.get('status')}")
                print(f"  Runners: {rec.get('runner', [])}")
                print(f"  Notes: {rec.get('notes', '')[:200]}")
                return 0
    print(f"Unknown method: {method}")
    return 1


def cmd_status() -> int:
    m = _load_matrix()
    out = EVAL_RESULTS_DIR / "decode_acceleration_status.json"
    payload = {
        "matrix": "decode_acceleration_matrix.yaml",
        "dflash_checkpoints": m.get("dflash_checkpoints", []),
        "first_sweep": m.get("first_sweep", {}),
        "applied": [],
        "note": "No DFlash server profiles applied yet — run first_sweep on vLLM nightly",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Decode acceleration matrix (DFlash, speculative, SSD)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List methods and DFlash mappings")
    c = sub.add_parser("check", help="Check target+method readiness")
    c.add_argument("--target", required=True)
    c.add_argument("--method", default="dflash")
    sub.add_parser("status", help="Write eval/results/decode_acceleration_status.json")
    args = p.parse_args()
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "check":
        return cmd_check(args.target, args.method)
    if args.cmd == "status":
        return cmd_status()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
