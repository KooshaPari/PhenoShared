import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def test_execute_phase_2_harness_script_smoke(tmp_path: Path) -> None:
    # Traces to: FR-HELIOS-IO-006 (explicit non-Git provenance handling).
    source_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "phase2-harness-workspace"
    workspace.mkdir()

    (workspace / "commands").mkdir(parents=True)
    (workspace / "clones").mkdir(parents=True)
    (workspace / "artifacts" / "phase-2").mkdir(parents=True)
    (workspace / "harness").mkdir(parents=True)

    command_src = source_root.parent / "commands" / "execute-phase-2-harness.sh"
    harness_src = source_root.parent / "harness"

    shutil.copy2(command_src, workspace / "commands" / "execute-phase-2-harness.sh")
    shutil.copytree(harness_src, workspace / "harness", dirs_exist_ok=True)

    repo_root = workspace / "clones" / "toyrepo"
    repo_root.mkdir()
    (repo_root / "package.json").write_text(
        '{\n  "scripts": {\n    "quality": "echo quality",\n    "test": "echo test"\n  }\n}\n'
    )

    env = os.environ.copy()
    env["HELIOS_HARNESS_ROOT"] = str(workspace)
    env["HELIOS_HARNESS_PYTHON"] = sys.executable

    proc = subprocess.run(
        ["bash", "commands/execute-phase-2-harness.sh"],
        cwd=workspace,
        env=env,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0
    assert "No such remote" not in proc.stderr

    evidence = json.loads((workspace / "artifacts" / "phase-2" / "evidence-all.json").read_text())
    targets = evidence["targets"]
    assert any(t["repo_name"] == "toyrepo" for t in targets)
    toy_target = next(t for t in targets if t["repo_name"] == "toyrepo")
    assert toy_target["run"]["result_code"] == "WARN"
    assert toy_target["run"]["provenance"]["reason"] == "non_git_repository"

    matrix_text = (
        workspace / "artifacts" / "phase-2" / "lane-d" / "integration-matrix.md"
    ).read_text()
    assert "toyrepo" in matrix_text


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only: invokes bash with Windows paths - backslashes eaten as "
    "escapes -> file-not-found (127)",
)
def test_phase_2_wrapper_uses_configured_root_and_discards_stale_outputs(
    tmp_path: Path,
) -> None:
    source_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "commands").mkdir()
    (workspace / "clones" / "toyrepo").mkdir(parents=True)
    artifact_root = workspace / "artifacts" / "phase-2"
    lane_dir = artifact_root / "lane-d"
    lane_dir.mkdir(parents=True)
    (artifact_root / "discovery-toyrepo.json").write_text('{"stale": true}')
    (lane_dir / "toyrepo-run.json").write_text('{"result_code": "PASS"}')
    shutil.copy2(
        source_root.parent / "commands" / "execute-phase-2-harness.sh",
        workspace / "commands" / "execute-phase-2-harness.sh",
    )
    (workspace / "harness" / "scripts").mkdir(parents=True)
    (workspace / "harness" / "scripts" / "run-harness.py").write_text("")
    fake_python = workspace / "fail-runner-python"
    fake_python.write_text(
        f'#!/bin/sh\nif [ "${{1:-}}" != "-" ]; then exit 1; fi\nexec {sys.executable} "$@"\n'
    )
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env["HELIOS_HARNESS_ROOT"] = str(workspace)
    env["HELIOS_HARNESS_PYTHON"] = str(fake_python)

    proc = subprocess.run(
        ["bash", str(workspace / "commands" / "execute-phase-2-harness.sh")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    evidence = json.loads((artifact_root / "evidence-all.json").read_text())
    target = next(item for item in evidence["targets"] if item["repo_name"] == "toyrepo")
    assert target["discovery"]["status"] == "missing"
    assert target["run"]["result_code"] == "MISSING"
