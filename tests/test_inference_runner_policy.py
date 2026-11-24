from __future__ import annotations

import unittest

import yaml

from pheno.paths import PHENO_ROOT


class InferenceRunnerPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = yaml.safe_load(
            (PHENO_ROOT / "config" / "inference_runners.yaml").read_text(
                encoding="utf-8"
            )
        )
        cls.decode_config = yaml.safe_load(
            (PHENO_ROOT / "config" / "decode_acceleration_matrix.yaml").read_text(
                encoding="utf-8"
            )
        )

    def test_install_templates_match_reviewed_runtime_pins(self) -> None:
        runners = self.config["runners"]
        # Phase 1.1 tiered-memory: sglang + vllm anchor on PR head refs, not
        # released versions. Confirm the git+https ref + PR anchor instead of
        # a pinned ==X.Y.Z string.
        sglang_install = runners["sglang"]["install"]
        self.assertIn("refs/pull/20126/head", sglang_install)
        self.assertEqual(runners["sglang"]["cherry_pick_pr"], 20126)
        vllm_install = runners["vllm"]["install"]
        self.assertIn("refs/pull/37190/head", vllm_install)
        self.assertEqual(runners["vllm"]["cherry_pick_pr"], 37190)
        self.assertIn("tensorrt_llm==1.2.1", runners["tensorrt_llm"]["install"])

    def test_serve_templates_are_single_shell_commands(self) -> None:
        for name, runner in self.config["runners"].items():
            template = runner.get("serve_template")
            if template is not None:
                with self.subTest(runner=name):
                    self.assertNotIn("\n", template.strip())

    def test_local_endpoints_require_loopback_and_real_key(self) -> None:
        self.assertIn(
            "--host 127.0.0.1", self.config["runners"]["sglang"]["serve_template"]
        )
        self.assertEqual(
            self.config["harbor_integration"]["env_vars"]["OPENAI_API_KEY"],
            "{required_local_api_key}",
        )

    def test_zaya_fork_cannot_download_or_launch_by_default(self) -> None:
        runner = self.config["runners"]["vllm_zaya"]
        self.assertEqual(runner["execution_gate"], "blocked")
        self.assertEqual(runner["artifact_policy"], "preapproved_local_path_only")
        self.assertIn("{model_path}", runner["serve_template"])
        self.assertNotIn("Zyphra/ZAYA1-8B", runner["serve_template"])

    def test_dflash_vllm_floor_matches_decode_matrix(self) -> None:
        matrix_floor = self.decode_config["categories"]["diffusion_block_draft"][
            "methods"
        ]["dflash"]["vllm_min"]
        self.assertEqual(
            self.config["runners"]["vllm_dflash"]["vllm_min"], matrix_floor
        )
        self.assertEqual(matrix_floor, "0.20.1")


if __name__ == "__main__":
    unittest.main()
