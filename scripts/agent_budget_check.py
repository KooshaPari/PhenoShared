#!/usr/bin/env python3
"""N19 — agent budget check (Forward DAG v2 §4.4).
Enforces per-session token cap from config/agent_model_routing_2026-07.yaml.
Usage: python scripts/agent_budget_check.py --tokens 123456
Exit 0 = under cap, 2 = warn (80%), 3 = over cap.
"""

import argparse
import sys
from pathlib import Path

import yaml

CFG = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "agent_model_routing_2026-07.yaml"
)


def load_cap():
    try:
        return int(yaml.safe_load(CFG.read_text())["budget"]["per_session_cap_tokens"])
    except Exception:
        return 600_000_000


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--tokens", type=int, required=True, help="tokens consumed this session"
    )
    p.add_argument("--cap", type=int, default=None, help="override cap")
    args = p.parse_args()
    cap = args.cap or load_cap()
    pct = args.tokens / cap * 100 if cap else 0
    if pct >= 100:
        print(f"OVER cap: {args.tokens} / {cap} ({pct:.1f}%)")
        sys.exit(3)
    if pct >= 80:
        print(f"WARN cap: {args.tokens} / {cap} ({pct:.1f}%)")
        sys.exit(2)
    print(f"OK: {args.tokens} / {cap} ({pct:.1f}%)")
    sys.exit(0)


if __name__ == "__main__":
    main()
