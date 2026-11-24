from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "config" / "desktop_nvidia_qwen35_lane.yaml"


def _load_lane() -> dict:
    value = yaml.safe_load(LANE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_desktop_lane_is_qwen35_only_and_paused_by_default() -> None:
    lane = _load_lane()
    assert lane["schema_version"] == "pheno.desktop-nvidia.qwen35-lane.v1"
    assert lane["status"] == "planning_only"
    assert lane["scope"]["model_family_allowlist"] == ["Qwen3.5"]
    assert lane["scope"]["model_family_denylist"] == ["Qwen2.5"]
    assert lane["scope"]["canonical_model"] == "Qwen/Qwen3.5-0.8B"
    assert lane["scope"]["mac_inference"] == "paused"
    policy = lane["execution_policy"]
    for key in (
        "allow_model_download",
        "allow_install",
        "allow_server_launch",
        "allow_model_inference",
        "allow_benchmark_execution",
        "allow_harbor",
    ):
        assert policy[key] is False
    assert policy["require_explicit_window"] is True
    assert policy["max_concurrent_workers"] == 1
    assert policy["topology"] == "independent_workers"


def test_desktop_lane_keeps_physical_and_logical_gpu_mappings_distinct() -> None:
    devices = _load_lane()["hardware"]["devices"]
    primary = devices["rtx_3090_ti"]
    helper = devices["gtx_1080_ti"]
    assert primary["role"] == "primary"
    assert helper["role"] == "helper"
    assert primary["nvidia_smi_index"] == 1
    assert helper["nvidia_smi_index"] == 0
    assert primary["cuda_visible_devices"] == "1"
    assert helper["cuda_visible_devices"] == "0"
    assert primary["pytorch_device"] == helper["pytorch_device"] == "cuda:0"
    assert (
        primary["llama_cpp_isolated_device"]
        == helper["llama_cpp_isolated_device"]
        == "CUDA0"
    )
    assert helper["tensor_parallel"] == "forbidden"


def test_desktop_lane_requires_reproducible_provenance_before_promotion() -> None:
    lane = _load_lane()
    required = lane["provenance_requirements"]
    assert "immutable_revision" in required["model"]
    assert "binary_sha256" in required["runtime"]
    assert "logical_device_mapping" in required["device"]
    assert "explicit_window_id" in required["run"]
    assert "workload_executed" in required["run"]
    assert "dry_run" in required["run"]
    assert "exact_qwen35_model_and_revision" in lane["promotion_gates"]
    assert "harbor_or_eval_window_authorized" in lane["promotion_gates"]


def test_desktop_lane_captures_runtime_specific_visibility_mappings() -> None:
    mappings = _load_lane()["hardware"]["runtime_device_mappings"]
    vllm = mappings["vllm_wsl"]
    llama = mappings["llama_cpp_windows_b10012"]
    assert vllm["logical_device"] == "cuda:0"
    assert vllm["physical_to_visible_index"] == {"gtx_1080_ti": "0", "rtx_3090_ti": "1"}
    assert llama["build"] == "b10012-c71854292"
    assert llama["logical_device"] == "CUDA0"
    assert llama["physical_to_visible_index"] == {
        "gtx_1080_ti": "1",
        "rtx_3090_ti": "0",
    }
    assert llama["physical_to_visible_index"] != vllm["physical_to_visible_index"]


def test_unsloth_is_external_api_reference_not_vendored_runtime() -> None:
    unsloth = _load_lane()["external_backend_references"]["unsloth"]
    assert unsloth["integration_mode"] == "external_openai_compatible_api"
    assert unsloth["source_url"] == "https://github.com/unslothai/unsloth"
    assert unsloth["copy_source"] is False
    assert "studio" in unsloth["prohibited_surfaces"]
    assert "unsloth_cli" in unsloth["prohibited_surfaces"]
    assert unsloth["required_model_family"] == "Qwen3.5"
