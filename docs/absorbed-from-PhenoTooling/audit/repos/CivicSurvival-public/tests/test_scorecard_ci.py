import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCORECARD = REPO_ROOT / "scripts" / "scorecard_ci.py"


def make_minimal_repo(root: Path) -> None:
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "LICENSE").write_text("fixture\n", encoding="utf-8")
    (root / "CONTRIBUTING.md").write_text("fixture\n", encoding="utf-8")
    (root / ".editorconfig").write_text("root = true\n", encoding="utf-8")
    (root / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
    workflow = root / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "ci.yml").write_text("name: fixture\n", encoding="utf-8")


class ScorecardBaselineTests(unittest.TestCase):
    def run_scorecard(
        self,
        fixture: Path,
        baseline: Path,
        threshold: int = 85,
        *extra_args: str,
        output: str = "json",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCORECARD),
                str(fixture),
                "--output",
                output,
                "--threshold",
                str(threshold),
                "--baseline-file",
                str(baseline),
                "--fail-on-drop",
                *extra_args,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_fail_on_drop_requires_target_even_when_baseline_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            make_minimal_repo(fixture)
            baseline = fixture / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_revision": "fixture",
                        "score": 6,
                        "total": 88,
                        "passed_pillar_ids": [1, 2, 3, 8, 9, 19],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_scorecard(fixture, baseline)

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["baseline_score"], 6)
            self.assertEqual(report["score_delta"], 0)
            self.assertFalse(report["regression"])
            self.assertFalse(report["target_met"])

    def test_rejects_threshold_below_hard_minimum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            make_minimal_repo(fixture)
            baseline = fixture / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_revision": "fixture",
                        "score": 6,
                        "total": 88,
                        "passed_pillar_ids": [1, 2, 3, 8, 9, 19],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_scorecard(fixture, baseline, threshold=6)

            self.assertEqual(result.returncode, 2)
            self.assertIn("at least 85", result.stderr)

    def test_fail_on_drop_rejects_score_neutral_lost_baseline_pillar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            make_minimal_repo(fixture)
            (fixture / "README.md").unlink()
            (fixture / "docs").mkdir()
            baseline = fixture / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_revision": "fixture",
                        "score": 6,
                        "total": 88,
                        "passed_pillar_ids": [1, 2, 3, 8, 9, 19],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_scorecard(fixture, baseline)

            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["regression"])
            self.assertEqual(report["score_delta"], 0)
            self.assertEqual(report["missing_baseline_pillar_ids"], [1])

    def test_markdown_baseline_fields_match_json_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            make_minimal_repo(fixture)
            (fixture / "README.md").unlink()
            (fixture / "docs").mkdir()
            baseline = fixture / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_revision": "fixture",
                        "score": 6,
                        "total": 88,
                        "passed_pillar_ids": [1, 2, 3, 8, 9, 19],
                    }
                ),
                encoding="utf-8",
            )

            json_result = self.run_scorecard(fixture, baseline)
            markdown_result = self.run_scorecard(fixture, baseline, output="markdown")

            self.assertEqual(json_result.returncode, 1, json_result.stderr)
            self.assertEqual(markdown_result.returncode, 1, markdown_result.stderr)
            report = json.loads(json_result.stdout)
            expected_fields = {
                "Baseline score": report["baseline_score"],
                "Score delta": report["score_delta"],
                "Missing baseline pillars": report["missing_baseline_pillar_ids"],
                "Regression": report["regression"],
            }
            for label, value in expected_fields.items():
                self.assertIn(f"**{label}:** {json.dumps(value)}", markdown_result.stdout)

    def test_rejects_baseline_without_pillar_identity_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            make_minimal_repo(fixture)
            baseline = fixture / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_revision": "fixture",
                        "score": 6,
                        "total": 88,
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_scorecard(fixture, baseline)

            self.assertEqual(result.returncode, 2)
            self.assertIn("passed_pillar_ids", result.stderr)

    def test_rejects_baseline_with_unexpected_source_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            make_minimal_repo(fixture)
            baseline = fixture / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_revision": "fixture",
                        "score": 6,
                        "total": 88,
                        "passed_pillar_ids": [1, 2, 3, 8, 9, 19],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_scorecard(
                fixture, baseline, 85, "--expected-source-revision", "different-fixture"
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("does not match", result.stderr)


if __name__ == "__main__":
    unittest.main()
