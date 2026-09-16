"""Security checks for repository reconciliation preflight.

Packet path safety, checksum verification, capture manifest validation,
remote snapshot verification, and bundle integrity.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import tarfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.reconciliation_preflight_check import (
    PreflightError,
    _sha256_bytes,
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CHECKSUM_RE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
_REQUIRED_PACKET_FILES = {
    "HEAD.txt",
    "ignored.txt",
    "local-only.bundle",
    "pheno-harness-full.tar.gz",
    "source-files.after.cjson",
    "source-files.before.cjson",
    "untracked.txt",
}
_CHECKSUM_MANIFEST_MAX_BYTES = 4 * 1024 * 1024
_PACKET_FILE_MAX_BYTES = 256 * 1024 * 1024
_PACKET_TOTAL_MAX_BYTES = 512 * 1024 * 1024
_REMOTE_SNAPSHOT_MAX_BYTES = 4 * 1024 * 1024
_CAPTURE_FILE_MAX_BYTES = 256 * 1024 * 1024
_CAPTURE_TOTAL_MAX_BYTES = 1024 * 1024 * 1024
_BUNDLE_HEADER_MAX_BYTES = 1024 * 1024


def _safe_relative_path(value: str) -> str:
    if not value or "\\" in value or "\x00" in value:
        raise PreflightError("UNSAFE_PACKET_PATH", "packet contains an unsafe path")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise PreflightError("UNSAFE_PACKET_PATH", "packet contains an unsafe path")
    return candidate.as_posix()


def _packet_path(packet: Path, relative: str) -> Path:
    relative = _safe_relative_path(relative)
    root = packet.resolve(strict=True)
    unresolved = root
    for part in PurePosixPath(relative).parts:
        unresolved /= part
        if unresolved.is_symlink():
            raise PreflightError(
                "UNSAFE_PACKET_PATH", "packet files must not use symbolic links"
            )
    candidate = unresolved.resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PreflightError(
            "UNSAFE_PACKET_PATH", "packet contains an unsafe path"
        ) from exc
    if not candidate.is_file():
        raise PreflightError("PACKET_FILE_MISSING", "a packet file is missing")
    return candidate


def _read_regular_file_once(
    path: Path,
    max_bytes: int,
    *,
    unavailable_code: str,
    too_large_code: str,
    unsafe_code: str,
    raced_code: str,
    description: str,
) -> bytes:
    """Read one regular file through one descriptor and reject observable races."""

    try:
        before = path.lstat()
    except OSError as exc:
        raise PreflightError(unavailable_code, f"{description} is unavailable") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise PreflightError(unsafe_code, f"{description} must be a regular file")
    try:
        with path.open("rb") as handle:
            opened_before = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened_before.st_mode):
                raise PreflightError(
                    unsafe_code, f"{description} must be a regular file"
                )
            payload = handle.read(max_bytes + 1)
            opened_after = os.fstat(handle.fileno())
        after = path.lstat()
    except PreflightError:
        raise
    except OSError as exc:
        raise PreflightError(unavailable_code, f"{description} is unavailable") from exc
    if len(payload) > max_bytes:
        raise PreflightError(
            too_large_code, f"{description} exceeds the safe size bound"
        )

    def identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_size,
            value.st_mtime_ns,
        )

    if (
        identity(before) != identity(opened_before)
        or identity(opened_before) != identity(opened_after)
        or identity(opened_after) != identity(after)
        or len(payload) != opened_after.st_size
    ):
        raise PreflightError(raced_code, f"{description} changed while it was read")
    return payload


def _read_packet_file(packet: Path, relative: str, max_bytes: int) -> bytes:
    try:
        path = _packet_path(packet, relative)
    except PreflightError:
        raise
    except OSError as exc:
        raise PreflightError(
            "PACKET_FILE_MISSING", "preservation packet file is unavailable"
        ) from exc
    return _read_regular_file_once(
        path,
        max_bytes,
        unavailable_code="PACKET_FILE_MISSING",
        too_large_code="PACKET_FILE_TOO_LARGE",
        unsafe_code="UNSAFE_PACKET_PATH",
        raced_code="PACKET_FILE_RACED",
        description="preservation packet file",
    )


def _verify_checksums(
    packet: Path, expected_manifest_sha256: str
) -> tuple[dict[str, str], dict[str, bytes], dict[str, Any]]:
    # Look up the read function via the public re-export module so
    # monkey-patching tests that target
    # ``scripts.reconciliation_preflight._read_packet_file`` apply.
    import scripts.reconciliation_preflight as _preflight

    try:
        manifest_bytes = _preflight._read_packet_file(
            packet, "SHA256SUMS.txt", _CHECKSUM_MANIFEST_MAX_BYTES
        )
    except PreflightError as exc:
        if exc.code != "PACKET_FILE_MISSING":
            raise
        raise PreflightError(
            "CHECKSUM_MANIFEST_MISSING", "preservation checksum manifest is missing"
        ) from exc
    expected_manifest_sha256 = expected_manifest_sha256.lower()
    if _SHA256_RE.fullmatch(expected_manifest_sha256) is None:
        raise PreflightError(
            "CHECKSUM_MANIFEST_DIGEST_INVALID",
            "preservation checksum manifest trust anchor is invalid",
        )
    manifest_sha256 = _sha256_bytes(manifest_bytes)
    if manifest_sha256 != expected_manifest_sha256:
        raise PreflightError(
            "CHECKSUM_MANIFEST_DIGEST_MISMATCH",
            "preservation checksum manifest trust anchor does not match",
        )
    entries: dict[str, str] = {}
    try:
        lines = manifest_bytes.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise PreflightError(
            "CHECKSUM_MANIFEST_INVALID", "preservation checksum manifest is invalid"
        ) from exc
    for line in lines:
        match = _CHECKSUM_RE.fullmatch(line)
        if match is None:
            raise PreflightError(
                "CHECKSUM_MANIFEST_INVALID", "preservation checksum manifest is invalid"
            )
        expected, relative = match.groups()
        relative = _safe_relative_path(relative)
        if relative in entries:
            raise PreflightError(
                "CHECKSUM_ENTRY_DUPLICATE", "preservation checksum entry is duplicated"
            )
        entries[relative] = expected
    missing_required = _REQUIRED_PACKET_FILES - entries.keys()
    if missing_required:
        raise PreflightError(
            "CHECKSUM_COVERAGE_INCOMPLETE",
            "preservation checksum coverage is incomplete",
        )
    files: dict[str, bytes] = {}
    total_bytes = len(manifest_bytes)
    # Look up the size caps via the public re-export module so monkey-
    # patching tests can override them via
    # ``scripts.reconciliation_preflight._PACKET_FILE_MAX_BYTES`` /
    # ``_PACKET_TOTAL_MAX_BYTES``.
    import scripts.reconciliation_preflight as _preflight

    for relative, expected in entries.items():
        payload = (
            manifest_bytes
            if relative == "SHA256SUMS.txt"
            else _preflight._read_packet_file(
                packet, relative, _preflight._PACKET_FILE_MAX_BYTES
            )
        )
        if relative != "SHA256SUMS.txt":
            total_bytes += len(payload)
        if total_bytes > _preflight._PACKET_TOTAL_MAX_BYTES:
            raise PreflightError(
                "PACKET_TOTAL_TOO_LARGE",
                "preservation packet exceeds the safe total size bound",
            )
        actual = _sha256_bytes(payload)
        if actual != expected:
            raise PreflightError(
                "CHECKSUM_MISMATCH", "preservation checksum verification failed"
            )
        files[relative] = payload
    return (
        entries,
        files,
        {
            "manifest_sha256": expected_manifest_sha256,
            "checked": len(entries),
            "bytes": total_bytes,
            "mismatched": 0,
            "missing": 0,
        },
    )


def _load_capture_manifest(payload_bytes: bytes) -> dict[str, tuple[int, str]]:
    try:
        payload = json.loads(payload_bytes)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightError(
            "CAPTURE_MANIFEST_INVALID", "capture manifest is invalid"
        ) from exc
    if not isinstance(payload, list):
        raise PreflightError("CAPTURE_MANIFEST_INVALID", "capture manifest is invalid")
    records: dict[str, tuple[int, str]] = {}
    total_bytes = 0
    for item in payload:
        if not isinstance(item, dict):
            raise PreflightError(
                "CAPTURE_MANIFEST_INVALID", "capture manifest is invalid"
            )
        relative = _safe_relative_path(item.get("path", ""))
        byte_count = item.get("bytes")
        sha256 = item.get("sha256")
        if (
            isinstance(byte_count, bool)
            or not isinstance(byte_count, int)
            or byte_count < 0
            or byte_count > _CAPTURE_FILE_MAX_BYTES
            or not isinstance(sha256, str)
            or _SHA256_RE.fullmatch(sha256) is None
        ):
            raise PreflightError(
                "CAPTURE_MANIFEST_INVALID", "capture manifest is invalid"
            )
        if relative in records:
            raise PreflightError(
                "CAPTURE_PATH_DUPLICATE", "capture manifest path is duplicated"
            )
        total_bytes += byte_count
        if total_bytes > _CAPTURE_TOTAL_MAX_BYTES:
            raise PreflightError(
                "CAPTURE_MANIFEST_BOUNDS_EXCEEDED",
                "capture manifest exceeds the safe content bound",
            )
        records[relative] = (byte_count, sha256)
    return records


def _load_recorded_exclusions(
    packet_files: Mapping[str, bytes], checksums: Mapping[str, str]
) -> set[str]:
    name = "archive-exclusions.cjson"
    if name not in checksums:
        return set()
    try:
        payload = json.loads(packet_files[name])
    except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightError(
            "ARCHIVE_EXCLUSIONS_INVALID", "archive exclusion record is invalid"
        ) from exc
    if not isinstance(payload, list):
        raise PreflightError(
            "ARCHIVE_EXCLUSIONS_INVALID", "archive exclusion record is invalid"
        )
    exclusions: set[str] = set()
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise PreflightError(
                "ARCHIVE_EXCLUSIONS_INVALID", "archive exclusion record is invalid"
            )
        relative = _safe_relative_path(item["path"])
        if relative in exclusions:
            raise PreflightError(
                "ARCHIVE_EXCLUSIONS_INVALID", "archive exclusion record is invalid"
            )
        exclusions.add(relative)
    return exclusions


def _load_path_inventory(payload: bytes) -> set[str]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise PreflightError(
            "CAPTURE_PATH_INVENTORY_INVALID", "capture path inventory is invalid"
        ) from exc
    inventory: set[str] = set()
    for line in lines:
        relative = _safe_relative_path(line)
        if relative in inventory:
            raise PreflightError(
                "CAPTURE_PATH_INVENTORY_INVALID", "capture path inventory is invalid"
            )
        inventory.add(relative)
    return inventory


def _normalize_tar_path(name: str, repo_name: str, expected: Mapping[str, Any]) -> str:
    relative = _safe_relative_path(name)
    if relative in expected:
        return relative
    prefix = f"{repo_name}/"
    if relative.startswith(prefix):
        stripped = _safe_relative_path(relative[len(prefix) :])
        if stripped in expected:
            return stripped
    return relative


def _verify_tar(
    archive_bytes: bytes,
    repo_name: str,
    expected: Mapping[str, tuple[int, str]],
) -> dict[str, Any]:
    seen: dict[str, tuple[int, str]] = {}
    total_bytes = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as handle:
            for member in handle:
                if not member.isfile():
                    raise PreflightError(
                        "TAR_NON_REGULAR_ENTRY",
                        "preservation archive has a non-regular entry",
                    )
                relative = _normalize_tar_path(member.name, repo_name, expected)
                if member.size > _CAPTURE_FILE_MAX_BYTES:
                    raise PreflightError(
                        "TAR_CONTENT_TOO_LARGE",
                        "preservation archive exceeds the safe content bound",
                    )
                if total_bytes + member.size > _CAPTURE_TOTAL_MAX_BYTES:
                    raise PreflightError(
                        "TAR_CONTENT_TOO_LARGE",
                        "preservation archive exceeds the safe content bound",
                    )
                if relative in seen:
                    raise PreflightError(
                        "TAR_PATH_DUPLICATE", "preservation archive path is duplicated"
                    )
                stream = handle.extractfile(member)
                if stream is None:
                    raise PreflightError(
                        "TAR_READ_FAILED", "preservation archive is unreadable"
                    )
                digest = hashlib.sha256()
                byte_count = 0
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    byte_count += len(chunk)
                    digest.update(chunk)
                state = (byte_count, digest.hexdigest())
                seen[relative] = state
                total_bytes += byte_count
    except PreflightError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise PreflightError(
            "TAR_READ_FAILED", "preservation archive is unreadable"
        ) from exc
    if seen.keys() != expected.keys():
        raise PreflightError(
            "TAR_COVERAGE_MISMATCH",
            "preservation archive coverage does not match its manifest",
        )
    if any(seen[path] != expected[path] for path in expected):
        raise PreflightError(
            "TAR_CONTENT_MISMATCH",
            "preservation archive content does not match its manifest",
        )
    return {
        "files": len(seen),
        "bytes": total_bytes,
        "duplicates": 0,
        "missing": 0,
        "extra": 0,
        "content_mismatches": 0,
    }


# Re-export packet/bundle verification from sub-module.
from scripts.reconciliation_preflight_checks_packet import (  # noqa: E402, F401
    _bundle_header,
    _verify_bundle,
    _verify_packet,
)

# Re-export remote snapshot verification from sub-module.
from scripts.reconciliation_preflight_checks_security_remote import (  # noqa: E402, F401
    _expected_branch_map,
    _remote_object,
    _require_exact_keys,
    _valid_branch_name,
    _verify_remote_snapshot,
)
