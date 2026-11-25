#!/usr/bin/env python3
"""Report the exact remaining desktop promotion evidence without launching work."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.desktop_execution_preflight import canonical_contract_sha256
from scripts.validate_desktop_evidence import (
    DEFAULT_CONTRACT,
    DEFAULT_EVIDENCE,
    EvidenceError,
    validate,
)

_NEXT_EVIDENCE = {
    "repeated_result_envelope_with_no_fallback_ambiguity": (
        "primary repeated no-fallback result envelope"
    ),
    "harbor_or_eval_window_authorized": "authorized Harbor or harness evaluation result",
}


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _preflight_summary(path: Path | None, contract_path: Path) -> dict[str, Any]:
    if path is None:
        return {"present": False, "promotion_effect": "none"}
    try:
        raw = path.read_bytes()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read preflight JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise EvidenceError("preflight root must be an object")
    if payload.get("schema_version") != "pheno.desktop-preflight.v1":
        raise EvidenceError("unsupported preflight schema")
    if payload.get("no_launch") is not True:
        raise EvidenceError("promotion report accepts no-launch preflight records only")
    contract = payload.get("contract")
    if (
        not isinstance(contract, dict)
        or contract.get("path") != "config/desktop_nvidia_qwen35_lane.yaml"
        or contract.get("sha256") != canonical_contract_sha256(contract_path)
    ):
        raise EvidenceError("preflight is not bound to the current lane contract")
    return {
        "present": True,
        "path": _relative(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "schema_version": payload["schema_version"],
        "no_launch": True,
        "promotion_effect": "none",
    }


def build_report(
    evidence_path: Path = DEFAULT_EVIDENCE,
    contract_path: Path = DEFAULT_CONTRACT,
    preflight_path: Path | None = None,
) -> dict[str, Any]:
    """Return a stable, inspection-only view of promotion readiness."""
    validation = validate(evidence_path, contract_path)
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    gates = payload["promotion"]["gates"]
    unmet = sorted(name for name, passed in gates.items() if not passed)
    next_required = next(
        (label for gate, label in _NEXT_EVIDENCE.items() if gate in unmet),
        "independent promotion review",
    )
    return {
        "schema_version": "pheno.desktop-promotion-readiness.v1",
        "valid_evidence": validation["valid"],
        "promotion_status": validation["status"],
        "passed_gates": validation["passed_gates"],
        "total_gates": validation["total_gates"],
        "unmet_gates": unmet,
        "next_required_evidence": next_required,
        "evidence": {
            "path": _relative(evidence_path),
            "artifact_sha256": validation["artifact_sha256"],
            "source_commit_reachable": validation["source_commit_reachable"],
        },
        "preflight": _preflight_summary(preflight_path, contract_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--preflight-record", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(args.evidence, args.contract, args.preflight_record)
    except (EvidenceError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
