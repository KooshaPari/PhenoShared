"""Tests for verifier.harness module — coverage sprint v0.35."""
from __future__ import annotations

from pathlib import Path

import pytest

from verifier.harness import (
    Verdict,
    VerifierHarness,
    VerifierResult,
    _check_json,
    _check_patch,
    _check_tests,
    _check_tool_call,
    _load_caps,
)


class TestVerifierResult:
    """VerifierResult dataclass tests."""

    def test_construction_minimum(self) -> None:
        r = VerifierResult(trace_id="t1", role="patch", ok=True)
        assert r.trace_id == "t1"
        assert r.role == "patch"
        assert r.ok is True
        assert r.checks == {}
        assert r.errors == []
        assert r.meta == {}

    def test_construction_full(self) -> None:
        r = VerifierResult(
            trace_id="t2",
            role="debug",
            ok=False,
            checks={"json_valid": True},
            errors=["err1"],
            meta={"key": "val"},
        )
        assert r.checks == {"json_valid": True}
        assert r.errors == ["err1"]
        assert r.meta == {"key": "val"}

    def test_to_dict(self) -> None:
        r = VerifierResult(
            trace_id="t3",
            role="retrieve",
            ok=True,
            checks={"a": True, "b": False},
            errors=[],
            meta={"k": 1},
        )
        d = r.to_dict()
        assert d["trace_id"] == "t3"
        assert d["role"] == "retrieve"
        assert d["ok"] is True
        assert d["checks"] == {"a": True, "b": False}
        assert d["errors"] == []
        assert d["meta"] == {"k": 1}

    def test_verdict_alias_is_same_class(self) -> None:
        """Verdict must be the canonical alias for VerifierResult."""
        assert Verdict is VerifierResult


class TestCheckJson:
    """Tests for _check_json helper."""

    def test_empty_response_fails(self) -> None:
        ok, err = _check_json("")
        assert ok is False
        assert err == "empty response"

    def test_whitespace_only_fails(self) -> None:
        ok, err = _check_json("   \n  ")
        assert ok is False
        assert err == "empty response"

    def test_valid_raw_json(self) -> None:
        ok, err = _check_json('{"a": 1, "b": [2, 3]}')
        assert ok is True
        assert err is None

    def test_valid_fenced_json(self) -> None:
        ok, err = _check_json('```json\n{"x": true}\n```')
        assert ok is True
        assert err is None

    def test_valid_fenced_json_no_lang(self) -> None:
        ok, err = _check_json('```\n[1, 2, 3]\n```')
        assert ok is True
        assert err is None

    def test_invalid_json_error_message(self) -> None:
        ok, err = _check_json("not json at all")
        assert ok is False
        assert err is not None
        assert "Expecting" in err or "JSON" in err

    def test_invalid_json_in_fence(self) -> None:
        ok, err = _check_json('```json\n{not valid}\n```')
        assert ok is False
        assert err is not None


class TestCheckToolCall:
    """Tests for _check_tool_call helper."""

    def test_tool_keyword_detected(self) -> None:
        ok, err = _check_tool_call('{"tool": "search", "args": {}}')
        assert ok is True
        assert err is None

    def test_name_arguments_detected(self) -> None:
        ok, err = _check_tool_call('{"name": "foo", "arguments": {"x": 1}}')
        assert ok is True
        assert err is None

    def test_xml_tool_call_detected(self) -> None:
        ok, err = _check_tool_call("I will call <tool_call>search</tool_call>")
        assert ok is True
        assert err is None

    def test_no_tool_call_detected(self) -> None:
        ok, err = _check_tool_call("Just a plain response with no tool.")
        assert ok is False
        assert "no tool call" in err

    def test_empty_response(self) -> None:
        ok, err = _check_tool_call("")
        assert ok is False
        assert err is not None


class TestCheckPatch:
    """Tests for _check_patch helper."""

    def test_no_repo_root(self) -> None:
        ok, err = _check_patch("--- a/file\n+++ b/file\n@@ -1 +1 @@\n-x\n+y\n", None)
        assert ok is False
        assert err == "repo_root missing for patch check"

    def test_repo_root_does_not_exist(self) -> None:
        # Path that doesn't exist at all
        ok, err = _check_patch("--- a\n+++ b\n@@\n", Path("/nonexistent/repo/that/does/not/exist"))
        assert ok is False
        assert err == "repo_root missing for patch check"

    def test_no_unified_diff(self, tmp_path: Path) -> None:
        ok, err = _check_patch("no diff here", tmp_path)
        assert ok is False
        assert err == "no unified diff found"

    def test_repo_not_git_checkout(self, tmp_path: Path) -> None:
        ok, err = _check_patch("--- a\n+++ b\n@@\n", tmp_path)
        assert ok is False
        assert err == "repo_root is not a git checkout; cannot dry-apply patch"

    def test_valid_diff_in_fence(self, tmp_path: Path) -> None:
        # Init a git repo with a tracked file so patch check works
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, capture_output=True)
        # Create + commit the file the patch will modify
        target = tmp_path / "x.txt"
        target.write_text("old\n", encoding="utf-8")
        subprocess.run(["git", "add", "x.txt"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True)

        diff = """```diff
--- a/x.txt
+++ b/x.txt
@@ -1 +1 @@
-old
+new
"""
        ok, err = _check_patch(diff, tmp_path)
        assert ok is True, f"patch failed: {err}"
    def test_invalid_diff_returns_git_error(self, tmp_path: Path) -> None:
        # Init git so we hit git apply
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, capture_output=True)

        # Malformed diff
        diff = "--- a\n+++ b\n@@ this is not a valid hunk header\n"
        ok, err = _check_patch(diff, tmp_path)
        assert ok is False
        assert err is not None


class TestCheckTests:
    """Tests for _check_tests helper."""

    def test_no_cmd_fails_loud(self) -> None:
        ok, err = _check_tests(None, None)
        assert ok is False
        assert err == "test_cmd required but missing"

    def test_empty_list_fails(self) -> None:
        ok, err = _check_tests([], None)
        assert ok is False
        assert err == "test_cmd required but missing"

    def test_successful_command(self, tmp_path: Path) -> None:
        ok, err = _check_tests(["python", "-c", "print('ok')"], tmp_path)
        assert ok is True
        assert err is None

    def test_failing_command(self, tmp_path: Path) -> None:
        ok, err = _check_tests(["python", "-c", "import sys; sys.exit(1)"], tmp_path)
        assert ok is False
        assert err is not None

    def test_command_tail_truncation(self, tmp_path: Path) -> None:
        # Generate >500 chars of output
        ok, err = _check_tests(["python", "-c", "print('x' * 1000)"], tmp_path)
        assert ok is True  # print is exit 0
        assert err is None


class TestLoadCaps:
    """Tests for _load_caps helper."""

    def test_no_config_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Patch CONFIG_DIR in verifier.harness module (imported at module load)
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        result = _load_caps()
        assert result == {}

    def test_loads_role_caps(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        caps_file = tmp_path / "context_caps.yaml"
        caps_file.write_text(
            "roles:\n  patch:\n    max_output: 1200\n    max_context: 32768\n  debug:\n    max_output: 500\n",
            encoding="utf-8",
        )
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        result = _load_caps()
        assert "patch" in result
        assert result["patch"]["max_output"] == 1200
        assert result["debug"]["max_output"] == 500

    def test_non_dict_roles_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        caps_file = tmp_path / "context_caps.yaml"
        caps_file.write_text("roles: notadict\n", encoding="utf-8")
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        result = _load_caps()
        assert result == {}

    def test_missing_roles_key_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        caps_file = tmp_path / "context_caps.yaml"
        caps_file.write_text("other_key: 1\n", encoding="utf-8")
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        result = _load_caps()
        assert result == {}


class TestVerifierHarness:
    """Tests for VerifierHarness class."""

    def test_init_no_config(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr_config.yaml"))
        assert h.config == {"verifiers": {}, "pass_threshold": 0.75}

    def test_init_with_config(self, tmp_path: Path) -> None:
        cfg = tmp_path / "rlvr.yaml"
        cfg.write_text("verifiers:\n  json:\n    enabled: false\n  tests:\n    enabled: true\n", encoding="utf-8")
        h = VerifierHarness(config_path=cfg)
        assert h.config.get("verifiers", {}).get("json", {}).get("enabled") is False

    def test_verify_trace_minimal(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "response": ""})
        assert result.trace_id == "t1"
        assert result.role == "patch"
        assert "json_valid" in result.checks

    def test_verify_trace_uses_trace_id_key(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"trace_id": "t2", "role": "patch", "response": ""})
        assert result.trace_id == "t2"

    def test_verify_trace_defaults_trace_id_to_unknown(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"role": "patch", "response": ""})
        assert result.trace_id == "unknown"

    def test_verify_trace_role_normalised_lowercase(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "PATCH", "response": ""})
        assert result.role == "patch"

    def test_verify_trace_header_role_fallback(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "header_role": "debug", "response": ""})
        assert result.role == "debug"

    def test_verify_trace_response_from_completion_key(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "completion": '{"a": 1}'})
        assert result.checks.get("json_valid") is True

    def test_verify_trace_response_from_output_key(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "output": '{"x": 2}'})
        assert result.checks.get("json_valid") is True

    def test_verify_trace_meta_includes_tokens(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "response": "x" * 100, "tokens_in": 50})
        assert result.meta.get("output_tokens") is not None
        assert result.meta.get("context_tokens") == 50
        assert result.meta.get("baseline_context_tokens") == 50

    def test_verify_trace_meta_uses_response_length(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        # No tokens_in given, fallback to len(response)//4
        result = h.verify_trace({"id": "t1", "role": "patch", "response": "x" * 400})
        assert result.meta.get("context_tokens") == 0  # No fallback for context_tokens
        assert result.meta.get("output_tokens") == 100  # 400 // 4

    def test_verify_trace_caps_from_meta(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Empty caps to isolate meta-derived caps
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({
            "id": "t1",
            "role": "patch",
            "response": "{}",
            "output_cap": 999,
            "context_budget": 888,
        })
        assert result.meta["output_cap"] == 999
        assert result.meta["context_budget"] == 888

    def test_verify_trace_test_cmd_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Empty caps to avoid risky_action errors polluting result
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        # test_cmd as list - should not crash
        result = h.verify_trace({
            "id": "t1",
            "role": "patch",
            "response": '{"a":1}',
            "test_cmd": ["python", "-c", "print(1)"],
        "verifiers": {"risky_action": {"enabled": False}}}
        )
        assert "tests_pass" in result.checks

    def test_verify_trace_test_cmd_string(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        result = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml")).verify_trace({
            "id": "t1",
            "role": "patch",
            "response": '{"a":1}',
            "test_cmd": "python -c print(1)",
        })
        assert "tests_pass" in result.checks

    def test_verify_trace_test_cmd_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "response": '{"a":1}'})
        assert result.checks.get("tests_pass") is False

    def test_verify_trace_test_cmd_other_type(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "response": '{"a":1}', "test_cmd": 12345})
        assert result.checks.get("tests_pass") is False

    def test_verify_trace_escalation_match(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({
            "id": "t1",
            "role": "patch",
            "response": '{"a":1}',
            "expected_escalation": "gpt4",
            "actual_escalation": "gpt4-turbo",
        })
        assert result.checks.get("correct_escalation") is True

    def test_verify_trace_escalation_mismatch(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({
            "id": "t1",
            "role": "patch",
            "response": '{"a":1}',
            "expected_escalation": "gpt4",
            "actual_escalation": "llama",
        })
        assert result.checks.get("correct_escalation") is False

    def test_verify_trace_escalation_none_default(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "response": '{"a":1}'})
        assert result.checks.get("correct_escalation") is False

    def test_verify_trace_actual_escalation_falls_back_to_model(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({
            "id": "t1",
            "role": "patch",
            "response": '{"a":1}',
            "expected_escalation": "model-x",
            "model": "model-x-v2",
        })
        assert result.checks.get("correct_escalation") is True

    def test_verify_trace_ok_when_required_pass(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "response": '{"a":1}'})
        # Default required: json_valid + tests_pass
        # json_valid passes, tests_pass fails because no test_cmd
        # So ok should be False overall
        assert result.ok is False

    def test_verify_trace_ok_when_all_required_pass(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        # Use "summarize" role (not "patch"/"plan"/"retrieve") so missing tool call doesn't error
        result = h.verify_trace({
            "id": "t1",
            "role": "summarize",
            "response": '{"a":1}',
            "test_cmd": ["python", "-c", "print(1)"],
        })
        # required: json_valid + tests_pass, both pass; risky_action_gate also passes
        assert result.ok is True

    def test_verify_trace_custom_required_checks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import verifier.harness as vh
        monkeypatch.setattr(vh, "CONFIG_DIR", tmp_path)
        cfg = tmp_path / "rlvr.yaml"
        # Explicit disable tests + risky_action to keep error list empty
        cfg.write_text(
            "verifiers: {risky_action: {enabled: false}, tests: {enabled: false}}\nrequired_checks: [json_valid]\npass_threshold: 0.5\n",
            encoding="utf-8",
        )
        h = VerifierHarness(config_path=cfg)
        # Use "summarize" role so tool errors don't apply
        result = h.verify_trace({"id": "t1", "role": "summarize", "response": '{"a":1}'})
        # json_valid passes; required is only json_valid
        assert result.ok is True

    def test_verify_jsonl_basic(self, tmp_path: Path) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        jsonl = tmp_path / "traces.jsonl"
        jsonl.write_text(
            '{"id":"t1","role":"patch","response":"{}"}\n'
            '{"id":"t2","role":"patch","response":"notjson"}\n',
            encoding="utf-8",
        )
        results = h.verify_jsonl(jsonl)
        assert len(results) == 2
        assert results[0].trace_id == "t1"
        assert results[1].trace_id == "t2"

    def test_verify_jsonl_skips_blank_lines(self, tmp_path: Path) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        jsonl = tmp_path / "traces.jsonl"
        jsonl.write_text(
            '{"id":"t1","role":"patch","response":"{}"}\n'
            '\n'
            '{"id":"t2","role":"patch","response":"{}"}\n',
            encoding="utf-8",
        )
        results = h.verify_jsonl(jsonl)
        assert len(results) == 2

    def test_find_traces_returns_sorted_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import verifier.harness as vh
        monkeypatch.setattr(vh, "TRAINING_DIR", tmp_path)
        (tmp_path / "traces_a.jsonl").write_text("", encoding="utf-8")
        (tmp_path / "traces_b.jsonl").write_text("", encoding="utf-8")
        (tmp_path / "other.txt").write_text("", encoding="utf-8")
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        paths = h.find_traces()
        assert len(paths) == 2
        assert paths[0].name == "traces_a.jsonl"
        assert paths[1].name == "traces_b.jsonl"

    def test_find_traces_custom_glob(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import verifier.harness as vh
        monkeypatch.setattr(vh, "TRAINING_DIR", tmp_path)
        (tmp_path / "eval_run_1.jsonl").write_text("", encoding="utf-8")
        (tmp_path / "eval_run_2.jsonl").write_text("", encoding="utf-8")
        (tmp_path / "traces_a.jsonl").write_text("", encoding="utf-8")
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        paths = h.find_traces("eval_run_*.jsonl")
        assert len(paths) == 2
        assert all("eval_run" in p.name for p in paths)

    def test_verify_trace_risky_action_gate_added(self) -> None:
        h = VerifierHarness(config_path=Path("/nonexistent/rlvr.yaml"))
        result = h.verify_trace({"id": "t1", "role": "patch", "response": '{"a":1}'})
        assert "risky_action_gate" in result.checks
        assert "risky_action_tier" in result.meta
        assert "risky_action" in result.meta