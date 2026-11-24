#!/usr/bin/env python3
"""12B distillation pipeline scaffold from teacher traces (Phase 5)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any

from pheno.paths import PHENO_ROOT, STATE_DIR


def _expand_env(s: str) -> str:
    if not isinstance(s, str):
        return s
    import os

    s = s.replace("${PHENO_ROOT}", str(PHENO_ROOT)).replace("${HOME}", str(Path.home()))
    return os.path.expandvars(s)


def load_config() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "training" / "distill_12b.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def collect_traces(cfg: dict[str, Any]) -> list[dict]:
    root = Path(_expand_env(cfg["data"]["root"]))
    rows: list[dict] = []
    for src in cfg["data"]["sources"]:
        for path in sorted(root.glob(src["glob"])):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                rec["_source_kind"] = src["kind"]
                rec["_source_file"] = path.name
                rows.append(rec)
                if len(rows) >= int(cfg["data"].get("max_samples", 50000)):
                    return rows
    return rows


def to_distill_sample(rec: dict[str, Any]) -> dict | None:
    prompt = rec.get("prompt") or rec.get("request_summary") or rec.get("input")
    response = (
        rec.get("response")
        or rec.get("completion")
        or rec.get("output")
        or rec.get("chosen")
    )
    if not prompt or not response:
        return None
    return {
        "prompt": prompt,
        "teacher_completion": response,
        "role": rec.get("role", "patch"),
        "model": rec.get("model") or rec.get("provider"),
        "tokens_in": rec.get("tokens_in"),
        "tokens_out": rec.get("tokens_out"),
        "source_kind": rec.get("_source_kind"),
    }


def build_manifest(cfg: dict[str, Any], samples: list[dict], *, dry_run: bool) -> dict[str, Any]:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(_expand_env(cfg["distillation"]["output_dir"]))
    manifest = {
        "timestamp": ts,
        "student_id": cfg["student"]["id"],
        "sample_count": len(samples),
        "teachers": cfg["teachers"],
        "distillation": cfg["distillation"],
        "dry_run": dry_run,
        "output_dir": str(out_dir),
    }
    if dry_run:
        return manifest

    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = out_dir / f"distill_dataset_{ts}.jsonl"
    with dataset_path.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    manifest["dataset_path"] = str(dataset_path)

    train_cmd = [
        "# scaffold — wire to axolotl / unsloth / custom trainer",
        f"# samples: {len(samples)}",
        f"# qlora_rank: {cfg['distillation']['qlora_rank']}",
        f"# output: {out_dir}",
    ]
    manifest["train_cmd_scaffold"] = train_cmd
    manifest_path = STATE_DIR / f"distill_12b_{ts}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Distill 12B dense from teacher traces")
    p.add_argument("--dry-run", action="store_true", help="Collect stats only")
    p.add_argument("--max-samples", type=int, default=None)
    args = p.parse_args()

    cfg = load_config()
    if args.max_samples:
        cfg["data"]["max_samples"] = args.max_samples

    raw = collect_traces(cfg)
    samples = [s for s in (to_distill_sample(r) for r in raw) if s]
    teacher_tokens = sum(
        (s.get("tokens_out") or len(s["teacher_completion"]) // 4) for s in samples
    )
    min_tok = int(cfg["data"].get("min_teacher_tokens", 500000))

    print(
        f"Raw records: {len(raw)}  distill samples: {len(samples)}  teacher_tokens~{teacher_tokens}"
    )
    if teacher_tokens < min_tok:
        print(
            f"WARN: below min_teacher_tokens ({min_tok}) — export more traces or run teachers"
        )

    manifest = build_manifest(cfg, samples, dry_run=args.dry_run)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
