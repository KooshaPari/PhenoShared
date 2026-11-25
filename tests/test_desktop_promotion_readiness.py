from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.desktop_execution_preflight import canonical_contract_sha256
from scripts.desktop_promotion_readiness import build_report
from scripts.validate_desktop_evidence import EvidenceError

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "bench/results/desktop/desktop_nvidia_qwen35_live_20260801.json"
CONTRACT = ROOT / "config/desktop_nvidia_qwen35_lane.yaml"
SCRIPT = ROOT / "scripts/desktop_promotion_readiness.py"


def test_report_lists_canonical_unmet_gates_in_stable_order() -> None:
    report = build_report(EVIDENCE, CONTRACT)

    assert report["schema_version"] == "pheno.desktop-promotion-readiness.v1"
    assert report["valid_evidence"] is True
    assert report["promotion_status"] == "blocked"
    assert report["unmet_gates"] == [
        "harbor_or_eval_window_authorized",
        "repeated_result_envelope_with_no_fallback_ambiguity",
    ]
    assert (
        report["next_required_evidence"]
        == "primary repeated no-fallback result envelope"
    )
    assert report["preflight"] == {"present": False, "promotion_effect": "none"}


def test_no_launch_preflight_is_reported_but_never_counts_as_a_promotion_gate(
    tmp_path: Path,
) -> None:
    preflight = tmp_path / "preflight.json"
    preflight.write_text(
        json.dumps(
            {
                "schema_version": "pheno.desktop-preflight.v1",
                "no_launch": True,
                "contract": {
                    "path": "config/desktop_nvidia_qwen35_lane.yaml",
                    "sha256": canonical_contract_sha256(CONTRACT),
                },
            }
        ),
        encoding="utf-8",
    )

    report = build_report(EVIDENCE, CONTRACT, preflight)

    assert report["preflight"]["present"] is True
    assert report["preflight"]["schema_version"] == "pheno.desktop-preflight.v1"
    assert report["preflight"]["no_launch"] is True
    assert report["preflight"]["promotion_effect"] == "none"
    assert report["unmet_gates"] == [
        "harbor_or_eval_window_authorized",
        "repeated_result_envelope_with_no_fallback_ambiguity",
    ]


def test_report_rejects_a_no_launch_preflight_from_another_contract(
    tmp_path: Path,
) -> None:
    preflight = tmp_path / "preflight.json"
    preflight.write_text(
        json.dumps(
            {
                "schema_version": "pheno.desktop-preflight.v1",
                "no_launch": True,
                "contract": {
                    "path": "config/desktop_nvidia_qwen35_lane.yaml",
                    "sha256": "0" * 64,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvidenceError, match="not bound to the current lane contract"):
        build_report(EVIDENCE, CONTRACT, preflight)


def test_cli_is_directly_invocable_and_machine_readable() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)], text=True, capture_output=True, check=False
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["promotion_status"] == "blocked"


def test_cli_reports_an_unreadable_contract_as_json_error(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--contract", str(tmp_path / "missing.yaml")],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stderr == ""
    assert "valid" in json.loads(completed.stdout)
