from __future__ import annotations

import copy
import re
import unittest

import yaml

from pheno.evidence.contracts import ContractError
from pheno.evidence.tournament import build_candidate_review, validate_tournament
from pheno.paths import PHENO_ROOT


class HeterogeneousTournamentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = yaml.safe_load(
            (PHENO_ROOT / "config" / "heterogeneous_tournament.yaml").read_text(
                encoding="utf-8"
            )
        )
        cls.evidence_config = yaml.safe_load(
            (PHENO_ROOT / "config" / "evidence_registry.yaml").read_text(
                encoding="utf-8"
            )
        )

    def test_review_config_preserves_all_safety_boundaries(self) -> None:
        config = validate_tournament(self.config)
        self.assertTrue(config["policy"]["review_only"])
        self.assertFalse(config["policy"]["allow_model_artifact_download"])
        self.assertFalse(config["devices"]["m1_pro_16gb"]["remote_mutation_authorized"])
        self.assertFalse(config["devices"]["gtx_1080_ti"]["install_authorized"])
        self.assertTrue(config["mobile_worker_policy"]["coordinator_authoritative"])
        self.assertTrue(config["mobile_worker_policy"]["outbound_only"])
        self.assertTrue(config["mobile_worker_policy"]["authenticated_transport"])
        self.assertTrue(config["mobile_worker_policy"]["replay_protected_leases"])
        self.assertIsNone(config["devices"]["galaxy_s21_ultra"]["default_runtime"])
        self.assertIsNone(config["devices"]["iphone_17_pro_max"]["default_runtime"])
        self.assertTrue(
            all(
                re.fullmatch(r"[0-9a-f]{40}", str(pin["commit"]))
                for pin in config["runtime_pins"].values()
                if "commit" in pin
            )
        )

    def test_bonsai_is_dense_and_needle_is_specialist(self) -> None:
        candidates = {
            item["id"]: item for item in validate_tournament(self.config)["candidates"]
        }
        self.assertEqual(candidates["bonsai-27b"]["architecture"], "dense")
        self.assertEqual(candidates["needle-26m"]["tier"], "specialist")
        self.assertEqual(candidates["needle-26m"]["total_parameters"], 30_427_676)

    def test_candidate_cannot_self_authorize_execution(self) -> None:
        config = copy.deepcopy(self.config)
        config["candidates"][0]["execution_gate"] = "approved"
        with self.assertRaisesRegex(ContractError, "execution"):
            validate_tournament(config)

    def test_mobile_candidate_requires_exact_artifact_runtime_gate(self) -> None:
        config = copy.deepcopy(self.config)
        candidate = next(
            item for item in config["candidates"] if item["id"] == "needle-26m"
        )
        candidate.pop("mobile_support_gate")
        with self.assertRaisesRegex(
            ContractError, "exact mobile artifact/runtime gate"
        ):
            validate_tournament(config)

    def test_backend_cannot_masquerade_as_runtime(self) -> None:
        config = copy.deepcopy(self.config)
        config["runtime_pins"]["vulkan"] = {"version": "1", "channel": "test"}
        config["devices"]["galaxy_s21_ultra"]["runtimes"].append("vulkan")
        with self.assertRaisesRegex(ContractError, "conflates a backend"):
            validate_tournament(config)

    def test_review_policy_cannot_authorize_phone_or_mac_install(self) -> None:
        for device in ("m1_pro_16gb", "galaxy_s21_ultra", "iphone_17_pro_max"):
            with self.subTest(device=device):
                config = copy.deepcopy(self.config)
                config["devices"][device]["install_authorized"] = True
                with self.assertRaisesRegex(ContractError, "must remain false"):
                    validate_tournament(config)

    def test_mobile_lease_requires_replay_and_separate_hash_fields(self) -> None:
        config = copy.deepcopy(self.config)
        config["mobile_worker_policy"]["lease"]["required_fields"].remove("nonce")
        with self.assertRaisesRegex(ContractError, "missing mandatory fields"):
            validate_tournament(config)

    def test_each_candidate_lane_has_a_supported_runtime(self) -> None:
        config = copy.deepcopy(self.config)
        config["devices"]["m1_pro_16gb"]["runtimes"].remove("cactus")
        with self.assertRaisesRegex(
            ContractError, "no supported runtime for lane m1_pro_16gb"
        ):
            validate_tournament(config)

    def test_no_normal_phone_worker_exceeds_four_billion_parameters(self) -> None:
        for candidate in validate_tournament(self.config)["candidates"]:
            mobile_lanes = {"galaxy_s21_ultra", "iphone_17_pro_max"} & set(
                candidate["lanes"]
            )
            if (
                mobile_lanes
                and candidate.get("phone_lane_mode", "normal_worker") == "normal_worker"
            ):
                self.assertLessEqual(candidate["total_parameters"], 4_000_000_000)

    def test_over_four_billion_mobile_candidate_requires_feasibility_semantics(
        self,
    ) -> None:
        config = copy.deepcopy(self.config)
        candidate = next(
            item for item in config["candidates"] if item["id"] == "needle-26m"
        )
        candidate["total_parameters"] = 4_000_000_001
        candidate["active_parameters"] = 4_000_000_001
        with self.assertRaisesRegex(ContractError, "4B normal phone-worker cap"):
            validate_tournament(config)

    def test_exact_publisher_artifacts_replace_overview_and_demo_keys(self) -> None:
        candidates = {
            item["id"]: item for item in validate_tournament(self.config)["candidates"]
        }
        self.assertEqual(
            candidates["gemma4-e2b"]["registry_keys"],
            [
                "google/gemma-4-E2B-it",
                "google/gemma-4-E2B-it-qat-mobile-transformers",
                "litert-community/gemma-4-E2B-it-litert-lm",
            ],
        )
        self.assertIn(
            "google/gemma-4-26B-A4B-it-qat-q4_0-gguf",
            candidates["gemma4-26b-a4b"]["registry_keys"],
        )
        self.assertEqual(
            set(candidates["bonsai-27b"]["registry_keys"]),
            {
                "prism-ml/Bonsai-27B-AWQ-4bit",
                "prism-ml/Bonsai-27B-gguf",
                "prism-ml/Bonsai-27B-mlx-1bit",
            },
        )
        self.assertNotIn("bonsai-8b", candidates)
        self.assertIn(
            "Cactus-Compute/needle", candidates["needle-26m"]["registry_keys"]
        )

    def test_july_refresh_adds_gated_mobile_and_3090_challengers(self) -> None:
        config = validate_tournament(self.config)
        candidates = {item["id"]: item for item in config["candidates"]}
        self.assertEqual(len(candidates), 25)
        self.assertEqual(config["runtime_pins"]["litert_lm"]["version"], "0.14.0")
        self.assertEqual(
            candidates["gemma4-e2b"]["phone_lane_mode"], "feasibility_only"
        )
        self.assertEqual(
            candidates["gemma4-e4b"]["phone_lane_mode"], "feasibility_only"
        )
        self.assertEqual(candidates["lfm25-1p2b"]["phone_lane_mode"], "normal_worker")
        self.assertEqual(
            candidates["gemma4-12b"]["acceleration_pairs"]["dspark_research_only"],
            "deepseek-ai/dspark_gemma4_12b_block7",
        )
        for candidate_id in ("north-mini-code-10", "glm47-flash"):
            self.assertEqual(candidates[candidate_id]["lanes"], ["rtx_3090_ti"])
            self.assertEqual(candidates[candidate_id]["execution_gate"], "blocked")

    def test_corrected_runtime_assumptions_are_execution_gated(self) -> None:
        candidates = {
            item["id"]: item for item in validate_tournament(self.config)["candidates"]
        }
        self.assertEqual(candidates["gemma4-e2b"]["architecture"], "moe")
        self.assertEqual(candidates["zaya1-8b"]["lanes"], ["rtx_3090_ti"])
        self.assertNotIn("tensorrt_llm", candidates["qwen36-35b-a3b"]["runtimes"])
        self.assertEqual(candidates["nex-n2-mini"]["discovery_state"], "metadata_only")

    def test_priority_artifact_repositories_are_discovery_inputs(self) -> None:
        resolves = set(self.evidence_config["sources"]["hf"]["resolve_models"])
        self.assertTrue(
            {
                "Qwen/Qwen3.5-4B",
                "Qwen/Qwen3.5-9B",
                "InternScience/Agents-A1-4B",
                "deepreinforce-ai/Ornith-1.0-35B",
                "google/gemma-4-E2B-it",
                "google/gemma-4-26B-A4B-it",
                "prism-ml/Bonsai-27B-AWQ-4bit",
                "arcee-ai/Trinity-Mini",
                "arcee-ai/Trinity-Nano-Preview",
            }.issubset(resolves)
        )

    def test_planning_ceiling_is_enforced_for_every_candidate(self) -> None:
        config = validate_tournament(self.config)
        ceiling = config["policy"]["max_total_parameters"]
        self.assertEqual(ceiling, 35_000_000_000)
        self.assertTrue(
            all(item["total_parameters"] <= ceiling for item in config["candidates"])
        )

    def test_registry_join_is_review_only(self) -> None:
        record = {
            "record_id": "hf:qwen/qwen3.6-27b:example",
            "retrieved_at": "2026-07-14T22:00:00Z",
            "source": {"revision": "abc"},
            "subject": {"canonical_name": "Qwen/Qwen3.6-27B"},
            "resolved": {"mutable": False},
            "license": {"declared": ["apache-2.0"], "verified": False},
        }
        review = build_candidate_review(self.config, {"record": record})
        row = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == "qwen36-27b"
        )
        self.assertEqual(row["resolution"], "resolved_immutable")
        self.assertFalse(row["promotion_authorized"])

    def test_registry_join_orders_timezone_offsets_by_instant(self) -> None:
        def observation(record_id: str, retrieved_at: str) -> dict:
            return {
                "record_id": record_id,
                "retrieved_at": retrieved_at,
                "source": {"revision": record_id},
                "subject": {"canonical_name": "Qwen/Qwen3.6-27B"},
                "resolved": {"mutable": False},
                "license": {"declared": ["apache-2.0"], "verified": False},
            }

        review = build_candidate_review(
            self.config,
            {
                "lexically-later": observation(
                    "lexically-later", "2026-07-14T22:00:00+00:00"
                ),
                "chronologically-later": observation(
                    "chronologically-later", "2026-07-14T21:30:00-02:00"
                ),
            },
        )
        row = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == "qwen36-27b"
        )
        self.assertEqual(row["record_id"], "chronologically-later")

    def test_registry_join_prefers_immutable_detail_over_newer_mutable_search(
        self,
    ) -> None:
        def observation(record_id: str, retrieved_at: str, *, mutable: bool) -> dict:
            return {
                "record_id": record_id,
                "retrieved_at": retrieved_at,
                "source": {"revision": record_id},
                "subject": {"canonical_name": "Qwen/Qwen3.6-27B"},
                "resolved": {"mutable": mutable},
                "license": {"declared": ["apache-2.0"], "verified": False},
            }

        review = build_candidate_review(
            self.config,
            {
                "immutable-detail": observation(
                    "immutable-detail", "2026-07-14T22:00:00Z", mutable=False
                ),
                "newer-search": observation(
                    "newer-search", "2026-07-14T23:00:00Z", mutable=True
                ),
            },
        )
        row = next(
            item
            for item in review["candidates"]
            if item["candidate_id"] == "qwen36-27b"
        )
        self.assertEqual(row["resolution"], "resolved_immutable")
        self.assertEqual(row["record_id"], "immutable-detail")


if __name__ == "__main__":
    unittest.main()
