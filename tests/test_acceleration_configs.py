from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class AccelerationConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decode = yaml.safe_load(
            (ROOT / "config" / "decode_acceleration_matrix.yaml").read_text(
                encoding="utf-8"
            )
        )
        cls.kv = yaml.safe_load(
            (ROOT / "config" / "kv_bakeoff.yaml").read_text(encoding="utf-8")
        )

    def test_decode_matrix_is_review_only_and_offline(self) -> None:
        policy = self.decode["execution_policy"]
        self.assertEqual(policy["phase"], "review_only")
        self.assertFalse(policy["allow_network"])
        self.assertFalse(policy["allow_downloads"])
        self.assertFalse(policy["allow_server_launch"])

    def test_dflash_runtime_floor_and_proxy_quarantine(self) -> None:
        dflash = self.decode["categories"]["diffusion_block_draft"]["methods"]["dflash"]
        self.assertEqual(dflash["vllm_min"], "0.20.1")

        quarantined_targets: set[str] = set()
        for row in self.decode["dflash_checkpoints"]:
            if row.get("proxy"):
                quarantined_targets.add(row["target_id"])
                self.assertIsNone(row["dflash_hf"])
                self.assertFalse(row["eligible"])
                self.assertTrue(row["status"].startswith("quarantined_"))
                self.assertTrue(row.get("rejected_proxy_hf"))

        for sweep in self.decode["first_sweep"]["pairs"]:
            if "dflash" in sweep["decode"]:
                self.assertNotIn(sweep["target"], quarantined_targets)

        exact = {
            row["target_id"]: row
            for row in self.decode["dflash_checkpoints"]
            if row.get("status") == "review_only_exact_pair_candidate"
        }
        self.assertEqual(
            exact["gemma4-12b"]["preferred_first_runtime"],
            "sglang",
        )
        self.assertTrue(exact["gemma4-12b"]["draft_license_metadata_missing"])
        self.assertEqual(exact["laguna-xs-2.1"]["preferred_first_runtime"], "vllm")
        self.assertEqual(exact["laguna-xs-2.1"]["runtime_min"], "0.25.0")
        self.assertIn("tool_template_fix_commit", exact["laguna-xs-2.1"])
        self.assertEqual(
            self.decode["first_sweep"]["pairs"][0]["runner"],
            "sglang",
        )

    def test_unverified_cross_family_ar_pairs_are_not_active(self) -> None:
        methods = self.decode["categories"]["autoregressive_speculative"]["methods"]
        self.assertEqual(methods["speculative_06b"]["pairs_with_targets"], [])
        self.assertNotIn("granite-4.1-8b", methods["eagle3"]["pairs_with_targets"])
        ultra = self.decode["categories"]["ultra_low_bit_draft"]["methods"]
        self.assertNotIn(
            "granite-4.1-8b", ultra["codescout_17b_draft"]["pairs_with_targets"]
        )

    def test_ssd_is_same_request_branch_predrafting_not_cache_reuse(self) -> None:
        ssd = self.decode["categories"]["speculative_speculative_decoding"]["methods"][
            "ssd"
        ]
        self.assertEqual(ssd["status"], "lab_only")
        self.assertEqual(ssd["scope"], "same_request")
        self.assertFalse(ssd["reuses_cross_request_cache"])
        self.assertNotIn("dflash", ssd["depends_on"])

        domino_tree = self.decode["categories"]["speculative_speculative_decoding"][
            "methods"
        ]["domino_tree"]
        self.assertFalse(domino_tree["eligible"])
        self.assertEqual(
            set(domino_tree["distinct_from"]),
            {"ddtree", "caddtree", "domino"},
        )

    def test_moe_speculation_is_paper_only_and_non_executable(self) -> None:
        methods = self.decode["categories"]["moe_self_assisted_speculation"]["methods"]
        for method in methods.values():
            self.assertEqual(method["status"], "paper_only")
            self.assertEqual(method["runner"], [])
            self.assertFalse(method["eligible"])
            self.assertIn("explicit_user_approval", method["activation_requires"])

    def test_dspark_and_dflare_support_is_not_generalized(self) -> None:
        categories = self.decode["categories"]
        dspark = categories["confidence_scheduled_speculative"]["methods"]["dspark"]
        self.assertEqual(
            set(dspark["released_targets"]),
            {"deepseek-v4", "qwen3-4b", "qwen3-8b", "qwen3-14b", "gemma4-12b"},
        )
        self.assertEqual(dspark["frontier_tournament_targets"], ["gemma4-12b"])
        self.assertEqual(
            dspark["gemma4_12b_runtime"],
            "deepspec_research_only_vllm_pr_47216_open",
        )
        self.assertFalse(dspark["qwen3_5_or_3_6_checkpoint_found"])
        self.assertFalse(dspark["stable_sglang_release_path"])

        dflare = categories["diffusion_block_draft"]["methods"]["dflare"]
        self.assertFalse(dflare["stock_vllm_path"])
        self.assertFalse(dflare["stock_sglang_path"])
        self.assertEqual(
            set(dflare["released_heads"]), {"qwen3-4b", "qwen3-8b", "gpt-oss-20b"}
        )
        self.assertFalse(dflare["eligible"])

    def test_kv_experimental_implementations_are_distinct_and_non_executable(
        self,
    ) -> None:
        policy = self.kv["execution_policy"]
        self.assertEqual(policy["phase"], "review_only")
        self.assertFalse(policy["allow_downloads"])
        self.assertFalse(policy["allow_execution"])

        variants = self.kv["variants"]
        self.assertFalse(
            any("rotor" in (v["id"] + v.get("label", "")).lower() for v in variants)
        )

        experimental = {v["id"]: v for v in self.kv["experimental_variants"]}
        self.assertEqual(
            experimental["vllm_turboquant_k8v4"]["implementation"], "stock_vllm"
        )
        self.assertEqual(
            experimental["community_turboquant_plus_format_review"]["implementation"],
            "community_turboquant_plus_fork",
        )
        community = experimental["community_turboquant_plus_format_review"]
        self.assertEqual(
            community["reported_current_formats"], ["turbo2", "turbo3", "turbo4"]
        )
        self.assertNotIn("tq1_0", str(community))
        for variant in experimental.values():
            self.assertFalse(variant["executable_by_current_script"])
            self.assertFalse(variant["allow_downloads"])

    def test_vericache_is_watchlist_only_with_quality_gates(self) -> None:
        vericache = self.kv["research_watchlist"]["vericache"]
        self.assertEqual(
            vericache["status"], "paper_watchlist_no_public_implementation"
        )
        self.assertFalse(vericache["executable_variant"])
        self.assertFalse(vericache["public_implementation_found"])
        self.assertEqual(vericache["paper"], "https://arxiv.org/abs/2605.17613")
        gates = set(vericache["promotion_requires"])
        self.assertIn("deterministic_cache_correctness_test", gates)
        self.assertIn("quality_non_regression_on_agent_suite", gates)
        self.assertIn("long_context_retrieval_and_tool_json_pass", gates)
        self.assertIn("exact_tool_argument_match", gates)
        self.assertIn("patch_parse_and_tests_pass", gates)
        self.assertIn("long_generation_divergence_bound", gates)
        self.assertIn("greedy_output_identity", gates)


if __name__ == "__main__":
    unittest.main()
