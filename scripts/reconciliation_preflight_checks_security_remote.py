"""Remote snapshot verification for repository reconciliation preflight."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from scripts.reconciliation_preflight_check import (
    REMOTE_SCHEMA_VERSION,
    PreflightError,
    PreflightInputs,
    _canonical_bytes,
    _sha256_bytes,
    _validate_sha,
)
from scripts.reconciliation_preflight_checks_security import (
    _SHA256_RE,
    _read_regular_file_once,
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")


def _valid_branch_name(name: str) -> bool:
    if not name or name.startswith(("/", ".")) or name.endswith(("/", ".")):
        return False
    forbidden = {"..", "@{", "//"}
    if any(token in name for token in forbidden):
        return False
    return re.search(r"[\x00-\x20~^:?*\[]", name) is None


def _expected_branch_map(items: Iterable[tuple[str, str]]) -> dict[str, str]:

    branches: dict[str, str] = {}
    for name, raw_sha in items:
        if not _valid_branch_name(name) or name in branches:
            raise PreflightError(
                "EXPECTED_BRANCH_INVALID", "expected branch set is invalid"
            )
        branches[name] = _validate_sha(raw_sha)
    if not branches:
        raise PreflightError(
            "EXPECTED_BRANCH_MISSING", "expected branch set is required"
        )
    return branches


def _remote_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise PreflightError(
                "REMOTE_SNAPSHOT_DUPLICATE_KEY",
                "remote snapshot contains a duplicate key",
            )
        payload[key] = value
    return payload


def _require_exact_keys(
    payload: Mapping[str, Any], expected: set[str], *, code: str
) -> None:
    if set(payload) != expected:
        raise PreflightError(code, "remote snapshot has missing or unknown fields")


def _verify_remote_snapshot(inputs: PreflightInputs) -> dict[str, Any]:
    # Look up the size cap via the public re-export module so monkey-
    # patching tests can override it via
    # ``scripts.reconciliation_preflight._REMOTE_SNAPSHOT_MAX_BYTES``.
    import scripts.reconciliation_preflight as _preflight

    expected_digest = inputs.remote_snapshot_sha256.lower()
    if _SHA256_RE.fullmatch(expected_digest) is None:
        raise PreflightError(
            "REMOTE_SNAPSHOT_DIGEST_INVALID", "remote snapshot digest is invalid"
        )
    payload_bytes = _read_regular_file_once(
        inputs.remote_snapshot,
        _preflight._REMOTE_SNAPSHOT_MAX_BYTES,
        unavailable_code="REMOTE_SNAPSHOT_MISSING",
        too_large_code="REMOTE_SNAPSHOT_TOO_LARGE",
        unsafe_code="REMOTE_SNAPSHOT_PATH_UNSAFE",
        raced_code="REMOTE_SNAPSHOT_RACED",
        description="remote snapshot",
    )
    if _sha256_bytes(payload_bytes) != expected_digest:
        raise PreflightError(
            "REMOTE_SNAPSHOT_DIGEST_MISMATCH", "remote snapshot digest does not match"
        )
    try:
        payload = json.loads(payload_bytes, object_pairs_hook=_remote_object)
    except PreflightError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightError(
            "REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid"
        ) from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != REMOTE_SCHEMA_VERSION
    ):
        raise PreflightError("REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid")
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "captured_at_utc",
            "repository",
            "base_sha",
            "local_sha",
            "live_sha",
            "branches",
        },
        code="REMOTE_SNAPSHOT_FIELDS_INVALID",
    )
    repository = payload.get("repository")
    if not isinstance(repository, dict):
        raise PreflightError("REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid")
    _require_exact_keys(
        repository,
        {"full_name", "private", "archived", "default_branch"},
        code="REMOTE_REPOSITORY_FIELDS_INVALID",
    )
    if repository.get("full_name") != inputs.expected_repository:
        raise PreflightError(
            "REMOTE_REPOSITORY_MISMATCH", "remote repository identity does not match"
        )
    if repository.get("private") is not True or repository.get("archived") is not False:
        raise PreflightError(
            "REMOTE_SAFETY_STATE_MISMATCH",
            "remote repository safety state does not match",
        )
    if repository.get("default_branch") != inputs.expected_default_branch:
        raise PreflightError(
            "REMOTE_DEFAULT_BRANCH_MISMATCH", "remote default branch does not match"
        )
    captured_at = payload.get("captured_at_utc")
    if not isinstance(captured_at, str):
        raise PreflightError("REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid")
    try:
        parsed_time = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PreflightError(
            "REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid"
        ) from exc
    if parsed_time.tzinfo is None:
        raise PreflightError("REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid")
    expected_values = {
        "base_sha": inputs.expected_base_sha,
        "local_sha": inputs.expected_local_sha,
        "live_sha": inputs.expected_live_sha,
    }
    for key, expected in expected_values.items():
        raw = payload.get(key)
        if not isinstance(raw, str) or _validate_sha(raw) != expected:
            raise PreflightError(
                "REMOTE_GRAPH_MISMATCH", "remote reconciliation graph does not match"
            )
    raw_branches = payload.get("branches")
    if not isinstance(raw_branches, list):
        raise PreflightError("REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid")
    branches: dict[str, str] = {}
    for item in raw_branches:
        if not isinstance(item, dict):
            raise PreflightError(
                "REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid"
            )
        _require_exact_keys(
            item,
            {"name", "sha"},
            code="REMOTE_BRANCH_FIELDS_INVALID",
        )
        name, raw_sha = item.get("name"), item.get("sha")
        if (
            not isinstance(name, str)
            or not _valid_branch_name(name)
            or name in branches
            or not isinstance(raw_sha, str)
        ):
            raise PreflightError(
                "REMOTE_SNAPSHOT_INVALID", "remote snapshot is invalid"
            )
        branches[name] = _validate_sha(raw_sha)
    expected_branches = _expected_branch_map(inputs.expected_branches)
    if branches != expected_branches:
        raise PreflightError(
            "REMOTE_BRANCH_SET_MISMATCH", "remote branch set does not match"
        )
    if branches.get(inputs.expected_default_branch) != inputs.expected_live_sha:
        raise PreflightError(
            "REMOTE_DEFAULT_REF_MISMATCH", "remote default branch tip does not match"
        )
    return {
        "verified": True,
        "network_used": False,
        "snapshot_sha256": expected_digest,
        "captured_at_utc": captured_at,
        "repository_private": True,
        "repository_archived": False,
        "default_branch": inputs.expected_default_branch,
        "branch_count": len(branches),
        "branch_set_sha256": _sha256_bytes(_canonical_bytes(branches)),
        "base_sha": inputs.expected_base_sha,
        "local_sha": inputs.expected_local_sha,
        "live_sha": inputs.expected_live_sha,
    }
