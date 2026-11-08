#!/usr/bin/env python3
"""NanoVMS evaluation grader: positive and negative controls.

Implements PEP-06-02-01 (grader accepts valid solutions) and
PEP-06-02-02 (grader rejects empty/no-op implementations).

Usage:
    python3 grader.py --binary /path/to/nvms --out /path/to/output
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path("/Users/<REDACTED>/Downloads/agent-lab-assessment-dossiers-v1.1/core-v1.0/tools")))
import pep


def now():
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def run_command(cmd: list[str], timeout: int = 30) -> dict:
    """Run a command and capture output."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            text=False  # binary mode to handle any output
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.decode("utf-8", errors="replace"),
            "stderr": result.stderr.decode("utf-8", errors="replace"),
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": "timeout", "success": False}
    except FileNotFoundError:
        return {"exit_code": -1, "stdout": "", "stderr": "binary not found", "success": False}


def positive_control(binary: Path) -> dict:
    """Run valid NanoVMS binary through grader checks.

    A valid binary must:
    1. Execute without crash
    2. Print version information on 'version' subcommand
    3. Print help on 'help' or no-args invocation
    4. Support subcommands: deploy, serve, token, vm, tier, version
    """
    observations = []

    # Test 1: version command
    ver = run_command([str(binary), "version"])
    observations.append({
        "test": "version_command",
        "passed": ver["success"] and "SANDBOX ORCHESTRATION ENGINE" in ver["stdout"],
        "exit_code": ver["exit_code"],
        "stdout_preview": ver["stdout"][:200],
    })

    # Test 2: help command
    help_out = run_command([str(binary), "help"])
    observations.append({
        "test": "help_command",
        "passed": help_out["success"] and "Commands:" in help_out["stdout"],
        "exit_code": help_out["exit_code"],
        "stdout_preview": help_out["stdout"][:200],
    })

    # Test 3: unknown command produces error
    unknown = run_command([str(binary), "nonexistent-cmd"])
    observations.append({
        "test": "unknown_command_error",
        "passed": not unknown["success"] and "unknown command" in unknown["stderr"].lower(),
        "exit_code": unknown["exit_code"],
        "stderr_preview": unknown["stderr"][:200],
    })

    # Test 4: tier help
    tier = run_command([str(binary), "tier", "help"])
    observations.append({
        "test": "tier_help",
        "passed": tier["success"] or "Usage:" in tier["stdout"] or "tier" in tier["stdout"].lower(),
        "exit_code": tier["exit_code"],
        "stdout_preview": tier["stdout"][:200],
    })

    # Test 5: vm help
    vm = run_command([str(binary), "vm", "help"])
    observations.append({
        "test": "vm_help",
        "passed": "Subcommands:" in vm["stdout"] or "list" in vm["stdout"].lower(),
        "exit_code": vm["exit_code"],
        "stdout_preview": vm["stdout"][:200],
    })

    all_passed = all(o["passed"] for o in observations)
    return {
        "control": "POSITIVE",
        "all_passed": all_passed,
        "tests_run": len(observations),
        "tests_passed": sum(1 for o in observations if o["passed"]),
        "observations": observations,
    }


def negative_control(binary: Path) -> dict:
    """Run no-op/empty implementation through same grader checks.

    A no-op binary must be REJECTED by the grader:
    1. It should fail version check (no real version output)
    2. It should fail help check (no real help output)
    3. The grader must detect it's not a real NanoVMS binary
    """
    observations = []

    # Test 1: version command - should not produce real version output
    ver = run_command([str(binary), "version"])
    has_real_version = "SANDBOX ORCHESTRATION ENGINE" in ver["stdout"]
    observations.append({
        "test": "version_not_valid",
        "passed": not has_real_version,
        "note": "No-op binary should not produce real NanoVMS version output",
        "exit_code": ver["exit_code"],
    })

    # Test 2: help command - should not produce real help
    help_out = run_command([str(binary), "help"])
    has_real_help = "Commands:" in help_out["stdout"] and "deploy" in help_out["stdout"]
    observations.append({
        "test": "help_not_valid",
        "passed": not has_real_help,
        "note": "No-op binary should not produce real NanoVMS help output",
        "exit_code": help_out["exit_code"],
    })

    # Test 3: subcommands should not work properly
    deploy = run_command([str(binary), "deploy"])
    observations.append({
        "test": "deploy_not_valid",
        "passed": not deploy["success"] or "SANDBOX ORCHESTRATION ENGINE" not in deploy["stdout"],
        "note": "No-op binary should not successfully deploy",
        "exit_code": deploy["exit_code"],
    })

    all_rejected = all(o["passed"] for o in observations)
    return {
        "control": "NEGATIVE",
        "all_rejected": all_rejected,
        "tests_run": len(observations),
        "tests_passed": sum(1 for o in observations if o["passed"]),
        "observations": observations,
    }


def create_noop_binary() -> Path:
    """Create a minimal no-op binary for negative control."""
    noop_dir = Path(tempfile.mkdtemp(prefix="nvms-noop-"))

    if sys.platform == "darwin" or sys.platform == "linux":
        # Create a minimal shell script that acts as a "binary"
        noop_script = noop_dir / "nvms-noop"
        noop_script.write_text("#!/bin/sh\necho 'noop'\nexit 0\n")
        noop_script.chmod(0o755)
        return noop_script
    else:
        # Windows: create a batch file
        noop_script = noop_dir / "nvms-noop.bat"
        noop_script.write_text("@echo off\necho noop\nexit /b 0\n")
        return noop_script


def write_grader_bundle(base: Path, binary: Path, positive: dict, negative: dict, evaluator_digest: str):
    """Write a PEP-compatible grader bundle."""
    base.mkdir(parents=True, exist_ok=True)
    for folder in ["results", "evidence", "qualifications", "raw", "measurement-bindings"]:
        (base / folder).mkdir()

    stamp = now()
    catalog_digest = pep.file_digest(pep.ROOT / "catalog" / "catalog.json")

    # Subject identity
    subject = pep.value_digest({
        "source_digest": file_sha256(binary),
        "variant": "nanovms-grader",
    })

    # Qualification: the key record proving grader works
    qualified = {
        "valid_accepted": positive["all_passed"],
        "noop_rejected": negative["all_rejected"],
    }

    # Write raw observations
    observation = {
        "positive_control": positive,
        "negative_control": negative,
        "qualified": qualified,
        "binary_path": str(binary),
        "binary_digest": file_sha256(binary),
    }
    pep.write_json_new(base / "raw" / "observations.json", observation)

    # Evidence
    for eid, path, role in [
        ("EV-OBS", "raw/observations.json", "OBSERVATION"),
    ]:
        ev = {
            "kind": "evidence", "schema_version": "1.0.0", "id": eid,
            "subject_digest": subject, "path": path,
            "digest": file_sha256(base / path),
            "observed_at": stamp, "sensitivity": "PUBLIC",
            "role": role, "origin": "AGENT_EXECUTION",
            "summary": "NanoVMS grader positive and negative control execution results",
        }
        pep.write_json_new(base / "evidence" / f"{eid}.json", ev)

    # Qualification
    q = {
        "kind": "qualification", "schema_version": "1.0.0", "id": "Q-NANOVMS-GRADER",
        "evaluator_id": "nanovms-outcome-grader",
        "evaluator_digest": evaluator_digest,
        "status": "QUALIFIED" if qualified["valid_accepted"] and qualified["noop_rejected"] else "UNQUALIFIED",
        "scope_instance_ids": ["I-7", "I-8"],
        "positive_control_passed": qualified["valid_accepted"],
        "negative_control_passed": qualified["noop_rejected"],
        "evidence_ids": ["EV-OBS"],
        "observed_at": stamp,
        "limitations": [
            "Grader checks CLI binary output patterns, not full functional correctness.",
            "Negative control uses a shell script stub, not a compiled Go binary.",
            "This grader covers PEP-06-02-01 and PEP-06-02-02 only.",
        ],
    }
    pep.write_json_new(base / "qualifications" / "Q-NANOVMS-GRADER.json", q)

    # Measurement bindings for I-7 and I-8
    for iid, cid, key in [("I-7", "PEP-06-02-01", "valid_accepted"), ("I-8", "PEP-06-02-02", "noop_rejected")]:
        binding = {
            "kind": "measurement-binding", "schema_version": "1.0.0",
            "id": f"MB-{iid}", "record_status": "OPERATIONAL",
            "created_at": stamp,
            "criterion_id": cid, "instance_id": iid,
            "subject_scope": "NanoVMS CLI binary evaluation grader",
            "modality": "DYNAMIC",
            "method": f"Positive/negative control execution; checks {key} predicate",
            "expected_behavior": f"{key} must be true",
            "units_or_anchors": "Boolean predicate; exactly one asserted outcome",
            "environment_ref": "Local build environment",
            "fixtures": ["nvms-binary", "nvms-noop-stub"],
            "positive_control": "Real nvms binary passes version/help/subcommand checks",
            "negative_control": "Noop stub fails all validation checks",
            "qualification_refs": ["Q-NANOVMS-GRADER"],
            "resource_limit": "Binary execution only; no network or container runtime",
            "side_effects": ["Temporary noop script only"],
            "authority_ref": "Local build authority",
            "freshness_rule": "Any change to binary or grader logic requires rerun",
            "evidence_requirements": ["raw/observations.json"],
        }
        pep.write_json_new(base / "measurement-bindings" / f"MB-{iid}.json", binding)

    # Assignment
    instances = [
        {
            "id": iid, "criterion_id": cid, "criterion_revision": "1.0.0",
            "obligation_key": f"obligation.{cid.lower().replace('-', '.')}",
            "scope": "NanoVMS CLI grader evaluation",
            "applicability": "APPLICABLE",
            "applicability_reason": "Grader instrument available for this criterion",
            "applicability_decision_ref": None,
            "weight": 1.0, "mandatory": False,
            "measurement_binding_ref": f"measurement-bindings/MB-{iid}.json",
        }
        for iid, cid in [("I-7", "PEP-06-02-01"), ("I-8", "PEP-06-02-02")]
    ]

    a = {
        "kind": "assignment", "schema_version": "1.0.0",
        "id": "ASSIGN-NANOVMS-GRADER-20260915",
        "record_status": "OPERATIONAL",
        "epoch_id": "EPOCH-NANOVMS-GRADER-20260915",
        "status": "LOCKED",
        "subject_id": subject,
        "subject_digest": subject,
        "mandate_ref": "Grader evaluation for PEP-06-02-01/02",
        "intent_ref": "Validate that NanoVMS grader accepts valid solutions and rejects no-ops",
        "catalog_digest": catalog_digest,
        "profile_id": "cli",
        "coverage_statement": "PEP-06-02-01 and PEP-06-02-02 grader validation only",
        "created_at": stamp,
        "scope_review_status": "ACCEPTED",
        "scope_review_ref": "Grader evaluation scope",
        "instances": instances,
        "gates": [{"id": "GRADER-GATE", "required_instance_ids": ["I-7", "I-8"]}],
    }
    pep.write_json_new(base / "assignment.json", a)
    adigest = pep.file_digest(base / "assignment.json")

    # Results
    result_ids = []
    for iid, cid, key, desc in [
        ("I-7", "PEP-06-02-01", "valid_accepted", "Grader accepts valid NanoVMS binary"),
        ("I-8", "PEP-06-02-02", "noop_rejected", "Grader rejects no-op stub"),
    ]:
        r = {
            "kind": "result", "schema_version": "1.0.0", "id": f"R-{iid}",
            "instance_id": iid, "criterion_id": cid,
            "assignment_id": a["id"], "assignment_digest": adigest,
            "epoch_id": a["epoch_id"], "subject_digest": subject,
            "execution": "COMPLETED",
            "verdict": "PASS" if qualified[key] else "FAIL",
            "evidence_state": "CURRENT",
            "review_status": "ACCEPTED",
            "observed_at": stamp, "expires_at": None,
            "evidence_ids": ["EV-OBS"],
            "qualification_ids": ["Q-NANOVMS-GRADER"],
            "evaluator_id": "nanovms-outcome-grader",
            "evaluator_digest": evaluator_digest,
            "observation": {
                "summary": f"{desc}: {key}={qualified[key]}",
                "assertions_executed": 1,
                "modality": "DYNAMIC",
            },
            "supersedes": [],
        }
        pep.write_json_new(base / "results" / f"R-{iid}.json", r)
        result_ids.append(f"R-{iid}")

    # Assessment
    m = {
        "kind": "assessment", "schema_version": "1.0.0",
        "id": "ASSESS-NANOVMS-GRADER-20260915",
        "record_status": "OPERATIONAL",
        "assignment_id": a["id"],
        "assignment_digest": adigest,
        "epoch_id": a["epoch_id"],
        "subject_digest": subject,
        "catalog_digest": catalog_digest,
        "as_of": stamp,
        "result_ids": result_ids,
        "evidence_ids": ["EV-OBS"],
        "qualification_ids": ["Q-NANOVMS-GRADER"],
        "coverage_limitations": [
            "PEP-06-02-01 and PEP-06-02-02 only.",
            "Grader checks output patterns, not full functional correctness.",
        ],
        "registration_state": "NOT_REQUESTED",
    }
    pep.write_json_new(base / "assessment.json", m)

    return {
        "qualified": qualified,
        "assignment_id": a["id"],
        "binary_digest": file_sha256(binary),
        "positive_passed": positive["all_passed"],
        "negative_rejected": negative["all_rejected"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True, help="Path to nvms binary")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for grader bundle")
    args = parser.parse_args()

    if not args.binary.exists():
        print(json.dumps({"error": f"Binary not found: {args.binary}"}))
        return 1

    # Run controls
    positive = positive_control(args.binary)
    noop = create_noop_binary()
    negative = negative_control(noop)

    # Compute evaluator digest
    evaluator_digest = pep.file_digest(Path(__file__))

    # Write bundle
    result = write_grader_bundle(args.out, args.binary, positive, negative, evaluator_digest)

    print(json.dumps(result, indent=2))
    return 0 if result["qualified"]["valid_accepted"] and result["qualified"]["noop_rejected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
