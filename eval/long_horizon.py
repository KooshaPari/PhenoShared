"""Manifest-first driver for Pheno's Harbor-compatible long-horizon suite.

This module discovers long-horizon tasks, builds a typed manifest
(``LongHorizonManifest``), and optionally executes via the Pier runner.
Execution is gated behind ``PHENO_LONG_HORIZON_ENABLE=1``.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from pheno.harbor_util import local_env
from pheno.model_policy import require_local_alias, require_runtime_alias
from pheno.paths import CONFIG_DIR, PHENO_ROOT

REQUIRED_TASK_PATHS = ("task.toml", "instruction.md", "environment", "tests")


@dataclass
class LongHorizonManifest:
    """Typed manifest for a long-horizon suite run.

    Attributes:
        schema_version: Manifest schema version.
        suite: Suite identifier from config.
        runner: Runner binary name.
        agent: Agent identifier.
        model_alias: Model alias selected for the run.
        task_root: Resolved task root directory.
        task_ids: Sorted task identifiers discovered under task_root.
        task_count: Number of tasks.
        scoreable: Whether all tasks are explicitly marked scoreable.
        review_required: True if not scoreable.
        verification_status: ``unverified`` or ``not_run``.
        corpus_sha256: Hash over all task files.
        roles: Role mapping from config.
        run_mode: ``execute`` or ``dry_run``.
        provider_cost_usd: Cost placeholder (always 0 for dry runs).
        policy: Policy dict from config.
        created_at: ISO-8601 creation timestamp.

    """

    schema_version: int
    suite: str
    runner: str
    agent: str
    model_alias: str
    task_root: str
    task_ids: list[str]
    task_count: int
    scoreable: bool
    review_required: bool
    verification_status: str
    corpus_sha256: str
    roles: dict[str, Any]
    run_mode: str
    provider_cost_usd: int
    policy: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the manifest to a JSON-compatible dict.

        Returns:
            Dict representation suitable for ``json.dump``.

        """
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        """Dict-style read access mirroring ``to_dict()`` keys.

        Allows ``manifest["task_count"]`` for callers that treat the
        manifest as a mapping without forcing ``to_dict()`` round-trips.
        """
        return getattr(self, key)


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load long-horizon suite config.

    Args:
        path: Optional override path. Defaults to
            ``CONFIG_DIR / "long_horizon.yaml"``.

    Returns:
        Parsed config dict, empty dict if file is empty.

    """
    return (
        yaml.safe_load(
            (path or CONFIG_DIR / "long_horizon.yaml").read_text(encoding="utf-8")
        )
        or {}
    )


def discover_tasks(task_root: Path) -> list[Path]:
    """Discover and validate task directories.

    Args:
        task_root: Root directory containing per-task subdirectories.

    Returns:
        Sorted list of validated task directory paths.

    Raises:
        ValueError: If ``task_root`` is missing or tasks are invalid.

    """
    if not task_root.is_dir():
        raise ValueError(f"task root does not exist: {task_root}")
    tasks: list[Path] = []
    for child in sorted(task_root.iterdir()):
        if not child.is_dir():
            continue
        missing = [name for name in REQUIRED_TASK_PATHS if not (child / name).exists()]
        if missing:
            raise ValueError(
                f"{child.name}: missing required paths: {', '.join(missing)}"
            )
        if not (child / "tests" / "test.sh").is_file():
            raise ValueError(f"{child.name}: tests/test.sh is required")
        tasks.append(child)
    if not tasks:
        raise ValueError(f"no tasks found under {task_root}")
    return tasks


def _coerce_roles(raw: Any) -> dict[str, Any]:
    """Coerce roles from a YAML list-of-names or mapping into a typed dict.

    Args:
        raw: Either ``list[str]`` (just role names) or ``dict[str, Any]``
            (explicit mapping). Returns an empty dict if ``raw`` is
            ``None`` / missing.

    Returns:
        ``dict[str, Any]`` suitable for ``LongHorizonManifest.roles``.

    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, list):
        return {str(name): {"name": str(name)} for name in raw}
    raise ValueError(f"unsupported roles payload: {type(raw).__name__}")


def corpus_hash(tasks: list[Path]) -> str:
    """Hash the full task corpus deterministically.

    Args:
        tasks: List of task directory paths.

    Returns:
        Hex-encoded SHA-256 over relative paths and file contents.

    """
    digest = hashlib.sha256()
    for task in tasks:
        for path in sorted(p for p in task.rglob("*") if p.is_file()):
            digest.update(path.relative_to(task.parent).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def build_manifest(
    config: dict[str, Any], *, task_root: Path, model_alias: str, execute: bool
) -> LongHorizonManifest:
    """Build a typed manifest for the long-horizon suite.

    Args:
        config: Loaded suite config from ``load_config``.
        task_root: Root directory for task discovery.
        model_alias: Model alias to validate against ``config["models"]``.
        execute: Whether the manifest intends execution (affects run_mode).

    Returns:
        A ``LongHorizonManifest`` dataclass.

    Raises:
        ValueError: If ``model_alias`` is not enabled for the suite.

    """
    require_local_alias(model_alias)
    if model_alias not in config["models"]:
        raise ValueError(
            f"model is not enabled for the local long-horizon set: {model_alias}"
        )
    tasks = discover_tasks(task_root)
    task_metadata: list[dict[str, Any]] = [
        tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
        for task in tasks
    ]
    # Scoreability is an admission decision, never an implicit default.  A
    # task without an explicit boolean marker is incomplete and must remain a
    # dry-run fixture until its verifier and review metadata are present.
    scoreable = all(metadata.get("scoreable") is True for metadata in task_metadata)
    suite: dict[str, Any] = config["suite"]
    return LongHorizonManifest(
        schema_version=1,
        suite=str(suite["id"]),
        runner=str(suite["runner"]),
        agent=str(suite["agent"]),
        model_alias=model_alias,
        task_root=str(task_root.resolve()),
        task_ids=[task.name for task in tasks],
        task_count=len(tasks),
        scoreable=scoreable,
        review_required=not scoreable,
        verification_status="unverified" if scoreable else "not_run",
        corpus_sha256=corpus_hash(tasks),
        roles=_coerce_roles(config["roles"]),
        run_mode="execute" if execute else "dry_run",
        provider_cost_usd=0,
        policy=dict(config["policy"]),
        created_at=datetime.now(UTC).isoformat(),
    )


def write_manifest(
    manifest: LongHorizonManifest | dict[str, Any], root: Path | None = None
) -> Path:
    """Persist a manifest to ``bench/results/long_horizon``.

    Args:
        manifest: Manifest dataclass or legacy dict.
        root: Optional override output root.

    Returns:
        Path to the written JSON file.

    """
    output_root = root or PHENO_ROOT / "bench" / "results" / "long_horizon"
    output_root.mkdir(parents=True, exist_ok=True)
    name = (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid.uuid4().hex[:8]
        + ".json"
    )
    path = output_root / name
    data: dict[str, Any] = (
        manifest.to_dict()
        if isinstance(manifest, LongHorizonManifest)
        else dict(manifest)
    )
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def execute(manifest: LongHorizonManifest | dict[str, Any]) -> int:
    """Execute a long-horizon run via the Pier runner.

    Args:
        manifest: Manifest dataclass or dict. Must be scoreable.

    Returns:
        Runner process return code.

    Raises:
        ValueError: If manifest is not scoreable or execution is not enabled.

    """
    data: dict[str, Any] = (
        manifest.to_dict()
        if isinstance(manifest, LongHorizonManifest)
        else dict(manifest)
    )
    if not data.get("scoreable"):
        raise ValueError("refusing to execute a non-scoreable schema fixture")
    if os.environ.get("PHENO_LONG_HORIZON_ENABLE") != "1":
        raise ValueError("set PHENO_LONG_HORIZON_ENABLE=1 for explicit execution")
    require_runtime_alias(str(data["model_alias"]))
    runner = os.environ.get("PHENO_PIER_BIN", str(data["runner"]))
    command = [
        runner,
        "run",
        "-p",
        str(data["task_root"]),
        "--agent",
        str(data["agent"]),
        "--model",
        "openai/" + str(data["model_alias"]),
        "--env",
        "docker",
    ]
    env = local_env(
        os.environ.get("PHENO_SERVE_BASE_URL", "http://127.0.0.1:21080/v1"),
        api_key="local-no-key",
    )
    return subprocess.run(command, cwd=PHENO_ROOT, env=env, check=False).returncode
