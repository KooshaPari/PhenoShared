import json
import tempfile
import unittest
from pathlib import Path

from eval.role_suite import build_manifest, build_spec


class RoleSuiteTests(unittest.TestCase):
    def _trace(self, path: Path) -> None:
        events = []
        for index in range(30):
            events.append(
                {
                    "source": "claude_code",
                    "event_type": "model_call",
                    "timestamp": str(index),
                    "content": "review this diff and run tests"
                    if index == 0
                    else "test passed",
                    "meta": {
                        "status": "completed"
                        if index == 29
                        else "retry"
                        if index == 10
                        else ""
                    },
                }
            )
        path.write_text(
            "\n".join(json.dumps(event) for event in events), encoding="utf-8"
        )

    def test_build_spec_is_review_only_and_replayable(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            self._trace(trace)
            events = [json.loads(line) for line in trace.read_text().splitlines()]
            spec, replay = build_spec(trace, events)
            self.assertEqual(spec["role_id"], "reviewer")
            self.assertFalse(spec["verification"]["scoreable"])
            self.assertEqual(len(replay), 30)

    def test_manifest_counts_only_review_specs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.spec.json").write_text(
                json.dumps(
                    {"role_id": "reviewer", "verification": {"scoreable": False}}
                )
            )
            report = build_manifest(root)
            self.assertEqual(report["role_counts"]["reviewer"], 1)
            self.assertFalse(report["scoreable"])


if __name__ == "__main__":
    unittest.main()
