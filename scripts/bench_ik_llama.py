#!/usr/bin/env python3
"""ik_llama / llama-server baseline bench for locked local models on 3090 Ti."""

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

from pheno.paths import BENCH_DIR, CONFIG_DIR

PROMPT = (
    "Write a Python function merge_sorted(a, b) that merges two sorted lists. "
    "Include docstring and O(n) complexity note. " * 8
)


def _expand_env(s: str) -> str:
    if not s:
        return s
    out = os.path.expandvars(s)
    if out.startswith("${") and ":-}" in out:
        key, default = out[2:].split(":-", 1)
        default = default.rstrip("}")
        return os.environ.get(key, default)
    return out


def load_models() -> list[dict]:
    raw = yaml.safe_load((CONFIG_DIR / "models.yaml").read_text(encoding="utf-8"))
    cfg = raw.get("llama_server", {})
    bench = []
    for b in raw.get("bench_models", []):
        tier_path = b["tier"].split(".")
        node = raw["tiers"]
        for k in tier_path:
            node = node[k]
        bench.append(
            {
                "name": b["name"],
                "path": _expand_env(node.get("path", "")),
                "ctx_sizes": b.get("ctx", [8192]),
                "binary": _expand_env(cfg.get("binary", "llama-server")),
                "ik_flags": cfg.get("ik_llama_flags", ""),
            }
        )
    return bench


def run_bench(model: dict[str, Any], ctx: int, dry_run: bool) -> dict[str, Any]:
    binary = model["binary"]
    gguf = model["path"]
    result = {
        "model": model["name"],
        "ctx": ctx,
        "gguf": gguf,
        "binary": binary,
        "timestamp": datetime.now(UTC).isoformat(),
        "dry_run": dry_run,
    }
    if dry_run or not gguf or not Path(gguf).exists():
        result["status"] = "skipped"
        result["reason"] = (
            "dry_run or missing gguf path — set PHENO_QWEN35_08B / PHENO_LFM25_8B_A1B / PHENO_ORNITH_8B"
        )
        result["tok_per_s"] = None
        result["vram_gb"] = None
        return result
    if shutil.which(binary) is None and not Path(binary).exists():
        result["status"] = "skipped"
        result["reason"] = f"binary not found: {binary} — set PHENO_LLAMA_SERVER"
        return result

    cmd = [
        binary,
        "-m",
        gguf,
        "-c",
        str(ctx),
        "-n",
        "128",
        "--temp",
        "0.1",
        "-p",
        PROMPT,
    ]
    if model.get("ik_flags"):
        cmd.extend(model["ik_flags"].split())
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        elapsed = time.perf_counter() - t0
        out = proc.stdout + proc.stderr
        # crude tok/s from llama.cpp bench lines
        tok_s = None
        for line in out.splitlines():
            if "tokens per second" in line.lower() or "t/s" in line.lower():
                parts = line.replace(",", " ").split()
                for i, p in enumerate(parts):
                    try:
                        v = float(p)
                        if v > 0.5:
                            tok_s = v
                    except ValueError:
                        continue
        result["status"] = "ok" if proc.returncode == 0 else "error"
        result["returncode"] = proc.returncode
        result["elapsed_s"] = round(elapsed, 2)
        result["tok_per_s"] = tok_s
        result["output_tail"] = out[-1500:]
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Skip actual inference")
    p.add_argument("--model", default=None, help="Single model name from bench_models")
    args = p.parse_args()
    models = load_models()
    if args.model:
        models = [m for m in models if m["name"] == args.model]
    results = []
    for m in models:
        for ctx in m["ctx_sizes"]:
            print(f"Bench {m['name']} ctx={ctx}...")
            results.append(run_bench(m, ctx, args.dry_run))
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = BENCH_DIR / f"baseline_{ts}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    ok = sum(1 for r in results if r.get("status") == "ok")
    skip = sum(1 for r in results if r.get("status") == "skipped")
    print(f"ok={ok} skipped={skip} total={len(results)}")


if __name__ == "__main__":
    main()
