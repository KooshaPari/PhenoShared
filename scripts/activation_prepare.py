#!/usr/bin/env python3
"""Activation-edit prep: abliteration / steering status and eval gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR, EVAL_RESULTS_DIR


def _load_policy() -> dict[str, Any]:
    return yaml.safe_load(
        (CONFIG_DIR / "activation_edit_policy.yaml").read_text(encoding="utf-8")
    )


def _load_gate() -> dict[str, Any]:
    return yaml.safe_load(
        (CONFIG_DIR / "risky_action_gate.yaml").read_text(encoding="utf-8")
    )


def cmd_list() -> int:
    pol = _load_policy()
    print("Activation edit methods (optional Q-axis):")
    for key, m in pol.get("methods", {}).items():
        hyp = (m.get("quality_hypothesis") or "")[:70].replace("\u2192", "->")
        print(f"  [{m.get('id', key)}] risk={m.get('safety_risk')} - {hyp}")
    print("\nCandidates:")
    for c in pol.get("candidates", []):
        print(f"  {c['model_id']}: {c.get('status')} -> {c.get('method_order')}")
    print(f"\nMandatory gate: {pol.get('risky_action_gate')}")
    return 0


def cmd_check(model_id: str) -> int:
    pol = _load_policy()
    gate = _load_gate()
    rec = next(
        (c for c in pol.get("candidates", []) if c["model_id"] == model_id), None
    )
    if not rec:
        print(f"Unknown activation-edit candidate: {model_id}")
        return 1

    print(f"Model: {model_id}")
    print(f"  Status: {rec.get('status')}")
    print(f"  Method order: {rec.get('method_order')}")
    print(f"  Notes: {rec.get('notes', '')}")
    print(f"\n  Risky action gate enabled: {gate.get('enabled', True)}")
    print(f"  Policy: {gate.get('policy_statement', '').strip()[:120]}...")

    if rec.get("status") == "defer_until_riy_ptq":
        print("\n  BLOCKED: complete REAP/RIY + PTQ first (moe_prepare.py)")
        return 2

    print("\n  Before abliteration/steering export:")
    for step in pol.get("eval_protocol", {}).get("before_promotion", []):
        print(f"    - {step}")
    print("\n  Reject if:")
    for r in pol.get("eval_protocol", {}).get("reject_if", []):
        print(f"    - {r}")
    return 0


def cmd_status() -> int:
    out = EVAL_RESULTS_DIR / "activation_edit_status.json"
    pol = _load_policy()
    payload = {
        "policy": "activation_edit_policy.yaml",
        "risky_action_gate": "risky_action_gate.yaml",
        "candidates": pol.get("candidates", []),
        "applied": [],
        "note": "No activation edits applied yet — run steer micro-eval before export",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Activation edit (abliteration) prep gates")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List methods and candidates")
    c = sub.add_parser("check", help="Check model readiness")
    c.add_argument("--model", required=True)
    sub.add_parser("status", help="Write eval/results/activation_edit_status.json")
    args = p.parse_args()
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "check":
        return cmd_check(args.model)
    if args.cmd == "status":
        return cmd_status()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
