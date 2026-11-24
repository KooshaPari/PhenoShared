"""P0 verifier paths — no silent scaffold success (FR-VER-001)."""

from __future__ import annotations

import json
from pathlib import Path

from verifier.harness import VerifierHarness, _check_patch, _check_tests
from verifier.risky_action import check_proposal


def test_check_patch_fails_loud_without_repo_root():
    """FR-VER-001: missing repo_root must fail, not scaffold-pass."""
    ok, err = _check_patch("--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y\n", None)
    assert ok is False
    assert err and "repo_root" in err


def test_check_patch_fails_loud_without_git(tmp_path: Path):
    """FR-VER-001: non-git tree cannot dry-apply; must fail loud."""
    diff = "--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b\n"
    ok, err = _check_patch(diff, tmp_path)
    assert ok is False
    assert err and "git" in err.lower()


def test_check_tests_fails_loud_when_cmd_missing():
    """FR-VER-001: enabled tests with no test_cmd must not silent-pass."""
    ok, err = _check_tests(None, None)
    assert ok is False
    assert err and "test_cmd" in err


def test_dry_run_when_available_fails_for_git_apply_without_repo():
    """FR-VER-001: medium-tier dry_run must not scaffold True."""
    text = "```bash\ngit apply /tmp/x.patch\n```"
    gate = check_proposal(text)
    assert gate.checks.get("dry_run_when_available") is False
    assert any("dry_run" in e for e in gate.errors)


def test_harness_verify_trace_json_and_tests(tmp_path: Path, monkeypatch):
    """FR-VER-001: verify_trace runs real JSON check; missing tests fail."""
    cfg = tmp_path / "rlvr.yaml"
    cfg.write_text(
        "pass_threshold: 0.5\n"
        "verifiers:\n"
        "  json: {enabled: true}\n"
        "  tool: {enabled: false}\n"
        "  patch: {enabled: false}\n"
        "  tests: {enabled: true}\n"
        "  risky_action: {enabled: false}\n"
        "  required_checks: [json_valid, tests_pass]\n",
        encoding="utf-8",
    )
    h = VerifierHarness(config_path=cfg)
    result = h.verify_trace(
        {
            "id": "t1",
            "role": "retrieve",
            "response": json.dumps({"ok": True}),
            # no test_cmd
        }
    )
    assert result.checks.get("json_valid") is True
    assert result.checks.get("tests_pass") is False
    assert result.ok is False
