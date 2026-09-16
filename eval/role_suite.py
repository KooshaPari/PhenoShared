"""Manifest-first trace-derived role suite."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pheno.evidence.redaction import contains_secret, redact_object
from traces.ingest import infer_role, trace_eligibility

ROLE_IDS = (
    "solo_engineer",
    "coding_subagent",
    "reviewer",
    "planner_manager",
    "planner_sponsor",
    "qa_test",
    "perf_profiler",
    "release_integration",
    "advisor_critic",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_spec(
    trace_path: Path, events: list[dict[str, Any]], *, allow_ineligible: bool = False
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build a role spec and replay from trace events.

    Args:
        trace_path: Source trace file path.
        events: Trace events to materialize.
        allow_ineligible: Whether to allow ineligible traces when not redacted.

    Returns:
        Tuple of (spec, replay) dicts.

    """
    if not events:
        raise ValueError("trace contains no events")
    redaction_applied = any(contains_secret(event) for event in events)
    safe_events = [redact_object(event) for event in events]
    eligibility = trace_eligibility(safe_events)
    # A secret-bearing trace may still be materialized for redaction review;
    # the raw event is never persisted and the resulting spec remains
    # non-scoreable.  Ordinary ineligible traces retain the fail-closed gate.
    if not eligibility["eligible"] and not allow_ineligible and not redaction_applied:
        raise ValueError(eligibility["reason"])
    role = infer_role(safe_events[0])
    source = str(safe_events[0].get("source", "unknown"))
    task_id = f"trace_replay_{trace_path.stem}_{_sha256(trace_path)[:12]}"
    replay: list[dict[str, Any]] = []
    for index, event in enumerate(safe_events, 1):
        meta = event.get("meta") or {}
        if event.get("event_type") == "tool_call" or meta.get("kind") == "tool_call":
            replay.append(
                {
                    "turn": index,
                    "kind": "tool_call",
                    "role_id": role,
                    "tool": meta.get("tool", "unknown"),
                    "args": meta.get("args", {}),
                    "expected_output_kind": meta.get("expected_output_kind", "opaque"),
                }
            )
        else:
            content = (
                event.get("content")
                or meta.get("request_summary")
                or meta.get("line")
                or ""
            )
            replay.append(
                {
                    "turn": index,
                    "kind": "model_call",
                    "role_id": role,
                    "messages": [{"role": "user", "content": str(content)[:4000]}],
                    "tools_allowed": meta.get("tools_allowed", []),
                }
            )
    first = safe_events[0]
    spec = {
        "schema_version": "phenolm.role_spec.v1",
        "task_id": task_id,
        "source": {
            "origin": source,
            "trace_path": str(trace_path.resolve()),
            "trace_sha256": _sha256(trace_path),
            "captured_at": first.get("timestamp", ""),
            "captured_model": first.get("model", ""),
            "captured_provider": first.get("provider", ""),
        },
        "task_kind": first.get("event_type", "agent_trace"),
        "role_id": role,
        "brief": str(
            first.get("prompt")
            or (first.get("meta") or {}).get("request_summary")
            or "Trace replay task"
        ),
        "constraints": {
            "max_turns": max(12, len(events) * 2),
            "max_wall_s": 3600,
            "max_cost_usd": 0,
            "max_tokens_in": 100000,
            "max_tokens_out": 30000,
        },
        "verification": {
            "kind": "human_review",
            "scoreable": False,
            "eligibility": eligibility,
        },
        "metadata": {
            "source_event_count": len(events),
            "synthetic": False,
            "review_required": True,
            "redaction_applied": redaction_applied,
        },
    }
    return spec, replay


_REPLAY_KINDS = {"model_call", "tool_call", "assertion", "scoring", "checkpoint"}


def validate_replay(
    spec: dict[str, Any], replay: list[dict[str, Any]]
) -> dict[str, Any]:
    """Validate replay structure without executing models or tools."""
    errors: list[str] = []
    if not isinstance(spec, dict):
        return {"valid": False, "errors": ["spec.not_object"]}
    if not isinstance(replay, list):
        return {"valid": False, "errors": ["replay.not_list"]}
    role_id = spec.get("role_id")
    raw_constraints = spec.get("constraints")
    constraints: dict[str, Any] = (
        raw_constraints if isinstance(raw_constraints, dict) else {}
    )
    max_turns: Any = constraints.get("max_turns")
    if isinstance(max_turns, int) and max_turns >= 0 and len(replay) > max_turns:
        errors.append("replay.max_turns_exceeded")
    for index, turn in enumerate(replay, 1):
        prefix = f"replay[{index - 1}]"
        if not isinstance(turn, dict):
            errors.append(f"{prefix}.not_object")
            continue
        if turn.get("turn") != index:
            errors.append(f"{prefix}.turn_not_contiguous")
        if role_id is not None and turn.get("role_id") != role_id:
            errors.append(f"{prefix}.role_mismatch")
        kind = turn.get("kind")
        if kind not in _REPLAY_KINDS:
            errors.append(f"{prefix}.unknown_kind")
        elif kind == "model_call" and not isinstance(turn.get("messages"), list):
            errors.append(f"{prefix}.messages_missing")
        elif kind == "tool_call" and not isinstance(turn.get("tool"), str):
            errors.append(f"{prefix}.tool_missing")
        elif kind == "assertion" and not isinstance(turn.get("predicate"), str):
            errors.append(f"{prefix}.predicate_missing")
        if contains_secret(turn):
            errors.append(f"{prefix}.contains_secret")
    return {"valid": not errors, "errors": errors}


def build_manifest(spec_root: Path) -> dict[str, Any]:
    """Build a role suite manifest from ``*.spec.json`` files.

    Args:
        spec_root: Directory containing spec JSON files.

    Returns:
        Manifest dict with role counts and validation flags.

    """
    specs = sorted(spec_root.glob("*.spec.json")) if spec_root.exists() else []
    counts: dict[str, int] = dict.fromkeys(ROLE_IDS, 0)
    invalid: list[str] = []
    for path in specs:
        try:
            spec: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            role: Any = spec.get("role_id")
            verification: Any = spec.get("verification", {})
            scoreable = (
                verification.get("scoreable")
                if isinstance(verification, dict)
                else None
            )
            if (
                not isinstance(role, str)
                or role not in counts
                or scoreable is not False
            ):
                invalid.append(path.name)
            else:
                counts[role] += 1
        except (OSError, json.JSONDecodeError):
            invalid.append(path.name)
    return {
        "schema_version": "phenolm.role_suite_manifest.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "spec_root": str(spec_root.resolve()),
        "spec_count": len(specs),
        "role_counts": counts,
        "invalid_specs": invalid,
        "scoreable": False,
        "review_required": True,
    }


__all__ = ["ROLE_IDS", "build_manifest", "build_spec", "validate_replay"]
