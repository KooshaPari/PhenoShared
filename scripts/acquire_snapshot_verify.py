"""Verification logic for GitHub reconciliation snapshot acquisition.

This module contains repository validation, branch enumeration,
default ref verification, compare assertions, and observation assembly.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from scripts.acquire_snapshot_download import (
    BRANCH_FILTER,
    BRANCH_PAGE_SIZE,
    COMPARE_FILTER,
    DEFAULT_BRANCH_FILTER,
    MAX_BRANCH_PAGE_REQUESTS,
    REPOSITORY_FILTER,
    SnapshotError,
    SnapshotOptions,
    _GhClient,
    _Observation,
    _require_exact_keys,
    _valid_branch_name,
    _validate_sha,
)


def _validate_options(options: SnapshotOptions) -> SnapshotOptions:
    from scripts.acquire_snapshot_download import REPOSITORY_RE

    if REPOSITORY_RE.fullmatch(options.repository) is None:
        raise SnapshotError(
            "ARGUMENT_REPOSITORY_INVALID", "repository must be exact OWNER/NAME"
        )
    if not _valid_branch_name(options.expected_default_branch):
        raise SnapshotError(
            "ARGUMENT_BRANCH_INVALID", "expected default branch is invalid"
        )
    if not 1.0 <= options.timeout_seconds <= 120.0:
        raise SnapshotError(
            "ARGUMENT_TIMEOUT_INVALID", "timeout must be between 1 and 120 seconds"
        )
    if not 1 <= options.attempts <= 5:
        raise SnapshotError(
            "ARGUMENT_ATTEMPTS_INVALID", "attempts must be between 1 and 5"
        )
    base_sha = _validate_sha(options.base_sha)
    local_sha = _validate_sha(options.local_sha)
    expected_live_sha = (
        _validate_sha(options.expected_live_sha)
        if options.expected_live_sha is not None
        else None
    )
    branches: dict[str, str] = {}
    for name, raw_sha in options.expected_branches:
        if not _valid_branch_name(name) or name in branches:
            raise SnapshotError(
                "ARGUMENT_BRANCH_SET_INVALID", "expected branch set is invalid"
            )
        branches[name] = _validate_sha(raw_sha)
    if branches and options.expected_default_branch not in branches:
        raise SnapshotError(
            "ARGUMENT_BRANCH_SET_INVALID",
            "an exact expected branch set must include the default branch",
        )
    if (
        branches
        and expected_live_sha is not None
        and branches[options.expected_default_branch] != expected_live_sha
    ):
        raise SnapshotError(
            "ARGUMENT_BRANCH_SET_INVALID",
            "expected default-branch and live object IDs disagree",
        )
    return SnapshotOptions(
        repository=options.repository,
        expected_default_branch=options.expected_default_branch,
        base_sha=base_sha,
        local_sha=local_sha,
        expected_live_sha=expected_live_sha,
        expected_branches=tuple(sorted(branches.items())),
        timeout_seconds=float(options.timeout_seconds),
        attempts=options.attempts,
    )


def _repository(
    client: _GhClient, repository: str, default_branch: str
) -> dict[str, Any]:
    payload = client.get_json(f"repos/{repository}", REPOSITORY_FILTER)
    if not isinstance(payload, dict):
        raise SnapshotError(
            "REMOTE_REPOSITORY_INVALID", "GitHub repository response is invalid"
        )
    _require_exact_keys(
        payload,
        {"full_name", "private", "archived", "default_branch"},
        code="REMOTE_REPOSITORY_FIELDS_INVALID",
    )
    if payload["full_name"] != repository:
        raise SnapshotError(
            "REMOTE_REPOSITORY_MISMATCH", "GitHub repository identity changed"
        )
    if payload["private"] is not True or payload["archived"] is not False:
        raise SnapshotError(
            "REMOTE_SAFETY_STATE_MISMATCH",
            "GitHub repository is not private and unarchived",
        )
    if payload["default_branch"] != default_branch:
        raise SnapshotError(
            "REMOTE_DEFAULT_BRANCH_MISMATCH", "GitHub default branch changed"
        )
    return payload


def _branch_page(
    client: _GhClient, repository: str, page: int
) -> list[tuple[str, str]]:
    endpoint = f"repos/{repository}/branches?per_page={BRANCH_PAGE_SIZE}&page={page}"
    payload = client.get_json(endpoint, BRANCH_FILTER)
    if not isinstance(payload, list) or len(payload) > BRANCH_PAGE_SIZE:
        raise SnapshotError(
            "REMOTE_BRANCH_PAGE_INVALID", "GitHub branch page is invalid"
        )
    rows: list[tuple[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise SnapshotError(
                "REMOTE_BRANCH_PAGE_INVALID", "GitHub branch page is invalid"
            )
        _require_exact_keys(item, {"name", "sha"}, code="REMOTE_BRANCH_FIELDS_INVALID")
        name, raw_sha = item["name"], item["sha"]
        if not isinstance(name, str) or not _valid_branch_name(name):
            raise SnapshotError(
                "REMOTE_BRANCH_INVALID", "GitHub returned an invalid branch name"
            )
        if not isinstance(raw_sha, str):
            raise SnapshotError(
                "REMOTE_BRANCH_INVALID", "GitHub returned an invalid branch object ID"
            )
        rows.append((name, _validate_sha(raw_sha, code="REMOTE_BRANCH_INVALID")))
    return rows


def _branches(client: _GhClient, repository: str) -> tuple[tuple[str, str], ...]:
    branches: dict[str, str] = {}
    for page in range(1, MAX_BRANCH_PAGE_REQUESTS + 1):
        rows = _branch_page(client, repository, page)
        for name, sha in rows:
            if name in branches:
                raise SnapshotError(
                    "REMOTE_BRANCH_DUPLICATE", "GitHub branch enumeration is ambiguous"
                )
            branches[name] = sha
        if len(rows) < BRANCH_PAGE_SIZE:
            if not branches:
                raise SnapshotError(
                    "REMOTE_BRANCH_SET_EMPTY", "GitHub repository has no branches"
                )
            return tuple(sorted(branches.items()))
    raise SnapshotError(
        "REMOTE_BRANCH_LIMIT_EXCEEDED",
        "GitHub branch set exceeds the bounded acquisition limit",
    )


def _default_ref(
    client: _GhClient,
    repository: str,
    default_branch: str,
    expected_sha: str,
) -> None:
    encoded_branch = quote(default_branch, safe="")
    payload = client.get_json(
        f"repos/{repository}/branches/{encoded_branch}", DEFAULT_BRANCH_FILTER
    )
    if not isinstance(payload, dict):
        raise SnapshotError(
            "REMOTE_DEFAULT_REF_INVALID", "GitHub default branch response is invalid"
        )
    _require_exact_keys(
        payload, {"name", "sha"}, code="REMOTE_DEFAULT_REF_FIELDS_INVALID"
    )
    if payload.get("name") != default_branch or payload.get("sha") != expected_sha:
        raise SnapshotError(
            "REMOTE_DEFAULT_REF_MISMATCH", "GitHub default branch tip is inconsistent"
        )


def _observe(client: _GhClient, repository: str, default_branch: str) -> _Observation:
    metadata = _repository(client, repository, default_branch)
    branches = _branches(client, repository)
    branch_map = dict(branches)
    live_sha = branch_map.get(default_branch)
    if live_sha is None:
        raise SnapshotError(
            "REMOTE_DEFAULT_REF_MISSING", "GitHub default branch is absent"
        )
    _default_ref(client, repository, default_branch, live_sha)
    return _Observation(repository=metadata, branches=branches)


def _compare(client: _GhClient, repository: str, base_sha: str, live_sha: str) -> None:
    payload = client.get_json(
        f"repos/{repository}/compare/{base_sha}...{live_sha}?per_page=1&page=2",
        COMPARE_FILTER,
    )
    if not isinstance(payload, dict):
        raise SnapshotError(
            "REMOTE_COMPARE_INVALID", "GitHub compare response is invalid"
        )
    _require_exact_keys(
        payload,
        {
            "status",
            "ahead_by",
            "behind_by",
            "total_commits",
            "base_sha",
            "merge_base_sha",
        },
        code="REMOTE_COMPARE_FIELDS_INVALID",
    )
    counts = (payload["ahead_by"], payload["behind_by"], payload["total_commits"])
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in counts
    ):
        raise SnapshotError(
            "REMOTE_COMPARE_INVALID", "GitHub compare counts are invalid"
        )
    status, ahead_by, behind_by, total_commits = (
        payload["status"],
        payload["ahead_by"],
        payload["behind_by"],
        payload["total_commits"],
    )
    if (
        payload["base_sha"] != base_sha
        or payload["merge_base_sha"] != base_sha
        or status not in {"ahead", "identical"}
        or behind_by != 0
        or total_commits != ahead_by
        or (status == "ahead" and ahead_by == 0)
        or (status == "identical" and ahead_by != 0)
    ):
        raise SnapshotError(
            "REMOTE_COMPARE_MISMATCH",
            "the base is not the exact ancestor expected for the live tip",
        )


def _captured_at(clock: Callable[[], datetime]) -> str:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise SnapshotError("CLOCK_INVALID", "snapshot clock must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
