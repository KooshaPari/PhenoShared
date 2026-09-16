#!/usr/bin/env python3
"""Validate a desktop NVIDIA Qwen3.5 evidence envelope.

Validation is deliberately independent of inference.  A blocked envelope is
valid evidence when it is internally consistent; ``--require-promotable``
turns a blocked envelope into a non-zero result for release automation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.desktop_execution_preflight import canonical_contract_sha256

DEFAULT_EVIDENCE = (
    ROOT / "bench/results/desktop/desktop_nvidia_qwen35_live_20260801.json"
)
DEFAULT_CONTRACT = ROOT / "config/desktop_nvidia_qwen35_lane.yaml"
EXPECTED_GATES = frozenset(
    {
        "exact_qwen35_model_and_revision",
        "exact_quantized_artifact_and_sha256",
        "captured_dual_gpu_device_manifest",
        "runtime_binary_and_driver_provenance",
        "bounded_single_worker_smoke",
        "repeated_result_envelope_with_no_fallback_ambiguity",
        "harbor_or_eval_window_authorized",
    }
)


class EvidenceError(ValueError):
    """Raised when an evidence envelope is malformed or inconsistent."""


def validate_perf_evidence_envelope(payload: dict[str, Any]) -> None:
    """Validate self-contained, non-promotable evidence labels in a perf payload."""
    from bench.contracts.cell_metrics import (
        EVIDENCE_REPORTED,
        EVIDENCE_VERIFIED,
        VALID_CELL_EVIDENCE_LABELS,
    )

    if payload.get("schema_version") != "pheno.perf.v1":
        raise EvidenceError("unsupported perf evidence schema")
    root_label = payload.get("evidence_label")
    if not isinstance(root_label, str) or root_label not in VALID_CELL_EVIDENCE_LABELS:
        raise EvidenceError("perf root evidence_label is invalid")

    cells: list[dict[str, Any]] = []
    levels = payload.get("levels")
    if isinstance(levels, list):
        for level in levels:
            if isinstance(level, dict) and isinstance(level.get("results"), list):
                results = level["results"]
                if any(not isinstance(cell, dict) for cell in results):
                    raise EvidenceError("perf result cells must be objects")
                cells.extend(results)
    warmup = payload.get("warmup")
    if isinstance(warmup, dict) and isinstance(warmup.get("results"), list):
        results = warmup["results"]
        if any(not isinstance(cell, dict) for cell in results):
            raise EvidenceError("perf result cells must be objects")
        cells.extend(results)
    if not cells:
        raise EvidenceError("perf evidence has no result cells")

    required_cell_fields = {
        "gen_ok",
        "pass_at_1",
        "verified_pass_at_1",
        "evidence_label",
    }
    for cell in cells:
        if not required_cell_fields <= cell.keys():
            raise EvidenceError("perf result cell metric fields are incomplete")
        metrics = ("gen_ok", "pass_at_1", "verified_pass_at_1")
        if any(
            isinstance(cell[name], bool) or not isinstance(cell[name], (int, float))
            for name in metrics
        ):
            raise EvidenceError("perf result cell metric fields must be numeric")
        if cell["pass_at_1"] != cell["gen_ok"]:
            raise EvidenceError("perf result cell pass_at_1 must equal gen_ok")
        if cell["gen_ok"] not in (0.0, 1.0):
            raise EvidenceError("perf result cell metric fields are out of range")
        if "error" in cell and cell["gen_ok"] != 0.0:
            raise EvidenceError("perf error cell cannot claim successful generation")
        if (
            not math.isfinite(cell["verified_pass_at_1"])
            or not 0.0 <= cell["verified_pass_at_1"] <= 1.0
        ):
            raise EvidenceError("perf result cell metric fields are out of range")
        if (
            cell["evidence_label"] == EVIDENCE_REPORTED
            and cell["verified_pass_at_1"] != 0.0
        ):
            raise EvidenceError("reported perf result cell has verifier score")

    labels = [cell.get("evidence_label") for cell in cells]
    if any(
        not isinstance(label, str) or label not in VALID_CELL_EVIDENCE_LABELS
        for label in labels
    ):
        raise EvidenceError("perf result cell evidence_label is invalid")
    expected_root = (
        EVIDENCE_VERIFIED
        if all(label == EVIDENCE_VERIFIED for label in labels)
        else EVIDENCE_REPORTED
    )
    if root_label != expected_root:
        raise EvidenceError("perf root evidence_label overstates result cells")


def _canonical_sha256(payload: dict[str, Any]) -> str:
    copy = json.loads(json.dumps(payload))
    try:
        copy["artifact_integrity"]["result_artifact_sha256"] = ""
    except (KeyError, TypeError) as exc:
        raise EvidenceError(
            "artifact_integrity.result_artifact_sha256 is required"
        ) from exc
    canonical = json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _require(payload: dict[str, Any], *path: str) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise EvidenceError("missing " + ".".join(path))
        value = value[key]
    return value


def _git_commit_exists(commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def validate(evidence_path: Path, contract_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read evidence JSON: {evidence_path}") from exc
    if not isinstance(payload, dict):
        raise EvidenceError("evidence root must be an object")

    if payload.get("schema_version") != "pheno.desktop-live-evidence.v2":
        raise EvidenceError("unsupported evidence schema")
    authorization = _require(payload, "authorization")
    if authorization.get("mac_inference") != "paused":
        raise EvidenceError("mac inference must remain paused")
    contract = _require(payload, "contract")
    if contract.get("path") != "config/desktop_nvidia_qwen35_lane.yaml":
        raise EvidenceError("evidence contract path is not canonical")
    actual_contract_sha = canonical_contract_sha256(contract_path)
    if contract.get("sha256") != actual_contract_sha:
        raise EvidenceError("evidence is bound to a different desktop lane contract")
    source_commit = contract.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", source_commit
    ):
        raise EvidenceError("evidence source_commit must be a full SHA-1")
    source_commit_reachable = _git_commit_exists(source_commit)

    if evidence_path.resolve() == DEFAULT_EVIDENCE.resolve():
        tracked = subprocess.run(
            [
                "git",
                "ls-files",
                "--error-unmatch",
                str(evidence_path.relative_to(ROOT)),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if tracked.returncode != 0:
            raise EvidenceError("canonical evidence artifact is not tracked")

    integrity = _require(payload, "artifact_integrity")
    expected_hash = integrity.get("result_artifact_sha256")
    actual_hash = _canonical_sha256(payload)
    if expected_hash != actual_hash:
        raise EvidenceError("artifact integrity hash mismatch")

    model = _require(payload, "model")
    if model.get("canonical_id") != "Qwen/Qwen3.5-0.8B":
        raise EvidenceError("evidence model is not the canonical Qwen3.5-0.8B")
    if "Qwen2.5" in model.get("canonical_id", ""):
        raise EvidenceError("Qwen2.5 evidence is forbidden")
    for key in ("hf_snapshot_revision", "gguf_sha256", "gguf_bytes", "quantization"):
        value = model.get(key)
        if value in (None, "", 0):
            raise EvidenceError(f"model.{key} is missing")

    devices = _require(payload, "host", "devices")
    if not isinstance(devices, list) or len(devices) != 2:
        raise EvidenceError("dual-GPU device manifest is incomplete")
    if {device.get("role") for device in devices} != {"primary", "helper"}:
        raise EvidenceError("device roles must include primary and helper")

    runtimes = _require(payload, "runtimes")
    for runtime_name in ("vllm", "llama_cpp"):
        runtime = _require(runtimes, runtime_name)
        for key in ("cuda_visible_devices", "logical_device", "device"):
            if runtime.get(key) in (None, ""):
                raise EvidenceError(f"runtimes.{runtime_name}.{key} is missing")
    runtime_gate = _require(payload, "promotion", "gates").get(
        "runtime_binary_and_driver_provenance"
    )
    if not isinstance(runtime_gate, bool):
        raise EvidenceError("runtime provenance gate must be boolean")
    vllm = runtimes["vllm"]
    if not runtime_gate and not vllm.get("binary_sha256"):
        gaps = _require(payload, "promotion", "provenance_gaps")
        if not any("vllm binary sha256" in gap for gap in gaps):
            raise EvidenceError("missing vllm binary provenance gap")

    recorded_runs = _require(payload, "runs")
    if not isinstance(recorded_runs, list) or not recorded_runs:
        raise EvidenceError("run-level provenance is missing")
    required_run_fields = {
        "run_id",
        "runtime",
        "started_at",
        "finished_at",
        "workload_executed",
        "dry_run",
        "timeout_seconds",
        "max_concurrency",
        "request",
        "response_assertion",
        "fallback_detected",
    }
    for run in recorded_runs:
        if not isinstance(run, dict) or not required_run_fields <= run.keys():
            raise EvidenceError("run-level provenance fields are incomplete")
        if run["dry_run"] or not run["workload_executed"] or run["fallback_detected"]:
            raise EvidenceError("recorded smoke run is not a bounded live run")

    helper = _require(payload, "repeatability", "helper")
    runs = helper.get("runs")
    if not isinstance(runs, list) or not runs:
        raise EvidenceError("helper repeatability has no runs")
    if helper.get("passed") != len(runs) or helper.get("failed") != 0:
        raise EvidenceError("helper repeatability counts are inconsistent")
    if any(run.get("response") != "HELPER_REPEAT_OK" for run in runs):
        raise EvidenceError(
            "helper repeatability contains a non-deterministic response"
        )

    promotion = _require(payload, "promotion")
    gates = promotion.get("gates")
    if not isinstance(gates, dict) or set(gates) != EXPECTED_GATES:
        raise EvidenceError("promotion gates do not match the lane contract")
    if any(not isinstance(value, bool) for value in gates.values()):
        raise EvidenceError("promotion gates must be boolean")
    expected_status = "pass" if all(gates.values()) else "blocked"
    if promotion.get("status") != expected_status:
        raise EvidenceError("promotion status does not match gate results")
    if expected_status == "pass" and not source_commit_reachable:
        raise EvidenceError("evidence source_commit is not a reachable commit")
    primary = _require(payload, "repeatability", "primary")
    if (
        not gates["repeated_result_envelope_with_no_fallback_ambiguity"]
        and primary.get("status") != "deferred_user_owned_runtime"
    ):
        raise EvidenceError("primary failure must name the deferred user-owned runtime")

    return {
        "valid": True,
        "status": promotion["status"],
        "passed_gates": sum(value for value in gates.values()),
        "total_gates": len(gates),
        "artifact_sha256": actual_hash,
        "source_commit_reachable": source_commit_reachable,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--require-promotable", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate(args.evidence, args.contract)
    except EvidenceError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    if args.require_promotable and result["status"] != "pass":
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
