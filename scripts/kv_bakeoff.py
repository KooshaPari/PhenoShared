#!/usr/bin/env python3
"""KV/TQ+ bakeoff matrix on burst 2×5090 cloud (Phase 4)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import BENCH_DIR, CONFIG_DIR, PHENO_ROOT, STATE_DIR, TRAINING_DIR


def _expand_env(s: str) -> str:
    if not s:
        return s
    out = os.path.expandvars(
        s.replace("${PHENO_ROOT}", str(PHENO_ROOT)).replace("${HOME}", str(Path.home()))
    )
    if out.startswith("${") and ":-}" in out:
        key, default = out[2:].split(":-", 1)
        default = default.rstrip("}")
        return os.environ.get(key, default)
    return out


def load_config() -> dict[str, Any]:
    raw = yaml.safe_load((CONFIG_DIR / "kv_bakeoff.yaml").read_text(encoding="utf-8"))
    for section in ("model", "trace_suite", "output", "burst"):
        if section in raw and isinstance(raw[section], dict):
            for k, v in raw[section].items():
                if isinstance(v, str):
                    raw[section][k] = _expand_env(v)
    if "output" in raw:
        raw["output"]["results_dir"] = _expand_env(
            raw["output"].get("results_dir", str(BENCH_DIR / "kv_bakeoff"))
        )
        raw["output"]["winner_state"] = _expand_env(
            raw["output"].get("winner_state", str(STATE_DIR / "kv_winner.json"))
        )
    return raw


def load_traces(cfg: dict[str, Any], limit: int) -> list[dict]:
    suite = cfg["trace_suite"]
    root = Path(_expand_env(suite.get("dir", str(TRAINING_DIR))))
    traces = []
    for path in sorted(root.glob(suite.get("glob", "traces_*.jsonl"))):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                traces.append(json.loads(line))
                if len(traces) >= limit:
                    return traces
    return traces


def build_cmd(binary: str, model_path: str, variant: dict[str, Any], prompt: str) -> list[str]:
    cmd = [binary, "-m", model_path, "-n", "128", "--temp", "0.1", "-p", prompt]
    flags = variant.get("llama_flags", "")
    if flags:
        cmd.extend(flags.split())
    ctk = variant.get("ctk")
    ctv = variant.get("ctv")
    if ctk and "-ctk" not in flags:
        cmd.extend(["-ctk", ctk])
    if ctv and "-ctv" not in flags:
        cmd.extend(["-ctv", ctv])
    return cmd


def run_variant(
    variant: dict[str, Any],
    *,
    binary: str,
    model_path: str,
    prompt: str,
    dry_run: bool,
) -> dict[str, Any]:
    result = {
        "variant_id": variant["id"],
        "label": variant.get("label", variant["id"]),
        "timestamp": datetime.now(UTC).isoformat(),
        "dry_run": dry_run,
    }
    cmd = build_cmd(binary, model_path, variant, prompt)
    result["cmd"] = cmd

    if dry_run or not model_path or not Path(model_path).exists():
        result["status"] = "skipped"
        result["reason"] = "dry_run or missing model path"
        result["tok_per_s"] = None
        result["vram_gb"] = None
        result["accepted_steps_per_sec_per_gb"] = None
        return result

    if shutil.which(binary) is None and not Path(binary).exists():
        result["status"] = "skipped"
        result["reason"] = f"binary not found: {binary}"
        return result

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        elapsed = time.perf_counter() - t0
        out = proc.stdout + proc.stderr
        tok_s = None
        for line in out.splitlines():
            if "tokens per second" in line.lower() or "t/s" in line.lower():
                for part in line.replace(",", " ").split():
                    try:
                        v = float(part)
                        if v > 0.5:
                            tok_s = v
                    except ValueError:
                        continue
        # scaffold VRAM estimate from ctx + cache type
        vram_gb = (
            8.0 if variant["id"] == "no_kv" else 6.5 if variant["id"] == "kv8" else 5.0
        )
        accepted_steps = 1.0  # placeholder until trace replay wired
        metric = (accepted_steps / max(elapsed, 0.01)) / max(vram_gb, 0.1)
        result.update(
            {
                "status": "ok" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "elapsed_s": round(elapsed, 2),
                "tok_per_s": tok_s,
                "vram_gb": vram_gb,
                "accepted_steps_per_sec_per_gb": round(metric, 4),
                "output_tail": out[-1000:],
            }
        )
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    return result


def pick_winner(results: list[dict], cfg: dict[str, Any]) -> dict | None:
    ok = [
        r
        for r in results
        if r.get("status") == "ok" and r.get("accepted_steps_per_sec_per_gb")
    ]
    if not ok:
        return None
    return max(ok, key=lambda r: r["accepted_steps_per_sec_per_gb"])


def main() -> None:
    p = argparse.ArgumentParser(description="KV bakeoff matrix (2×5090 burst cloud)")
    p.add_argument(
        "--dry-run", action="store_true", help="Plan matrix without inference"
    )
    p.add_argument(
        "--variant",
        default=None,
        help="Single variant id (no_kv, kv8, kv4, tq_plus, rotor_baseline)",
    )
    p.add_argument(
        "--binary", default=os.environ.get("PHENO_LLAMA_SERVER", "llama-server")
    )
    args = p.parse_args()

    cfg = load_config()
    model_path = _expand_env(cfg["model"].get("path", ""))
    prompt_file = cfg["model"].get("prompt_file", "")
    prompt = "Summarize the following context in 3 bullets. " * 64
    if prompt_file and Path(prompt_file).exists():
        prompt = Path(prompt_file).read_text(encoding="utf-8")[:8000]

    variants = cfg.get("variants", [])
    if args.variant:
        variants = [v for v in variants if v["id"] == args.variant]

    traces = load_traces(cfg, int(cfg["trace_suite"].get("max_traces", 50)))
    print(
        f"Burst: {cfg['burst']['gpu_count']}×{cfg['burst']['gpu']} @ ${cfg['burst']['hourly_usd']}/hr"
    )
    print(f"Traces loaded: {len(traces)} (suite replay scaffold)")

    results = []
    for v in variants:
        print(f"  variant {v['id']}...")
        results.append(
            run_variant(
                v,
                binary=args.binary,
                model_path=model_path,
                prompt=prompt,
                dry_run=args.dry_run,
            )
        )

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(cfg["output"]["results_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"bakeoff_{ts}.json"
    payload = {
        "timestamp": ts,
        "burst": cfg["burst"],
        "trace_count": len(traces),
        "results": results,
    }
    winner = pick_winner(results, cfg)
    if winner:
        payload["winner"] = {
            "variant_id": winner["variant_id"],
            "accepted_steps_per_sec_per_gb": winner["accepted_steps_per_sec_per_gb"],
            "tok_per_s": winner.get("tok_per_s"),
            "vram_gb": winner.get("vram_gb"),
        }
        if not args.dry_run:
            winner_path = Path(cfg["output"]["winner_state"])
            winner_path.parent.mkdir(parents=True, exist_ok=True)
            winner_path.write_text(
                json.dumps(payload["winner"], indent=2), encoding="utf-8"
            )
            print(f"Winner written: {winner_path}")

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    ok = sum(1 for r in results if r.get("status") == "ok")
    skip = sum(1 for r in results if r.get("status") == "skipped")
    print(f"ok={ok} skipped={skip} total={len(results)}")


if __name__ == "__main__":
    main()
