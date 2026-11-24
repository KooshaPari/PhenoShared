"""Validate the no-launch desktop preflight required before live wrapper calls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/desktop_nvidia_qwen35_lane.yaml"
SCHEMA = "pheno.desktop-preflight.v1"
EXPECTED = {"primary": (1, 8000), "helper": (0, 8082)}
MINIMUM_FREE_MIB = 4096


class PreflightError(ValueError):
    """Raised when the execution preflight does not prove a safe topology."""


def _load(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise PreflightError("--preflight-record is required for --execute")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightError("preflight record is unreadable") from exc
    if not isinstance(payload, dict):
        raise PreflightError("preflight record root must be an object")
    return payload


def canonical_contract_sha256(path: Path) -> str:
    """Hash contract bytes after CRLF/CR normalization for Windows parity."""
    source = path.read_bytes()
    normalized = source.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def validate_execution_preflight(
    path: Path | None,
    runtime: str,
    base_url: str,
    *,
    contract_path: Path = CONTRACT,
) -> None:
    """Require a matching no-launch dual-GPU preflight before endpoint probing."""
    expected = EXPECTED.get(runtime)
    if expected is None:
        raise PreflightError(f"unsupported runtime: {runtime}")
    payload = _load(path)
    if payload.get("schema_version") != SCHEMA or payload.get("no_launch") is not True:
        raise PreflightError(
            "preflight must be a pheno.desktop-preflight.v1 no-launch record"
        )
    contract = payload.get("contract")
    if (
        not isinstance(contract, dict)
        or contract.get("path") != "config/desktop_nvidia_qwen35_lane.yaml"
        or contract.get("sha256") != canonical_contract_sha256(contract_path)
    ):
        raise PreflightError("preflight is not bound to the current lane contract")
    try:
        endpoint_port = urlparse(base_url).port
    except ValueError as exc:
        raise PreflightError("execution endpoint has an invalid port") from exc
    if endpoint_port != expected[1]:
        raise PreflightError(f"{runtime} endpoint must use port {expected[1]}")
    runtime_record = payload.get("runtime")
    runtime_port_key = f"{runtime}_port"
    if (
        not isinstance(runtime_record, dict)
        or runtime_record.get(runtime_port_key) != endpoint_port
    ):
        raise PreflightError(
            f"preflight runtime port must match the {runtime} endpoint"
        )
    ports = payload.get("ports")
    if not isinstance(ports, list) or not any(
        isinstance(port, dict)
        and port.get("port") == endpoint_port
        and port.get("available") is True
        for port in ports
    ):
        raise PreflightError(
            f"preflight must record available endpoint port {endpoint_port}"
        )
    devices = payload.get("devices")
    if not isinstance(devices, list):
        raise PreflightError("preflight devices must be a list")
    found = {
        device.get("role"): device for device in devices if isinstance(device, dict)
    }
    for role, index in (("helper", 0), ("primary", 1)):
        device = found.get(role)
        if not isinstance(device, dict) or device.get("physical_index") != index:
            raise PreflightError(
                f"preflight must include {role} physical GPU index {index}"
            )
        free_mib = device.get("free_mib")
        if (
            not isinstance(free_mib, int)
            or isinstance(free_mib, bool)
            or free_mib < MINIMUM_FREE_MIB
        ):
            raise PreflightError(
                f"preflight {role} GPU requires {MINIMUM_FREE_MIB} MiB free"
            )
