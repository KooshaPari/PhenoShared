#!/usr/bin/env python3
"""Nightly DPO pair export from verifier pass/fail traces (Phase 3)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import CONFIG_DIR, STATE_DIR, TRAINING_DIR
from verifier.harness import VerifierHarness
from verifier.rewards import compute_rewards


def _load_role_config() -> dict[str, Any]:
    path = CONFIG_DIR / "role_lora.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _trace_to_messages(trace: dict[str, Any]) -> list[dict]:
    prompt = (
        trace.get("prompt") or trace.get("request_summary") or trace.get("input") or ""
    )
    response = (
        trace.get("response") or trace.get("completion") or trace.get("output") or ""
    )
    return [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response},
    ]


def build_dpo_pairs(
    traces: list[dict],
    harness: VerifierHarness,
    *,
    pass_threshold: float,
) -> list[dict]:
    """Group traces by prompt; winner = highest reward among passing; loser = lowest failing."""
    by_prompt: dict[str, list[tuple[dict, float, bool]]] = {}
    for trace in traces:
        result = harness.verify_trace(trace)
        reward = compute_rewards(result, pass_threshold=pass_threshold)
        key = (
            trace.get("prompt") or trace.get("request_summary") or trace.get("id") or ""
        )[:512]
        by_prompt.setdefault(key, []).append((trace, reward.total, reward.passed))

    pairs: list[dict] = []
    for _key, scored in by_prompt.items():
        if len(scored) < 2:
            continue
        passed = [s for s in scored if s[2]]
        failed = [s for s in scored if not s[2]]
        if not passed or not failed:
            continue
        chosen = max(passed, key=lambda x: x[1])[0]
        rejected = min(failed, key=lambda x: x[1])[0]
        pairs.append(
            {
                "prompt_messages": _trace_to_messages(chosen)[:1],
                "chosen": _trace_to_messages(chosen)[1]["content"],
                "rejected": _trace_to_messages(rejected)[1]["content"],
                "role": chosen.get("role", "patch"),
                "chosen_reward": max(s[1] for s in passed),
                "rejected_reward": min(s[1] for s in failed),
            }
        )
    return pairs


def main() -> None:
    p = argparse.ArgumentParser(description="Build DPO pairs from verified traces")
    p.add_argument(
        "--glob", default="traces_*.jsonl", help="Trace JSONL glob under training dir"
    )
    p.add_argument("--out-dir", type=Path, default=TRAINING_DIR)
    p.add_argument("--dry-run", action="store_true", help="Print stats only")
    args = p.parse_args()

    role_cfg = _load_role_config()
    rlvr_path = Path(__file__).resolve().parents[1] / "training" / "rlvr_config.yaml"
    rlvr = yaml.safe_load(rlvr_path.read_text(encoding="utf-8"))
    threshold = float(rlvr.get("pass_threshold", 0.75))

    harness = VerifierHarness(rlvr_path)
    traces: list[dict] = []
    for path in sorted(TRAINING_DIR.glob(args.glob)):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                traces.append(json.loads(line))

    if not traces:
        print(f"No traces matching {args.glob} in {TRAINING_DIR}")
        return

    verified = []
    for trace in traces:
        result = harness.verify_trace(trace)
        reward = compute_rewards(result, pass_threshold=threshold)
        rec = {**trace, "verifier": result.to_dict(), "reward": reward.to_dict()}
        verified.append(rec)

    pairs = build_dpo_pairs(traces, harness, pass_threshold=threshold)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    if args.dry_run:
        n_pass = sum(1 for v in verified if v["reward"]["passed"])
        print(f"traces={len(traces)} passed={n_pass} dpo_pairs={len(pairs)}")
        by_role: dict[str, int] = {}
        for pair in pairs:
            r = pair.get("role", "unknown")
            by_role[r] = by_role.get(r, 0) + 1
        print("pairs_by_role:", by_role)
        min_pairs = role_cfg.get("nightly", {}).get("min_pairs_per_role", 32)
        for role, count in by_role.items():
            if count < min_pairs:
                print(f"  WARN {role}: {count} < min_pairs {min_pairs}")
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    verified_path = args.out_dir / f"verified_{ts}.jsonl"
    dpo_path = args.out_dir / f"dpo_pairs_{ts}.jsonl"
    with verified_path.open("w", encoding="utf-8") as f:
        for rec in verified:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with dpo_path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    manifest = {
        "timestamp": ts,
        "traces": len(traces),
        "verified_pass": sum(1 for v in verified if v["reward"]["passed"]),
        "dpo_pairs": len(pairs),
        "verified_path": str(verified_path),
        "dpo_path": str(dpo_path),
    }
    manifest_path = STATE_DIR / f"nightly_dpo_{ts}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
