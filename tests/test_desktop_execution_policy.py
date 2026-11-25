from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from scripts import run_desktop_agentic_fixture, run_desktop_lane_eval
from scripts.desktop_execution_preflight import (
    canonical_contract_sha256,
    validate_execution_preflight,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("module", "extra_args"),
    [
        (
            run_desktop_lane_eval,
            ["--manifest-output", "manifest.json"],
        ),
        (run_desktop_agentic_fixture, []),
    ],
)
def test_execute_is_blocked_by_paused_contract_before_endpoint_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: object,
    extra_args: list[str],
) -> None:
    """A window ID cannot override a contract that forbids live execution."""
    endpoint_probed = False

    def unexpected_endpoint_probe(*args: object, **kwargs: object) -> list[str]:
        nonlocal endpoint_probed
        endpoint_probed = True
        raise AssertionError("execution policy must block before an endpoint probe")

    monkeypatch.setattr(module, "_endpoint_models", unexpected_endpoint_probe)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "desktop-wrapper",
            "--runtime",
            "primary",
            "--window-id",
            "sponsor-window-123",
            "--output",
            str(tmp_path / "result.json"),
            "--execute",
            *[
                value if value != "manifest.json" else str(tmp_path / value)
                for value in extra_args
            ],
        ],
    )

    with pytest.raises(SystemExit, match="execution policy"):
        module.main()

    assert endpoint_probed is False


def test_preflight_accepts_only_a_matching_two_device_record(tmp_path: Path) -> None:
    """A valid record binds both physical devices and the selected endpoint."""
    contract = tmp_path / "contract.yaml"
    contract.write_bytes(run_desktop_lane_eval.CONTRACT.read_bytes())
    record = {
        "schema_version": "pheno.desktop-preflight.v1",
        "no_launch": True,
        "contract": {
            "path": "config/desktop_nvidia_qwen35_lane.yaml",
            "sha256": canonical_contract_sha256(contract),
        },
        "devices": [
            {"role": "helper", "physical_index": 0, "free_mib": 4096},
            {"role": "primary", "physical_index": 1, "free_mib": 4096},
        ],
        "ports": [
            {"port": 8082, "available": True},
            {"port": 8000, "available": True},
        ],
        "runtime": {
            "primary_runtime": "vllm",
            "helper_port": 8082,
            "primary_port": 8000,
        },
    }
    path = tmp_path / "preflight.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    validate_execution_preflight(
        path,
        "primary",
        "http://127.0.0.1:8000",
        contract_path=contract,
    )


def test_preflight_rejects_a_runtime_record_with_a_mismatched_endpoint_port(
    tmp_path: Path,
) -> None:
    """A record from a custom-port launcher run cannot authorize the default endpoint."""
    contract = tmp_path / "contract.yaml"
    contract.write_bytes(run_desktop_lane_eval.CONTRACT.read_bytes())
    record = {
        "schema_version": "pheno.desktop-preflight.v1",
        "no_launch": True,
        "contract": {
            "path": "config/desktop_nvidia_qwen35_lane.yaml",
            "sha256": canonical_contract_sha256(contract),
        },
        "devices": [
            {"role": "helper", "physical_index": 0, "free_mib": 4096},
            {"role": "primary", "physical_index": 1, "free_mib": 4096},
        ],
        "ports": [
            {"port": 8082, "available": True},
            {"port": 9000, "available": True},
        ],
        "runtime": {
            "primary_runtime": "vllm",
            "helper_port": 8082,
            "primary_port": 9000,
        },
    }
    path = tmp_path / "preflight.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(Exception, match="runtime port"):
        validate_execution_preflight(
            path,
            "primary",
            "http://127.0.0.1:8000",
            contract_path=contract,
        )


def test_preflight_contract_hash_is_stable_across_windows_line_endings(
    tmp_path: Path,
) -> None:
    """A Windows launcher record must bind the same contract on Unix CI."""
    unix = tmp_path / "contract-unix.yaml"
    windows = tmp_path / "contract-windows.yaml"
    unix.write_bytes(
        b"status: planning_only\nexecution_policy:\n  allow_model_inference: false\n"
    )
    windows.write_bytes(
        b"status: planning_only\r\nexecution_policy:\r\n  allow_model_inference: false\r\n"
    )

    assert canonical_contract_sha256(unix) == canonical_contract_sha256(windows)


@pytest.mark.parametrize(
    ("module", "extra_args"),
    [
        (run_desktop_lane_eval, ["--manifest-output", "manifest.json"]),
        (run_desktop_agentic_fixture, []),
    ],
)
def test_active_contract_requires_no_launch_preflight_before_endpoint_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: object,
    extra_args: list[str],
) -> None:
    """An active policy still cannot reach an endpoint without a device preflight."""
    contract = yaml.safe_load(
        run_desktop_lane_eval.CONTRACT.read_text(encoding="utf-8")
    )
    contract["status"] = "active"
    contract["execution_policy"]["allow_model_inference"] = True
    contract["execution_policy"]["allow_benchmark_execution"] = True
    contract_path = tmp_path / "active-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract), encoding="utf-8")
    monkeypatch.setattr(module, "CONTRACT", contract_path)

    endpoint_probed = False

    def unexpected_endpoint_probe(*args: object, **kwargs: object) -> list[str]:
        nonlocal endpoint_probed
        endpoint_probed = True
        raise AssertionError("missing preflight must block before endpoint probe")

    monkeypatch.setattr(module, "_endpoint_models", unexpected_endpoint_probe)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "desktop-wrapper",
            "--runtime",
            "primary",
            "--window-id",
            "sponsor-window-123",
            "--output",
            str(tmp_path / "result.json"),
            "--execute",
            *[
                value if value != "manifest.json" else str(tmp_path / value)
                for value in extra_args
            ],
        ],
    )

    with pytest.raises(SystemExit, match="preflight"):
        module.main()

    assert endpoint_probed is False


@pytest.mark.parametrize(
    ("module", "extra_args"),
    [
        (run_desktop_lane_eval, ["--manifest-output", "manifest.json"]),
        (run_desktop_agentic_fixture, []),
    ],
)
def test_valid_policy_and_preflight_still_require_owner_issued_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module: object,
    extra_args: list[str],
) -> None:
    """A caller-provided window ID and topology record cannot authorize a run."""
    contract = yaml.safe_load(
        run_desktop_lane_eval.CONTRACT.read_text(encoding="utf-8")
    )
    contract["status"] = "active"
    contract["execution_policy"]["allow_model_inference"] = True
    contract["execution_policy"]["allow_benchmark_execution"] = True
    contract_path = tmp_path / "active-contract.yaml"
    contract_path.write_text(yaml.safe_dump(contract), encoding="utf-8")
    monkeypatch.setattr(module, "CONTRACT", contract_path)

    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(
        json.dumps(
            {
                "schema_version": "pheno.desktop-preflight.v1",
                "no_launch": True,
                "contract": {
                    "path": "config/desktop_nvidia_qwen35_lane.yaml",
                    "sha256": canonical_contract_sha256(contract_path),
                },
                "devices": [
                    {"role": "helper", "physical_index": 0, "free_mib": 4096},
                    {"role": "primary", "physical_index": 1, "free_mib": 4096},
                ],
                "ports": [
                    {"port": 8082, "available": True},
                    {"port": 8000, "available": True},
                ],
                "runtime": {
                    "primary_runtime": "vllm",
                    "helper_port": 8082,
                    "primary_port": 8000,
                },
            }
        ),
        encoding="utf-8",
    )

    endpoint_probed = False

    def unexpected_endpoint_probe(*args: object, **kwargs: object) -> list[str]:
        nonlocal endpoint_probed
        endpoint_probed = True
        raise AssertionError("authority must block before endpoint probing")

    monkeypatch.setattr(module, "_endpoint_models", unexpected_endpoint_probe)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "desktop-wrapper",
            "--runtime",
            "primary",
            "--window-id",
            "caller-string-is-not-authority",
            "--output",
            str(tmp_path / "result.json"),
            "--execute",
            "--preflight-record",
            str(preflight_path),
            *[
                value if value != "manifest.json" else str(tmp_path / value)
                for value in extra_args
            ],
        ],
    )

    with pytest.raises(SystemExit, match="owner-issued authority"):
        module.main()

    assert endpoint_probed is False
