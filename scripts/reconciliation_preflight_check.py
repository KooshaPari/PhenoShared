"""Individual check implementations for repository reconciliation preflight.

This module contains all preflight verification logic: checksum validation,
tar/bundle verification, snapshot comparison, git control and object
inspection, and current-state capture.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pheno.reconciliation.preflight.v1"
REMOTE_SCHEMA_VERSION = "pheno.reconciliation.remote-snapshot.v1"


class PreflightError(RuntimeError):
    """A safely reportable, fail-closed preflight error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


@dataclass(frozen=True)
class PreflightInputs:
    repo_root: Path
    packet: Path
    packet_checksum_manifest_sha256: str
    remote_snapshot: Path
    remote_snapshot_sha256: str
    expected_repository: str
    expected_default_branch: str
    expected_base_sha: str
    expected_local_sha: str
    expected_live_sha: str
    expected_branches: tuple[tuple[str, str], ...]
    quiescence_delay_ms: int = 250


@dataclass(frozen=True)
class FileState:
    kind: str
    size: int | None
    sha256: str | None
    raced: bool = False

    def fingerprint(self) -> tuple[str, int | None, str | None, bool]:
        return (self.kind, self.size, self.sha256, self.raced)


@dataclass(frozen=True)
class CurrentSnapshot:
    fingerprint: str
    local_head: str
    categories: Mapping[str, Mapping[str, Any]]
    captured_payload: Mapping[str, Any]
    git_controls: Mapping[str, Any]
    git_objects: Mapping[str, Any]
    race_count: int
    delta_paths: frozenset[str]


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _validate_sha(value: str, *, code: str = "INVALID_SHA") -> str:
    normalized = value.lower()
    if not _SHA_RE.fullmatch(normalized):
        raise PreflightError(code, "an expected Git object ID is invalid")
    return normalized


def _base_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "decision": "FAILED",
        "read_only": True,
        "network_used": False,
        "git_optional_locks": "0",
        "errors": [],
        "checks": {},
    }


# Re-export everything from sub-modules for backward compatibility.
from scripts.reconciliation_preflight_checks_infra import (  # noqa: E402, F401
    _STATIC_GIT_CONTROL_PATHS,
    _capture_current_state,
    _captured_payload_report,
    _category_report,
    _current_git_control_paths,
    _current_git_object_paths,
    _decode_nul_paths,
    _decode_unmerged_paths,
    _delta_total,
    _file_state,
    _git_control_report,
    _git_object_report,
    _run_git,
    _verify_local_graph,
)
from scripts.reconciliation_preflight_checks_security import (  # noqa: E402, F401
    _BUNDLE_HEADER_MAX_BYTES,
    _CAPTURE_FILE_MAX_BYTES,
    _CAPTURE_TOTAL_MAX_BYTES,
    _CHECKSUM_MANIFEST_MAX_BYTES,
    _CHECKSUM_RE,
    _PACKET_FILE_MAX_BYTES,
    _PACKET_TOTAL_MAX_BYTES,
    _REMOTE_SNAPSHOT_MAX_BYTES,
    _REQUIRED_PACKET_FILES,
    _SHA256_RE,
    _SHA_RE,
    _bundle_header,
    _expected_branch_map,
    _load_capture_manifest,
    _load_path_inventory,
    _load_recorded_exclusions,
    _normalize_tar_path,
    _packet_path,
    _read_packet_file,
    _read_regular_file_once,
    _remote_object,
    _require_exact_keys,
    _safe_relative_path,
    _valid_branch_name,
    _verify_bundle,
    _verify_checksums,
    _verify_packet,
    _verify_remote_snapshot,
    _verify_tar,
)
