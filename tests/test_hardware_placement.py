import unittest

from perf.heterogeneous import run_heterogeneous
from scripts.plan_hardware_placement import plan


class HardwarePlacementTests(unittest.TestCase):
    def test_capacity_weighted_scheduler_prefers_faster_worker(self):
        workers = [
            {"id": "3090", "capacity_weight": 2.34},
            {"id": "1080", "capacity_weight": 1.0},
        ]
        result = run_heterogeneous(
            workers,
            [{"task_id": str(i)} for i in range(10)],
            2,
            lambda worker, task: {"elapsed_ms": 1, "completion_tokens": 1},
        )
        assert result["scheduler"] == "capacity_weighted_least_normalized_load"
        assert (
            result["worker_assignments"]["3090"] > result["worker_assignments"]["1080"]
        )
        assert result["capacity_weights"] == {"3090": 2.34, "1080": 1.0}
        assert (
            abs(
                result["normalized_load_by_worker"]["3090"]
                - result["normalized_load_by_worker"]["1080"]
            )
            < 0.02
        )

    def test_primary_and_legacy_helper_are_distinct(self):
        config = {
            "policy": {"reserve_vram_fraction": 0.12},
            "models": {
                "local/test": {"artifact_q4_gb": 5.0, "preferred": ["latency_primary"]}
            },
        }
        result = plan(
            config,
            None,
            [
                {"index": 0, "name": "NVIDIA GeForce GTX 1080 Ti", "vram_mib": 11264},
                {"index": 1, "name": "NVIDIA GeForce RTX 3090 Ti", "vram_mib": 24564},
            ],
        )
        gpu = [row for row in result["placements"] if "gpu_index" in row]
        assert {row["role"] for row in gpu} == {"primary", "helper"}
        assert {row["status"] for row in gpu} == {"candidate", "not_preferred"}

    def test_failed_artifact_cannot_be_placed(self):
        config = {
            "policy": {"reserve_vram_fraction": 0.12},
            "models": {
                "local/bad": {"artifact_q4_gb": 5.0, "artifact_status": "failed"}
            },
        }
        result = plan(
            config, None, [{"index": 1, "name": "RTX 3090 Ti", "vram_mib": 24564}]
        )
        assert result["placements"][0]["status"] == "blocked_artifact"

    def test_workload_routes_are_explicit_and_non_migrating(self):
        config = {
            "policy": {"reserve_vram_fraction": 0.12},
            "workload_classes": {
                "short_draft": {
                    "preferred_tier": "legacy_helper",
                    "fallback_tier": "host_spill",
                    "constraints": ["short_context"],
                },
            },
            "models": {},
        }
        result = plan(config, None, [], "short_draft")
        assert result["workload_routes"] == [
            {
                "workload_class": "short_draft",
                "preferred_tier": "legacy_helper",
                "fallback_tier": "host_spill",
                "constraints": ["short_context"],
                "migration": "explicit_only",
            }
        ]

    def test_runtime_validated_artifact_is_not_blocked(self):
        config = {
            "policy": {"reserve_vram_fraction": 0.12},
            "models": {
                "local/ornith-8b": {
                    "artifact_q4_gb": 5.38,
                    "artifact_status": "published_mtp_q4_runtime_validated_on_1080",
                }
            },
        }
        result = plan(
            config,
            "local/ornith-8b",
            [{"index": 0, "name": "GTX 1080 Ti", "vram_mib": 11264}],
        )
        assert result["placements"][0]["status"] == "candidate"
