"""Fail-closed reader for legacy snapshot JSON; it creates no candidates."""
import hashlib
import json
import math
from pathlib import Path


CONVERTER = {"identity": "dry_run.snapshot_adapter", "version": "1"}


class AdapterError(ValueError):
    """Raised when a source cannot be represented without guessing."""


def _constant(value):
    raise AdapterError("nonfinite JSON constant: " + value)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AdapterError("duplicate JSON object key: " + key)
        result[key] = value
    return result


def _finite(value):
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite(item) for item in value)
    return True


def adapt_snapshot(path, kind):
    """Return an UNREVIEWED diagnostic draft; never infer mappings or status."""
    if kind not in {"rubric", "card"}:
        raise AdapterError("unsupported source kind: " + str(kind))
    source = Path(path)
    try:
        raw = source.read_bytes()
        envelope = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                              parse_constant=_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError("invalid JSON input: " + str(source)) from exc
    if not _finite(envelope):
        raise AdapterError("nonfinite JSON value: " + str(source))
    result = {"schema_version": "snapshot-adapter/v1", "converter": CONVERTER,
              "status": "UNREVIEWED", "source": {"path": str(source),
              "sha256": hashlib.sha256(raw).hexdigest(), "length": len(raw), "kind": kind},
              "raw_envelope": envelope, "records": [], "blockers": []}
    rows = envelope.get("criteria") if isinstance(envelope, dict) else None
    if not isinstance(rows, list):
        result["blockers"].append("unsupported_top_level_shape")
        return result
    for index, row in enumerate(rows):
        blockers = []
        if not isinstance(row, dict):
            blockers.append("unsupported_row_shape")
        elif kind == "card":
            blockers.append("missing_reviewed_mapping")
        elif not all(isinstance(row.get(field), str) and row[field]
                     for field in ("source", "domain", "id")):
            blockers.append("missing_qualified_identity")
        result["records"].append({"source_locator": "$.criteria[" + str(index) + "]",
                                  "raw": row, "blockers": blockers})
    return result


def build_draft_manifest(input_root, inputs):
    """Adapt only caller-enumerated paths into an UNREVIEWED draft manifest."""
    root = Path(input_root).resolve()
    if not root.is_dir() or not isinstance(inputs, list) or not inputs:
        raise AdapterError("inputs must be a nonempty explicit list")
    adapted, blockers, seen = [], [], set()
    for entry in inputs:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise AdapterError("input requires relative path and kind")
        relative = entry["path"]
        path = (root / relative).resolve()
        if Path(relative).is_absolute() or root not in path.parents or path in seen:
            raise AdapterError("unsafe or duplicate input path: " + relative)
        seen.add(path)
        report = adapt_snapshot(path, entry.get("kind"))
        report["source"]["path"] = relative
        adapted.append(report)
        blockers.extend(report["blockers"])
        blockers.extend(blocker for record in report["records"] for blocker in record["blockers"])
    return {"schema_version": "snapshot-adapter/v1", "converter": CONVERTER,
            "status": "UNREVIEWED", "inputs": adapted, "blockers": sorted(set(blockers))}
