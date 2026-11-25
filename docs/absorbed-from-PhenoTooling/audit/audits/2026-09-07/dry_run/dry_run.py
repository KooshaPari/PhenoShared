"""Synthetic-only deterministic dry-run contract validator."""
import hashlib
import json
import math
from pathlib import Path


class ContractError(ValueError):
    """Raised for unsafe or structurally invalid dry-run inputs."""


def _constant(value):
    raise ContractError("nonfinite JSON constant: " + value)


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ContractError("duplicate JSON object key: " + key)
        out[key] = value
    return out


def _load(path):
    try:
        value = json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("invalid JSON input " + str(path)) from exc
    if not isinstance(value, list):
        raise ContractError("JSON input must be an array: " + str(path))
    if not _finite(value):
        raise ContractError("nonfinite JSON value: " + str(path))
    return value


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        return False
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return True


def _bytes(value):
    if not _finite(value):
        raise ContractError("candidate output contains a nonfinite value")
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def _identity_value(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"$nonfinite": repr(value)}
    if isinstance(value, dict):
        return {str(key): _identity_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_identity_value(item) for item in value]
    return value


def _key(row):
    parts = [row.get(name) if isinstance(row, dict) else None
             for name in ("source", "domain", "legacy_id")]
    if not all(isinstance(part, str) and part for part in parts):
        return None
    return json.dumps(["criterion-v2"] + parts, ensure_ascii=False, separators=(",", ":"))


def _qualified(value):
    try:
        parts = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return False
    return (isinstance(parts, list) and len(parts) == 4 and parts[0] == "criterion-v2" and
            all(isinstance(part, str) and part for part in parts[1:]) and
            json.dumps(parts, ensure_ascii=False, separators=(",", ":")) == value)


def _safe_path(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ContractError("input path must be a nonempty relative path")
    path = (root / relative).resolve()
    if root not in path.parents:
        raise ContractError("input path escapes input root")
    return path


def _inputs(root, manifest):
    entries = manifest.get("inputs") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ContractError("manifest must enumerate inputs")
    loaded, fingerprints = [], []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("kind"), str) or not entry["kind"]:
            raise ContractError("each input requires a nonempty kind")
        path = _safe_path(root, entry.get("path"))
        locator = str(path)
        if locator in seen:
            raise ContractError("duplicate explicitly enumerated input: " + entry["path"])
        seen.add(locator)
        if not path.is_file():
            raise ContractError("missing explicitly enumerated input: " + str(path))
        raw = path.read_bytes()
        values = _load(path) if entry["kind"] in {"rubric", "audit"} else []
        loaded.append((entry["kind"], entry["path"], values))
        fingerprints.append({"path": entry["path"], "kind": entry["kind"], "length": len(raw),
                             "sha256": hashlib.sha256(raw).hexdigest()})
    return loaded, fingerprints


def _lineage(root, manifest, audit_rows, fingerprints):
    data = manifest.get("lineage", {}) if isinstance(manifest, dict) else {}
    required = ("assessed_subject", "source_path", "source_hash", "declared_subject",
                "declared_date", "conversion_identity", "conversion_version", "rubric_hash",
                "rubric_version", "scorer_hash", "scorer_version", "capture_timestamp")
    blockers = ["lineage_" + field for field in required
                if not isinstance(data.get(field), str) or not data.get(field)]
    if data.get("assessed_subject") and data.get("declared_subject") and \
            data["assessed_subject"] != data["declared_subject"]:
        blockers.extend(("lineage_assessed_subject", "lineage_subject_mismatch"))
    subjects = {row.get("subject") for row in audit_rows if isinstance(row, dict)}
    if subjects and subjects != {data.get("assessed_subject")}:
        blockers.append("lineage_audit_subject_mismatch")
    by_path = {f["path"]: f for f in fingerprints}
    for field, path_field in (("source_hash", "source_path"),):
        path, claimed = data.get(path_field), data.get(field)
        if path not in by_path or by_path[path]["kind"] != "source":
            blockers.append("lineage_" + path_field)
        elif claimed != by_path[path]["sha256"] or not isinstance(claimed, str) or len(claimed) != 64:
            blockers.append("lineage_" + field)
    rubric_hashes = {f["sha256"] for f in fingerprints if f["kind"] == "rubric"}
    scorer_hashes = {f["sha256"] for f in fingerprints if f["kind"] == "scorer"}
    if data.get("rubric_hash") not in rubric_hashes:
        blockers.append("lineage_rubric_hash")
    if data.get("scorer_hash") not in scorer_hashes:
        blockers.append("lineage_scorer_hash")
    try:
        declared = json.loads(_safe_path(root, data.get("source_path")).read_text("utf-8"))
    except (ContractError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        declared = None
    if not isinstance(declared, dict) or declared.get("subject") != data.get("declared_subject") or \
            declared.get("date") != data.get("declared_date"):
        blockers.append("lineage_declared_source")
    reviewed = manifest.get("reviewed_metadata")
    expected = (("capture_timestamp", reviewed.get("capture_timestamp") if isinstance(reviewed, dict) else None),
                ("rubric_version", reviewed.get("rubric", {}).get("version") if isinstance(reviewed, dict) and isinstance(reviewed.get("rubric"), dict) else None),
                ("scorer_version", reviewed.get("scorer", {}).get("version") if isinstance(reviewed, dict) and isinstance(reviewed.get("scorer"), dict) else None),
                ("conversion_identity", reviewed.get("conversion", {}).get("identity") if isinstance(reviewed, dict) and isinstance(reviewed.get("conversion"), dict) else None),
                ("conversion_version", reviewed.get("conversion", {}).get("version") if isinstance(reviewed, dict) and isinstance(reviewed.get("conversion"), dict) else None))
    for field, expected_value in expected:
        if not isinstance(expected_value, str) or data.get(field) != expected_value:
            blockers.append("lineage_" + field)
    if manifest.get("capture_timestamp") != data.get("capture_timestamp") or \
            manifest.get("capture_timestamp") != (reviewed.get("capture_timestamp") if isinstance(reviewed, dict) else None):
        blockers.append("lineage_capture_timestamp")
    for kind in ("rubric", "scorer", "conversion"):
        declaration = reviewed.get(kind) if isinstance(reviewed, dict) else None
        hashes = {f["sha256"] for f in fingerprints if f["kind"] == kind}
        if not isinstance(declaration, dict) or declaration.get("sha256") not in hashes:
            blockers.append("reviewed_" + kind + "_hash")
    return data, blockers


def _write(output_root, manifest, fingerprints, files):
    identity_input = {"manifest": manifest, "actual_inputs": fingerprints,
                      "implementation_version": manifest.get("implementation_version")}
    raw = _bytes(_identity_value(identity_input))
    identity = hashlib.sha256(raw).hexdigest()
    candidate = output_root / ("dry-run-candidate-" + identity)
    if candidate.exists():
        raise ContractError("candidate output already exists: " + str(candidate))
    encoded = {name: _bytes(value) for name, value in files.items()}
    candidate.mkdir(parents=True)
    for name, value in encoded.items():
        (candidate / name).write_bytes(value)
    return candidate


def run_dry_run(input_root, output_root, manifest):
    """Use only manifest-enumerated synthetic JSON arrays; never discover inputs."""
    root, out = Path(input_root).resolve(), Path(output_root).resolve()
    if not isinstance(manifest, dict):
        raise ContractError("manifest must be an object")
    for field in ("lineage", "expected_baseline", "reviewed_metadata"):
        if field in manifest and not isinstance(manifest[field], dict):
            raise ContractError("manifest " + field + " must be an object")
    if isinstance(manifest.get("expected_baseline"), dict) and \
            "rubric" in manifest["expected_baseline"] and \
            not isinstance(manifest["expected_baseline"]["rubric"], dict):
        raise ContractError("manifest expected_baseline.rubric must be an object")
    if not root.is_dir() or out == root or root in out.parents:
        raise ContractError("output root must not be within source input root")
    loaded, fingerprints = _inputs(root, manifest)
    rows, rubric_rows, audit_rows = [], [], []
    for kind, path, values in loaded:
        for index, row in enumerate(values):
            record = {"kind": kind, "path": path, "row_index": index, "row": row,
                      "qualified_key": _key(row), "disposition": "mapped", "reasons": []}
            rows.append(record)
            (rubric_rows if kind == "rubric" else audit_rows).append(record)
    blockers, groups = [], []
    baseline = manifest.get("expected_baseline", {}).get("rubric", {})
    rubric_hashes = [f["sha256"] for f in fingerprints
                     if any(x[0] == "rubric" and x[1] == f["path"] for x in loaded)]
    if not isinstance(baseline, dict) or not isinstance(baseline.get("count"), int) or \
            not isinstance(baseline.get("sha256"), str):
        blockers.append("missing_expected_baseline")
    elif baseline.get("count") != len(rubric_rows) or baseline.get("sha256") not in rubric_hashes:
        blockers.append("baseline_drift")
    return _finish(root, out, manifest, fingerprints, rows, rubric_rows, audit_rows, blockers, groups)


def _finish(root, out, manifest, fingerprints, rows, rubric_rows, audit_rows, blockers, groups):
    def quarantine(records, reason):
        keys = tuple(r["qualified_key"] for r in records)
        for record in records:
            record["disposition"] = "quarantined"
            if reason not in record["reasons"]:
                record["reasons"].append(reason)
        if not any(g["members"] == list(keys) and reason in g["reasons"] for g in groups):
            groups.append({"qualified_key": records[0]["qualified_key"], "members": list(keys),
                           "locators": [{"path": r["path"], "row_index": r["row_index"]} for r in records],
                           "reasons": [reason]})

    rubric_by_key, audit_by_key = {}, {}
    for record in rubric_rows:
        rubric_by_key.setdefault(record["qualified_key"], []).append(record)
    for record in audit_rows:
        audit_by_key.setdefault(record["qualified_key"], []).append(record)
    for key, records in rubric_by_key.items():
        if key is None:
            quarantine(records, "invalid_qualified_key")
        elif len(records) > 1:
            quarantine(records, "repeated_qualified_tuple")
    for key, records in audit_by_key.items():
        status_values = [r["row"].get("status") for r in records if isinstance(r["row"], dict)]
        target_lists = [r["row"].get("target_keys") for r in records
                        if isinstance(r["row"], dict) and "target_keys" in r["row"]]
        if key is None:
            quarantine(records, "invalid_qualified_key")
        elif any(not isinstance(status, str) for status in status_values):
            quarantine(records, "invalid_status")
        elif any(not isinstance(targets, list) or len(targets) != 1 for targets in target_lists):
            quarantine(records, "one_to_many_mapping")
            blockers.append("one_to_many_mapping")
        elif any(not _qualified(targets[0]) or targets[0] != key or targets[0] not in rubric_by_key
                 for targets in target_lists):
            quarantine(records, "invalid_reviewed_mapping")
            blockers.append("invalid_reviewed_mapping")
        elif key not in rubric_by_key:
            quarantine(records, "unknown_subject")
        elif any(r["disposition"] == "quarantined" for r in rubric_by_key[key]):
            quarantine(records, "ambiguous_rubric_target")
        elif len(records) > 1:
            statuses = set(status_values)
            quarantine(records, "conflicting_statuses" if len(statuses) > 1 else "duplicate_qualified_audit_key")
        elif set(status_values) - {"satisfied", "unsatisfied"}:
            quarantine(records, "invalid_status")
    lineage, lineage_blocks = _lineage(root, manifest, [r["row"] for r in audit_rows], fingerprints)
    for record in audit_rows:
        subject = record["row"].get("subject") if isinstance(record["row"], dict) else None
        if not isinstance(subject, str) or not subject or subject != lineage.get("assessed_subject"):
            quarantine([record], "unknown_subject")
    blockers.extend(lineage_blocks)
    if any(r["disposition"] == "quarantined" for r in rows):
        blockers.append("quarantined_rows")
    return _outputs(root, out, manifest, fingerprints, rows, audit_rows, lineage, blockers, groups)


def _outputs(root, out, manifest, fingerprints, rows, audit_rows, lineage, blockers, groups):
    applicable = manifest.get("applicability", [])
    weights = manifest.get("weights", {})
    if not isinstance(applicable, list) or not all(_qualified(k) for k in applicable):
        raise ContractError("applicability must be an explicit key list")
    applicable = sorted(set(applicable))
    invalid_weights = not isinstance(weights, dict) or not _finite(weights) or any(
        not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0 for v in weights.values())
    if invalid_weights:
        blockers.append("invalid_weights")
    if not isinstance(manifest.get("capture_timestamp"), str) or not manifest["capture_timestamp"]:
        blockers.append("missing_capture_timestamp")
    clean = {r["qualified_key"] for r in audit_rows if r["disposition"] == "mapped" and
             isinstance(r["row"], dict) and r["row"].get("status") in {"satisfied", "unsatisfied"}}
    known = {r["qualified_key"] for r in rows if r["kind"] == "rubric" and r["qualified_key"]}
    unresolved = [k for k in applicable if k not in known or k not in clean]
    if unresolved:
        blockers.append("unresolved_applicable")
    unknown_applicable = any(k not in known for k in applicable)
    assessed = [] if invalid_weights or unknown_applicable else sorted(set(applicable) & clean)
    unassessed = sorted(set(applicable) - set(assessed))
    if not assessed:
        blockers.append("insufficient_evidence")
    before = {f["path"]: (f["length"], f["sha256"]) for f in fingerprints}
    after = {}
    for fp in fingerprints:
        raw = _safe_path(root, fp["path"]).read_bytes()
        after[fp["path"]] = (len(raw), hashlib.sha256(raw).hexdigest())
    if before != after:
        blockers.append("source_changed")
    blockers = sorted(set(blockers))
    crosswalk = {"rows": [{"locator": {"path": r["path"], "row_index": r["row_index"]},
                             "file_sha256": next(f["sha256"] for f in fingerprints if f["path"] == r["path"]),
                             "qualified_key": r["qualified_key"], "disposition": r["disposition"],
                             "reasons": sorted(r["reasons"]), "row": r["row"]} for r in rows]}
    files = {
        "inputs.json": {"capture_timestamp": manifest.get("capture_timestamp"), "inputs": fingerprints},
        "identity-crosswalk.json": crosswalk,
        "quarantine.json": {"groups": sorted(groups, key=lambda g: (g["qualified_key"] or "", g["reasons"]))},
        "lineage.json": lineage,
        "applicability.json": {"applicable_keys": applicable, "assessed_keys": assessed,
                                "unassessed_keys": unassessed,
                                "counts": {"applicable": len(applicable), "assessed": len(assessed),
                                           "unassessed": len(unassessed)}},
        "validation.json": {"blockers": sorted(set(blockers + ["diagnostic_only"])), "publication_allowed": False,
                            "readiness_grade": None},
    }
    candidate = _write(out, manifest, fingerprints, files)
    files["output_dir"] = candidate
    return files
