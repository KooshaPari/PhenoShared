#!/usr/bin/env python3
"""Run a provenance-bound desktop Qwen3.5 performance evaluation.

The wrapper never launches or terminates a server.  ``--execute`` requires an
explicit sponsor window ID and performs an endpoint model check before calling
``run_perf_suite.py``.  Without ``--execute`` it only prints a dry-run plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# AGENTS.md §12.3 / §12.4 canonical evidence labels for direct-generate cells.
EVIDENCE_REPORTED = "reported"
EVIDENCE_VERIFIED = "verified"


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.desktop_execution_preflight import (
    PreflightError,
    canonical_contract_sha256,
    validate_execution_preflight,
)

CONTRACT = ROOT / "config/desktop_nvidia_qwen35_lane.yaml"
MODEL_ALIAS = "local/qwen35-08b"
RUNTIME_DEFAULTS = {
    "primary": ("http://127.0.0.1:8000", "desktop-vllm-3090ti"),
    "helper": ("http://127.0.0.1:8082", "desktop-llama-cpp-1080ti"),
}


def _endpoint_models(base_url: str, timeout: float) -> list[str]:
    request = urllib.request.Request(base_url.rstrip("/") + "/v1/models")
    try:
        with (
            urllib.request.urlopen(request, timeout=timeout) as response  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            payload = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"endpoint model probe failed: {exc}") from exc
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("endpoint /v1/models response has no data list")
    return [str(row.get("id", "")) for row in rows if isinstance(row, dict)]


def _contract_sha256() -> str:
    return canonical_contract_sha256(CONTRACT)


def _require_live_execution_policy() -> None:
    """Fail closed unless the lane contract explicitly authorizes live evals."""
    try:
        contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"execution policy is unavailable or invalid: {exc}") from exc
    policy = contract.get("execution_policy") if isinstance(contract, dict) else None
    if not isinstance(policy, dict) or (
        contract.get("status") != "active"
        or policy.get("allow_model_inference") is not True
        or policy.get("allow_benchmark_execution") is not True
    ):
        raise SystemExit("execution policy forbids live desktop evaluation")


def _require_owner_issued_execution_authority() -> None:
    """Fail closed until an owner publishes a bound execution authority."""
    raise SystemExit(
        "desktop execution is blocked: no owner-issued authority contract is configured"
    )


def _is_qwen35_model(model_id: str) -> bool:
    normalized = model_id.lower().replace(".", "").replace("-", "").replace("/", "")
    return "qwen35" in normalized


# DAG-30: wire `evidence_label` into the desktop lane output per AGENTS.md
# §12.3 / §12.4. The desktop lane is a direct-generate path (not Harbor),
# so by default ``harbor_reward=None`` yields ``evidence_label="reported"``
# and ``verified_pass_at_1=0.0`` for every per-cell result.
_CellPassFieldsFn = Callable[..., dict[str, Any]]


def _load_cell_pass_fields() -> _CellPassFieldsFn:
    """Return ``bench.contracts.cell_metrics.cell_pass_fields`` if importable.

    Falls back to an inline implementation that mirrors the v0.2 contract
    (gen_ok, pass_at_1, verified_pass_at_1, evidence_label) so the desktop
    lane stays usable even if ``bench.contracts.cell_metrics`` is absent.
    """
    try:
        from bench.contracts.cell_metrics import cell_pass_fields

        return cell_pass_fields
    except ImportError:

        def cell_pass_fields(
            gen_success: bool, *, harbor_reward: float | None = None
        ) -> dict[str, Any]:
            gen_ok = 1.0 if gen_success else 0.0
            if harbor_reward is not None:
                return {
                    "gen_ok": gen_ok,
                    "pass_at_1": gen_ok,
                    "verified_pass_at_1": float(harbor_reward),
                    "evidence_label": EVIDENCE_VERIFIED,
                }
            return {
                "gen_ok": gen_ok,
                "pass_at_1": gen_ok,
                "verified_pass_at_1": 0.0,
                "evidence_label": EVIDENCE_REPORTED,
            }

        return cell_pass_fields


def _augment_results_with_evidence_label(
    results: Any,
    cell_pass_fields: _CellPassFieldsFn,
    harbor_reward: float | None,
) -> None:
    """Mutate each cell in ``results`` to carry v0.5 cell fields in place."""
    if not isinstance(results, list):
        return
    for cell in results:
        if not isinstance(cell, dict):
            continue
        gen_success = "error" not in cell
        # Preserve any pre-existing explicit cell fields; cell_pass_fields
        # wins because the contract v0.2 fields are the canonical emit.
        cell.update(cell_pass_fields(gen_success, harbor_reward=harbor_reward))


def apply_evidence_label_to_perf_output(
    perf_result: dict[str, Any], *, harbor_reward: float | None = None
) -> dict[str, Any]:
    """Add per-cell ``evidence_label`` to a desktop-lane perf result.

    Iterates ``levels[].results`` and ``warmup.results`` (the natural
    per-cell containers of the ``pheno.perf.v1`` schema). Each cell is
    augmented with the v0.2 contract fields ``gen_ok``, ``pass_at_1``,
    ``verified_pass_at_1``, and ``evidence_label``. The desktop lane is a
    direct-generate path so by default no Harbor reward is supplied and
    every cell ends up with ``evidence_label = "reported"``.

    Returns the same dict (mutated in place) so callers can chain writes.
    """
    cell_pass_fields = _load_cell_pass_fields()
    levels = perf_result.get("levels")
    if isinstance(levels, list):
        for level in levels:
            if isinstance(level, dict):
                _augment_results_with_evidence_label(
                    level.get("results"), cell_pass_fields, harbor_reward
                )
    warmup = perf_result.get("warmup")
    if isinstance(warmup, dict):
        _augment_results_with_evidence_label(
            warmup.get("results"), cell_pass_fields, harbor_reward
        )
    labels = [
        cell["evidence_label"]
        for level in levels
        if isinstance(level, dict)
        for cell in level.get("results", [])
        if isinstance(cell, dict) and "evidence_label" in cell
    ]
    if isinstance(warmup, dict):
        labels.extend(
            cell["evidence_label"]
            for cell in warmup.get("results", [])
            if isinstance(cell, dict) and "evidence_label" in cell
        )
    perf_result["evidence_label"] = (
        EVIDENCE_VERIFIED
        if labels and all(label == EVIDENCE_VERIFIED for label in labels)
        else EVIDENCE_REPORTED
    )
    return perf_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=sorted(RUNTIME_DEFAULTS), required=True)
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--preflight-record", type=Path)
    parser.add_argument("--timeout-s", type=float, default=10.0)
    return parser.parse_args()


def _plan(args: argparse.Namespace) -> dict[str, Any]:
    default_url, engine = RUNTIME_DEFAULTS[args.runtime]
    return {
        "schema_version": "pheno.desktop-lane-eval-plan.v1",
        "runtime": args.runtime,
        "base_url": args.base_url or default_url,
        "engine_label": engine,
        "model": MODEL_ALIAS,
        "request_model": MODEL_ALIAS,
        "window_id": args.window_id,
        "contract_sha256": _contract_sha256(),
        "execute": args.execute,
        "output": str(args.output),
        "manifest_output": str(args.manifest_output),
    }


def main() -> int:
    args = parse_args()
    plan = _plan(args)
    if not args.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    _require_live_execution_policy()
    try:
        validate_execution_preflight(
            args.preflight_record,
            args.runtime,
            plan["base_url"],
            contract_path=CONTRACT,
        )
    except PreflightError as exc:
        raise SystemExit(
            f"execution preflight blocks live desktop evaluation: {exc}"
        ) from exc
    _require_owner_issued_execution_authority()
    models = _endpoint_models(plan["base_url"], args.timeout_s)
    if not any("qwen35" in model.lower() for model in models):
        raise SystemExit(f"endpoint does not advertise Qwen3.5: {models}")

    command = [
        sys.executable,
        str(ROOT / "scripts/run_perf_suite.py"),
        "--base-url",
        plan["base_url"],
        "--model",
        MODEL_ALIAS,
        "--engine-label",
        plan["engine_label"],
        "--concurrency",
        "1",
        "--requests-per-level",
        "3",
        "--warmup",
        "1",
        "--timeout-s",
        str(args.timeout_s),
        "--no-gpu-sampling",
        "--output",
        str(args.output),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    # DAG-30: annotate each per-cell result with the canonical
    # ``evidence_label`` enum per AGENTS.md §12.3 / §12.4 before sealing
    # the output with a SHA. Desktop lane is direct-generate, so the
    # default ``harbor_reward=None`` path yields ``evidence_label="reported"``.
    perf_result = json.loads(args.output.read_text(encoding="utf-8"))
    apply_evidence_label_to_perf_output(perf_result)
    args.output.write_text(json.dumps(perf_result, indent=2), encoding="utf-8")
    result_sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    manifest = {
        **plan,
        "executed_at": datetime.now(UTC).isoformat(),
        "result_sha256": result_sha,
        "result_schema": "pheno.perf.v1",
    }
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
