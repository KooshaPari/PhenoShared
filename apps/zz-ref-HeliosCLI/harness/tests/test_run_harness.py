import json
import subprocess
import sys
from pathlib import Path

import pytest
from harness.scripts.run_harness import _legacy_module

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run-harness.py"
PHASE2_SCRIPT = Path(__file__).resolve().parents[2] / "commands" / "execute-phase-2-harness.sh"


def _run(cmd, cwd: Path) -> str:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _initialize_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "tests@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Harness tests"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "test fixture"], check=True)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only: run-harness.py:123 os.open(workspace, O_RDONLY|O_DIRECTORY|O_NOFOLLOW) "
    "opens a directory handle -> PermissionError [Errno 13] on Windows",
)
def test_validated_output_path_rejects_workspace_escape(tmp_path, monkeypatch):
    # Traces to: FR-HELIOS-IO-006 (bounded evidence output).
    monkeypatch.chdir(tmp_path)
    write_output = _legacy_module()._write_output
    nested = tmp_path / "artifacts"
    nested.mkdir()

    write_output("artifacts/run.json", "{}")
    assert (nested / "run.json").read_text() == "{}"
    with pytest.raises(ValueError, match="inside the invoking workspace"):
        write_output("../outside.json", "{}")

    (tmp_path / "link").symlink_to(Path("/tmp"), target_is_directory=True)
    with pytest.raises(ValueError, match="inside the invoking workspace"):
        write_output("link/run.json", "{}")


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only: run-harness.py:123 descriptor-safe write uses "
    "os.open(workspace, O_RDONLY|O_DIRECTORY|O_NOFOLLOW) -> Errno 13 on Windows",
)
def test_write_output_uses_descriptor_safe_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_output = _legacy_module()._write_output
    (tmp_path / "artifacts").mkdir()

    def unsafe_write(*_args, **_kwargs):
        raise AssertionError("Path.write_text leaves a check/write race")

    monkeypatch.setattr(Path, "write_text", unsafe_write)
    write_output("artifacts/run.json", "{}")

    assert (tmp_path / "artifacts" / "run.json").read_text() == "{}"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only: run-harness.py subprocess hits os.open(dir) at line 123 "
    "-> PermissionError [Errno 13] -> exit 1 on Windows",
)
def test_harness_dry_run_and_plan_hash(tmp_path):
    # Traces to: FR-HELIOS-IO-006 (strict dry-run envelope).
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text(
        '{"scripts":{"lint":"echo lint","test":"echo test","build":"echo build"}}'
    )
    _initialize_git_repo(repo)
    out_discover = tmp_path / "discover.json"
    out_run = tmp_path / "run.json"

    _run(
        [
            sys.executable,
            str(SCRIPT),
            "discover",
            "--root",
            str(repo),
            "--out",
            str(out_discover),
            "--max-scan-depth",
            "2",
        ],
        cwd=tmp_path,
    )
    payload = json.loads(out_discover.read_text())
    assert payload["buckets"].get("static")

    _run(
        [
            sys.executable,
            str(SCRIPT),
            "run",
            "--repo",
            str(repo),
            "--out",
            str(out_run),
            "--dry-run",
            "--timeout",
            "2",
            "--retries",
            "1",
        ],
        cwd=tmp_path,
    )
    output = json.loads(out_run.read_text())
    assert output["result_code"] == "PASS"
    assert output["plan_hash"]


@pytest.mark.skipif(
    sys.platform == "win32",
    reason='POSIX-only: fixture path contains " which is illegal on NTFS -> OSError WinError 123 on Windows',
)
def test_phase2_skip_marker_escapes_repo_name(tmp_path):
    # Traces to: FR-HELIOS-IO-006 (valid bounded evidence artifacts).
    root = tmp_path / "root"
    (root / "clones" / 'bad"name').mkdir(parents=True)
    subprocess.run(
        [str(PHASE2_SCRIPT)],
        env={
            **__import__("os").environ,
            "HELIOS_HARNESS_ROOT": str(root),
            "HELIOS_HARNESS_PYTHON": sys.executable,
            "PHASE2_SKIP_REPOS": 'bad"name',
        },
        check=True,
        capture_output=True,
        text=True,
    )

    marker = root / "artifacts" / "phase-2" / 'discovery-bad"name.json'
    payload = json.loads(marker.read_text())
    assert payload == {"repo_name": 'bad"name', "status": "skipped"}


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only: run-harness.py subprocess hits os.open(dir) at line 123 "
    "-> PermissionError [Errno 13] -> exit 1 on Windows",
)
def test_harness_replay_and_validate(tmp_path):
    # Traces to: FR-HELIOS-IO-006 (deterministic replay evidence).
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Makefile").write_text("check:\n\t@echo check\n")
    _initialize_git_repo(repo)
    out_first = tmp_path / "first.json"
    out_second = tmp_path / "second.json"

    _run(
        [
            sys.executable,
            str(SCRIPT),
            "run",
            "--repo",
            str(repo),
            "--out",
            str(out_first),
            "--timeout",
            "2",
        ],
        cwd=tmp_path,
    )

    _run(
        [
            sys.executable,
            str(SCRIPT),
            "run",
            "--repo",
            str(repo),
            "--out",
            str(out_second),
            "--replay",
            str(out_first),
            "--timeout",
            "2",
        ],
        cwd=tmp_path,
    )

    second_payload = json.loads(out_second.read_text())
    assert second_payload["replay"]["same_plan"] is True
    assert "prior_plan_hash" in second_payload["replay"]
    assert second_payload["subject"]["commit"]
    assert second_payload["provenance"]["source_ref"] == second_payload["subject"]["ref"]

    schema = Path("harness/schemas/benchmark_run.schema.json").resolve()
    if not schema.exists():
        schema = Path("schemas/benchmark_run.schema.json").resolve()
    _run(
        [
            sys.executable,
            str(SCRIPT),
            "validate",
            "--schema",
            str(schema),
            "--file",
            str(out_second),
        ],
        cwd=tmp_path,
    )


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only: run-harness.py subprocess hits os.open(dir) at line 123 "
    "-> PermissionError [Errno 13] -> exit 1 on Windows",
)
def test_replay_uses_stored_plan_hash_when_plan_details_are_absent(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Makefile").write_text("check:\n\t@echo check\n")
    _initialize_git_repo(repo)
    first = tmp_path / "first.json"
    replay = tmp_path / "replay.json"

    _run(
        [sys.executable, str(SCRIPT), "run", "--repo", str(repo), "--out", str(first)],
        cwd=tmp_path,
    )
    prior = json.loads(first.read_text())
    expected_hash = prior["plan_hash"]
    prior.pop("plan", None)
    prior.pop("commands", None)
    prior.pop("tasks", None)
    first.write_text(json.dumps(prior))

    _run(
        [
            sys.executable,
            str(SCRIPT),
            "run",
            "--repo",
            str(repo),
            "--out",
            str(replay),
            "--replay",
            str(first),
        ],
        cwd=tmp_path,
    )

    output = json.loads(replay.read_text())
    assert output["replay"]["prior_plan_hash"] == expected_hash
    assert output["replay"]["same_plan"] is True
