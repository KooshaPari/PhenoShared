from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.validate_desktop_evidence import (
    EvidenceError,
    _canonical_sha256,
    validate,
    validate_perf_evidence_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "bench/results/desktop/desktop_nvidia_qwen35_live_20260801.json"
CONTRACT = ROOT / "config/desktop_nvidia_qwen35_lane.yaml"
VALIDATOR = ROOT / "scripts/validate_desktop_evidence.py"


def test_live_desktop_envelope_is_integrity_bound_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.validate_desktop_evidence._git_commit_exists", lambda _commit: False
    )
    result = validate(EVIDENCE, CONTRACT)

    assert result["valid"] is True
    assert result["status"] == "blocked"
    assert result["passed_gates"] < result["total_gates"]
    assert result["source_commit_reachable"] is False


def test_live_desktop_envelope_rejects_tampering(tmp_path: Path) -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    payload["model"]["quantization"] = "tampered"
    candidate = tmp_path / "evidence.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceError, match="hash mismatch"):
        validate(candidate, CONTRACT)


def test_evidence_contract_digest_normalizes_windows_line_endings(
    tmp_path: Path,
) -> None:
    """Evidence from a CRLF contract must validate on a Unix reviewer."""
    windows_contract = tmp_path / "lane-windows.yaml"
    windows_contract.write_bytes(CONTRACT.read_bytes().replace(b"\n", b"\r\n"))
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    from scripts.desktop_execution_preflight import canonical_contract_sha256

    payload["contract"]["sha256"] = canonical_contract_sha256(windows_contract)
    payload["artifact_integrity"]["result_artifact_sha256"] = ""
    payload["artifact_integrity"]["result_artifact_sha256"] = _canonical_sha256(payload)
    candidate = tmp_path / "evidence.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    assert validate(candidate, windows_contract)["valid"] is True


def test_live_desktop_envelope_rejects_unknown_promotion_gate(tmp_path: Path) -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    payload["promotion"]["gates"]["made_up_gate"] = False
    payload["artifact_integrity"]["result_artifact_sha256"] = ""
    from scripts.validate_desktop_evidence import _canonical_sha256

    payload["artifact_integrity"]["result_artifact_sha256"] = _canonical_sha256(payload)
    candidate = tmp_path / "evidence.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceError, match="promotion gates"):
        validate(candidate, CONTRACT)


@pytest.mark.parametrize("source_commit", ["", "not-a-git-commit"])
def test_live_desktop_envelope_rejects_malformed_source_commit(
    tmp_path: Path,
    source_commit: str,
) -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    payload["contract"]["source_commit"] = source_commit
    payload["artifact_integrity"]["result_artifact_sha256"] = ""
    from scripts.validate_desktop_evidence import _canonical_sha256

    payload["artifact_integrity"]["result_artifact_sha256"] = _canonical_sha256(payload)
    candidate = tmp_path / "evidence.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceError, match="source_commit must be a full SHA-1"):
        validate(candidate, CONTRACT)


def test_live_desktop_envelope_requires_a_local_source_commit_for_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    payload["promotion"]["gates"] = dict.fromkeys(payload["promotion"]["gates"], True)
    payload["promotion"]["status"] = "pass"
    payload["artifact_integrity"]["result_artifact_sha256"] = ""
    from scripts.validate_desktop_evidence import _canonical_sha256

    payload["artifact_integrity"]["result_artifact_sha256"] = _canonical_sha256(payload)
    candidate = tmp_path / "evidence.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.validate_desktop_evidence._git_commit_exists", lambda _commit: False
    )

    with pytest.raises(EvidenceError, match="source_commit is not a reachable commit"):
        validate(candidate, CONTRACT)


def test_perf_evidence_envelope_rejects_root_label_that_overstates_cells() -> None:
    """Root verified is valid only when every labelled result cell is verified."""
    perf = {
        "schema_version": "pheno.perf.v1",
        "evidence_label": "verified",
        "warmup": {
            "results": [
                {
                    "gen_ok": 1.0,
                    "pass_at_1": 1.0,
                    "verified_pass_at_1": 0.0,
                    "evidence_label": "reported",
                }
            ]
        },
        "levels": [
            {
                "results": [
                    {
                        "gen_ok": 1.0,
                        "pass_at_1": 1.0,
                        "verified_pass_at_1": 0.8,
                        "evidence_label": "verified",
                    }
                ]
            }
        ],
    }

    with pytest.raises(EvidenceError, match="root evidence_label"):
        validate_perf_evidence_envelope(perf)


def test_perf_evidence_envelope_rejects_verified_cell_without_metric_contract() -> None:
    """A verified label alone cannot stand in for the v0.2 result contract."""
    perf = {
        "schema_version": "pheno.perf.v1",
        "evidence_label": "verified",
        "warmup": {"results": [{"evidence_label": "verified"}]},
        "levels": [],
    }

    with pytest.raises(EvidenceError, match="metric fields"):
        validate_perf_evidence_envelope(perf)


def test_perf_evidence_envelope_rejects_out_of_range_cell_metrics() -> None:
    """Cell evidence follows the binary generation and bounded score contract."""
    perf = {
        "schema_version": "pheno.perf.v1",
        "evidence_label": "verified",
        "warmup": {
            "results": [
                {
                    "gen_ok": 2.0,
                    "pass_at_1": 2.0,
                    "verified_pass_at_1": float("inf"),
                    "evidence_label": "verified",
                }
            ]
        },
        "levels": [],
    }

    with pytest.raises(EvidenceError, match="metric fields"):
        validate_perf_evidence_envelope(perf)


def test_perf_evidence_envelope_rejects_non_object_result_cells() -> None:
    """Every listed result must carry the same validated cell contract."""
    valid_verified_cell = {
        "gen_ok": 1.0,
        "pass_at_1": 1.0,
        "verified_pass_at_1": 0.8,
        "evidence_label": "verified",
    }
    perf = {
        "schema_version": "pheno.perf.v1",
        "evidence_label": "verified",
        "warmup": {"results": [valid_verified_cell, None]},
        "levels": [],
    }

    with pytest.raises(EvidenceError, match="result cells"):
        validate_perf_evidence_envelope(perf)


def test_perf_evidence_envelope_rejects_success_metrics_on_error_cell() -> None:
    """A transport or generation error cannot also count as successful output."""
    perf = {
        "schema_version": "pheno.perf.v1",
        "evidence_label": "verified",
        "warmup": {
            "results": [
                {
                    "error": "endpoint refused request",
                    "gen_ok": 1.0,
                    "pass_at_1": 1.0,
                    "verified_pass_at_1": 0.8,
                    "evidence_label": "verified",
                }
            ]
        },
        "levels": [],
    }

    with pytest.raises(EvidenceError, match="error cell"):
        validate_perf_evidence_envelope(perf)


@pytest.mark.parametrize("bad_label", [[], {}])
def test_perf_evidence_envelope_rejects_non_string_labels(bad_label: object) -> None:
    """Malformed labels must use the validator's normal error path, not TypeError."""
    perf = {
        "schema_version": "pheno.perf.v1",
        "evidence_label": bad_label,
        "warmup": {"results": []},
        "levels": [],
    }

    with pytest.raises(EvidenceError, match="root evidence_label"):
        validate_perf_evidence_envelope(perf)


def test_evidence_validator_cli_runs_outside_repository_root(tmp_path: Path) -> None:
    """The executable bootstraps its own imports when launched by absolute path."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["valid"] is True
