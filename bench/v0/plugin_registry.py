"""V0 benchmark suite registration and case definitions."""

from __future__ import annotations

from typing import Any

from .contracts import SLICE_SCHEMA_VERSION

V0_SUITE_NAME = "pheno-bench-v0-first-slice"
V0_SUITE_REVISION = "day6"
DEFAULT_GPU_UUID = "GPU-8d337a84-43de-158d-7526-7175288a6064"

_CASE_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "case_id": "transport_baseline",
        "kind": "transport_stub",
        "requires_model": False,
        "requires_live": False,
    },
    {
        "case_id": "qwen_08b_warm_gh",
        "kind": "generation_warm",
        "requires_model": True,
        "requires_live": True,
    },
    {
        "case_id": "qwen_08b_cold_gh",
        "kind": "generation_cold",
        "requires_model": True,
        "requires_live": True,
    },
    {
        "case_id": "concurrency_sweep",
        "kind": "concurrency_sweep",
        "requires_model": True,
        "requires_live": True,
    },
    {
        "case_id": "prefix_affinity_ab",
        "kind": "prefix_affinity_ab",
        "requires_model": True,
        "requires_live": True,
    },
)


def register_v0_suite() -> dict[str, Any]:
    """Return the registered V0 first-slice suite definition."""

    return {
        "name": V0_SUITE_NAME,
        "revision": V0_SUITE_REVISION,
        "schema_version": SLICE_SCHEMA_VERSION,
        "gpu_uuids": [DEFAULT_GPU_UUID],
        "cases": [
            {
                "case_id": item["case_id"],
                "kind": item["kind"],
                "requires_model": item["requires_model"],
                "requires_live": item["requires_live"],
            }
            for item in _CASE_DEFINITIONS
        ],
    }
