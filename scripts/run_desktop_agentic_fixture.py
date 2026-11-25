#!/usr/bin/env python3
"""Run a provenance-bound, single-tool desktop agentic fixture.

The wrapper never launches or terminates a server. ``--execute`` requires an
explicit authorization window and an endpoint advertising the exact canonical
Qwen3.5 model. The fixture validates a tool-call envelope but does not execute
the returned tool, so it is safe to run before a Harbor authorization window.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.desktop_execution_preflight import (
    PreflightError,
    canonical_contract_sha256,
    validate_execution_preflight,
)

CONTRACT = ROOT / "config/desktop_nvidia_qwen35_lane.yaml"
CANONICAL_MODEL = "Qwen/Qwen3.5-0.8B"
SERVED_MODEL_ALIASES = frozenset({CANONICAL_MODEL, "local/qwen35-08b", "qwen35-08b"})
EXPECTED_TOOL = "get_runtime_status"
EXPECTED_ARGUMENTS = {"component": "runtime"}
RUNTIME_DEFAULTS = {
    "primary": ("http://127.0.0.1:8000", "desktop-vllm-3090ti"),
    "helper": ("http://127.0.0.1:8082", "desktop-llama-cpp-1080ti"),
}


def _contract_sha256() -> str:
    return canonical_contract_sha256(CONTRACT)


def _require_live_execution_policy() -> None:
    """Fail closed unless the lane contract explicitly authorizes live fixtures."""
    try:
        contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"execution policy is unavailable or invalid: {exc}") from exc
    policy = contract.get("execution_policy") if isinstance(contract, dict) else None
    if not isinstance(policy, dict) or (
        contract.get("status") != "active"
        or policy.get("allow_model_inference") is not True
        or policy.get("allow_benchmark_execution") is not True
    ):
        raise SystemExit("execution policy forbids live desktop agentic fixture")


def _require_owner_issued_execution_authority() -> None:
    """Fail closed until an owner publishes a bound execution authority."""
    raise SystemExit(
        "desktop execution is blocked: no owner-issued authority contract is configured"
    )


def _is_qwen35_model(model_id: str) -> bool:
    """Allow only the canonical model or its documented local serving aliases."""
    return model_id in SERVED_MODEL_ALIASES


def _endpoint_models(base_url: str, timeout: float) -> list[str]:
    request = urllib.request.Request(base_url.rstrip("/") + "/v1/models")
    try:
        with (
            urllib.request.urlopen(request, timeout=timeout) as response  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            payload = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"endpoint model probe failed: {exc}") from exc
    rows = payload.get("data") if isinstance(payload, dict) else None
    if rows is None and isinstance(payload, dict):
        rows = payload.get("models")
    if not isinstance(rows, list):
        raise RuntimeError("endpoint /v1/models response has no data/models list")
    models: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            models.extend(str(row.get(key, "")) for key in ("id", "name", "model"))
    return [model for model in models if model]


def _build_request(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a bounded runtime agent. Use the requested tool exactly once.",
            },
            {
                "role": "user",
                "content": "Call get_runtime_status for the runtime component. Do not answer with prose.",
            },
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": EXPECTED_TOOL,
                    "description": "Report the status of one runtime component.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "component": {"type": "string", "enum": ["runtime"]}
                        },
                        "required": ["component"],
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": EXPECTED_TOOL}},
        "max_tokens": 128,
        "temperature": 0.0,
        "stream": False,
    }


def _validate_tool_call_response(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices") or []
    message = choices[0].get("message") if choices else None
    calls = message.get("tool_calls") if isinstance(message, dict) else None
    if not isinstance(calls, list) or len(calls) != 1:
        return {"passed": False, "error": "expected exactly one tool call"}
    function = calls[0].get("function") if isinstance(calls[0], dict) else None
    if not isinstance(function, dict) or function.get("name") != EXPECTED_TOOL:
        return {"passed": False, "error": f"expected tool {EXPECTED_TOOL}"}
    try:
        arguments = json.loads(function.get("arguments", ""))
    except (TypeError, json.JSONDecodeError) as exc:
        return {"passed": False, "error": f"tool arguments are not JSON: {exc}"}
    if arguments != EXPECTED_ARGUMENTS:
        return {"passed": False, "error": f"unexpected tool arguments: {arguments!r}"}
    return {
        "passed": True,
        "tool_call_id": calls[0].get("id"),
        "tool_name": EXPECTED_TOOL,
        "arguments": arguments,
    }


def _post_tool_request(base_url: str, model: str, timeout: float) -> dict[str, Any]:
    body = _build_request(model)
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Connection": "close",
        },
    )
    started = time.perf_counter()
    try:
        with (
            urllib.request.urlopen(request, timeout=timeout) as response  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            payload = json.loads(response.read())
            status = response.status
    except urllib.error.HTTPError as exc:
        return {
            "passed": False,
            "error": f"HTTP {exc.code}: {exc.read(512).decode(errors='replace')}",
        }
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"passed": False, "error": f"agentic request failed: {exc}"}
    result = _validate_tool_call_response(payload)
    result.update(
        {"status": status, "elapsed_ms": (time.perf_counter() - started) * 1000.0}
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=sorted(RUNTIME_DEFAULTS), required=True)
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--preflight-record", type=Path)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.window_id.strip():
        raise SystemExit("--window-id must be a non-empty authorization identifier")
    default_url, engine = RUNTIME_DEFAULTS[args.runtime]
    plan = {
        "schema_version": "pheno.desktop-agentic-fixture-plan.v1",
        "runtime": args.runtime,
        "engine_label": engine,
        "base_url": args.base_url or default_url,
        "model": CANONICAL_MODEL,
        "request_model": CANONICAL_MODEL,
        "window_id": args.window_id,
        "contract_sha256": _contract_sha256(),
        "execute": args.execute,
        "output": str(args.output),
    }
    if not args.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    _require_live_execution_policy()
    try:
        validate_execution_preflight(
            args.preflight_record,
            args.runtime,
            plan["base_url"],
            contract_path=CONTRACT,
        )
    except PreflightError as exc:
        raise SystemExit(
            f"execution preflight blocks live desktop agentic fixture: {exc}"
        ) from exc
    _require_owner_issued_execution_authority()
    try:
        models = _endpoint_models(plan["base_url"], args.timeout_s)
    except RuntimeError as exc:
        print(
            json.dumps({**plan, "status": "blocked", "error": str(exc)}, sort_keys=True)
        )
        return 2
    served_model = next((model for model in models if _is_qwen35_model(model)), None)
    if served_model is None:
        print(
            json.dumps(
                {
                    **plan,
                    "status": "blocked",
                    "error": f"endpoint does not advertise Qwen3.5: {models}",
                },
                sort_keys=True,
            )
        )
        return 2
    plan["request_model"] = served_model
    started = datetime.now(UTC).isoformat()
    result = _post_tool_request(plan["base_url"], served_model, args.timeout_s)
    artifact = {
        **plan,
        "schema_version": "pheno.desktop-agentic-fixture.v1",
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "workload_executed": True,
        "dry_run": False,
        "fallback_detected": False,
        "result": result,
    }
    canonical = json.dumps(artifact, sort_keys=True, separators=(",", ":"))
    artifact["artifact_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"output": str(args.output), "passed": result.get("passed", False)},
            sort_keys=True,
        )
    )
    return 0 if result.get("passed") else 3


if __name__ == "__main__":
    raise SystemExit(main())
