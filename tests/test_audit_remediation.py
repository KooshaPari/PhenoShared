"""Tests for audit remediation fixes (P3 findings from audit run v37)."""
from __future__ import annotations

from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent.parent
WORKFLOWS_DIR = TESTS_DIR / ".github" / "workflows"
DOCS_SECURITY_DIR = TESTS_DIR / "docs" / "security"


# ── Fix 1: CI Runner Version Pinning ───────────────────────────────────


class TestCIRunnerPinning:
    """Verify all CI workflows use pinned runner versions (L10 audit finding)."""

    WORKFLOW_FILES = [
        "audit.yml",
        "scorecard.yml",
        "dependency-scan.yml",
    ]

    @pytest.mark.parametrize("wf_name", WORKFLOW_FILES)
    def test_workflow_exists(self, wf_name: str) -> None:
        """Verify workflow file exists."""
        wf_path = WORKFLOWS_DIR / wf_name
        assert wf_path.exists(), f"Workflow not found: {wf_path}"

    @pytest.mark.parametrize("wf_name", WORKFLOW_FILES)
    def test_runner_pinned_to_ubuntu_24_04(self, wf_name: str) -> None:
        """Verify runner is pinned to ubuntu-24.04, not ubuntu-latest."""
        wf_path = WORKFLOWS_DIR / wf_name
        content = wf_path.read_text()

        # Must use pinned runner version
        assert "runs-on: ubuntu-24.04" in content, (
            f"{wf_name} does not use ubuntu-24.04"
        )

        # Must NOT use ubuntu-latest
        assert "ubuntu-latest" not in content, (
            f"{wf_name} still uses ubuntu-latest"
        )

    @pytest.mark.parametrize("wf_name", WORKFLOW_FILES)
    def test_actions_pinned_by_sha(self, wf_name: str) -> None:
        """Verify third-party actions are pinned by SHA with comment."""
        wf_path = WORKFLOWS_DIR / wf_name
        content = wf_path.read_text()

        lines = content.splitlines()
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            # Check uses lines for third-party actions (not in-repo ones)
            if line_stripped.startswith("uses:"):
                action_ref = line_stripped.split("uses:")[1].strip()
                # Skip self-hosted or local actions
                if action_ref.startswith("./"):
                    continue
                # Check for SHA pinning pattern: org/repo@SHA # comment
                has_sha_pin = False
                has_version_comment = False
                if "@" in action_ref:
                    after_at = action_ref.split("@")[1]
                    # SHA is 40-64 hex chars with optional # comment
                    sha_part = after_at.split()[0] if after_at.split() else after_at
                    # Check if next line has a # version comment OR same line
                    if len(sha_part) >= 40 and all(c in "0123456789abcdef" for c in sha_part[:40]):
                        has_sha_pin = True
                    # Check for inline version comment
                    if " # " in action_ref or " #" in action_ref:
                        has_version_comment = True
                    # Check next line for comment
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line.startswith("#") or next_line.startswith("#"):
                            has_version_comment = True

                assert has_sha_pin, (
                    f"Action {action_ref} in {wf_name} is not pinned by SHA"
                )


# ── Fix 2: Dependency Scanning ─────────────────────────────────────────


class TestDependencyScanning:
    """Verify dependency scanning workflow is configured (L28 audit finding)."""

    def test_dependency_scan_workflow_exists(self) -> None:
        """Verify dependency-scan.yml was created."""
        wf_path = WORKFLOWS_DIR / "dependency-scan.yml"
        assert wf_path.exists(), "dependency-scan.yml workflow not found"

    def test_dependency_scan_has_osv_scanner(self) -> None:
        """Verify dependency scan uses osv-scanner."""
        wf_path = WORKFLOWS_DIR / "dependency-scan.yml"
        content = wf_path.read_text()
        assert "osv-scanner" in content.lower(), (
            "OSV scanner not found in dependency-scan workflow"
        )

    def test_dependency_scan_runs_on_schedule(self) -> None:
        """Verify dependency scan has a schedule trigger."""
        wf_path = WORKFLOWS_DIR / "dependency-scan.yml"
        content = wf_path.read_text()
        assert "cron:" in content, (
            "dependency-scan workflow missing schedule/cron trigger"
        )

    def test_dependency_scan_sarif_upload(self) -> None:
        """Verify dependency scan uploads SARIF results."""
        wf_path = WORKFLOWS_DIR / "dependency-scan.yml"
        content = wf_path.read_text()
        assert "upload-sarif" in content or "sarif_file" in content, (
            "dependency-scan workflow missing SARIF upload step"
        )


# ── Fix 3: Security Documentation ──────────────────────────────────────


class TestSecurityDocs:
    """Verify security documentation stubs have been replaced (L20/L22 audit finding)."""

    def test_security_requirements_exists(self) -> None:
        """Verify security requirements document exists."""
        req_path = DOCS_SECURITY_DIR / "requirements.md"
        assert req_path.exists(), "docs/security/requirements.md not found"

    def test_security_requirements_not_todo(self) -> None:
        """Verify security requirements doc replaces the TODO stub."""
        req_path = DOCS_SECURITY_DIR / "requirements.md"
        content = req_path.read_text()

        # Should not contain the TODO placeholder
        assert "TODO" not in content, (
            "docs/security/requirements.md still contains TODO"
        )

        # Should have actual content (substantive sections)
        sections = [
            "Assets",
            "Threat Model Boundary",
            "CI/CD Pipeline Security",
            "Content Security",
            "Repository Security",
            "Non-Goals",
        ]
        for section in sections:
            assert section in content, (
                f"Missing section '{section}' in security requirements"
            )

    def test_threat_model_exists(self) -> None:
        """Verify threat model document exists."""
        tm_path = DOCS_SECURITY_DIR / "threat-model.md"
        assert tm_path.exists(), "docs/security/threat-model.md not found"

    def test_threat_model_has_stride_analysis(self) -> None:
        """Verify threat model contains STRIDE analysis."""
        tm_path = DOCS_SECURITY_DIR / "threat-model.md"
        content = tm_path.read_text()

        # Must cover all STRIDE categories
        for letter in ["S", "T", "R", "I", "D", "E"]:
            assert f"**{letter} " in content or f"**{letter}**" in content, (
                f"Threat model missing {letter} in STRIDE"
            )

    def test_threat_model_has_components(self) -> None:
        """Verify threat model has at least one component analyzed."""
        tm_path = DOCS_SECURITY_DIR / "threat-model.md"
        content = tm_path.read_text()
        assert "Component:" in content, (
            "Threat model missing component analysis"
        )

    def test_threat_model_has_mitigations(self) -> None:
        """Verify threat model includes mitigations."""
        tm_path = DOCS_SECURITY_DIR / "threat-model.md"
        content = tm_path.read_text()
        assert "Mitigation" in content, (
            "Threat model missing mitigations"
        )


class TestWorkflowIntegrity:
    """Verify workflow files have no structural issues."""

    ALL_WORKFLOWS = [
        "audit.yml",
        "scorecard.yml",
        "dependency-scan.yml",
    ]

    @pytest.mark.parametrize("wf_name", ALL_WORKFLOWS)
    def test_no_duplicate_top_level_keys(self, wf_name: str) -> None:
        """Verify no duplicate top-level YAML keys in workflows."""
        wf_path = WORKFLOWS_DIR / wf_name
        content = wf_path.read_text()

        # Check for duplicate top-level keys (simplified check)
        top_level_keys: list[str] = []
        for line in content.splitlines():
            if line and not line[0].isspace() and ":" in line:
                key = line.split(":")[0].strip()
                top_level_keys.append(key)

        # No key should appear more than once
        for key in set(top_level_keys):
            count = top_level_keys.count(key)
            assert count == 1, (
                f"Duplicate top-level key '{key}' in {wf_name} (appears {count} times)"
            )

    @pytest.mark.parametrize("wf_name", ALL_WORKFLOWS)
    def test_workflow_has_concurrency(self, wf_name: str) -> None:
        """Verify workflow has concurrency group to prevent duplicate runs."""
        wf_path = WORKFLOWS_DIR / wf_name
        content = wf_path.read_text()
        assert "concurrency:" in content, (
            f"{wf_name} missing concurrency group"
        )
