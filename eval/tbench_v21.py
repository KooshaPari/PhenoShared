"""Terminal-Bench 2.x local-first driver and manifest contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pheno.harbor_util import local_env
from pheno.model_policy import require_local_alias, require_runtime_alias
from pheno.paths import CONFIG_DIR, PHENO_ROOT


def _utc_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]


def build_manifest(
    *,
    model_alias: str,
    subset: str,
    dry_run: bool,
    suite: str = "terminal-bench@2.0",
    subset_manifest: Path | None = None,
) -> dict[str, Any]:
    """Build a Terminal-Bench invocation manifest.

    Args:
        model_alias: Local model alias.
        subset: Task subset identifier.
        dry_run: Whether this is a dry-run manifest.
        suite: Suite identifier (terminal-bench@2.0 or 2.1).
        subset_manifest: Optional pinned subset manifest path.

    Returns:
        Invocation manifest dict (non-scoreable).

    """
    require_local_alias(model_alias)
    if suite not in {"terminal-bench@2.0", "terminal-bench@2.1"}:
        raise ValueError(f"unsupported Terminal-Bench suite: {suite}")
    suite_version = suite.rsplit("@", 1)[-1]
    acquired = PHENO_ROOT / "state" / "harbor_terminal_bench_2_0_artifacts.json"
    tb21_acquired = (
        PHENO_ROOT / "state" / "tbench21_source_acquisition_complete_20260801.json"
    )
    artifact_manifest = None
    if suite == "terminal-bench@2.0" and acquired.exists():
        artifact_manifest = str(acquired)
    elif suite == "terminal-bench@2.1" and tb21_acquired.exists():
        candidate = json.loads(tb21_acquired.read_text(encoding="utf-8"))
        source_root = Path(str(candidate.get("source_path", "")))
        if (
            candidate.get("status") == "source_acquired_pinned"
            and candidate.get("git_head")
            and source_root.is_dir()
            and int(candidate.get("task_count", 0)) > 0
        ):
            artifact_manifest = str(tb21_acquired)
    tbench_21_status = "not_requested"
    if suite == "terminal-bench@2.1":
        tbench_21_status = "available" if artifact_manifest else "missing"
    artifact_meta: dict[str, Any] = {}
    if artifact_manifest:
        artifact_payload = json.loads(
            Path(artifact_manifest).read_text(encoding="utf-8")
        )
        artifact_meta = artifact_payload.get(
            "task_manifest_sha256"
        ) or artifact_payload.get("manifest_sha256", {})
    else:
        artifact_payload = {}
    selected_tasks: list[str] = []
    subset_hash = None
    subset_source = None
    if (
        subset_manifest is None
        and suite == "terminal-bench@2.0"
        and subset == "representative-6"
    ):
        subset_manifest = PHENO_ROOT / "config" / "tbench20_representative_subset.json"
    if subset_manifest is None and suite == "terminal-bench@2.0" and subset == "16":
        candidate = PHENO_ROOT / "config" / "tbench20_16task_subset.json"
        if candidate.exists():
            subset_manifest = candidate
    if subset_manifest is not None:
        subset_source = str(subset_manifest)
        subset_payload = json.loads(subset_manifest.read_text(encoding="utf-8"))
        if subset_payload.get("suite") != suite:
            raise ValueError("subset manifest suite does not match requested suite")
        selected_tasks = [str(item) for item in subset_payload.get("task_ids", [])]
        subset_hash = subset_payload.get("subset_manifest_sha256")
        if not selected_tasks or not isinstance(subset_hash, str):
            raise ValueError(
                "subset manifest must contain task_ids and subset_manifest_sha256"
            )
    return {
        "schema_version": 1,
        "suite": suite,
        "suite_status": "dataset_acquired_verifier_unverified"
        if artifact_manifest
        else "availability_unverified",
        "tbench_21_status": tbench_21_status,
        "model_alias": model_alias,
        "route": "local_pheno_serve",
        "base_url": os.environ.get("PHENO_SERVE_BASE_URL", "http://127.0.0.1:21080/v1"),
        "n_attempts": 1,
        "subset": subset,
        "suite_version": suite_version,
        "task_count": len(selected_tasks)
        if selected_tasks
        else (
            int(artifact_payload.get("task_count", 89))
            if artifact_manifest
            else (89 if suite == "terminal-bench@2.0" else None)
        ),
        "task_names": selected_tasks,
        "subset_manifest": subset_source,
        "subset_manifest_sha256": subset_hash,
        "task_artifact_manifest": artifact_manifest,
        "task_artifact_root": artifact_payload.get("local_root")
        or artifact_payload.get("source_path"),
        "task_manifest_sha256": artifact_meta
        if isinstance(artifact_meta, str)
        else None,
        "run_mode": "dry_run" if dry_run else "execute",
        "provider_cost_usd": 0,
        # A Harbor invocation manifest is not a verified benchmark result.
        "scoreable": False,
        "review_required": True,
        "verification_status": "not_run",
        "created_at": datetime.now(UTC).isoformat(),
        "integrity": {
            "local_only": True,
            "cloud_evals_disabled": True,
            "no_training_on_eval_tasks": True,
            "single_attempt_only": True,
        },
    }


def write_manifest(manifest: dict[str, Any], root: Path | None = None) -> Path:
    """Persist the manifest to disk and return its path.

    Args:
        manifest: Manifest dict from build_manifest.
        root: Optional output root; defaults to bench/results/tbench/<version>.

    Returns:
        Path to the written JSON file.

    """
    version_dir = str(manifest.get("suite_version", "2.0")).replace(".", "")
    output_root = root or PHENO_ROOT / "bench" / "results" / "tbench" / version_dir
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / f"{_utc_run_id()}.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def execute(manifest: dict[str, Any], output_dir: Path) -> int:
    """Run Harbor only after the caller has explicitly selected execution."""
    require_runtime_alias(str(manifest["model_alias"]))
    dataset = str(manifest["suite"])
    if dataset == "terminal-bench@2.1":
        root = manifest.get("task_artifact_root")
        if not root or not Path(str(root)).is_dir():
            raise ValueError(
                "Terminal-Bench 2.1 execution requires the pinned local task root; "
                "refusing Harbor registry fallback"
            )
    model = "openai/" + str(manifest["model_alias"])
    harbor_prefix = [os.environ.get("PHENO_HARBOR_BIN", "harbor")]
    if os.environ.get("PHENO_HARBOR_PODMAN_COMPAT") == "1":
        harbor_prefix = [
            os.environ.get("PHENO_PIER_PYTHON", sys.executable),
            str(PHENO_ROOT / "scripts" / "harbor_podman_compat.py"),
        ]
    command = harbor_prefix + [
        "run",
        "-c",
        str(CONFIG_DIR / "harbor_tbench_agent.yaml"),
        "-a",
        "terminus-2",
        "--agent-import-path",
        "harness.harbor.terminus_safe:SafeTerminus2",
        "-m",
        model,
        "--env",
        "docker",
        "--n-concurrent",
        "1",
        "-o",
        str(output_dir),
        "-y",
    ]
    # Keep the Python driver aligned with harbor/run_tbench_local.ps1.  In
    # particular, max_turns is not a Harbor global; omitting it leaves
    # Terminus-2 at its million-episode default and can make local runs loop
    # indefinitely on a weak model.
    for key, value in (
        ("api_base", str(manifest["base_url"])),
        ("max_turns", "3"),
        ("max_tokens", "2048"),
        ("temperature", "0"),
        ("max_thinking_tokens", "1024"),
        ("reasoning_effort", "none"),
        ("interleaved_thinking", "false"),
        ("enable_summarize", "false"),
        ("record_terminal_session", "false"),
    ):
        command.extend(["--agent-kwarg", f"{key}={value}"])
    artifact_root = manifest.get("task_artifact_root")
    if artifact_root and Path(str(artifact_root)).is_dir():
        command.extend(["-p", str(artifact_root)])
    else:
        command.extend(["-d", dataset])
    for task_name in manifest.get("task_names", []):
        command.extend(["--include-task-name", str(task_name)])
    env = local_env(str(manifest["base_url"]), api_key="local-no-key")
    return subprocess.run(command, cwd=PHENO_ROOT, env=env, check=False).returncode
