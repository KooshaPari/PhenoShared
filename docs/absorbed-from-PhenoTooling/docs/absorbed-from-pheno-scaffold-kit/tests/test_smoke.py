from __future__ import annotations

import json
import types

import pheno_scaffold_kit as kit


def test_sub_libraries_reexport_exists() -> None:
    for key in (
        "llms_txt",
        "prompt_test",
        "vibecoding_guard",
        "worklog_schema",
        "predict",
        "framework_lint",
        "drift_detector",
    ):
        assert key in kit.SUB_LIBRARIES


def test_no_agents_md_reexport() -> None:
    """V6 PR-1: pheno-agents-md is a Rust crate, not a pip dep."""
    assert "agents_md" not in kit.SUB_LIBRARIES


def test_init_scaffold_calls_all_sub_libs(monkeypatch, tmp_path) -> None:
    calls: list[str] = []

    def make_module(name: str, entrypoint: str) -> types.SimpleNamespace:
        def run(repo_dir, **kwargs):
            calls.append(name)
            assert repo_dir == tmp_path
            assert "repo_type" in kwargs
            return {"ok": True, "name": name}

        return types.SimpleNamespace(__name__=name, **{entrypoint: run})

    monkeypatch.setattr(kit, "llms_txt", make_module("llms", "init_llms"))
    monkeypatch.setattr(kit, "prompt_test", make_module("prompt_test", "init_prompt_test"))
    monkeypatch.setattr(kit, "vibecoding_guard", make_module("hooks", "install_hooks"))
    monkeypatch.setattr(kit, "worklog_schema", make_module("worklog", "init_worklog"))

    result = kit.init_scaffold(tmp_path)

    assert calls == ["llms", "prompt_test", "hooks", "worklog"]
    for key in ("llms", "prompt_test", "hooks", "worklog"):
        assert result[key]["ok"] is True


def test_init_scaffold_survives_failing_substep(monkeypatch, tmp_path) -> None:
    """V6 PR-2: a single sub-step failure must not abort the run."""

    def boom(repo_dir, **kwargs):  # noqa: ARG001
        raise RuntimeError("intentional boom")

    monkeypatch.setattr(kit, "llms_txt", types.SimpleNamespace(__name__="llms", init_llms=boom))
    monkeypatch.setattr(kit, "prompt_test", types.SimpleNamespace(__name__="pt", init_prompt_test=lambda d, **k: {"ok": True}))
    monkeypatch.setattr(kit, "vibecoding_guard", types.SimpleNamespace(__name__="vg", install_hooks=lambda d, **k: {"ok": True}))
    monkeypatch.setattr(kit, "worklog_schema", types.SimpleNamespace(__name__="ws", init_worklog=lambda d, **k: {"ok": True}))

    result = kit.init_scaffold(tmp_path)
    assert result["llms"]["ok"] is False
    assert "RuntimeError" in result["llms"]["error"]
    assert result["prompt_test"]["ok"] is True
    assert result["hooks"]["ok"] is True
    assert result["worklog"]["ok"] is True


def test_init_scaffold_handles_missing_sub_lib(tmp_path) -> None:
    """V6 PR-2: missing sub-lib returns a clean JSON error, not an exception."""
    result = kit.init_scaffold(tmp_path)
    for step in ("llms", "prompt_test", "hooks", "worklog"):
        assert step in result
        # Either "sub-library not installed" (sub-libs absent) or ok=True (sub-libs mocked).
        if "error" in result[step]:
            assert "not installed" in result[step]["error"] or "entrypoint" in result[step]["error"]


def test_cli_dry_run(tmp_path) -> None:
    """V6 PR-7: --dry-run prints the sub-step plan and exits 0."""
    # Use the `pheno-scaffold` console script installed by pip; fall back to
    # the in-process Click runner if the script isn't on PATH (editable install
    # with hatchling doesn't always wire the entry-point up).
    from click.testing import CliRunner

    from pheno_scaffold_kit.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path), "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["repo_dir"] == str(tmp_path)
    step_names = [s["name"] for s in payload["steps"]]
    assert step_names == ["llms", "prompt_test", "hooks", "worklog"]
