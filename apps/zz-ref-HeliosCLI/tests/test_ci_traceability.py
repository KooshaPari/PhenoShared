"""Executable traceability checks for AgilePlus feature 003 / WP02."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE = "agileplus/003-helios-portage-completion/spec.md (WP02)"
TRACED_WORKFLOWS = (
    "bazel.yml",
    "cargo-deny.yml",
    "ci.yml",
    "rust-ci.yml",
    "sdk.yml",
)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class CiTraceabilityTests(unittest.TestCase):
    def test_hcli_fr_003_001_ci_policy_has_feature_trace(self) -> None:
        for name in TRACED_WORKFLOWS:
            text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
            self.assertIn(FEATURE, text, name)

    def test_hcli_fr_003_002_external_actions_are_sha_pinned(self) -> None:
        failures: list[str] = []
        for name in TRACED_WORKFLOWS:
            path = ROOT / ".github" / "workflows" / name
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = re.search(r"\buses:\s*([^@\s]+)@([^\s#]+)", line)
                if not match or match.group(1).startswith("./"):
                    continue
                if not FULL_SHA.fullmatch(match.group(2)):
                    failures.append(f"{name}:{line_number}: {match.group(0)}")
        self.assertEqual([], failures)

    def test_hcli_fr_003_003_diagnostic_artifacts_are_absent(self) -> None:
        forbidden = (
            "_check_runs.json",
            "_codespell_fail.log",
            "_codespell_fail2.log",
            "_deny_fail.log",
            "_pr604_checks.txt",
            "_pr_body.md",
        )
        self.assertEqual([], [name for name in forbidden if (ROOT / name).exists()])

    def test_hcli_fr_003_004_required_gate_configuration_is_strict(self) -> None:
        rust_ci = (ROOT / ".github/workflows/rust-ci.yml").read_text(encoding="utf-8")
        codespell = (ROOT / ".github/workflows/codespell.yml").read_text(encoding="utf-8")
        self.assertIn("cargo test --workspace", rust_ci)
        self.assertIn("cargo clippy --all-targets -- -D warnings", rust_ci)
        self.assertIn("cargo fmt --check", rust_ci)
        self.assertIn("cargo-deny-action@", rust_ci)
        self.assertIn("config: .codespellrc", codespell)
        self.assertTrue((ROOT / "sonar-project.properties").is_file())
        self.assertFalse((ROOT / ".github/workflows/sonarcloud.yml").exists())

    def test_hcli_fr_003_005_user_specific_push_scripts_are_absent(self) -> None:
        forbidden = (
            "_do_commit_push.bat",
            "_do_commit_push_ci.bat",
            "_do_commit_push_codespell.bat",
            "_do_pr.bat",
            "scripts/push_ci_green_pr.bat",
        )
        self.assertEqual([], [name for name in forbidden if (ROOT / name).exists()])


if __name__ == "__main__":
    unittest.main()
