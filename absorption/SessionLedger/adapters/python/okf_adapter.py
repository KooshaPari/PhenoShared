#!/usr/bin/env python3
"""OKF language adapter stub — Python reference (C08 L75).

Implements the language-agnostic contract in adapters/README.md:
  load(path) -> dict
  validate(doc) -> None (raises ValueError on failure)
  emit(doc) -> str

CLI:
  python okf_adapter.py validate <path.okf.json>
  python okf_adapter.py emit <path.okf.json>

Hermetic: stdlib only. Not a Harbor / agent-eval harness.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

OKF_DIALECT = "1.0"
REQUIRED_SHARED_ENTITY_TYPES = frozenset(
    {
        "intent",
        "acceptance",
        "constraint",
        "resource",
        "state",
        "gate",
    }
)
ALLOWED_RELATION_TYPES = frozenset(
    {
        "verified_by",
        "bounded_by",
        "grounds",
        "requires",
        "asserts",
    }
)


def load(path: str | Path) -> MutableMapping[str, Any]:
    """Read an OKF JSON document from disk."""
    raw = Path(path).read_text(encoding="utf-8")
    doc = json.loads(raw)
    if not isinstance(doc, dict):
        raise ValueError("OKF root must be a JSON object")
    return doc


def validate(doc: Mapping[str, Any], *, stem: str | None = None) -> None:
    """Enforce OKF v1.0 structural rules used by the cross-language parity harness."""
    if doc.get("okf") != OKF_DIALECT:
        raise ValueError(f"expected okf '{OKF_DIALECT}', got {doc.get('okf')!r}")

    source_id = doc.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("missing non-empty source_id")
    if stem is not None and source_id != stem:
        raise ValueError(f"source_id {source_id!r} must equal filename stem {stem!r}")

    provenance = doc.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("missing document provenance object")
    if provenance.get("source_id") != source_id:
        raise ValueError("provenance.source_id must equal top-level source_id")

    entities = doc.get("entities")
    if not isinstance(entities, Sequence) or isinstance(entities, (str, bytes)):
        raise ValueError("entities must be a JSON array")
    if len(entities) < 1:
        raise ValueError("entities must be non-empty")

    ids: set[str] = set()
    types: set[str] = set()
    for entity in entities:
        if not isinstance(entity, Mapping):
            raise ValueError("each entity must be an object")
        eid = entity.get("id")
        etype = entity.get("type")
        label = entity.get("label")
        if not isinstance(eid, str) or not eid:
            raise ValueError("entity missing id")
        if not isinstance(etype, str) or not etype:
            raise ValueError(f"entity {eid!r} missing type")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"entity {eid!r} missing label")
        if eid in ids:
            raise ValueError(f"duplicate entity id {eid!r}")
        ids.add(eid)
        types.add(etype)

    missing = REQUIRED_SHARED_ENTITY_TYPES - types
    if missing:
        raise ValueError(f"missing required shared entity types: {sorted(missing)}")

    relations = doc.get("relations")
    if not isinstance(relations, Sequence) or isinstance(relations, (str, bytes)):
        raise ValueError("relations must be a JSON array")
    if len(relations) < 1:
        raise ValueError("relations must be non-empty")

    for rel in relations:
        if not isinstance(rel, Mapping):
            raise ValueError("each relation must be an object")
        src = rel.get("source")
        tgt = rel.get("target")
        rtype = rel.get("type")
        rprov = rel.get("provenance")
        if src not in ids:
            raise ValueError(f"relation source {src!r} not in entities")
        if tgt not in ids:
            raise ValueError(f"relation target {tgt!r} not in entities")
        if rtype not in ALLOWED_RELATION_TYPES:
            raise ValueError(f"relation type {rtype!r} not in OKF v1.0 set")
        if not isinstance(rprov, Mapping) or rprov.get("source_id") != source_id:
            raise ValueError("relation provenance.source_id must equal top-level source_id")


def emit(doc: Mapping[str, Any]) -> str:
    """Serialize a validated OKF document to pretty JSON with a trailing newline."""
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def _stem_of(path: Path) -> str:
    name = path.name
    suffix = ".okf.json"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return path.stem


def main(argv: Sequence[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"validate", "emit"}:
        sys.stderr.write(
            "usage: okf_adapter.py validate|emit <path.okf.json>\n"
        )
        return 2

    command, path_s = argv[1], argv[2]
    path = Path(path_s)
    if not path.is_file():
        sys.stderr.write(f"fixture not found: {path}\n")
        return 1

    try:
        doc = load(path)
        validate(doc, stem=_stem_of(path))
        if command == "validate":
            sys.stdout.write(f"OKF validate ok: {path} (source_id={doc['source_id']})\n")
            return 0
        sys.stdout.write(emit(doc))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(f"OKF adapter error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
