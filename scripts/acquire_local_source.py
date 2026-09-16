#!/usr/bin/env python3
"""Plan or explicitly acquire one locked HF source repo; never an eval artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pheno.model_policy import local_aliases  # noqa: E402


def refs() -> dict[str, str]:
    import yaml

    data = (
        yaml.safe_load(
            (ROOT / "config" / "local_model_bench_matrix.yaml").read_text(
                encoding="utf-8"
            )
        )
        or {}
    )
    return {
        str(item["alias"]): str(item["hf_owner_id"]) for item in data["models"].values()
    }


def file_hashes(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": digest.hexdigest(),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire a locked model source repo")
    parser.add_argument("--model", required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--revision")
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--existing-source",
        action="store_true",
        help="Skip download and verify/hash an already acquired source tree",
    )
    parser.add_argument(
        "--allow-unquantized-source",
        action="store_true",
        help="acknowledge this is source input, never a benchmark artifact",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mapping = refs()
    if args.model not in local_aliases() or args.model not in mapping:
        parser.error(f"model is not one of the locked local aliases: {args.model}")
    if args.execute and not args.allow_unquantized_source:
        parser.error("--execute requires --allow-unquantized-source")
    target_root = args.target_root.resolve()
    drive = target_root.anchor.upper()
    if drive not in {"D:\\", "E:\\"}:
        parser.error(f"target root must be on D: or E: (got {target_root})")
    free = shutil.disk_usage(target_root.anchor).free
    minimum = 50 * 1024**3
    token = os.environ.get(args.token_env)
    api = HfApi(token=token) if token else HfApi()
    repo = mapping[args.model]
    info = api.model_info(repo, revision=args.revision, files_metadata=False)
    revision = args.revision or info.sha
    destination = target_root / args.model.split("/", 1)[1]
    report: dict[str, Any] = {
        "schema_version": "phenolm.source_acquisition.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "model_alias": args.model,
        "repo": repo,
        "revision": revision,
        "target": str(destination),
        "authenticated": bool(token),
        "execute": args.execute,
        "download_performed": False,
        "eval_artifact": False,
        "disk_admission": "pass" if free >= minimum else "reject_low_disk",
        "free_bytes": free,
        "minimum_free_bytes": minimum,
    }
    if args.execute:
        if free < minimum:
            parser.error("target volume is below the 50 GB hard stop")
        destination.mkdir(parents=True, exist_ok=True)
        if not args.existing_source:
            snapshot_download(
                repo_id=repo, revision=revision, local_dir=str(destination), token=token
            )
        elif not (destination / "config.json").is_file():
            parser.error(
                f"--existing-source requires a completed source tree: {destination}"
            )
        report["download_performed"] = True
        report["files"] = file_hashes(destination)
        report["source_tree_sha256"] = hashlib.sha256(
            "".join(
                f"{row['path']}:{row['bytes']}:{row['sha256']}\n"
                for row in report["files"]
            ).encode()
        ).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "model": args.model,
                "revision": revision,
                "download_performed": report["download_performed"],
                "disk_admission": report["disk_admission"],
            },
            indent=2,
        )
    )
    return 0 if report["disk_admission"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
