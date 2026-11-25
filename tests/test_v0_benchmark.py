from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from bench.v0.contracts import (
    DERIVED_SCHEMA_VERSION,
    HYPOTHESIS_SCHEMA_VERSION,
    OBSERVATION_SCHEMA_VERSION,
    SIMULATION_SCHEMA_VERSION,
    validate_derived_metric,
    validate_hypothesis,
    validate_observation,
    validate_simulation,
    validate_slice_artifact,
)
from bench.v0.plugin import (
    DEFAULT_GPU_UUID,
    register_v0_suite,
    run_v0_first_slice,
)
from pheno.evidence.contracts import ContractError, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "bench" / "v0" / "fixtures" / "first_slice_day6.json"
SCHEMA_DIR = ROOT / "bench" / "v0" / "schema"


def _digest(label: str) -> str:
    return sha256_hex(label.encode("utf-8"))


def _provenance() -> dict[str, str]:
    return {
        "config_sha256": _digest("config"),
        "model_sha256": _digest("model"),
        "fixture_sha256": _digest("fixture"),
        "environment_sha256": _digest("environment"),
        "phenocompose_run_sha256": _digest("phenocompose-run"),
        "nvms_provenance_sha256": _digest("nvms"),
    }


def _gpu_telemetry() -> dict[str, dict[str, None]]:
    return {
        DEFAULT_GPU_UUID: {
            "utilization_percent": None,
            "memory_used_mib": None,
            "memory_total_mib": None,
            "power_watts": None,
            "temperature_c": None,
        }
    }


def _observation_identity(
    *,
    case_id: str = "transport_baseline",
    status: str = "measured",
    evidence_class: str = "local_measured",
    measurements: dict[str, Any] | None = None,
    block_reason: str | None = None,
) -> dict[str, Any]:
    from pheno.evidence.contracts import canonical_json_bytes

    identity = {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "case_id": case_id,
        "status": status,
        "evidence_class": evidence_class,
        "provenance": _provenance(),
        "gpu_uuids": [DEFAULT_GPU_UUID],
        "gpu_telemetry": _gpu_telemetry(),
        "measurements": measurements,
        "block_reason": block_reason,
    }
    observation_id = sha256_hex(canonical_json_bytes(identity))
    return {"observation_id": observation_id, **identity}


class V0BenchmarkContractTests(unittest.TestCase):
    def test_observation_accepts_measured_row(self) -> None:
        payload = _observation_identity(
            measurements={
                "transport_probe_ms": 0.0,
                "measurement_quality": "offline_stub",
            }
        )
        validated = validate_observation(payload)
        self.assertEqual(validated["status"], "measured")
        self.assertEqual(validated["gpu_uuids"], [DEFAULT_GPU_UUID])

    def test_observation_rejects_simulated_measurements_on_blocked(self) -> None:
        payload = _observation_identity(
            case_id="qwen_08b_warm_gh",
            status="blocked",
            evidence_class="blocked",
            measurements={"decode_tok_s": 999.0},
            block_reason="would be simulated",
        )
        with self.assertRaises(ContractError):
            validate_observation(payload)

    def test_observation_rejects_bad_gpu_uuid(self) -> None:
        payload = _observation_identity(measurements={"x": 1})
        payload["gpu_uuids"] = ["not-a-gpu-uuid"]
        with self.assertRaises(ContractError):
            validate_observation(payload)

    def test_observation_rejects_mismatched_telemetry_keys(self) -> None:
        payload = _observation_identity(measurements={"x": 1})
        payload["gpu_telemetry"] = {}
        with self.assertRaises(ContractError):
            validate_observation(payload)

    def test_derived_requires_provenance_and_sources(self) -> None:
        obs = validate_observation(
            _observation_identity(measurements={"elapsed_ms": 1.0})
        )
        from pheno.evidence.contracts import canonical_json_bytes

        identity = {
            "schema_version": DERIVED_SCHEMA_VERSION,
            "case_id": "transport_baseline",
            "evidence_class": "derived",
            "provenance": _provenance(),
            "source_observation_ids": [obs["observation_id"]],
            "metrics": {"decode_tok_s": 12.5},
        }
        derived_id = sha256_hex(canonical_json_bytes(identity))
        payload = {"derived_id": derived_id, **identity}
        validated = validate_derived_metric(payload)
        self.assertEqual(validated["metrics"]["decode_tok_s"], 12.5)

    def test_simulation_is_never_measured_class(self) -> None:
        from pheno.evidence.contracts import canonical_json_bytes

        identity = {
            "schema_version": SIMULATION_SCHEMA_VERSION,
            "case_id": "qwen_08b_warm_gh",
            "evidence_class": "simulated",
            "provenance": _provenance(),
            "model_spec_sha256": _digest("spec"),
            "inputs_sha256": _digest("inputs"),
            "outputs": {"tokens_per_s": 100.0},
        }
        simulation_id = sha256_hex(canonical_json_bytes(identity))
        payload = {"simulation_id": simulation_id, **identity}
        validated = validate_simulation(payload)
        self.assertEqual(validated["evidence_class"], "simulated")

    def test_hypothesis_requires_digests(self) -> None:
        from pheno.evidence.contracts import canonical_json_bytes

        identity = {
            "schema_version": HYPOTHESIS_SCHEMA_VERSION,
            "case_id": "prefix_affinity_ab",
            "claim": "prefix affinity improves TTFT",
            "expected_direction": "decrease",
            "linked_case_ids": ["prefix_affinity_ab"],
            "provenance": _provenance(),
        }
        hypothesis_id = sha256_hex(canonical_json_bytes(identity))
        payload = {"hypothesis_id": hypothesis_id, **identity}
        validated = validate_hypothesis(payload)
        self.assertEqual(validated["expected_direction"], "decrease")


class V0BenchmarkPluginTests(unittest.TestCase):
    def test_register_v0_suite_lists_first_slice(self) -> None:
        suite = register_v0_suite()
        self.assertEqual(suite["name"], "pheno-bench-v0-first-slice")
        self.assertEqual(len(suite["cases"]), 5)

    def test_offline_run_marks_model_cases_blocked_not_simulated(self) -> None:
        artifact = run_v0_first_slice(config={"environment": "offline-test"})
        self.assertEqual(artifact["summary"]["measured_count"], 1)
        self.assertEqual(artifact["summary"]["blocked_count"], 4)
        self.assertEqual(artifact["simulations"], [])
        blocked = [
            obs
            for obs in artifact["observations"]
            if obs["case_id"] != "transport_baseline"
        ]
        for obs in blocked:
            self.assertEqual(obs["status"], "blocked")
            self.assertEqual(obs["evidence_class"], "blocked")
            self.assertIsNone(obs["measurements"])
            self.assertIn("never simulated", obs["block_reason"])

    def test_offline_transport_baseline_passes(self) -> None:
        artifact = run_v0_first_slice()
        transport_case = next(
            case
            for case in artifact["cases"]
            if case["case_id"] == "transport_baseline"
        )
        self.assertEqual(transport_case["outcome"], "pass")

    def test_model_assets_without_live_still_block_gpu_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir) / "model"
            model_dir.mkdir()
            (model_dir / "config.json").write_text("{}", encoding="utf-8")
            artifact = run_v0_first_slice(
                config={"model_path": str(model_dir), "live": False},
            )
        self.assertGreaterEqual(artifact["summary"]["blocked_count"], 4)
        warm = next(
            obs
            for obs in artifact["observations"]
            if obs["case_id"] == "qwen_08b_warm_gh"
        )
        self.assertEqual(warm["status"], "blocked")
        self.assertIn("PHENO_V0_LIVE", warm["block_reason"])

    def test_checked_in_fixture_is_schema_valid(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        validated = validate_slice_artifact(payload)
        self.assertEqual(validated["suite"]["revision"], "day6")
        self.assertEqual(validated["gpu_uuids"], [DEFAULT_GPU_UUID])

    def test_schema_files_exist(self) -> None:
        expected = {
            "observations.schema.json",
            "derived_metrics.schema.json",
            "simulations.schema.json",
            "hypotheses.schema.json",
            "slice.schema.json",
        }
        present = {path.name for path in SCHEMA_DIR.glob("*.json")}
        self.assertTrue(expected.issubset(present))


class V0BenchmarkFakeFilesystemTests(unittest.TestCase):
    def test_provenance_digests_follow_config_and_fixture_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = root / "suite.yaml"
            fixture = root / "fixture.json"
            config.write_text("name: test\n", encoding="utf-8")
            fixture.write_text("{}", encoding="utf-8")
            artifact = run_v0_first_slice(
                config={"environment": "fake-fs"},
                config_path=config,
                fixture_path=fixture,
            )
            self.assertEqual(
                artifact["provenance"]["config_sha256"],
                sha256_hex(config.read_bytes()),
            )
            self.assertEqual(
                artifact["provenance"]["fixture_sha256"],
                sha256_hex(fixture.read_bytes()),
            )

    def test_live_path_uses_streaming_provider_without_network_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir) / "model"
            model_dir.mkdir()
            (model_dir / "config.json").write_text("{}", encoding="utf-8")

            class FakeStreaming:
                def stream_chat(self, *_args, **_kwargs):
                    return {
                        "ttft_ms": 10.0,
                        "elapsed_ms": 100.0,
                        "decode_tok_s": 50.0,
                        "completion_tokens": 5,
                        "measurement_quality": "stream_chunk_proxy",
                    }

            class FakeResources:
                def sample_gpu_summary(self, **_kwargs):
                    return {"gpus": {}}

            class FakeSweep:
                def run_sweep(self, caller, tasks, levels, warmup=0):
                    return {
                        "warmup": {
                            "requested": warmup,
                            "results": [],
                            "error_count": 0,
                        },
                        "levels": [
                            {
                                "concurrency": level,
                                "request_count": len(tasks),
                                "success_count": len(tasks),
                                "error_count": 0,
                                "wall_ms": 1.0,
                                "aggregate_tokens": 4,
                                "aggregate_tokens_per_s": 4.0,
                                "latency_ms_p50": 1.0,
                                "latency_ms_p95": 1.0,
                                "results": [caller(task) for task in tasks],
                            }
                            for level in levels
                        ],
                    }

            class FakeHeterogeneous:
                def run_heterogeneous(self, workers, tasks, concurrency, caller):
                    results = [
                        caller(worker, task) for worker, task in zip(workers, tasks)
                    ]
                    return {
                        "concurrency": concurrency,
                        "worker_count": len(workers),
                        "request_count": len(results),
                        "success_count": len(results),
                        "error_count": 0,
                        "results": results,
                    }

            artifact = run_v0_first_slice(
                config={
                    "model_path": str(model_dir),
                    "live": True,
                    "api_base": "http://fake/v1",
                },
                streaming=FakeStreaming(),
                resources=FakeResources(),
                sweep=FakeSweep(),
                heterogeneous=FakeHeterogeneous(),
            )
        warm = next(
            obs
            for obs in artifact["observations"]
            if obs["case_id"] == "qwen_08b_warm_gh"
        )
        self.assertEqual(warm["status"], "measured")
        self.assertEqual(warm["measurements"]["decode_tok_s"], 50.0)


if __name__ == "__main__":
    unittest.main()
