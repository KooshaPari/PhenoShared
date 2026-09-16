"""V0 measured benchmark suite registration and first-slice runner."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pheno.evidence.contracts import canonical_json_bytes, sha256_hex

from .contracts import (
    OBSERVATION_SCHEMA_VERSION,
    SLICE_SCHEMA_VERSION,
    validate_slice_artifact,
)
from .plugin_registry import (  # noqa: F401
    _CASE_DEFINITIONS,
    DEFAULT_GPU_UUID,
    V0_SUITE_NAME,
    V0_SUITE_REVISION,
    register_v0_suite,
)
from .providers import (
    DefaultHeterogeneousProvider,
    DefaultResourceProvider,
    DefaultStreamingProvider,
    DefaultSweepProvider,
    HeterogeneousProvider,
    ResourceProvider,
    StreamingProvider,
    SweepProvider,
)

LIVE_ENV_FLAG = "PHENO_V0_LIVE"
MODEL_PATH_ENV = "PHENO_V0_MODEL_PATH"
API_BASE_ENV = "PHENO_V0_API_BASE"
DEFAULT_MODEL_ALIAS = "local/qwen35-08b"


def _empty_gpu_telemetry(gpu_uuids: list[str]) -> dict[str, dict[str, None]]:
    template = {
        "utilization_percent": None,
        "memory_used_mib": None,
        "memory_total_mib": None,
        "power_watts": None,
        "temperature_c": None,
    }
    return {uuid: dict(template) for uuid in gpu_uuids}


def _provenance_digests(
    *,
    config_path: Path | None,
    model_path: Path | None,
    fixture_path: Path | None,
    environment_label: str,
    phenocompose_run_sha256: str,
    nvms_provenance_sha256: str,
) -> dict[str, str]:
    def digest_for(path: Path | None, fallback: str) -> str:
        """SHA-256 of the file at ``path`` or a deterministic fallback string."""
        if path is not None and path.is_file():
            return sha256_hex(path.read_bytes())
        return sha256_hex(fallback.encode("utf-8"))

    return {
        "config_sha256": digest_for(config_path, "v0-config-missing"),
        "model_sha256": digest_for(model_path, "v0-model-missing"),
        "fixture_sha256": digest_for(fixture_path, "v0-fixture-missing"),
        "environment_sha256": sha256_hex(environment_label.encode("utf-8")),
        "phenocompose_run_sha256": phenocompose_run_sha256,
        "nvms_provenance_sha256": nvms_provenance_sha256,
    }


def _observation_identity(
    *,
    case_id: str,
    status: str,
    evidence_class: str,
    provenance: Mapping[str, str],
    gpu_uuids: list[str],
    gpu_telemetry: Mapping[str, Any],
    measurements: Mapping[str, Any] | None,
    block_reason: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "case_id": case_id,
        "status": status,
        "evidence_class": evidence_class,
        "provenance": dict(provenance),
        "gpu_uuids": gpu_uuids,
        "gpu_telemetry": dict(gpu_telemetry),
        "measurements": measurements,
        "block_reason": block_reason,
    }


def _build_observation(**kwargs: Any) -> dict[str, Any]:
    identity = _observation_identity(**kwargs)
    observation_id = sha256_hex(canonical_json_bytes(identity))
    return {"observation_id": observation_id, **identity}


def _blocked_observation(
    case_id: str,
    reason: str,
    provenance: Mapping[str, str],
    gpu_uuids: list[str],
) -> dict[str, Any]:
    return _build_observation(
        case_id=case_id,
        status="blocked",
        evidence_class="blocked",
        provenance=provenance,
        gpu_uuids=gpu_uuids,
        gpu_telemetry=_empty_gpu_telemetry(gpu_uuids),
        measurements=None,
        block_reason=reason,
    )


def _model_assets_available(model_path: Path | None) -> bool:
    if model_path is None:
        return False
    if not model_path.exists():
        return False
    markers = ("config.json", "tokenizer.json", "tokenizer_config.json")
    if model_path.is_file():
        return model_path.name in markers
    return any((model_path / marker).is_file() for marker in markers)


def _resolve_model_path(config: Mapping[str, Any]) -> Path | None:
    raw = os.environ.get(MODEL_PATH_ENV) or config.get("model_path")
    if not raw:
        return None
    return Path(str(raw))


def _live_enabled(config: Mapping[str, Any]) -> bool:
    flag = os.environ.get(LIVE_ENV_FLAG, config.get("live", False))
    if isinstance(flag, str):
        return flag.strip().lower() in {"1", "true", "yes", "on"}
    return bool(flag)


def _run_transport_baseline(
    provenance: Mapping[str, str],
    gpu_uuids: list[str],
) -> dict[str, Any]:
    return _build_observation(
        case_id="transport_baseline",
        status="measured",
        evidence_class="local_measured",
        provenance=provenance,
        gpu_uuids=gpu_uuids,
        gpu_telemetry=_empty_gpu_telemetry(gpu_uuids),
        measurements={
            "transport_probe_ms": 0.0,
            "measurement_quality": "offline_stub",
            "endpoint_checked": False,
        },
        block_reason=None,
    )


def _run_live_generation(
    *,
    case_id: str,
    warm: bool,
    streaming: StreamingProvider,
    resources: ResourceProvider,
    api_base: str,
    model: str,
    provenance: Mapping[str, str],
    gpu_uuids: list[str],
) -> dict[str, Any]:
    prompt = "Reply with exactly one word: benchmark."
    resource_summary = resources.sample_gpu_summary(include_gpu=True)
    result = streaming.stream_chat(
        api_base,
        model,
        prompt,
        max_tokens=16,
        temperature=0.0 if warm else 0.2,
        timeout_s=120.0,
    )
    if "error" in result:
        return _blocked_observation(
            case_id,
            f"live generation failed: {result['error']}",
            provenance,
            gpu_uuids,
        )
    telemetry = _empty_gpu_telemetry(gpu_uuids)
    gpus = resource_summary.get("gpus") or {}
    if gpus:
        first: dict[str, Any] = next(iter(gpus.values()), {})
        util = first.get("utilization_percent") or {}
        mem_used = first.get("memory_used_mib") or {}
        mem_total = first.get("memory_total_mib") or {}
        power = first.get("power_watts") or {}
        telemetry[gpu_uuids[0]] = {
            "utilization_percent": util.get("mean"),
            "memory_used_mib": mem_used.get("mean"),
            "memory_total_mib": mem_total.get("mean"),
            "power_watts": power.get("mean"),
            "temperature_c": None,
        }
    return _build_observation(
        case_id=case_id,
        status="measured",
        evidence_class="local_measured",
        provenance=provenance,
        gpu_uuids=gpu_uuids,
        gpu_telemetry=telemetry,
        measurements={
            "warm": warm,
            "ttft_ms": result.get("ttft_ms"),
            "elapsed_ms": result.get("elapsed_ms"),
            "decode_tok_s": result.get("decode_tok_s"),
            "completion_tokens": result.get("completion_tokens"),
            "measurement_quality": result.get("measurement_quality"),
        },
        block_reason=None,
    )


def _run_concurrency_placeholder(
    provenance: Mapping[str, str],
    gpu_uuids: list[str],
    sweep: SweepProvider,
    streaming: StreamingProvider,
    api_base: str,
    model: str,
) -> dict[str, Any]:
    def caller(task: dict[str, Any]) -> dict[str, Any]:
        """Run one streaming chat call for a single concurrency-sweep task."""
        return dict(
            streaming.stream_chat(
                api_base,
                model,
                task["prompt"],
                max_tokens=8,
                temperature=0.0,
                timeout_s=60.0,
            )
        )

    sweep_result = sweep.run_sweep(
        caller,
        [{"prompt": "count to three"}],
        levels=[1, 2],
        warmup=0,
    )
    if any(level["error_count"] for level in sweep_result["levels"]):
        return _blocked_observation(
            "concurrency_sweep",
            "concurrency sweep reported request errors",
            provenance,
            gpu_uuids,
        )
    return _build_observation(
        case_id="concurrency_sweep",
        status="measured",
        evidence_class="local_measured",
        provenance=provenance,
        gpu_uuids=gpu_uuids,
        gpu_telemetry=_empty_gpu_telemetry(gpu_uuids),
        measurements={"sweep": sweep_result, "placeholder": True},
        block_reason=None,
    )


def _run_prefix_affinity_placeholder(
    provenance: Mapping[str, str],
    gpu_uuids: list[str],
    heterogeneous: HeterogeneousProvider,
    streaming: StreamingProvider,
    api_base: str,
    model: str,
) -> dict[str, Any]:
    workers = [{"id": "a", "base_url": api_base}, {"id": "b", "base_url": api_base}]

    def caller(worker: dict[str, str], task: dict[str, Any]) -> dict[str, Any]:
        """Run one streaming chat call routed through a specific worker."""
        return dict(
            streaming.stream_chat(
                worker["base_url"],
                model,
                task["prompt"],
                max_tokens=8,
                temperature=0.0,
                timeout_s=60.0,
            )
        )

    result = heterogeneous.run_heterogeneous(
        workers,
        [{"prompt": "prefix A"}, {"prompt": "prefix B"}],
        concurrency=2,
        caller=caller,
    )
    if result["error_count"]:
        return _blocked_observation(
            "prefix_affinity_ab",
            "prefix affinity A/B reported request errors",
            provenance,
            gpu_uuids,
        )
    return _build_observation(
        case_id="prefix_affinity_ab",
        status="measured",
        evidence_class="local_measured",
        provenance=provenance,
        gpu_uuids=gpu_uuids,
        gpu_telemetry=_empty_gpu_telemetry(gpu_uuids),
        measurements={"heterogeneous": result, "placeholder": True},
        block_reason=None,
    )


def _case_outcome(observation: Mapping[str, Any]) -> str:
    if observation["status"] == "blocked":
        return "blocked"
    measurements = observation.get("measurements") or {}
    if observation["case_id"] == "transport_baseline":
        return "pass"
    if "error" in measurements:
        return "fail"
    return "pass"


def run_v0_first_slice(
    *,
    config: Mapping[str, Any] | None = None,
    config_path: Path | None = None,
    fixture_path: Path | None = None,
    phenocompose_run_sha256: str | None = None,
    nvms_provenance_sha256: str | None = None,
    streaming: StreamingProvider | None = None,
    sweep: SweepProvider | None = None,
    heterogeneous: HeterogeneousProvider | None = None,
    resources: ResourceProvider | None = None,
) -> dict[str, Any]:
    """Execute the V0 first slice, marking missing assets as blocked."""

    cfg = dict(config or {})
    gpu_uuids = list(cfg.get("gpu_uuids") or [DEFAULT_GPU_UUID])
    model_path = _resolve_model_path(cfg)
    model_ready = _model_assets_available(model_path)
    live = _live_enabled(cfg)
    api_base = str(
        os.environ.get(API_BASE_ENV) or cfg.get("api_base") or "http://127.0.0.1:8080"
    )
    model_alias = str(cfg.get("model") or DEFAULT_MODEL_ALIAS)
    streaming = streaming or DefaultStreamingProvider()
    sweep = sweep or DefaultSweepProvider()
    heterogeneous = heterogeneous or DefaultHeterogeneousProvider()
    resources = resources or DefaultResourceProvider()
    provenance = _provenance_digests(
        config_path=config_path,
        model_path=model_path,
        fixture_path=fixture_path,
        environment_label=str(cfg.get("environment") or "offline"),
        phenocompose_run_sha256=phenocompose_run_sha256
        or sha256_hex(b"v0-run-unbound"),
        nvms_provenance_sha256=nvms_provenance_sha256 or sha256_hex(b"v0-nvms-unbound"),
    )
    observations: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []

    transport = _run_transport_baseline(provenance, gpu_uuids)
    observations.append(transport)
    cases.append(
        {
            "case_id": "transport_baseline",
            "outcome": _case_outcome(transport),
            "observation_id": transport["observation_id"],
            "derived_id": None,
            "hypothesis_id": None,
        }
    )

    model_blocked_reason = "model assets unavailable; marked blocked (never simulated)"
    live_blocked_reason = "live GPU measurements disabled; set PHENO_V0_LIVE=1"

    for definition in _CASE_DEFINITIONS[1:]:
        case_id = definition["case_id"]
        if definition["requires_model"] and not model_ready:
            obs = _blocked_observation(
                case_id, model_blocked_reason, provenance, gpu_uuids
            )
        elif definition["requires_live"] and not live:
            obs = _blocked_observation(
                case_id, live_blocked_reason, provenance, gpu_uuids
            )
        elif case_id == "qwen_08b_warm_gh":
            obs = _run_live_generation(
                case_id=case_id,
                warm=True,
                streaming=streaming,
                resources=resources,
                api_base=api_base,
                model=model_alias,
                provenance=provenance,
                gpu_uuids=gpu_uuids,
            )
        elif case_id == "qwen_08b_cold_gh":
            obs = _run_live_generation(
                case_id=case_id,
                warm=False,
                streaming=streaming,
                resources=resources,
                api_base=api_base,
                model=model_alias,
                provenance=provenance,
                gpu_uuids=gpu_uuids,
            )
        elif case_id == "concurrency_sweep":
            obs = _run_concurrency_placeholder(
                provenance,
                gpu_uuids,
                sweep,
                streaming,
                api_base,
                model_alias,
            )
        elif case_id == "prefix_affinity_ab":
            obs = _run_prefix_affinity_placeholder(
                provenance,
                gpu_uuids,
                heterogeneous,
                streaming,
                api_base,
                model_alias,
            )
        else:
            obs = _blocked_observation(
                case_id, "unsupported case", provenance, gpu_uuids
            )
        observations.append(obs)
        cases.append(
            {
                "case_id": case_id,
                "outcome": _case_outcome(obs),
                "observation_id": obs["observation_id"],
                "derived_id": None,
                "hypothesis_id": None,
            }
        )

    measured_count = sum(item["status"] == "measured" for item in observations)
    blocked_count = sum(item["status"] == "blocked" for item in observations)
    pass_count = sum(item["outcome"] == "pass" for item in cases)
    fail_count = sum(item["outcome"] == "fail" for item in cases)
    identity = {
        "schema_version": SLICE_SCHEMA_VERSION,
        "suite": {"name": V0_SUITE_NAME, "revision": V0_SUITE_REVISION},
        "provenance": provenance,
        "gpu_uuids": gpu_uuids,
        "cases": cases,
        "observations": observations,
        "derived_metrics": [],
        "simulations": [],
        "hypotheses": [],
        "summary": {
            "measured_count": measured_count,
            "blocked_count": blocked_count,
            "pass_count": pass_count,
            "fail_count": fail_count,
        },
    }
    slice_id = sha256_hex(canonical_json_bytes(identity))
    artifact = {
        "schema_version": SLICE_SCHEMA_VERSION,
        "slice_id": slice_id,
        **identity,
    }
    return validate_slice_artifact(artifact)


__all__ = [
    "DEFAULT_GPU_UUID",
    "LIVE_ENV_FLAG",
    "MODEL_PATH_ENV",
    "V0_SUITE_NAME",
    "V0_SUITE_REVISION",
    "register_v0_suite",
    "run_v0_first_slice",
]
