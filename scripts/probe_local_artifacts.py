#!/usr/bin/env python3
"""Probe locked local model repositories without downloading weights."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from huggingface_hub import HfApi  # noqa: E402

from pheno.model_policy import local_aliases  # noqa: E402
from pheno.paths import CONFIG_DIR, STATE_DIR  # noqa: E402


def _model_refs() -> dict[str, str]:
    import yaml

    data = (
        yaml.safe_load(
            (CONFIG_DIR / "local_model_bench_matrix.yaml").read_text(encoding="utf-8")
        )
        or {}
    )
    return {
        str(item["alias"]): str(item["hf_owner_id"]) for item in data["models"].values()
    }


def _file_record(item: Any) -> dict[str, Any]:
    name = str(getattr(item, "path", getattr(item, "rfilename", "")))
    size = getattr(item, "size", None)
    lowered = name.lower()
    formats = []
    for marker, label in (
        (".gguf", "gguf"),
        (".safetensors", "safetensors"),
        (".awq", "awq"),
        (".gptq", "gptq"),
        (".onnx", "onnx"),
        (".bin", "pytorch_bin"),
    ):
        if marker in lowered:
            formats.append(label)
    quant_markers = [
        q
        for q in ("q2", "q3", "q4", "q5", "q6", "q8", "nvfp4", "fp4", "int4", "int8")
        if q in lowered
    ]
    return {
        "path": name,
        "size_bytes": size,
        "formats": formats,
        "quant_markers": quant_markers,
    }


def probe(api: HfApi, alias: str, repo: str) -> dict[str, Any]:
    try:
        info = api.model_info(repo, files_metadata=False)
        files = [
            _file_record(item)
            for item in api.list_repo_tree(repo, recursive=True, expand=False)
        ]
        return {
            "alias": alias,
            "repo": repo,
            "status": "ok",
            "sha": info.sha,
            "last_modified": info.lastModified.isoformat()
            if info.lastModified
            else None,
            "pipeline_tag": info.pipeline_tag,
            "files": files,
            "download_allowed_by_probe": False,
        }
    except Exception as exc:
        return {
            "alias": alias,
            "repo": repo,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "download_allowed_by_probe": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Metadata-only HF probe for locked local models"
    )
    parser.add_argument(
        "--model", action="append", dest="models", help="locked alias; repeatable"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--token-env",
        default="HF_TOKEN",
        help="environment variable name, never token value",
    )
    args = parser.parse_args()
    refs = _model_refs()
    aliases = args.models or sorted(local_aliases())
    unknown = sorted(set(aliases) - set(refs))
    if unknown:
        parser.error(f"unknown or unlocked aliases: {unknown}")
    token = os.environ.get(args.token_env)
    api = HfApi(token=token) if token else HfApi()
    report: dict[str, Any] = {
        "schema_version": "phenolm.local_artifact_probe.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "authenticated": bool(token),
        "download_performed": False,
        "models": [probe(api, alias, refs[alias]) for alias in aliases],
    }
    output = args.output or STATE_DIR / "local_artifact_probe.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "authenticated": bool(token),
                "models": len(report["models"]),
                "download_performed": False,
            },
            indent=2,
        )
    )
    return 0 if all(row["status"] == "ok" for row in report["models"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
