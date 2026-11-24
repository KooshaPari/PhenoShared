"""Compile qualified, historical mapping fixtures without scoring or writes."""
import re
from collections import defaultdict


class MappingError(ValueError):
    """Raised when a mapping cannot be reconstructed without a choice."""


def _normalized_title(value):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", value.strip()).lower())[:120]


def _validated_rows(label, rows):
    if not isinstance(rows, list):
        raise MappingError(label + " rows must be a list")
    grouped = defaultdict(list)
    seen_keys = set()
    for row in rows:
        if not isinstance(row, dict):
            raise MappingError(label + " row must be an object")
        values = {field: row.get(field) for field in ("id", "domain", "title")}
        if not all(isinstance(value, str) and value for value in values.values()):
            raise MappingError(label + " row requires nonempty id, domain, and title")
        key = (values["domain"], values["id"])
        if key in seen_keys:
            raise MappingError(label + " has duplicate domain/id: " + values["domain"] + "/" + values["id"])
        seen_keys.add(key)
        grouped[values["domain"]].append(row)
    return grouped


def _ordered(domain, rows):
    ordered = sorted(rows, key=lambda row: (_normalized_title(row["title"]), row["id"]))
    titles = [_normalized_title(row["title"]) for row in ordered]
    if len(titles) != len(set(titles)):
        raise MappingError("ambiguous normalized titles in domain: " + domain)
    return ordered


def compile_mapping(source, legacy_rows, normalized_rows):
    """Return qualified mappings; reject non-deterministic legacy pairings."""
    if not isinstance(source, str) or not source:
        raise MappingError("source must be a nonempty string")
    legacy = _validated_rows("legacy", legacy_rows)
    normalized = _validated_rows("normalized", normalized_rows)
    if set(legacy) != set(normalized):
        raise MappingError("legacy and normalized domains differ")

    mappings = []
    for domain in sorted(legacy):
        left = _ordered(domain, legacy[domain])
        right = _ordered(domain, normalized[domain])
        if len(left) != len(right):
            raise MappingError("unequal row count in domain: " + domain)
        for legacy_row, normalized_row in zip(left, right):
            if _normalized_title(legacy_row["title"]) != _normalized_title(normalized_row["title"]):
                raise MappingError("title mismatch in domain: " + domain)
            mappings.append({
                "legacy_id": legacy_row["id"],
                "unified_id": normalized_row["id"],
                "domain": domain,
                "title": legacy_row["title"],
                "legacy_key": ["criterion-v2", source, domain, legacy_row["id"]],
                "normalized_key": ["criterion-v2", source, domain, normalized_row["id"]],
            })
    return mappings
