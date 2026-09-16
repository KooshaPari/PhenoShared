"""Deterministic bridge from Agentora/MLX ``SuiteResult`` to replay v2."""

from __future__ import annotations

import hashlib
from typing import Any

from .replay_contract import (
    SigningConfig,
    canonical_json_bytes,
    replay_hash,
    sign_envelope,
)
from .types import SuiteResult, TaskStatus

_SCHEMA_VERSION = "2.0.0"
_TS = "2026-01-01T00:00:00+00:00"


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _id(prefix: str, value: Any) -> str:
    return f"{prefix}_{_sha(value)}"


def suite_result_to_benchmark_run(
    result: SuiteResult,
    *,
    commit: str,
    signing_config: SigningConfig,
    tenant_id: str = "phenotype",
    hardware: str = "synthetic",
) -> dict[str, Any]:
    """Create a deterministic, signed replay v2 envelope from a suite result.

    ``signing_config`` is deliberately required: v2 never falls back to a
    placeholder signature or a repository-defined key.
    """

    tasks: list[dict[str, Any]] = [
        task.to_dict() if hasattr(task, "to_dict") else dict(task)  # type: ignore[call-overload]
        for task in result.task_results
    ]
    if not tasks:
        raise ValueError("Agentora benchmark conversion requires at least one task")
    if len(commit) < 7 or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("commit must be a lowercase hexadecimal revision")

    inputs = {
        "repo": "pheno-harness",
        "commit": commit,
        "harness": "agentora",
        "model": result.model,
        "task_id": result.suite,
        "hardware": hardware,
    }
    identity_hash = _sha(inputs)
    run_id = _id("run", inputs)
    causality = {
        "tenant_id": tenant_id,
        "session_id": _id("ses", inputs),
        "run_id": run_id,
        "attempt_id": _id("att", inputs),
    }
    events: list[dict[str, Any]] = []

    def emit(kind: str, details: dict[str, Any], seq: int, **extra: Any) -> None:
        """Append one replay-v2 event to the running ``events`` list."""
        event_id = _id(
            "evt", {"run": run_id, "seq": seq, "type": kind, "payload": details}
        )
        events.append(
            {
                "event_id": event_id,
                "seq": seq,
                "ts": _TS,
                "type": kind,
                "payload_sha256": _sha(details),
                "causality": causality,
                "details": details,
                **extra,
            }
        )

    emit("run_started", {"suite": result.suite, "task_count": len(tasks)}, 0)
    checkpoint_id = _id("chk", {"run": run_id, "kind": "initial"})
    emit("checkpoint", {"checkpoint": "initial"}, 1, checkpoint_id=checkpoint_id)
    emit(
        "compaction",
        {
            "tokens_before": result.tokens_in,
            "tokens_after": result.tokens_in,
            "retained_event_ids": [],
            "dropped_event_ids": [],
        },
        2,
        checkpoint_id=checkpoint_id,
    )
    sequence = 3
    artifacts: list[dict[str, str]] = []
    for task in tasks:
        calls = task.get("tool_calls") or []
        for call in calls:
            call_id = call.get("id") or _id(
                "call", {"task": task.get("task_id"), "call": call}
            )
            call_details = {
                "task_id": task.get("task_id", ""),
                "tool_call_id": call_id,
                "tool_name": call.get("name", "unknown"),
                "arguments": call.get("arguments", {}),
            }
            emit("tool_call", call_details, sequence)
            sequence += 1
            emit(
                "tool_result",
                {**call_details, "result": call.get("result", "")},
                sequence,
            )
            sequence += 1
        artifacts.append(
            {
                "kind": "report",
                "uri": f"urn:agentora:task:{task.get('task_id', '')}",
                "sha256": _sha({"task": task, "calls": calls}),
            }
        )
    outcome = {
        "suite": result.suite,
        "model": result.model,
        "tasks": tasks,
        "passed": result.passed,
        "wrong": result.wrong,
        "errored": result.errored,
    }
    outcome_sha = _sha(outcome)
    status = (
        "passed"
        if all(task.get("status") == TaskStatus.OK.value for task in tasks)
        else "failed"
    )
    # The terminal event deliberately excludes replay_hash, avoiding a circular hash.
    emit("run_finished", {"status": status, "outcome_sha256": outcome_sha}, sequence)

    envelope = {
        "schema_version": _SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "session_id": causality["session_id"],
        "run_id": run_id,
        "attempt_id": causality["attempt_id"],
        "deterministic_identity": {
            "algorithm": "sha256(canonical-json(inputs))",
            "canonical_json_sha256": identity_hash,
            "inputs": inputs,
        },
        "subject": {
            "repo": "pheno-harness",
            "commit": commit,
            "harness": "agentora",
            "runtime": "python",
            "model": result.model,
            "provider": "mlx",
            "hardware": hardware,
            "network": {"mode": "offline", "egress_policy": "deny"},
        },
        "lease": {
            "lease_id": _id("lease", inputs),
            "owner": "agentora-replay",
            "ttl_seconds": 60,
            "heartbeat_interval_seconds": 10,
        },
        "task_manifest": {
            "task_id": result.suite,
            "input_sha256": _sha([task.get("prompt", "") for task in tasks]),
            "timeout_seconds": 30,
            "assertions": [
                {
                    "id": task.get("task_id", ""),
                    "kind": "exact_match",
                    "expected": task.get("expected"),
                }
                for task in tasks
            ],
            "judge": {"name": "deterministic", "version": "1"},
        },
        "events": events,
        "result": {
            "status": status,
            "outcome_sha256": outcome_sha,
            "replay_hash": replay_hash(events),
            "failure_class": "none" if status == "passed" else "assertion",
            "artifacts": artifacts,
        },
        "provenance": {
            "collector": "pheno-harness.agentora",
            "collected_at": _TS,
            "source_hashes": {"suite_result": _sha(tasks)},
        },
    }
    return sign_envelope(envelope, signing_config)


__all__ = ["suite_result_to_benchmark_run"]
