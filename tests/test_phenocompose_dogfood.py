from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "phenocompose_dogfood_v0.yaml"
EXPECTED_DIGEST = "2de2ba70302a55f83920663e8cbec2293dd4ebf127ba44e224c50b3bfbfccfde"
PRIMARY_GPU_UUID = "GPU-8d337a84-43de-158d-7526-7175288a6064"
ACTION = "harbor-headless-terminal"
OUTPUT_ROOT = "jobs/harbor"
ALLOWED_OPERATIONS = frozenset(
    {"plan", "apply-dry-run", "run-action", "export-provenance", "down"}
)
BANNED_CONTROL_TOKENS = (
    "podman exec",
    "podman run",
    "docker exec",
    "docker run",
    "wsl.exe",
    "nvidia-smi",
    "CUDA_VISIBLE_DEVICES",
    "/opt/pheno/evaluate",
)
PORTAGE_ARGV = [
    "run",
    "-c",
    "config/harbor.yaml",
    "-a",
    "harness.harbor.terminus_safe:SafeTerminus2",
    "-m",
    "openai/local/qwen35-08b",
    "--env",
    "docker",
    "--n-concurrent",
    "1",
    "--agent-kwarg",
    "api_base=http://127.0.0.1:8080/v1",
    "--agent-kwarg",
    "max_turns=3",
    "--agent-kwarg",
    "max_thinking_tokens=1024",
    "--agent-kwarg",
    "reasoning_effort=none",
    "--agent-kwarg",
    "interleaved_thinking=false",
    "--agent-kwarg",
    "enable_summarize=false",
    "--agent-kwarg",
    "record_terminal_session=false",
    "--agent-kwarg",
    "max_output_retries=2",
    "--agent-kwarg",
    "terminal_command_timeout_sec=30",
    "--agent-kwarg",
    "model_info=base64json:eyJtYXhfaW5wdXRfdG9rZW5zIjozMjc2OCwibWF4X291dHB1dF90b2tlbnMiOjMwNzJ9",
    "--agent-kwarg",
    "llm_call_kwargs=base64json:eyJtYXhfdG9rZW5zIjozMDcyLCJ0ZW1wZXJhdHVyZSI6MH0=",
    "--agent-env",
    "OPENAI_API_KEY=local-dummy-key",
    "-y",
    "-p",
    r"D:\WSL\eval-cache\harbor-terminal-bench-2.0\terminal-bench",
    "--n-tasks",
    "1",
    "--include-task-name",
    "headless-terminal",
]


def _manifest() -> dict[str, Any]:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def _resolve_cli() -> Path | None:
    explicit = os.environ.get("PHENO_COMPOSE_BIN")
    if explicit:
        return Path(explicit).expanduser().resolve()
    source_dir = os.environ.get("PHENOCOMPOSE_SOURCE_DIR")
    if source_dir:
        suffix = ".exe" if os.name == "nt" else ""
        return (
            Path(source_dir).expanduser()
            / "crates"
            / "phenocompose-cli"
            / "target"
            / "release"
            / f"pheno-compose{suffix}"
        ).resolve()
    discovered = shutil.which("pheno-compose")
    return Path(discovered).resolve() if discovered else None


@pytest.fixture(scope="module")
def pheno_compose_cli() -> Path:
    binary = _resolve_cli()
    if binary is None or not binary.is_file():
        pytest.skip(
            "set PHENO_COMPOSE_BIN or PHENOCOMPOSE_SOURCE_DIR, or put "
            "pheno-compose on PATH"
        )
    return binary


def _operation_args(
    operation: str,
    *,
    manifest: Path = MANIFEST,
    run_id: str = "",
    job_id: str = "",
    output: Path | None = None,
) -> list[str]:
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError(f"unsupported dogfood operation: {operation}")
    if operation == "plan":
        return ["plan", str(manifest)]
    if operation == "apply-dry-run":
        return ["apply", str(manifest), "--dry-run"]
    if operation == "run-action":
        return ["run-action", run_id, ACTION, "--job-id", job_id]
    if operation == "export-provenance":
        args = ["export-provenance", run_id]
        return [*args, "--output", str(output)] if output else args
    return ["down", run_id]


def _invoke(
    binary: Path,
    state_dir: Path,
    operation: str,
    *,
    check: bool = True,
    environment: dict[str, str] | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    command = [
        str(binary),
        "--state-dir",
        str(state_dir),
        *_operation_args(operation, **kwargs),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=330,
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"pheno-compose {operation} failed ({completed.returncode}): "
            f"{completed.stderr}"
        )
    return completed


def _write_run_fixture(
    state_dir: Path, dry_run: dict[str, Any], normalized: dict[str, Any]
) -> str:
    run_id = dry_run["run_id"]
    state_dir.mkdir(parents=True)
    state = {
        "state_version": "phenocompose.run/v0",
        "run_id": run_id,
        "manifest_sha256": dry_run["manifest_sha256"],
        "provider": "podman",
        "created_unix_seconds": 1,
        "lifecycle": "running",
        "containers": {},
        "manifest": normalized,
    }
    (state_dir / f"{run_id}.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )
    return run_id


def _write_fake_nvms(directory: Path) -> Path:
    script = directory / "fake_nvms.py"
    script.write_text(
        """\
import hashlib
import json
import os
from pathlib import Path
import sys

if sys.argv[1:] != ["action", "--request", "-"]:
    raise SystemExit(2)
request = json.load(sys.stdin)
Path(os.environ["FAKE_NVMS_CAPTURE"]).write_text(
    json.dumps(request, indent=2), encoding="utf-8"
)
failed = os.environ.get("FAKE_NVMS_RESULT") == "failure"
stdout = "bounded fake stdout"
stderr = "injected action failure" if failed else ""
result = {
    "version": "nanovms.io/evaluation-action/v1",
    "success": not failed,
    "error_code": "action_failed" if failed else "",
    "error_message": stderr,
    "lifecycle": {
        "exit_code": 7 if failed else 0,
        "duration_ms": 17,
        "timed_out": False,
        "truncated": False,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
    },
    "provenance": {
        "manifest_sha256": request["manifest_sha256"],
        "effective_engine": "podman",
        "resolved_provider": "podman",
        "execution_plane": "nanovms",
        "podman_pipe": request["podman_pipe"],
        "gpu_uuids": [binding["uuid"] for binding in request["gpu_bindings"]],
        "job_directory": str(Path(request["output_root"]) / "fake-job"),
    },
    "released": True,
}
print(json.dumps(result))
raise SystemExit(4 if failed else 0)
""",
        encoding="utf-8",
    )
    if os.name == "nt":
        launcher = directory / "fake_nvms.cmd"
        launcher.write_text(
            f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n',
            encoding="utf-8",
        )
        return launcher
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    script.write_text(
        f"#!{sys.executable}\n" + script.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return script


def _assert_job_evidence(job: dict[str, Any], *, success: bool) -> None:
    assert job["manifest_sha256"] == EXPECTED_DIGEST
    assert job["effective_engine"] == "podman"
    assert job["resolved_provider"] == "podman"
    assert job["execution_plane"] == "nanovms"
    assert job["gpu_bindings"] == [
        {
            "uuid": PRIMARY_GPU_UUID,
            "cuda_toolkit": "13.0",
            "cdi_device": f"nvidia.com/gpu={PRIMARY_GPU_UUID}",
        }
    ]
    lifecycle = job["lifecycle"]
    assert 0 <= lifecycle["duration_ms"] <= job["timeout_millis"]
    assert len(lifecycle["stdout"]) <= job["max_output_bytes"]
    assert len(lifecycle["stderr"]) <= job["max_output_bytes"]
    assert (
        lifecycle["stdout_sha256"]
        == hashlib.sha256(lifecycle["stdout"].encode("utf-8")).hexdigest()
    )
    assert (
        lifecycle["stderr_sha256"]
        == hashlib.sha256(lifecycle["stderr"].encode("utf-8")).hexdigest()
    )
    assert job["success"] is success
    assert bool(job.get("error_code")) is (not success)


def test_manifest_declares_available_delegated_host_action() -> None:
    manifest = _manifest()
    assert manifest["providers"] == {
        "evaluation": {
            "capability": "evaluation.nanovms.host_action",
            "status": "available",
            "implementation": "NanoVMS/Podman",
        }
    }
    assert manifest["metadata"]["labels"]["action_execution"] == "host_via_nanovms"
    assert manifest["metadata"]["labels"]["action_output_root"] == OUTPUT_ROOT
    assert manifest["actions"][ACTION]["output_root"] == OUTPUT_ROOT
    assert "wsl_distribution" not in manifest["runtime"]
    assert manifest.get("artifacts") in (None, [])
    assert all(
        "health_check" not in service for service in manifest["services"].values()
    )


def test_manifest_pins_exact_gpu_and_toolkit_binding() -> None:
    manifest = _manifest()
    assert manifest["environment"]["toolkit"] == {"name": "cuda", "version": "13.0"}
    gpu = manifest["services"]["sglang-primary"]["resources"]["gpu"]
    assert gpu == {"vendor": "nvidia", "uuids": [PRIMARY_GPU_UUID]}
    assert manifest["actions"][ACTION]["service"] == "sglang-primary"


def test_portage_argv_matches_successful_headless_terminal_lock() -> None:
    command = _manifest()["actions"][ACTION]["command"]
    assert command == ["portage", *PORTAGE_ARGV]
    assert command.count("headless-terminal") == 1
    assert command[command.index("--n-tasks") + 1] == "1"
    assert all('"' not in value and "'" not in value for value in command)
    assert command[command.index("--env") + 1] == "docker"
    assert not Path(command[0]).is_absolute()


def test_control_path_literals_are_absent_except_portage_schema_token() -> None:
    serialized = json.dumps(_manifest(), sort_keys=True)
    for token in BANNED_CONTROL_TOKENS:
        assert token not in serialized
    command = _manifest()["actions"][ACTION]["command"]
    assert [index for index, value in enumerate(command) if value == "docker"] == [
        command.index("--env") + 1
    ]
    assert _manifest()["runtime"]["portage_compatibility"] == {
        "external_engine_token": "docker",
        "effective_engine": "podman",
    }


def test_helper_enforces_operation_allow_list() -> None:
    assert set(ALLOWED_OPERATIONS) == {
        "plan",
        "apply-dry-run",
        "run-action",
        "export-provenance",
        "down",
    }
    with pytest.raises(ValueError, match="unsupported dogfood operation"):
        _operation_args("raw-runtime")


def test_plan_digest_is_deterministic_and_apply_is_non_mutating(
    pheno_compose_cli: Path, tmp_path: Path
) -> None:
    state_dir = tmp_path / "state"
    first = json.loads(_invoke(pheno_compose_cli, state_dir, "plan").stdout)
    second = json.loads(_invoke(pheno_compose_cli, state_dir, "plan").stdout)
    dry_run = json.loads(_invoke(pheno_compose_cli, state_dir, "apply-dry-run").stdout)
    assert first == second
    assert first["manifest_sha256"] == EXPECTED_DIGEST
    assert dry_run["manifest_sha256"] == EXPECTED_DIGEST
    assert dry_run["dry_run"] is True
    assert dry_run["mutation"] is False
    assert dry_run["provider"] == "podman"
    assert dry_run["containers"] == {}
    assert not state_dir.exists()


@pytest.mark.parametrize(
    ("output_root", "error_code"),
    [("jobs/../escape", "action_output_root_traversal")],
)
def test_invalid_output_root_fails_before_fake_nvms_invocation(
    pheno_compose_cli: Path,
    tmp_path: Path,
    output_root: str,
    error_code: str,
) -> None:
    manifest = _manifest()
    manifest["actions"][ACTION]["output_root"] = output_root
    invalid_manifest = tmp_path / "invalid-output-root.yaml"
    invalid_manifest.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    state_dir = tmp_path / "state"
    plan = json.loads(
        _invoke(pheno_compose_cli, state_dir, "plan", manifest=invalid_manifest).stdout
    )
    dry_run = json.loads(
        _invoke(
            pheno_compose_cli,
            state_dir,
            "apply-dry-run",
            manifest=invalid_manifest,
        ).stdout
    )
    run_id = _write_run_fixture(state_dir, dry_run, plan["normalized"])
    capture = tmp_path / "request.json"
    fake_nvms = _write_fake_nvms(tmp_path)

    completed = _invoke(
        pheno_compose_cli,
        state_dir,
        "run-action",
        run_id=run_id,
        job_id="invalid-output-root",
        environment={
            **os.environ,
            "NVMS_BIN": str(fake_nvms),
            "FAKE_NVMS_CAPTURE": str(capture),
        },
        check=False,
    )

    assert completed.returncode != 0
    assert not capture.exists()
    job = json.loads(
        (state_dir / f"{run_id}.jobs" / "invalid-output-root.json").read_text(
            encoding="utf-8"
        )
    )
    assert job["error_code"] == error_code


@pytest.mark.skipif(os.name != "nt", reason="Windows drive-relative path contract")
def test_ambiguous_windows_output_root_fails_before_fake_nvms_invocation(
    pheno_compose_cli: Path, tmp_path: Path
) -> None:
    manifest = _manifest()
    manifest["actions"][ACTION]["output_root"] = r"C:jobs\harbor"
    invalid_manifest = tmp_path / "ambiguous-output-root.yaml"
    invalid_manifest.write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    state_dir = tmp_path / "state"
    plan = json.loads(
        _invoke(pheno_compose_cli, state_dir, "plan", manifest=invalid_manifest).stdout
    )
    dry_run = json.loads(
        _invoke(
            pheno_compose_cli,
            state_dir,
            "apply-dry-run",
            manifest=invalid_manifest,
        ).stdout
    )
    run_id = _write_run_fixture(state_dir, dry_run, plan["normalized"])
    capture = tmp_path / "request.json"
    fake_nvms = _write_fake_nvms(tmp_path)

    completed = _invoke(
        pheno_compose_cli,
        state_dir,
        "run-action",
        run_id=run_id,
        job_id="ambiguous-output-root",
        environment={
            **os.environ,
            "NVMS_BIN": str(fake_nvms),
            "FAKE_NVMS_CAPTURE": str(capture),
        },
        check=False,
    )

    assert completed.returncode != 0
    assert not capture.exists()
    job = json.loads(
        (state_dir / f"{run_id}.jobs" / "ambiguous-output-root.json").read_text(
            encoding="utf-8"
        )
    )
    assert job["error_code"] == "action_output_root_ambiguous"


def test_fake_e2e_persists_success_failure_and_exports_provenance(
    pheno_compose_cli: Path, tmp_path: Path
) -> None:
    state_dir = tmp_path / "state"
    plan = json.loads(_invoke(pheno_compose_cli, state_dir, "plan").stdout)
    dry_run = json.loads(_invoke(pheno_compose_cli, state_dir, "apply-dry-run").stdout)
    run_id = _write_run_fixture(state_dir, dry_run, plan["normalized"])
    capture = tmp_path / "request.json"
    fake_nvms = _write_fake_nvms(tmp_path)
    environment = {
        **os.environ,
        "NVMS_BIN": str(fake_nvms),
        "FAKE_NVMS_CAPTURE": str(capture),
    }

    success = json.loads(
        _invoke(
            pheno_compose_cli,
            state_dir,
            "run-action",
            run_id=run_id,
            job_id="fake-success",
            environment=environment,
        ).stdout
    )
    _assert_job_evidence(success, success=True)
    success_job_path = state_dir / f"{run_id}.jobs" / "fake-success.json"
    assert success_job_path.is_file()
    request = json.loads(capture.read_text(encoding="utf-8"))
    assert request["version"] == "nanovms.io/evaluation-action/v1"
    assert request["backend"] == "podman"
    assert request.get("fallback_backends", []) == []
    assert request["manifest_sha256"] == EXPECTED_DIGEST
    assert request["executable"] == "portage"
    assert request["argv"] == PORTAGE_ARGV
    assert request["lock_invocation"] == ["portage", *PORTAGE_ARGV]
    assert request["external_engine_token"] == "docker"
    assert request.get("wsl_distribution", "") == ""
    assert request["gpu_bindings"] == success["gpu_bindings"]
    assert request["output_root"] == str((ROOT / OUTPUT_ROOT).resolve())
    assert Path(request["output_root"]).is_absolute()
    assert Path(request["output_root"]) != state_dir
    assert success_job_path.is_relative_to(state_dir)

    failed = _invoke(
        pheno_compose_cli,
        state_dir,
        "run-action",
        run_id=run_id,
        job_id="fake-failure",
        environment={**environment, "FAKE_NVMS_RESULT": "failure"},
        check=False,
    )
    assert failed.returncode != 0
    failure_job = json.loads(
        (state_dir / f"{run_id}.jobs" / "fake-failure.json").read_text(encoding="utf-8")
    )
    _assert_job_evidence(failure_job, success=False)
    assert (state_dir / f"{run_id}.jobs" / "fake-failure.json").is_relative_to(
        state_dir
    )

    exported = json.loads(
        _invoke(
            pheno_compose_cli,
            state_dir,
            "export-provenance",
            run_id=run_id,
        ).stdout
    )
    assert set(exported["jobs"]) == {"fake-failure", "fake-success"}
    _assert_job_evidence(exported["jobs"]["fake-success"], success=True)
    _assert_job_evidence(exported["jobs"]["fake-failure"], success=False)

    down = json.loads(
        _invoke(pheno_compose_cli, state_dir, "down", run_id=run_id).stdout
    )
    assert down == {"run_id": run_id, "lifecycle": "down", "services": {}}


@pytest.mark.skipif(
    os.environ.get("PHENO_DOGFOOD_LIVE") != "1",
    reason="set PHENO_DOGFOOD_LIVE=1 for the explicit live boundary test",
)
def test_live_delegated_action_fails_closed_without_complete_evidence(
    tmp_path: Path,
) -> None:  # pragma: no cover - exercised only by explicit live hardware runs
    compose_value = os.environ.get("PHENOCOMPOSE_BIN")
    nvms_value = os.environ.get("NVMS_BIN")
    assert compose_value, "PHENOCOMPOSE_BIN is required in live mode"
    assert nvms_value, "NVMS_BIN is required in live mode"
    compose = Path(compose_value).expanduser().resolve()
    nvms = Path(nvms_value).expanduser().resolve()
    assert compose.is_file(), "PHENOCOMPOSE_BIN must name a file"
    assert nvms.is_file(), "NVMS_BIN must name a file"

    state_dir = tmp_path / "state"
    plan = json.loads(_invoke(compose, state_dir, "plan").stdout)
    dry_run = json.loads(_invoke(compose, state_dir, "apply-dry-run").stdout)
    run_id = _write_run_fixture(state_dir, dry_run, plan["normalized"])
    completed = _invoke(
        compose,
        state_dir,
        "run-action",
        run_id=run_id,
        job_id="live-boundary",
        environment={**os.environ, "NVMS_BIN": str(nvms)},
        check=False,
    )
    exported = json.loads(
        _invoke(compose, state_dir, "export-provenance", run_id=run_id).stdout
    )
    job = exported["jobs"].get("live-boundary")
    assert job is not None, f"missing persisted live evidence: {completed.stderr}"
    _assert_job_evidence(job, success=True)
    assert completed.returncode == 0
    down = json.loads(_invoke(compose, state_dir, "down", run_id=run_id).stdout)
    assert down["lifecycle"] == "down"
