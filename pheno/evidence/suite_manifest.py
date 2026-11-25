"""Content-addressed evaluator suite manifests derived from pinned Git trees.

The contract records task identities and descriptor blob identities only. It
does not contain task instructions, solutions, test bodies, images, or other
dataset artifacts, and it cannot authorize benchmark execution.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from .contracts import ContractError, canonical_json_bytes, sha256_hex

SUITE_MANIFEST_SCHEMA_VERSION = "pheno.eval.suite-tree-manifest.v1"
MAX_TASKS = 10_000
MAX_TREE_ENTRIES = 200_000
_SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_SUITE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,255}$")
_PATH_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,255}$")


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _exact_fields(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    if set(value) != expected:
        raise ContractError(f"{path} fields do not match the contract")


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _sha(value: Any, path: str) -> str:
    result = _text(value, path).lower()
    if _SHA.fullmatch(result) is None:
        raise ContractError(f"{path} must be a full Git object ID")
    return result


def _timestamp(value: Any, path: str) -> str:
    result = _text(value, path)
    try:
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{path} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{path} must include a timezone")
    return parsed.astimezone(UTC).isoformat()


def _repository_url(value: Any) -> str:
    result = _text(value, "source.repository_url")
    parsed = urlparse(result)
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() != "github.com"
        or parsed.query
        or parsed.fragment
    ):
        raise ContractError("source.repository_url must be an exact HTTPS GitHub URL")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or any(_PATH_PART.fullmatch(part) is None for part in parts):
        raise ContractError("source.repository_url must identify one owner/repository")
    return f"https://github.com/{parts[0]}/{parts[1]}"


def _relative_path(value: Any, path: str, *, single_component: bool = False) -> str:
    result = _text(value, path)
    if "\\" in result or result.startswith("/") or result.endswith("/"):
        raise ContractError(f"{path} must be a normalized relative POSIX path")
    parts = result.split("/")
    if (
        not parts
        or (single_component and len(parts) != 1)
        or any(part in {"", ".", ".."} for part in parts)
        or any(_PATH_PART.fullmatch(part) is None for part in parts)
    ):
        raise ContractError(f"{path} must be a normalized relative POSIX path")
    return result


def task_ids_sha256(task_ids: Sequence[str]) -> str:
    """Hash the exact sorted task-ID array used by suite locks."""

    return sha256_hex(canonical_json_bytes(list(task_ids)))


def task_manifest_sha256(
    task_root_sha: str, descriptors: Sequence[Mapping[str, Any]]
) -> str:
    """Hash the task subtree identity and every immediate task descriptor."""

    return sha256_hex(
        canonical_json_bytes(
            {
                "descriptors": [dict(item) for item in descriptors],
                "task_root_sha": task_root_sha,
            }
        )
    )


def suite_manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """Hash a manifest while excluding its self-hash field."""

    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    return sha256_hex(canonical_json_bytes(payload))


def validate_suite_tree_manifest(payload: Any) -> dict[str, Any]:
    """Validate and recompute a suite-tree manifest."""

    root = _object(payload, "manifest")
    _exact_fields(
        root,
        {
            "schema_version",
            "suite_id",
            "source",
            "task_layout",
            "task_count",
            "task_ids",
            "descriptors",
            "task_ids_sha256",
            "task_manifest_sha256",
            "manifest_sha256",
            "metadata_only",
            "artifact_download",
            "execution_authorized",
        },
        "manifest",
    )
    if root.get("schema_version") != SUITE_MANIFEST_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {SUITE_MANIFEST_SCHEMA_VERSION}")
    suite_id = _text(root.get("suite_id"), "suite_id")
    if _SUITE_ID.fullmatch(suite_id) is None:
        raise ContractError("suite_id is invalid")
    if root.get("metadata_only") is not True:
        raise ContractError("metadata_only must be true")
    if root.get("artifact_download") is not False:
        raise ContractError("artifact_download must be false")
    if root.get("execution_authorized") is not False:
        raise ContractError("execution_authorized must be false")

    source = _object(root.get("source"), "source")
    _exact_fields(
        source,
        {
            "repository_url",
            "commit_sha",
            "tree_sha",
            "task_root_sha",
            "commit_verified",
            "tree_truncated",
            "double_observed",
            "observed_at",
        },
        "source",
    )
    _repository_url(source.get("repository_url"))
    _sha(source.get("commit_sha"), "source.commit_sha")
    _sha(source.get("tree_sha"), "source.tree_sha")
    task_root_sha = _sha(source.get("task_root_sha"), "source.task_root_sha")
    if not isinstance(source.get("commit_verified"), bool):
        raise ContractError("source.commit_verified must be boolean")
    if source.get("tree_truncated") is not False:
        raise ContractError("source.tree_truncated must be false")
    if source.get("double_observed") is not True:
        raise ContractError("source.double_observed must be true")
    _timestamp(source.get("observed_at"), "source.observed_at")

    layout = _object(root.get("task_layout"), "task_layout")
    _exact_fields(layout, {"task_root", "descriptor_name"}, "task_layout")
    task_root = _relative_path(
        layout.get("task_root"), "task_layout.task_root", single_component=True
    )
    descriptor_name = _relative_path(
        layout.get("descriptor_name"),
        "task_layout.descriptor_name",
        single_component=True,
    )

    count = root.get("task_count")
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or not 1 <= count <= MAX_TASKS
    ):
        raise ContractError(f"task_count must be between 1 and {MAX_TASKS}")
    task_ids = root.get("task_ids")
    if not isinstance(task_ids, list) or len(task_ids) != count:
        raise ContractError("task_ids length must equal task_count")
    normalized_ids: list[str] = []
    for index, value in enumerate(task_ids):
        task_id = _text(value, f"task_ids[{index}]")
        if _TASK_ID.fullmatch(task_id) is None:
            raise ContractError(f"task_ids[{index}] is invalid")
        normalized_ids.append(task_id)
    if normalized_ids != sorted(set(normalized_ids)):
        raise ContractError("task_ids must be unique and sorted")

    raw_descriptors = root.get("descriptors")
    if not isinstance(raw_descriptors, list) or len(raw_descriptors) != count:
        raise ContractError("descriptors length must equal task_count")
    descriptors: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_descriptors):
        item = _object(raw, f"descriptors[{index}]")
        _exact_fields(
            item,
            {"task_id", "path", "blob_sha", "bytes"},
            f"descriptors[{index}]",
        )
        task_id = _text(item.get("task_id"), f"descriptors[{index}].task_id")
        path = _relative_path(item.get("path"), f"descriptors[{index}].path")
        expected_path = f"{task_root}/{task_id}/{descriptor_name}"
        if path != expected_path:
            raise ContractError(f"descriptors[{index}].path does not match its task")
        size = item.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ContractError(f"descriptors[{index}].bytes must be nonnegative")
        descriptors.append(
            {
                "task_id": task_id,
                "path": path,
                "blob_sha": _sha(
                    item.get("blob_sha"), f"descriptors[{index}].blob_sha"
                ),
                "bytes": size,
            }
        )
    if [item["task_id"] for item in descriptors] != normalized_ids:
        raise ContractError("descriptors must be sorted one-to-one with task_ids")

    expected_ids_hash = task_ids_sha256(normalized_ids)
    if root.get("task_ids_sha256") != expected_ids_hash:
        raise ContractError("task_ids_sha256 does not match task_ids")
    expected_manifest_hash = task_manifest_sha256(task_root_sha, descriptors)
    if root.get("task_manifest_sha256") != expected_manifest_hash:
        raise ContractError("task_manifest_sha256 does not match descriptors")
    expected_self_hash = suite_manifest_sha256(root)
    if root.get("manifest_sha256") != expected_self_hash:
        raise ContractError("manifest_sha256 does not match the manifest")
    return dict(root)


def build_suite_tree_manifest(
    *,
    suite_id: str,
    repository_url: str,
    commit_sha: str,
    tree_sha: str,
    commit_verified: bool,
    observed_at: str,
    tree_payload: Mapping[str, Any],
    task_root: str = "tasks",
    descriptor_name: str = "task.toml",
    expected_task_count: int | None = None,
) -> dict[str, Any]:
    """Build a compact manifest from one double-observed GitHub tree payload."""

    if not isinstance(tree_payload, Mapping):
        raise ContractError("GitHub tree payload must be an object")
    if tree_payload.get("truncated") is not False:
        raise ContractError("GitHub recursive tree is truncated")
    normalized_tree_sha = _sha(tree_sha, "source.tree_sha")
    if _sha(tree_payload.get("sha"), "tree.sha") != normalized_tree_sha:
        raise ContractError("GitHub tree SHA does not match the pinned commit")
    normalized_root = _relative_path(task_root, "task_root", single_component=True)
    normalized_descriptor = _relative_path(
        descriptor_name, "descriptor_name", single_component=True
    )
    raw_entries = tree_payload.get("tree")
    if (
        not isinstance(raw_entries, list)
        or not 1 <= len(raw_entries) <= MAX_TREE_ENTRIES
    ):
        raise ContractError("GitHub tree entries violate the size bound")

    task_root_shas: list[str] = []
    descriptors: list[dict[str, Any]] = []
    suffix = f"/{normalized_descriptor}"
    for index, raw in enumerate(raw_entries):
        item = _object(raw, f"tree[{index}]")
        path = item.get("path")
        entry_type = item.get("type")
        if path == normalized_root and entry_type == "tree":
            task_root_shas.append(_sha(item.get("sha"), f"tree[{index}].sha"))
            continue
        if not isinstance(path, str) or entry_type != "blob":
            continue
        prefix = f"{normalized_root}/"
        if not path.startswith(prefix) or not path.endswith(suffix):
            continue
        middle = path[len(prefix) : -len(suffix)]
        if "/" in middle or _TASK_ID.fullmatch(middle) is None:
            continue
        size = item.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ContractError("GitHub task descriptor is missing a valid size")
        descriptors.append(
            {
                "task_id": middle,
                "path": path,
                "blob_sha": _sha(item.get("sha"), f"tree[{index}].sha"),
                "bytes": size,
            }
        )
    if len(task_root_shas) != 1:
        raise ContractError("GitHub tree must contain one exact task root")
    descriptors.sort(key=lambda item: item["task_id"])
    task_ids = [item["task_id"] for item in descriptors]
    if len(task_ids) != len(set(task_ids)) or not task_ids:
        raise ContractError(
            "GitHub tree contains missing or duplicate task descriptors"
        )
    if expected_task_count is not None and len(task_ids) != expected_task_count:
        raise ContractError("GitHub task count does not match the expected lock count")

    manifest: dict[str, Any] = {
        "schema_version": SUITE_MANIFEST_SCHEMA_VERSION,
        "suite_id": suite_id,
        "source": {
            "repository_url": repository_url,
            "commit_sha": _sha(commit_sha, "source.commit_sha"),
            "tree_sha": normalized_tree_sha,
            "task_root_sha": task_root_shas[0],
            "commit_verified": commit_verified,
            "tree_truncated": False,
            "double_observed": True,
            "observed_at": _timestamp(observed_at, "source.observed_at"),
        },
        "task_layout": {
            "task_root": normalized_root,
            "descriptor_name": normalized_descriptor,
        },
        "task_count": len(task_ids),
        "task_ids": task_ids,
        "descriptors": descriptors,
        "task_ids_sha256": task_ids_sha256(task_ids),
        "task_manifest_sha256": task_manifest_sha256(task_root_shas[0], descriptors),
        "manifest_sha256": "",
        "metadata_only": True,
        "artifact_download": False,
        "execution_authorized": False,
    }
    manifest["manifest_sha256"] = suite_manifest_sha256(manifest)
    return validate_suite_tree_manifest(manifest)


__all__ = [
    "MAX_TASKS",
    "MAX_TREE_ENTRIES",
    "SUITE_MANIFEST_SCHEMA_VERSION",
    "build_suite_tree_manifest",
    "suite_manifest_sha256",
    "task_ids_sha256",
    "task_manifest_sha256",
    "validate_suite_tree_manifest",
]
