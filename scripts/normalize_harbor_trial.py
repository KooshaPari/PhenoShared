#!/usr/bin/env python3
"""Normalize one Harbor job into a Pheno garden-compatible observation artifact."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_QWEN35_MODELS = {
    "Qwen/Qwen3.5-0.8B",
    "local/qwen35-08b",
    "openai/local/qwen35-08b",
}
_AUTHORIZATION_SCHEMA = "pheno.desktop-harbor-authorization.v1"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _desktop_provenance(
    model_id: str,
    authorization: dict[str, Any] | None,
    started_at: Any,
) -> dict[str, Any]:
    """Bind Qwen3.5 Harbor results to an explicit desktop authorization envelope."""
    if model_id not in _QWEN35_MODELS:
        return {"status": "not_required"}
    if not isinstance(authorization, dict):
        return {
            "status": "blocked",
            "reason": "desktop authorization manifest is required",
        }
    if authorization.get("schema_version") != _AUTHORIZATION_SCHEMA:
        return {"status": "blocked", "reason": "desktop authorization schema mismatch"}
    window_id = authorization.get("window_id")
    contract_sha256 = authorization.get("contract_sha256")
    canonical_model = authorization.get("canonical_model")
    request_model = authorization.get("request_model")
    base_url = authorization.get("base_url")
    authorization_created_at = _timestamp(authorization.get("created_at"))
    trial_started_at = _timestamp(started_at)
    if not isinstance(window_id, str) or not window_id.strip():
        return {
            "status": "blocked",
            "reason": "desktop authorization window_id is required",
        }
    if not isinstance(contract_sha256, str) or not _SHA256_RE.fullmatch(
        contract_sha256
    ):
        return {
            "status": "blocked",
            "reason": "desktop authorization contract_sha256 is invalid",
        }
    if canonical_model != "Qwen/Qwen3.5-0.8B":
        return {
            "status": "blocked",
            "reason": "desktop authorization must name Qwen3.5",
        }
    if request_model not in _QWEN35_MODELS:
        return {
            "status": "blocked",
            "reason": "desktop authorization request_model is invalid",
        }
    if not isinstance(base_url, str) or not base_url.startswith(
        ("http://", "https://")
    ):
        return {
            "status": "blocked",
            "reason": "desktop authorization base_url is required",
        }
    if authorization_created_at is None or trial_started_at is None:
        return {
            "status": "blocked",
            "reason": "desktop authorization timestamps are required",
        }
    if authorization_created_at > trial_started_at:
        return {
            "status": "blocked",
            "reason": "desktop authorization is stale for this trial",
        }
    return {
        "status": "bound",
        "window_id": window_id,
        "contract_sha256": contract_sha256,
        "canonical_model": canonical_model,
        "request_model": request_model,
        "base_url": base_url,
    }


def normalize(
    job_result: dict[str, Any],
    trial_result: dict[str, Any],
    *,
    job: Path,
    authorization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = (
        trial_result.get("config")
        if isinstance(trial_result.get("config"), dict)
        else {}
    )
    agent = config.get("agent") if isinstance(config.get("agent"), dict) else {}
    verifier = trial_result.get("verifier_result")
    verifier_ok = isinstance(verifier, dict) and isinstance(
        verifier.get("rewards"), dict
    )
    rewards = verifier.get("rewards", {}) if verifier_ok else {}
    reward = rewards.get("reward") if isinstance(rewards, dict) else None
    exception = trial_result.get("exception_info")
    completed = trial_result.get("finished_at") is not None and exception is None
    stats = job_result.get("stats") if isinstance(job_result.get("stats"), dict) else {}
    agent_result = (
        trial_result.get("agent_result")
        if isinstance(trial_result.get("agent_result"), dict)
        else {}
    )
    started = trial_result.get("started_at")
    finished = trial_result.get("finished_at")
    model_id = str(agent.get("model_name", "unknown"))
    provenance = _desktop_provenance(model_id, authorization, started)
    scoreable = bool(
        completed and verifier_ok and provenance["status"] in {"bound", "not_required"}
    )
    return {
        "schema_version": "phenolm.harbor_trial.v1",
        "status": "completed" if completed else "failed",
        "scoreable": scoreable,
        "model_id": model_id,
        "suite": "terminal-bench@2.0",
        "job_artifact": str(job),
        "trial": str(trial_result.get("trial_name", "unknown")),
        "task": str((config.get("task") or {}).get("path", "unknown")),
        "metrics": {
            "reward": reward,
            "trial_count": 1,
            "error_count": 0 if exception is None else 1,
            "input_tokens": agent_result.get("n_input_tokens"),
            "cache_tokens": agent_result.get("n_cache_tokens"),
            "output_tokens": agent_result.get("n_output_tokens"),
            "episodes": (agent_result.get("metadata") or {}).get("n_episodes"),
        },
        "verifier": {
            "present": verifier_ok,
            "rewards": rewards,
        },
        "exception": exception,
        "job_stats": {
            "completed_trials": stats.get("n_completed_trials"),
            "errored_trials": stats.get("n_errored_trials"),
        },
        "timing": {"started_at": started, "finished_at": finished},
        "provenance": provenance,
        "promotion": "baseline_only; garden policy decides promotion",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path, help="Harbor job directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorization-manifest", type=Path)
    args = parser.parse_args()
    job = args.job.resolve()
    job_result = _read(job / "result.json")
    trials = sorted(job.glob("**/result.json"))
    trials = [path for path in trials if path != job / "result.json"]
    if len(trials) != 1:
        raise SystemExit(
            f"expected exactly one trial result under {job}, found {len(trials)}"
        )
    authorization = (
        _read(args.authorization_manifest) if args.authorization_manifest else None
    )
    payload = normalize(
        job_result, _read(trials[0]), job=job, authorization=authorization
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "scoreable": payload["scoreable"],
                "reward": payload["metrics"]["reward"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
