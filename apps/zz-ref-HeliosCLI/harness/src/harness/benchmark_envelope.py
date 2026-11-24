"""Strict benchmark-envelope construction and integrity verification."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

_FULL_GIT_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_UNSIGNED_SIGNATURE = {
    "status": "unsigned",
    "algorithm": "none",
    "reason": "signing_authority_not_configured",
}


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _replay_digest(events: list[dict[str, Any]]) -> str:
    normalized = [{key: value for key, value in event.items() if key != "ts"} for event in events]
    return _digest(normalized)


def _require_resolved_git_sha(subject_commit: str) -> str:
    if _FULL_GIT_SHA.fullmatch(subject_commit) is None:
        raise ValueError("benchmark envelope requires a resolved Git SHA for the subject commit")
    return subject_commit


def _require_resolved_ref(subject_ref: str) -> str:
    if not subject_ref or any(character.isspace() for character in subject_ref):
        raise ValueError("benchmark envelope requires a resolved source ref")
    return subject_ref


def _require_plan_hash(plan_hash: str) -> str:
    if _SHA256.fullmatch(plan_hash) is None:
        raise ValueError("benchmark envelope requires a SHA-256 command plan hash")
    return plan_hash


def stored_plan_hash(payload: dict[str, Any]) -> str | None:
    """Return a valid plan identity from a strict or legacy envelope."""
    candidates = (
        payload.get("plan_hash"),
        payload.get("task_manifest", {}).get("input_sha256"),
        payload.get("provenance", {}).get("source_hashes", {}).get("plan"),
    )
    return next(
        (
            candidate
            for candidate in candidates
            if isinstance(candidate, str) and _SHA256.fullmatch(candidate) is not None
        ),
        None,
    )


def _string_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def _canonical_commands(raw_commands: object, repo: str) -> list[dict[str, Any]]:
    if not isinstance(raw_commands, list):
        return []
    commands = [
        {
            "command": str(command.get("command", "")),
            "bucket": _string_value(command.get("bucket", "runtime")),
            "required": bool(command.get("required", True)),
            "cwd": str(command.get("cwd", repo)),
            "source": str(command.get("source", "")),
            "rationale": str(command.get("rationale", "")),
        }
        for command in raw_commands
        if isinstance(command, dict)
    ]
    return sorted(
        commands,
        key=lambda entry: (
            entry["bucket"],
            entry["required"],
            entry["command"],
            entry["source"],
            entry["cwd"],
        ),
    )


def _task(command: dict[str, Any], plan_hash: str, index: int, repo: str) -> dict[str, Any]:
    task_id = f"task_{_digest({'plan': plan_hash, 'index': index, 'command': command.get('command', '')})}"
    return {
        "task_id": task_id,
        "command": str(command.get("command", "")),
        "bucket": _string_value(command.get("bucket", "runtime")),
        "required": bool(command.get("required", True)),
        "cwd": str(command.get("cwd", repo)),
        "source": str(command.get("source", "")),
        "rationale": str(command.get("rationale", "")),
    }


def _events(causality: dict[str, str], run_id: str) -> list[dict[str, Any]]:
    now = datetime.now(UTC).isoformat()
    checkpoint_id = f"cp_{_digest({'run_id': run_id, 'checkpoint': 0})[:16]}"
    events: list[dict[str, Any]] = []
    event_types = ("run_started", "checkpoint", "compaction", "run_finished")
    for sequence, event_type in enumerate(event_types):
        event: dict[str, Any] = {
            "event_id": f"evt_{_digest({'run_id': run_id, 'seq': sequence, 'type': event_type})}",
            "seq": sequence,
            "ts": now,
            "type": event_type,
            "payload_sha256": _digest({"type": event_type, "seq": sequence}),
            "causality": causality,
        }
        if event_type in {"checkpoint", "compaction"}:
            event["checkpoint_id"] = checkpoint_id
        if event_type == "compaction":
            event["details"] = {
                "tokens_before": 0,
                "tokens_after": 0,
                "retained_event_ids": [],
                "dropped_event_ids": [],
            }
        events.append(event)
    return events


def add_envelope(
    payload: dict[str, Any],
    *,
    repo: str,
    plan_hash: str,
    subject_commit: str,
    subject_ref: str,
) -> dict[str, Any]:
    """Promote harness output into a strict, explicitly unsigned envelope."""
    subject_commit = _require_resolved_git_sha(subject_commit)
    subject_ref = _require_resolved_ref(subject_ref)
    plan_hash = _require_plan_hash(plan_hash)
    result_code = str(payload.get("result_code", "WARN"))
    if result_code not in {"PASS", "WARN", "FAIL"}:
        raise ValueError(f"unsupported benchmark result code: {result_code}")

    identity = {
        "repo": repo,
        "commit": subject_commit,
        "harness": "helios-harness",
        "model": "unknown",
        "task_id": f"plan:{plan_hash}",
        "hardware": "unknown",
    }
    identity_digest = _digest(identity)
    run_id = f"run_{identity_digest}"
    session_id = f"ses_{_digest({'run_id': run_id, 'session': 'default'})}"
    attempt_id = f"att_{_digest({'run_id': run_id, 'attempt': 0})}"
    causality = {
        "tenant_id": "phenotype",
        "session_id": session_id,
        "run_id": run_id,
        "attempt_id": attempt_id,
    }
    raw_commands = payload.get("commands", payload.get("plan", []))
    commands = _canonical_commands(raw_commands, repo)
    tasks = [_task(command, plan_hash, index, repo) for index, command in enumerate(commands)]
    raw_runs = [run for run in payload.get("runs", []) if isinstance(run, dict)]
    task_ids_by_command: dict[str, list[str]] = {}
    for task in tasks:
        task_ids_by_command.setdefault(task["command"], []).append(task["task_id"])
    runs = []
    for index, run in enumerate(raw_runs[: len(tasks)]):
        matching_task_ids = task_ids_by_command.get(str(run.get("command", "")), [])
        task_id = matching_task_ids.pop(0) if matching_task_ids else tasks[index]["task_id"]
        runs.append(
            {
                "run_id": f"taskrun_{_digest({'run': run, 'index': index})}",
                "task_id": task_id,
                "command": str(run.get("command", "")),
                "status": (
                    "timeout"
                    if run.get("timed_out")
                    else "skipped"
                    if run.get("skipped")
                    else "passed"
                    if run.get("returncode") in (0, None)
                    else "failed"
                ),
                "returncode": run.get("returncode"),
                "duration_ms": int(run.get("duration_ms", 0)),
            }
        )
    events = _events(causality, run_id)
    legacy_digest = _digest(payload)
    passed = result_code == "PASS"
    skipped = any(run.get("skipped") for run in raw_runs)
    envelope: dict[str, Any] = {
        "schema_version": "1.0.0",
        **causality,
        "deterministic_identity": {
            "algorithm": "sha256(canonical-json(inputs))",
            "canonical_json_sha256": identity_digest,
            "inputs": identity,
        },
        "subject": {
            "repo": repo,
            "ref": subject_ref,
            "commit": subject_commit,
            "harness": "helios-harness",
            "runtime": "python",
            "model": "unknown",
            "hardware": "unknown",
        },
        "lease": {
            "lease_id": f"lease_{attempt_id[4:20]}",
            "owner": "helios-harness",
            "ttl_seconds": 120,
            "heartbeat_interval_seconds": 20,
        },
        "task_manifest": {
            "task_id": f"plan:{plan_hash}",
            "input_sha256": plan_hash,
            "timeout_seconds": 1,
            "assertions": [{"id": "plan_discovered", "kind": "command_plan", "expected": True}],
            "judge": {"name": "helios-harness", "version": "0.1.0"},
        },
        "plan_hash": plan_hash,
        "plan": tasks,
        "commands": tasks,
        "tasks": tasks,
        "runs": runs,
        "events": events,
        "result": {
            "status": "passed" if passed else "cancelled" if skipped else "failed",
            "outcome_sha256": legacy_digest,
            "replay_hash": _replay_digest(events),
            "failure_class": "none" if passed else "policy" if skipped else "unknown",
            "artifacts": [
                {
                    "kind": "report",
                    "uri": f"urn:helios:legacy-evidence:{legacy_digest}",
                    "sha256": legacy_digest,
                }
            ],
        },
        "provenance": {
            "collector": "helios-harness",
            "collected_at": datetime.now(UTC).isoformat(),
            "source_ref": subject_ref,
            "source_sha": subject_commit,
            "source_hashes": {"plan": plan_hash},
        },
        "signature": dict(_UNSIGNED_SIGNATURE),
        "result_code": result_code,
    }
    replay = payload.get("replay")
    if isinstance(replay, dict):
        envelope["replay"] = replay
    verify_envelope_integrity(envelope)
    return envelope


def verify_envelope_integrity(envelope: dict[str, Any]) -> None:
    """Reject inconsistent hashes, source identity, or signature claims."""
    identity = envelope.get("deterministic_identity", {})
    inputs = identity.get("inputs", {})
    if identity.get("canonical_json_sha256") != _digest(inputs):
        raise ValueError("benchmark envelope deterministic identity hash mismatch")
    subject = envelope.get("subject", {})
    if subject.get("repo") != inputs.get("repo") or subject.get("commit") != inputs.get("commit"):
        raise ValueError("benchmark envelope deterministic identity does not match subject")
    _require_resolved_git_sha(str(subject.get("commit", "")))
    _require_resolved_ref(str(subject.get("ref", "")))

    plan_hash = str(envelope.get("plan_hash", ""))
    _require_plan_hash(plan_hash)
    task_manifest = envelope.get("task_manifest", {})
    provenance = envelope.get("provenance", {})
    if (
        provenance.get("source_sha") != subject.get("commit")
        or provenance.get("source_ref") != subject.get("ref")
        or provenance.get("source_hashes", {}).get("plan") != plan_hash
        or task_manifest.get("input_sha256") != plan_hash
    ):
        raise ValueError("benchmark envelope provenance does not match subject and plan")

    task_lists = [envelope.get(field) for field in ("plan", "commands", "tasks")]
    if not all(isinstance(tasks, list) for tasks in task_lists):
        raise ValueError("benchmark envelope plan hash cannot be verified")
    normalized_lists = [
        _canonical_commands(tasks, str(subject.get("repo", ""))) for tasks in task_lists
    ]
    if any(commands != normalized_lists[0] for commands in normalized_lists[1:]):
        raise ValueError("benchmark envelope plan hash does not match task collections")
    if _digest(normalized_lists[0]) != plan_hash:
        raise ValueError("benchmark envelope plan hash does not match plan contents")
    for index, task in enumerate(task_lists[0]):
        expected_task_id = _task(task, plan_hash, index, str(subject.get("repo", "")))["task_id"]
        if task.get("task_id") != expected_task_id:
            raise ValueError("benchmark envelope plan hash does not match task identity")

    events = envelope.get("events", [])
    if not isinstance(events, list):
        raise ValueError("benchmark envelope events must be a list")
    for event in events:
        expected = _digest({"type": event.get("type"), "seq": event.get("seq")})
        if event.get("payload_sha256") != expected:
            raise ValueError("benchmark envelope event payload hash mismatch")
    result = envelope.get("result", {})
    if result.get("replay_hash") != _replay_digest(events):
        raise ValueError("benchmark envelope replay hash mismatch")
    if envelope.get("signature") != _UNSIGNED_SIGNATURE:
        raise ValueError("benchmark envelope has an invalid unsigned signature state")
