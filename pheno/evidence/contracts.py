"""Validation and canonicalization for normalized research evidence."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from .redaction import contains_secret

EVIDENCE_SCHEMA_VERSION = "pheno.evidence.v1"

SOURCE_KINDS = frozenset(
    {
        "hf",
        "modelscope",
        "github",
        "arxiv",
        "reddit",
        "local_corpus",
        "openalex",
        "semantic_scholar",
        "wikipedia",
    }
)
EVIDENCE_CLASSES = frozenset({"V", "C", "L", "I", "A"})
RUNTIME_STATES = frozenset(
    {"released", "main", "open_pr", "fork", "claimed", "unsupported"}
)
LICENSE_GATE_STATES = frozenset(
    {"approved", "review_required", "rejected", "not_applicable"}
)
EXECUTION_GATE_STATES = frozenset({"approved", "review_required", "blocked"})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RECORD_ID = re.compile(r"^[a-z0-9][a-z0-9._:/@+~-]{2,511}$")

_ROOT_FIELDS = {
    "schema_version",
    "record_id",
    "retrieved_at",
    "source",
    "subject",
    "model",
    "artifacts",
    "runtime_support",
    "benchmark_claims",
    "gates",
    "discovery",
    "resolved",
    "license",
    "quality",
    "compliance",
    "notes",
}
_MAX_NORMALIZED_RECORD_BYTES = 2 * 1024 * 1024

_SOURCE_HOSTS = {
    "hf": {"huggingface.co", "www.huggingface.co"},
    "modelscope": {
        "modelscope.cn",
        "www.modelscope.cn",
        "modelscope.com",
        "www.modelscope.com",
    },
    "github": {"github.com", "api.github.com", "raw.githubusercontent.com"},
    "arxiv": {"arxiv.org", "export.arxiv.org", "info.arxiv.org"},
    "reddit": {"reddit.com", "www.reddit.com", "oauth.reddit.com"},
    "openalex": {"api.openalex.org"},
    "semantic_scholar": {"api.semanticscholar.org"},
    "wikipedia": {"en.wikipedia.org"},
}


class ContractError(ValueError):
    """Raised when persisted evidence violates the registry contract."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically for hashes and content addressing."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of ``value``."""
    return hashlib.sha256(value).hexdigest()


def make_record_id(source_kind: str, stable_id: str, revision: str) -> str:
    """Build an inspectable record id while bounding untrusted source text."""

    kind = source_kind.strip().lower()
    if kind not in SOURCE_KINDS:
        raise ContractError(f"unsupported source kind: {source_kind!r}")
    stable = re.sub(r"[^a-z0-9._/@+~-]+", "-", stable_id.strip().lower()).strip("-")
    if not stable:
        raise ContractError("stable_id must contain at least one identifier character")
    stable = stable[:240]
    revision_digest = hashlib.sha256(revision.encode("utf-8")).hexdigest()[:16]
    return f"{kind}:{stable}:{revision_digest}"


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{path} must be an object")
    return value


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(f"{path} contains unknown fields: {unknown}")


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{path} must be an array")
    return value


def _text(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{path} must be a non-empty string")
    return value


def _timestamp(value: Any, path: str) -> str:
    text = _text(value, path)
    assert text is not None  # nosec B101
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{path} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{path} must include a timezone")
    return text


def _date_or_timestamp(value: Any, path: str) -> None:
    text = _text(value, path)
    assert text is not None  # nosec B101
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{path} must be an ISO date or timestamp") from exc


def _nonnegative_number(value: Any, path: str, *, integer: bool = False) -> None:
    valid_type = isinstance(value, int) if integer else isinstance(value, (int, float))
    if isinstance(value, bool) or not valid_type:
        expected = "integer" if integer else "number"
        raise ContractError(f"{path} must be a non-negative {expected} or null")
    if value < 0 or (isinstance(value, float) and not math.isfinite(value)):
        raise ContractError(f"{path} must be finite and non-negative")


def _validate_source_url(kind: str, value: Any) -> None:
    text = _text(value, "source.url")
    assert text is not None  # nosec B101
    parsed = urlparse(text)
    if kind == "local_corpus":
        if parsed.scheme != "local" or parsed.netloc != "sha256":
            raise ContractError("local_corpus URLs must use local://sha256/<digest>")
        digest = parsed.path.lstrip("/")
        if not _SHA256.fullmatch(digest):
            raise ContractError("local_corpus URL must contain a SHA-256 digest")
        return
    if parsed.scheme != "https":
        raise ContractError("remote source URLs must use https")
    if (parsed.hostname or "").lower() not in _SOURCE_HOSTS[kind]:
        raise ContractError(f"source.url host is not allowed for {kind}")


def _validate_model(model: Mapping[str, Any]) -> None:
    _reject_unknown(
        model,
        {
            "architecture",
            "total_parameters",
            "active_parameters",
            "context_tokens",
            "modalities",
            "mtp_or_draft",
            "expert_count",
            "experts_per_token",
        },
        "model",
    )
    _text(model.get("architecture"), "model.architecture", nullable=True)
    _text(model.get("mtp_or_draft"), "model.mtp_or_draft", nullable=True)
    for field in (
        "total_parameters",
        "active_parameters",
        "context_tokens",
        "expert_count",
        "experts_per_token",
    ):
        value = model.get(field)
        if value is not None:
            _nonnegative_number(value, f"model.{field}", integer=True)
    expert_count = model.get("expert_count")
    experts_per_token = model.get("experts_per_token")
    if (
        isinstance(expert_count, int)
        and isinstance(experts_per_token, int)
        and experts_per_token > expert_count
    ):
        raise ContractError("model.experts_per_token cannot exceed model.expert_count")
    modalities = model.get("modalities", [])
    for index, value in enumerate(_list(modalities, "model.modalities")):
        _text(value, f"model.modalities[{index}]")


def _validate_artifacts(artifacts: list[Any]) -> None:
    for index, raw in enumerate(artifacts):
        item = _mapping(raw, f"artifacts[{index}]")
        _reject_unknown(
            item,
            {"format", "quantization", "bytes", "sha256_or_etag"},
            f"artifacts[{index}]",
        )
        _text(item.get("format"), f"artifacts[{index}].format")
        _text(
            item.get("quantization"), f"artifacts[{index}].quantization", nullable=True
        )
        size = item.get("bytes")
        if size is not None:
            _nonnegative_number(size, f"artifacts[{index}].bytes", integer=True)
        checksum = item.get("sha256_or_etag")
        if checksum is not None:
            _text(checksum, f"artifacts[{index}].sha256_or_etag")


def _validate_runtime_support(rows: list[Any]) -> None:
    for index, raw in enumerate(rows):
        item = _mapping(raw, f"runtime_support[{index}]")
        _reject_unknown(
            item,
            {"runtime", "version_or_commit", "state", "parser"},
            f"runtime_support[{index}]",
        )
        _text(item.get("runtime"), f"runtime_support[{index}].runtime")
        _text(
            item.get("version_or_commit"), f"runtime_support[{index}].version_or_commit"
        )
        state = _text(item.get("state"), f"runtime_support[{index}].state")
        if state not in RUNTIME_STATES:
            raise ContractError(f"runtime_support[{index}].state is invalid")
        _text(item.get("parser"), f"runtime_support[{index}].parser", nullable=True)


def _validate_claims(rows: list[Any]) -> None:
    for index, raw in enumerate(rows):
        item = _mapping(raw, f"benchmark_claims[{index}]")
        _reject_unknown(
            item,
            {"suite", "score", "harness", "attempts", "evidence_class"},
            f"benchmark_claims[{index}]",
        )
        _text(item.get("suite"), f"benchmark_claims[{index}].suite")
        evidence_class = _text(
            item.get("evidence_class"), f"benchmark_claims[{index}].evidence_class"
        )
        if evidence_class not in {"C", "V"}:
            raise ContractError(
                f"benchmark_claims[{index}].evidence_class must be C or V"
            )
        if "score" not in item:
            raise ContractError(f"benchmark_claims[{index}].score is required")
        score = item["score"]
        if isinstance(score, float) and not math.isfinite(score):
            raise ContractError(f"benchmark_claims[{index}].score must be finite")
        if not isinstance(score, (str, int, float, bool)) and score is not None:
            raise ContractError(
                f"benchmark_claims[{index}].score must be a JSON scalar"
            )
        _text(item.get("harness"), f"benchmark_claims[{index}].harness")
        attempts = item.get("attempts")
        if attempts is not None:
            _nonnegative_number(
                attempts,
                f"benchmark_claims[{index}].attempts",
                integer=True,
            )


def validate_evidence_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a plain copy of one normalized evidence record."""

    root = _mapping(record, "record")
    _reject_unknown(root, _ROOT_FIELDS, "record")
    try:
        normalized_size = len(canonical_json_bytes(root))
    except (TypeError, ValueError) as exc:
        raise ContractError(
            "record must contain finite JSON-compatible values"
        ) from exc
    if normalized_size > _MAX_NORMALIZED_RECORD_BYTES:
        raise ContractError(
            f"normalized record is {normalized_size} bytes; "
            f"limit is {_MAX_NORMALIZED_RECORD_BYTES}"
        )
    if root.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ContractError(f"schema_version must be {EVIDENCE_SCHEMA_VERSION!r}")
    record_id = _text(root.get("record_id"), "record_id")
    assert record_id is not None  # nosec B101
    if not _RECORD_ID.fullmatch(record_id):
        raise ContractError("record_id contains unsupported characters or length")
    _timestamp(root.get("retrieved_at"), "retrieved_at")

    source = _mapping(root.get("source"), "source")
    _reject_unknown(
        source,
        {"kind", "url", "revision", "evidence_class", "raw_sha256"},
        "source",
    )
    kind = _text(source.get("kind"), "source.kind")
    if kind not in SOURCE_KINDS:
        raise ContractError(f"source.kind must be one of {sorted(SOURCE_KINDS)}")
    _validate_source_url(kind, source.get("url"))
    _text(source.get("revision"), "source.revision")
    evidence_class = _text(source.get("evidence_class"), "source.evidence_class")
    if evidence_class not in EVIDENCE_CLASSES:
        raise ContractError("source.evidence_class must be V, C, L, I, or A")
    if kind == "reddit" and evidence_class != "A":
        raise ContractError("reddit evidence must be class A (anecdotal)")
    if kind == "local_corpus" and evidence_class != "L":
        raise ContractError("local corpus evidence must be class L")
    raw_sha256 = _text(source.get("raw_sha256"), "source.raw_sha256")
    if raw_sha256 is None or not _SHA256.fullmatch(raw_sha256):
        raise ContractError("source.raw_sha256 must be a lowercase SHA-256 digest")

    subject = _mapping(root.get("subject"), "subject")
    _reject_unknown(
        subject,
        {"canonical_name", "aliases", "released_at", "license"},
        "subject",
    )
    canonical_name = _text(subject.get("canonical_name"), "subject.canonical_name")
    aliases = _list(subject.get("aliases", []), "subject.aliases")
    for index, alias in enumerate(aliases):
        _text(alias, f"subject.aliases[{index}]")
    if subject.get("released_at") is not None:
        _date_or_timestamp(subject.get("released_at"), "subject.released_at")
    _text(subject.get("license"), "subject.license", nullable=True)

    model_value = root.get("model")
    if model_value is not None:
        _validate_model(_mapping(model_value, "model"))
    _validate_artifacts(_list(root.get("artifacts", []), "artifacts"))
    _validate_runtime_support(_list(root.get("runtime_support", []), "runtime_support"))
    _validate_claims(_list(root.get("benchmark_claims", []), "benchmark_claims"))

    gates = _mapping(root.get("gates"), "gates")
    _reject_unknown(gates, {"metadata_only", "license", "execution"}, "gates")
    if gates.get("metadata_only") is not True:
        raise ContractError("gates.metadata_only must be true for registry records")
    license_state = _text(gates.get("license"), "gates.license")
    if license_state not in LICENSE_GATE_STATES:
        raise ContractError("gates.license has an invalid state")
    execution_state = _text(gates.get("execution"), "gates.execution")
    if execution_state not in EXECUTION_GATE_STATES:
        raise ContractError("gates.execution has an invalid state")

    discovery = _mapping(root.get("discovery"), "discovery")
    _reject_unknown(
        discovery,
        {
            "method",
            "endpoint",
            "query",
            "final_url",
            "adapter_version",
            "api_version",
            "status",
            "response_headers",
            "incomplete",
        },
        "discovery",
    )
    method = _text(discovery.get("method"), "discovery.method")
    if method not in {"GET", "POST", "LOCAL_SCAN", "IMPORT"}:
        raise ContractError("discovery.method is invalid")
    _text(discovery.get("endpoint"), "discovery.endpoint")
    _mapping(discovery.get("query", {}), "discovery.query")
    _text(discovery.get("final_url"), "discovery.final_url")
    _text(discovery.get("adapter_version"), "discovery.adapter_version")
    _text(discovery.get("api_version"), "discovery.api_version", nullable=True)
    status = discovery.get("status")
    if (
        not isinstance(status, int)
        or isinstance(status, bool)
        or not 100 <= status <= 599
    ):
        raise ContractError(
            "discovery.status must be an HTTP-like integer from 100 to 599"
        )
    _mapping(discovery.get("response_headers", {}), "discovery.response_headers")
    if not isinstance(discovery.get("incomplete"), bool):
        raise ContractError("discovery.incomplete must be boolean")

    resolved = _mapping(root.get("resolved"), "resolved")
    _reject_unknown(resolved, {"revision", "mutable"}, "resolved")
    _text(resolved.get("revision"), "resolved.revision")
    if not isinstance(resolved.get("mutable"), bool):
        raise ContractError("resolved.mutable must be boolean")
    if resolved.get("revision") != source.get("revision"):
        raise ContractError("resolved.revision must equal source.revision")

    license_info = _mapping(root.get("license"), "license")
    _reject_unknown(
        license_info,
        {"declared", "source_urls", "verified", "caveats"},
        "license",
    )
    declared = _list(license_info.get("declared", []), "license.declared")
    for index, value in enumerate(declared):
        _text(value, f"license.declared[{index}]")
    source_urls = _list(license_info.get("source_urls", []), "license.source_urls")
    for index, value in enumerate(source_urls):
        _text(value, f"license.source_urls[{index}]")
    if not isinstance(license_info.get("verified"), bool):
        raise ContractError("license.verified must be boolean")
    caveats = _list(license_info.get("caveats", []), "license.caveats")
    for index, value in enumerate(caveats):
        _text(value, f"license.caveats[{index}]")

    quality = _mapping(root.get("quality"), "quality")
    _reject_unknown(
        quality,
        {"incomplete", "confidence", "needs_revalidation_at"},
        "quality",
    )
    if not isinstance(quality.get("incomplete"), bool):
        raise ContractError("quality.incomplete must be boolean")
    if quality.get("confidence") not in {"high", "medium", "low"}:
        raise ContractError("quality.confidence must be high, medium, or low")
    needs_revalidation = quality.get("needs_revalidation_at")
    if needs_revalidation is not None:
        _timestamp(needs_revalidation, "quality.needs_revalidation_at")

    compliance = _mapping(root.get("compliance"), "compliance")
    _reject_unknown(
        compliance,
        {"retention_class", "purge_after", "tombstoned_at"},
        "compliance",
    )
    retention_class = _text(
        compliance.get("retention_class"), "compliance.retention_class"
    )
    if retention_class not in {"durable_metadata", "ephemeral_user_content"}:
        raise ContractError("compliance.retention_class is invalid")
    if kind == "reddit" and retention_class != "durable_metadata":
        raise ContractError("durable Reddit records may contain citation metadata only")
    for field in ("purge_after", "tombstoned_at"):
        if compliance.get(field) is not None:
            _timestamp(compliance[field], f"compliance.{field}")

    notes = _list(root.get("notes", []), "notes")
    for index, value in enumerate(notes):
        _text(value, f"notes[{index}]")

    expected_record_id = make_record_id(
        kind, str(canonical_name), str(source["revision"])
    )
    if record_id != expected_record_id:
        raise ContractError(
            "record_id does not match source kind, canonical subject, and revision"
        )

    if contains_secret(root):
        raise ContractError(
            "record contains a token, credential, or authorization value"
        )
    return dict(root)


__all__ = [
    "ContractError",
    "EVIDENCE_CLASSES",
    "EVIDENCE_SCHEMA_VERSION",
    "SOURCE_KINDS",
    "canonical_json_bytes",
    "make_record_id",
    "sha256_hex",
    "validate_evidence_record",
]
