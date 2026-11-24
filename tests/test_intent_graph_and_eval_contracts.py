from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from eval.long_horizon import build_manifest, load_config
from harness.intent_graph import GraphEdge, GraphNode, IntentGraph, IntentGraphRecorder
from pheno.harbor_util import route_env
from pheno.model_policy import require_local_alias
from pheno.paths import PHENO_ROOT


class IntentGraphTests(unittest.TestCase):
    def test_recorder_writes_valid_graph(self) -> None:
        recorder = IntentGraphRecorder("run-1", "synthetic")
        root = recorder.start_node("run", "root")
        child = recorder.start_node("model_call", "model", parent=root)
        recorder.finish_node(child, status="completed", attributes={"tokens": 3})
        recorder.finish_node(root, status="completed")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = recorder.write(Path(temp_dir) / "run.graph.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["run_id"], "run-1")
        self.assertEqual(len(payload["nodes"]), 2)
        self.assertEqual(payload["nodes"][1]["attributes"]["tokens"], 3)

    def test_cycle_is_rejected(self) -> None:
        graph = IntentGraph(
            run_id="cycle",
            suite="synthetic",
            nodes=[GraphNode("a", "run", "a"), GraphNode("b", "tool_call", "b")],
            edges=[
                GraphEdge("a", "b", "depends_on"),
                GraphEdge("b", "a", "depends_on"),
            ],
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            graph.validate()


class EvalContractTests(unittest.TestCase):
    def test_local_model_and_disk_policies_are_locked(self) -> None:
        root = PHENO_ROOT
        matrix = yaml.safe_load(
            (root / "config" / "local_model_bench_matrix.yaml").read_text(
                encoding="utf-8"
            )
        )
        aliases = {item["alias"] for item in matrix["models"].values()}
        self.assertEqual(
            aliases,
            {
                "local/qwen35-08b",
                "local/qwen35-4b",
                "local/lfm25-8b-a1b",
                "local/ornith-8b",
            },
        )
        budget = yaml.safe_load(
            (root / "config" / "disk_budget.yaml").read_text(encoding="utf-8")
        )
        self.assertFalse(budget["policy"]["allow_network_download"])
        self.assertEqual(
            budget["filesystem"]["cache_root_env"], "PHENO_MODEL_CACHE_ROOT"
        )
        self.assertEqual(set(budget["policy"]["local_models"]), aliases)

    def test_cloud_alias_is_rejected_by_local_policy(self) -> None:
        with self.assertRaises(ValueError):
            require_local_alias("inclusionai/ling-2.6-flash")

    def test_pheno_serve_route_is_local(self) -> None:
        kind, model, env = route_env(
            {
                "id": "local/qwen35-08b",
                "route_kind": "pheno_serve",
                "api_model": "local/qwen35-08b",
                "base_url": "http://127.0.0.1:21080/v1",
            }
        )
        self.assertEqual(kind, "pheno_serve")
        self.assertEqual(model, "openai/local/qwen35-08b")
        self.assertEqual(env["OPENAI_BASE_URL"], "http://127.0.0.1:21080/v1")
        self.assertEqual(env["OPENAI_API_KEY"], "local-no-key")

    def test_schema_fixture_is_non_scoreable(self) -> None:
        root = PHENO_ROOT / "bench" / "fixtures" / "long_horizon_example"
        manifest = build_manifest(
            load_config(),
            task_root=root,
            model_alias="local/lfm25-8b-a1b",
            execute=False,
        )
        self.assertEqual(manifest["task_count"], 1)
        self.assertFalse(manifest["scoreable"])
        self.assertEqual(len(manifest["corpus_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
