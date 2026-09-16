"""Immutable evaluator suite-lock validation.

Candidate locks may intentionally contain unresolved hashes, but then they are
non-scoreable.  Setting ``integrity.scoreable`` to true makes every immutable
identity and holdout field mandatory.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

from .contracts import ContractError, canonical_json_bytes, sha256_hex
from .redaction import contains_secret

SUITE_LOCK_SCHEMA_VERSION = "pheno.eval.suite-lock.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(f"{path} contains unknown fields: {unknown}")


def _text(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _hash(value: Any, path: str, *, nullable: bool = False) -> str | None:
    text = _text(value, path, nullable=nullable)
    if text is None:
        return None
    if not _SHA256.fullmatch(text):
        raise ContractError(f"{path} must be a SHA-256 digest")
    return text


def _git_sha(value: Any, path: str, *, nullable: bool = False) -> str | None:
    text = _text(value, path, nullable=nullable)
    if text is None:
        return None
    if not _GIT_SHA.fullmatch(text):
        raise ContractError(f"{path} must be a 40-character Git SHA")
    return text


def _timestamp(value: Any, path: str) -> None:
    text = _text(value, path)
    assert text is not None  # nosec B101
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{path} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{path} must include a timezone")


def _strings(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        raise ContractError(f"{path} must be an array")
    for index, item in enumerate(value):
        _text(item, f"{path}[{index}]")
    return list(value)


def _unique_strings(value: Any, path: str) -> list[str]:
    result = _strings(value, path)
    if len(result) != len(set(result)):
        raise ContractError(f"{path} must not contain duplicates")
    return result


def _artifact_paths(value: Any, path: str) -> list[str]:
    result = _unique_strings(value, path)
    for index, item in enumerate(result):
        normalized = item.removesuffix("/")
        candidate = PurePosixPath(normalized)
        raw_parts = normalized.split("/")
        if (
            not normalized
            or candidate.is_absolute()
            or "\\" in item
            or any(part in {"", ".", ".."} for part in raw_parts)
        ):
            raise ContractError(f"{path}[{index}] must be a safe relative POSIX path")
    return result


def suite_lock_scoreability_reasons(lock: Mapping[str, Any]) -> list[str]:
    """Return unresolved identities that prevent a candidate lock from scoring."""

    root = validate_suite_lock(lock, enforce_scoreable=False)
    reasons: list[str] = []
    dataset = root["dataset"]
    for field in (
        "task_ids_sha256",
        "task_manifest_sha256",
        "subset_manifest_sha256",
    ):
        if dataset.get(field) is None:
            reasons.append(f"dataset.{field} is unresolved")
    if not dataset.get("subset_ids"):
        reasons.append("dataset.subset_ids is unresolved")
    if (
        root["suite_id"] == "terminal-bench-2.1"
        and dataset.get("changed_task_ids_sha256") is None
    ):
        reasons.append("dataset.changed_task_ids_sha256 is unresolved")
    runner = root["runner"]
    if str(runner.get("version", "")).lower() in {"unknown", "unresolved"}:
        reasons.append("runner.version is unresolved")
    if runner.get("revision_sha") is None and runner.get("package_sha256") is None:
        reasons.append("runner immutable revision/package hash is unresolved")
    harness = root["harness"]
    for field in (
        "revision_sha",
        "system_prompt_sha256",
        "agent_config_sha256",
        "tool_definitions_sha256",
    ):
        if harness.get(field) is None:
            reasons.append(f"harness.{field} is unresolved")
    verifier = root["verifier"]
    if verifier.get("revision_sha") is None:
        reasons.append("verifier.revision_sha is unresolved")
    if not verifier.get("image_digests"):
        reasons.append("verifier.image_digests is unresolved")
    if verifier.get("separate_environment") is not True:
        reasons.append("verifier.separate_environment is not true")
    if not verifier.get("expected_artifacts"):
        reasons.append("verifier.expected_artifacts is unresolved")
    integrity = root["integrity"]
    if not integrity["held_out_from_training"]:
        reasons.append("held-out-from-training assertion is false")
    if integrity.get("holdout_manifest_sha256") is None:
        reasons.append("integrity.holdout_manifest_sha256 is unresolved")
    if str(root["source"].get("license_spdx", "")).lower() in {
        "unknown",
        "unresolved",
    }:
        reasons.append("source.license_spdx is unresolved")
    reasons.extend(str(reason) for reason in integrity.get("unverified_reasons", []))
    return list(dict.fromkeys(reasons))


def validate_suite_lock(
    lock: Mapping[str, Any], *, enforce_scoreable: bool = True
) -> dict[str, Any]:
    """Validate a closed evaluator suite-lock and optionally enforce scoreability."""
    root = _object(lock, "lock")
    _reject_unknown(
        root,
        {
            "schema_version",
            "suite_id",
            "source",
            "dataset",
            "runner",
            "harness",
            "verifier",
            "integrity",
        },
        "lock",
    )
    if root.get("schema_version") != SUITE_LOCK_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {SUITE_LOCK_SCHEMA_VERSION}")
    _text(root.get("suite_id"), "suite_id")

    source = _object(root.get("source"), "source")
    _reject_unknown(
        source,
        {
            "owner",
            "repository_url",
            "revision_sha",
            "retrieved_at",
            "license_spdx",
        },
        "source",
    )
    _text(source.get("owner"), "source.owner")
    repository_url = _text(source.get("repository_url"), "source.repository_url")
    if repository_url is None or not repository_url.startswith("https://github.com/"):
        raise ContractError("source.repository_url must be an HTTPS GitHub URL")
    _git_sha(source.get("revision_sha"), "source.revision_sha")
    _timestamp(source.get("retrieved_at"), "source.retrieved_at")
    _text(source.get("license_spdx"), "source.license_spdx")

    dataset = _object(root.get("dataset"), "dataset")
    _reject_unknown(
        dataset,
        {
            "task_count",
            "task_ids_sha256",
            "task_manifest_sha256",
            "subset_ids",
            "subset_manifest_sha256",
            "changed_task_ids_sha256",
        },
        "dataset",
    )
    count = dataset.get("task_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ContractError("dataset.task_count must be a positive integer")
    for field in (
        "task_ids_sha256",
        "task_manifest_sha256",
        "subset_manifest_sha256",
        "changed_task_ids_sha256",
    ):
        _hash(dataset.get(field), f"dataset.{field}", nullable=True)
    subset_ids = _unique_strings(dataset.get("subset_ids", []), "dataset.subset_ids")
    if len(subset_ids) > count:
        raise ContractError("dataset.subset_ids cannot exceed dataset.task_count")

    runner = _object(root.get("runner"), "runner")
    _reject_unknown(
        runner,
        {"name", "version", "revision_sha", "package_sha256"},
        "runner",
    )
    _text(runner.get("name"), "runner.name")
    _text(runner.get("version"), "runner.version")
    _git_sha(runner.get("revision_sha"), "runner.revision_sha", nullable=True)
    _hash(runner.get("package_sha256"), "runner.package_sha256", nullable=True)

    harness = _object(root.get("harness"), "harness")
    _reject_unknown(
        harness,
        {
            "name",
            "revision_sha",
            "system_prompt_sha256",
            "agent_config_sha256",
            "tool_definitions_sha256",
        },
        "harness",
    )
    _text(harness.get("name"), "harness.name")
    _git_sha(harness.get("revision_sha"), "harness.revision_sha", nullable=True)
    for field in (
        "system_prompt_sha256",
        "agent_config_sha256",
        "tool_definitions_sha256",
    ):
        _hash(harness.get(field), f"harness.{field}", nullable=True)

    verifier = _object(root.get("verifier"), "verifier")
    _reject_unknown(
        verifier,
        {
            "revision_sha",
            "image_digests",
            "separate_environment",
            "expected_artifacts",
        },
        "verifier",
    )
    _hash(verifier.get("revision_sha"), "verifier.revision_sha", nullable=True)
    image_digests = verifier.get("image_digests", [])
    if not isinstance(image_digests, list):
        raise ContractError("verifier.image_digests must be an array")
    for index, digest in enumerate(image_digests):
        _hash(digest, f"verifier.image_digests[{index}]")
    if len(image_digests) != len(set(image_digests)):
        raise ContractError("verifier.image_digests must not contain duplicates")
    if not isinstance(verifier.get("separate_environment"), bool):
        raise ContractError("verifier.separate_environment must be boolean")
    _artifact_paths(
        verifier.get("expected_artifacts", []), "verifier.expected_artifacts"
    )

    integrity = _object(root.get("integrity"), "integrity")
    _reject_unknown(
        integrity,
        {
            "held_out_from_training",
            "holdout_manifest_sha256",
            "scoreable",
            "unverified_reasons",
        },
        "integrity",
    )
    for field in ("held_out_from_training", "scoreable"):
        if not isinstance(integrity.get(field), bool):
            raise ContractError(f"integrity.{field} must be boolean")
    _hash(
        integrity.get("holdout_manifest_sha256"),
        "integrity.holdout_manifest_sha256",
        nullable=True,
    )
    _strings(integrity.get("unverified_reasons", []), "integrity.unverified_reasons")
    if contains_secret(root):
        raise ContractError("suite lock contains a credential")
    result = dict(root)
    if enforce_scoreable and integrity["scoreable"]:
        reasons = suite_lock_scoreability_reasons(result)
        if reasons:
            raise ContractError(
                "scoreable suite lock is incomplete: " + "; ".join(reasons)
            )
    return result


def suite_lock_sha256(lock: Mapping[str, Any]) -> str:
    """Validate the suite lock and return its canonical SHA-256 digest."""
    return sha256_hex(canonical_json_bytes(validate_suite_lock(lock)))


__all__ = [
    "SUITE_LOCK_SCHEMA_VERSION",
    "suite_lock_scoreability_reasons",
    "suite_lock_sha256",
    "validate_suite_lock",
]
