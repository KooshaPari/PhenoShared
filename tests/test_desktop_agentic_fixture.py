from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import run_desktop_agentic_fixture
from scripts.run_desktop_agentic_fixture import (
    CANONICAL_MODEL,
    _build_request,
    _is_qwen35_model,
    _validate_tool_call_response,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_desktop_agentic_fixture.py"


def test_agentic_request_forces_the_canonical_tool() -> None:
    body = _build_request(CANONICAL_MODEL)

    assert body["model"] == CANONICAL_MODEL
    assert body["stream"] is False
    assert body["tool_choice"] == {
        "type": "function",
        "function": {"name": "get_runtime_status"},
    }
    assert body["tools"][0]["function"]["name"] == "get_runtime_status"


def test_agentic_fixture_accepts_the_observed_desktop_qwen35_alias() -> None:
    assert _is_qwen35_model("qwen35-08b") is True
    assert _is_qwen35_model("Qwen/Qwen2.5-0.5B") is False


def test_agentic_response_requires_the_expected_tool_and_arguments() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_001",
                            "type": "function",
                            "function": {
                                "name": "get_runtime_status",
                                "arguments": '{"component":"runtime"}',
                            },
                        }
                    ]
                }
            }
        ]
    }

    result = _validate_tool_call_response(payload)

    assert result["passed"] is True
    assert result["tool_name"] == "get_runtime_status"
    assert result["arguments"] == {"component": "runtime"}


def test_agentic_response_rejects_wrong_tool() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_001",
                            "type": "function",
                            "function": {
                                "name": "shell",
                                "arguments": "{}",
                            },
                        }
                    ]
                }
            }
        ]
    }

    result = _validate_tool_call_response(payload)

    assert result["passed"] is False
    assert "get_runtime_status" in result["error"]


def test_agentic_fixture_is_dry_run_by_default(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime",
            "helper",
            "--window-id",
            "desktop-test-window",
            "--output",
            str(tmp_path / "agentic.json"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    plan = json.loads(result.stdout)
    assert plan["execute"] is False
    assert plan["request_model"] == CANONICAL_MODEL
    assert not (tmp_path / "agentic.json").exists()


def test_agentic_fixture_contract_digest_normalizes_windows_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows line endings must not change the contract identity."""
    unix = tmp_path / "lane-unix.yaml"
    windows = tmp_path / "lane-windows.yaml"
    unix.write_bytes(
        b"status: planning_only\nexecution_policy:\n  allow_model_inference: false\n"
    )
    windows.write_bytes(
        b"status: planning_only\r\nexecution_policy:\r\n  allow_model_inference: false\r\n"
    )

    monkeypatch.setattr(run_desktop_agentic_fixture, "CONTRACT", unix)
    unix_digest = run_desktop_agentic_fixture._contract_sha256()
    monkeypatch.setattr(run_desktop_agentic_fixture, "CONTRACT", windows)

    assert unix_digest == run_desktop_agentic_fixture._contract_sha256()
