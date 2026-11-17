"""Strict benchmark-envelope contract tests.

Traces to: FR-HELIOS-IO-006 (truthful, tamper-evident benchmark evidence).
"""

import hashlib
import json
import subprocess
from copy import deepcopy
from importlib import import_module
from pathlib import Path

import pytest
from harness.benchmark_envelope import add_envelope, verify_envelope_integrity
from harness.interfaces import RepoManifest
from jsonschema import Draft202012Validator


def test_envelope_module_exposes_strict_contract_api() -> None:
    module = import_module("harness.benchmark_envelope")

    assert callable(getattr(module, "add_envelope", None))
    assert callable(getattr(module, "verify_envelope_integrity", None))


def _valid_envelope() -> dict:
    commands = [
        {
            "command": "pytest -q",
            "bucket": "test",
            "required": True,
            "cwd": ".",
            "source": "pyproject.toml",
            "rationale": "",
        }
    ]
    return add_envelope(
        {
            "commands": commands,
            "runs": [
                {
                    "command": "pytest -q",
                    "returncode": 0,
                    "timed_out": False,
                    "duration_ms": 12,
                }
            ],
            "result_code": "PASS",
        },
        repo="helios-cli",
        plan_hash=hashlib.sha256(
            json.dumps(commands, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        subject_commit="a" * 40,
        subject_ref="main",
    )


def _schema_validator() -> Draft202012Validator:
    schema_path = Path(__file__).resolve().parents[1] / "schemas/benchmark_run.schema.json"
    return Draft202012Validator(json.loads(schema_path.read_text()))


def test_envelope_is_strict_truthful_and_self_consistent() -> None:
    # Traces to: FR-HELIOS-IO-006 (strict benchmark evidence).
    envelope = _valid_envelope()

    verify_envelope_integrity(envelope)
    assert envelope["signature"] == {
        "status": "unsigned",
        "algorithm": "none",
        "reason": "signing_authority_not_configured",
    }
    assert envelope["subject"]["commit"] == "a" * 40
    assert envelope["provenance"]["source_sha"] == envelope["subject"]["commit"]
    assert envelope["result"]["status"] == "passed"
    assert len(envelope["tasks"]) == 1
    assert envelope["runs"][0]["task_id"] == envelope["tasks"][0]["task_id"]


def test_schema_accepts_truthful_unsigned_envelope() -> None:
    # Traces to: FR-HELIOS-SCHEMA-001 (strict envelope schema).
    _schema_validator().validate(_valid_envelope())


def test_schema_rejects_placeholder_signature_claim() -> None:
    # Traces to: FR-HELIOS-SCHEMA-001 (truthful pre-signature contract).
    envelope = deepcopy(_valid_envelope())
    envelope["signature"] = {
        "algorithm": "placeholder",
        "key_id": "unconfigured",
        "signature_b64": "",
    }

    errors = list(_schema_validator().iter_errors(envelope))
    assert any(error.absolute_path and error.absolute_path[0] == "signature" for error in errors)


def test_schema_rejects_short_subject_provenance() -> None:
    # Traces to: FR-HELIOS-SCHEMA-001 (full source identity).
    envelope = deepcopy(_valid_envelope())
    envelope["subject"]["commit"] = "abc1234"
    envelope["provenance"]["source_sha"] = "abc1234"

    errors = list(_schema_validator().iter_errors(envelope))
    paths = {tuple(error.absolute_path) for error in errors}
    assert ("subject", "commit") in paths
    assert ("provenance", "source_sha") in paths


@pytest.mark.parametrize("commit", ["", "unknown", "abc1234", "g" * 40])
def test_envelope_rejects_unresolved_or_short_provenance(commit: str) -> None:
    # Traces to: FR-HELIOS-IO-006 (resolved full source identity).
    with pytest.raises(ValueError, match="resolved Git SHA"):
        add_envelope(
            {"result_code": "PASS"},
            repo="helios-cli",
            plan_hash="b" * 64,
            subject_commit=commit,
            subject_ref="main",
        )


def test_envelope_rejects_missing_source_ref() -> None:
    # Traces to: FR-HELIOS-IO-006 (resolved source ref).
    with pytest.raises(ValueError, match="resolved source ref"):
        add_envelope(
            {"result_code": "PASS"},
            repo="helios-cli",
            plan_hash="b" * 64,
            subject_commit="a" * 40,
            subject_ref="",
        )


def test_integrity_verifier_rejects_subject_tampering() -> None:
    # Traces to: FR-HELIOS-IO-006 (tamper detection).
    envelope = deepcopy(_valid_envelope())
    envelope["subject"]["repo"] = "other-repo"

    with pytest.raises(ValueError, match="deterministic identity"):
        verify_envelope_integrity(envelope)


def test_integrity_verifier_rejects_event_hash_tampering() -> None:
    # Traces to: FR-HELIOS-IO-006 (event hash integrity).
    envelope = deepcopy(_valid_envelope())
    envelope["events"][0]["payload_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="event payload hash"):
        verify_envelope_integrity(envelope)


def test_integrity_verifier_rejects_replay_hash_tampering() -> None:
    # Traces to: FR-HELIOS-IO-006 (replay integrity).
    envelope = deepcopy(_valid_envelope())
    envelope["result"]["replay_hash"] = "0" * 64

    with pytest.raises(ValueError, match="replay hash"):
        verify_envelope_integrity(envelope)


def test_integrity_verifier_rejects_provenance_mismatch() -> None:
    # Traces to: FR-HELIOS-IO-006 (provenance integrity).
    envelope = deepcopy(_valid_envelope())
    envelope["provenance"]["source_sha"] = "c" * 40

    with pytest.raises(ValueError, match="provenance"):
        verify_envelope_integrity(envelope)


def test_integrity_verifier_rejects_plan_content_tampering() -> None:
    envelope = deepcopy(_valid_envelope())
    for field in ("plan", "commands", "tasks"):
        envelope[field][0]["command"] = "pytest --collect-only"

    with pytest.raises(ValueError, match="plan hash"):
        verify_envelope_integrity(envelope)


def test_budget_skipped_run_is_non_passing() -> None:
    commands = [
        {
            "command": "pytest -q",
            "bucket": "test",
            "required": True,
            "cwd": ".",
            "source": "pyproject.toml",
            "rationale": "",
        }
    ]
    envelope = add_envelope(
        {
            "commands": commands,
            "runs": [
                {
                    "command": "pytest -q",
                    "returncode": 0,
                    "timed_out": False,
                    "skipped": True,
                    "duration_ms": 0,
                }
            ],
            "result_code": "WARN",
        },
        repo="helios-cli",
        plan_hash=hashlib.sha256(
            json.dumps(commands, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        subject_commit="a" * 40,
        subject_ref="main",
    )

    assert envelope["runs"][0]["status"] == "skipped"
    assert envelope["result"]["status"] == "cancelled"
    _schema_validator().validate(envelope)


def test_run_task_identity_survives_canonical_plan_sorting() -> None:
    commands = [
        {
            "command": "z-last",
            "bucket": "test",
            "required": True,
            "cwd": ".",
            "source": "fixture",
            "rationale": "",
        },
        {
            "command": "a-first",
            "bucket": "build",
            "required": True,
            "cwd": ".",
            "source": "fixture",
            "rationale": "",
        },
    ]
    canonical = sorted(
        commands,
        key=lambda entry: (
            entry["bucket"],
            entry["required"],
            entry["command"],
            entry["source"],
            entry["cwd"],
        ),
    )
    plan_hash = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    envelope = add_envelope(
        {
            "commands": commands,
            "runs": [
                {"command": "z-last", "returncode": 0, "duration_ms": 1},
                {"command": "a-first", "returncode": 0, "duration_ms": 1},
            ],
            "result_code": "PASS",
        },
        repo="helios-cli",
        plan_hash=plan_hash,
        subject_commit="a" * 40,
        subject_ref="main",
    )
    task_ids_by_command = {task["command"]: task["task_id"] for task in envelope["tasks"]}

    assert all(run["task_id"] == task_ids_by_command[run["command"]] for run in envelope["runs"])


def test_integrity_verifier_rejects_placeholder_signature_claim() -> None:
    # Traces to: FR-HELIOS-IO-006 (truthful pre-signature state).
    envelope = deepcopy(_valid_envelope())
    envelope["signature"] = {
        "status": "unsigned",
        "algorithm": "placeholder",
        "key_id": "unconfigured",
        "signature_b64": "",
    }

    with pytest.raises(ValueError, match="unsigned signature state"):
        verify_envelope_integrity(envelope)


def test_replay_hash_excludes_collection_timestamps() -> None:
    # Traces to: FR-HELIOS-IO-006 (deterministic replay hash).
    first = _valid_envelope()
    second = _valid_envelope()

    assert first["result"]["replay_hash"] == second["result"]["replay_hash"]


def test_repo_manifest_missing_remote_is_quiet(tmp_path: Path, capfd) -> None:
    # Traces to: FR-HELIOS-IO-006 (truthful unresolved provenance without Git noise).
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "tests@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Harness tests"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-qm", "fixture"], check=True
    )

    manifest = RepoManifest.from_repo(tmp_path, "fixture")

    assert manifest.commit
    assert "No such remote" not in capfd.readouterr().err
