#!/usr/bin/env python3
"""Plan or execute HF-SafeTensors -> GGUF quantization with manifest hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert one local source tree to a GGUF quant artifact"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--convert-script",
        type=Path,
        required=True,
        help="llama.cpp convert_hf_to_gguf.py",
    )
    parser.add_argument(
        "--quantize-bin", type=Path, required=True, help="llama-quantize executable"
    )
    parser.add_argument(
        "--type",
        default="Q4_K_M",
        choices=["Q2_K", "Q3_K_S", "Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"],
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Reuse an existing intermediate GGUF",
    )
    parser.add_argument(
        "--reuse-output",
        action="store_true",
        help="Validate and manifest an existing quantized output",
    )
    parser.add_argument(
        "--intermediate", type=Path, help="Explicit existing intermediate GGUF path"
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        help="Source acquisition manifest for provenance",
    )
    parser.add_argument(
        "--toolchain-manifest", type=Path, help="llama.cpp binary acquisition manifest"
    )
    parser.add_argument("--model-alias", default="local/qwen35-08b")
    parser.add_argument(
        "--runtime-validated",
        action="store_true",
        help="Promote the artifact only with a separate successful runtime evidence file",
    )
    parser.add_argument(
        "--runtime-evidence",
        type=Path,
        help="JSON/log evidence produced by a successful model load and generation smoke",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.runtime_validated and (
        not args.runtime_evidence or not args.runtime_evidence.is_file()
    ):
        parser.error("--runtime-validated requires an existing --runtime-evidence file")
    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_dir() or not (source / "config.json").is_file():
        parser.error(
            f"source must be an existing HF directory with config.json: {source}"
        )
    if output == source or output.is_relative_to(source):
        parser.error("output must not be inside the source tree")
    if output.anchor.upper() not in {"D:\\", "E:\\"}:
        parser.error("quantized output must be on D: or E:")
    if args.execute and (
        not args.convert_script.is_file() or not args.quantize_bin.is_file()
    ):
        parser.error("--execute requires existing converter script and quantize binary")
    output.parent.mkdir(parents=True, exist_ok=True)
    intermediate = (
        args.intermediate.resolve()
        if args.intermediate
        else output.with_name(output.stem + ".f16.gguf")
    )
    report: dict[str, Any] = {
        "schema_version": "phenolm.gguf_conversion.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "model_alias": args.model_alias,
        "source": str(source),
        "output": str(output),
        "quantization": args.type,
        "intermediate": str(intermediate),
        "source_config_sha256": sha256(source / "config.json"),
        "conversion_performed": False,
        "eval_artifact": False,
        "runtime_validated": bool(args.runtime_validated),
        "runtime_evidence": str(args.runtime_evidence.resolve())
        if args.runtime_evidence
        else None,
        "command": [
            str(args.convert_script),
            str(source),
            "--outfile",
            str(intermediate),
            "--outtype",
            "f16",
        ],
        "quantize_command": [
            str(args.quantize_bin),
            str(intermediate),
            str(output),
            args.type,
        ],
    }
    if args.source_manifest and args.source_manifest.is_file():
        source_report = json.loads(args.source_manifest.read_text(encoding="utf-8"))
        report["source_revision"] = source_report.get("revision")
        report["source_tree_sha256"] = source_report.get("source_tree_sha256")
        report["source_manifest"] = str(args.source_manifest.resolve())
    if args.convert_script.is_file():
        report["converter_sha256"] = sha256(args.convert_script)
    if args.quantize_bin.is_file():
        report["quantizer_sha256"] = sha256(args.quantize_bin)
    if args.toolchain_manifest and args.toolchain_manifest.is_file():
        report["toolchain_manifest"] = str(args.toolchain_manifest.resolve())
        report["toolchain"] = json.loads(
            args.toolchain_manifest.read_text(encoding="utf-8-sig")
        )
    if args.execute:
        if not args.skip_convert:
            subprocess.run(
                [
                    sys.executable,
                    str(args.convert_script),
                    str(source),
                    "--outfile",
                    str(intermediate),
                    "--outtype",
                    "f16",
                ],
                check=True,
                cwd=ROOT,
            )
        if not intermediate.is_file():
            raise RuntimeError(f"intermediate GGUF does not exist: {intermediate}")
        if not (args.reuse_output and output.is_file()):
            subprocess.run(
                [str(args.quantize_bin), str(intermediate), str(output), args.type],
                check=True,
                cwd=ROOT,
            )
        if not output.is_file() or output.stat().st_size < 1024:
            raise RuntimeError("converter returned without a valid output")
        report["conversion_performed"] = True
        report["output_bytes"] = output.stat().st_size
        report["output_sha256"] = sha256(output)
        report["eval_artifact"] = bool(args.runtime_validated)
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "manifest": str(args.output_manifest),
                "conversion_performed": report["conversion_performed"],
                "eval_artifact": report["eval_artifact"],
                "quantization": args.type,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
