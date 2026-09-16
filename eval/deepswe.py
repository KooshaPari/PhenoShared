"""DeepSWE manifest and explicit Pier execution contract.

This module builds a manifest for the DeepSWE suite without executing
it, and exposes ``docker_runtime_preflight`` / ``pier_preflight`` helpers
that validate the binary and Docker surface before any execution.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml

from pheno.harbor_util import local_env
from pheno.model_policy import require_local_alias, require_runtime_alias
from pheno.paths import CONFIG_DIR, PHENO_ROOT


@dataclass(frozen=True)
class PierPreflight:
    """Structured surface for Pier binary detection and version pin check.

    Attributes:
        schema_version: Preflight schema version.
        runner: Runner binary name from config.
        binary_path: Resolved binary path if found.
        binary_found: Whether the binary exists on PATH.
        binary_version: Detected version string if probed.
        minimum_runner_version: Minimum required version from config.
        version_satisfied: Whether version satisfies minimum, None if unknown.
        task_root_env: Environment variable naming the task root.
        task_root_required: Whether task root is required for execution.
        task_root_value: Raw env var value.
        task_root_resolved: Resolved path if env var set.
        task_root_present: Whether resolved path exists and is a directory.

    """

    schema_version: str
    runner: str
    binary_path: str | None
    binary_found: bool
    binary_version: str | None
    minimum_runner_version: str
    version_satisfied: bool | None  # None when binary is absent
    task_root_env: str
    task_root_required: bool
    task_root_value: str | None
    task_root_resolved: Path | None
    task_root_present: bool

    def as_dict(self) -> dict[str, Any]:
        """Serialize preflight to a JSON-compatible dict.

        Returns:
            Dict with ``task_root_resolved`` coerced to string if present.

        """
        value: dict[str, Any] = asdict(self)
        if value["task_root_resolved"] is not None:
            value["task_root_resolved"] = str(value["task_root_resolved"])
        return value


_VERSION_TUPLE_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _runner_command(binary_path: str, *args: str) -> list[str]:
    """Build a subprocess command for native binaries and Windows wrappers.

    Args:
        binary_path: Path or name of the runner binary.
        *args: Additional CLI arguments to append.

    Returns:
        Command list suitable for ``subprocess.run``.

    """
    module_python = os.environ.get("PHENO_PIER_PYTHON")
    module_root = os.environ.get("PHENO_PIER_PYTHONPATH")
    if (
        module_python
        and module_root
        and Path(module_root).is_dir()
        and (
            Path(binary_path).suffix.lower() in {".cmd", ".bat"}
            or binary_path == module_python
        )
    ):
        return [module_python, "-m", "pier.cli.main", *args]
    suffix = Path(binary_path).suffix.lower()
    if suffix in {".cmd", ".bat"}:
        return ["cmd", "/d", "/c", "call", binary_path, *args]
    return [binary_path, *args]


def _isolated_pier_version(root: str) -> str | None:
    """Read the version from an explicitly selected isolated wheel root.

    Args:
        root: Filesystem path to an isolated ``distributions`` root.

    Returns:
        Version string if ``datacurve-pier`` distribution is found, else None.

    """
    try:
        for dist in distributions(path=[root]):
            if (dist.metadata.get("Name") or "").lower() == "datacurve-pier":
                return dist.version
    except (OSError, ValueError):
        return None
    return None


def docker_runtime_preflight(*, timeout: float = 3.0) -> dict[str, Any]:
    """Probe the Docker-compatible API selected for an execute-mode run.

    Args:
        timeout: HTTP/CLI probe timeout in seconds.

    Returns:
        Dict with ``reachable`` and diagnostic fields. Never raises for
        missing binaries; returns a ``reason`` field instead.

    """
    host = os.environ.get("DOCKER_HOST")
    if not host:
        executable = shutil.which("docker")
        if not executable:
            return {
                "checked": True,
                "reachable": False,
                "reason": "docker_host_and_cli_missing",
            }
        try:
            proc = subprocess.run(
                [executable, "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as exc:
            return {
                "checked": True,
                "reachable": False,
                "reason": f"docker_cli_probe_failed:{type(exc).__name__}",
            }
        if proc.returncode != 0:
            return {
                "checked": True,
                "reachable": False,
                "reason": "docker_cli_nonzero",
                "stderr": proc.stderr[-500:],
            }
        return {
            "checked": True,
            "reachable": True,
            "docker_host": "cli",
            "server_version": proc.stdout.strip(),
        }
    if not host.startswith(("tcp://", "http://", "https://")):
        return {
            "checked": True,
            "reachable": False,
            "docker_host": host,
            "reason": "unsupported_docker_host_scheme",
        }
    base = host.replace("tcp://", "http://", 1).rstrip("/")
    probe_result: dict[str, Any] = {"checked": True, "docker_host": host}
    try:
        with (
            urlopen(Request(base + "/_ping"), timeout=timeout) as response  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            probe_result["ping"] = response.read().decode(errors="replace").strip()
        with (
            urlopen(Request(base + "/version"), timeout=timeout) as response  # nosec B310 — internal HTTP to localhost/controlled endpoint, reviewed false positive
        ):
            version = json.loads(response.read().decode("utf-8"))
        probe_result.update(
            reachable=True,
            server_version=version.get("Version"),
            api_version=version.get("ApiVersion"),
            os=version.get("Os"),
            arch=version.get("Arch"),
        )
        return probe_result
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        probe_result.update(
            reachable=False, reason=f"docker_api_probe_failed:{type(exc).__name__}"
        )
        return probe_result


def _version_probe(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Probe native commands and Windows batch wrappers without pipe deadlocks.

    Args:
        command: Command list as produced by ``_runner_command``.

    Returns:
        CompletedProcess with captured stdout/stderr.

    """
    module_root = os.environ.get("PHENO_PIER_PYTHONPATH")
    probe_env: dict[str, str] | None = None
    if module_root and len(command) >= 3 and command[1:3] == ["-m", "pier.cli.main"]:
        probe_env = os.environ.copy()
        existing = probe_env.get("PYTHONPATH")
        probe_env["PYTHONPATH"] = module_root + (
            os.pathsep + existing if existing else ""
        )
    timeout = 30 if len(command) >= 3 and command[1:3] == ["-m", "pier.cli.main"] else 3
    if command[:3] == ["cmd", "/d", "/c"]:
        with tempfile.TemporaryFile(mode="w+b") as output:
            result = subprocess.run(
                command,
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
                env=probe_env,
            )
            output.seek(0)
            text = output.read().decode(errors="replace")
        return subprocess.CompletedProcess(command, result.returncode, text, "")
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=probe_env,
    )


def _parse_version(text: str) -> tuple[int, int, int] | None:
    """Parse a ``MAJOR.MINOR.PATCH`` version tuple from freeform text.

    Args:
        text: String that may contain a version.

    Returns:
        Tuple of ints if found, else None.

    """
    match = _VERSION_TUPLE_RE.search(text)
    if not match:
        return None
    try:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def pier_preflight(config: dict[str, Any]) -> PierPreflight:
    """Read-only preflight: Pier binary plus version plus task-root resolution.

    Args:
        config: Loaded DeepSWE config containing ``suite`` block.

    Returns:
        ``PierPreflight`` describing binary and task-root availability.

    """
    suite: dict[str, Any] = config["suite"]
    runner = str(suite["runner"])
    min_version = str(suite["min_pier_version"])
    env_override = os.environ.get("PHENO_PIER_BIN")
    binary_path = env_override or shutil.which(runner)
    binary_found = bool(binary_path)
    binary_version: str | None = None
    version_satisfied: bool | None = None
    isolated_root = os.environ.get("PHENO_PIER_PYTHONPATH")
    isolated_version = (
        _isolated_pier_version(isolated_root)
        if isolated_root and Path(isolated_root).is_dir()
        else None
    )
    if binary_found and isolated_version is not None:
        binary_version = isolated_version
        current = _parse_version(binary_version)
        required = _parse_version(min_version)
        version_satisfied = (
            current >= required
            if current is not None and required is not None
            else None
        )
    elif binary_found:
        try:
            assert binary_path is not None
            result = _version_probe(_runner_command(binary_path, "--version"))
            if result.returncode == 0:
                raw = (
                    (result.stdout or result.stderr or "").strip().splitlines()[0]
                    if (result.stdout or result.stderr)
                    else None
                )
                binary_version = raw.strip() if raw else None
                current = _parse_version(binary_version or "")
                required = _parse_version(min_version)
                if current is not None and required is not None:
                    version_satisfied = current >= required
                else:
                    version_satisfied = None
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            binary_found = False
            binary_path = env_override or shutil.which(runner)
    task_root_env = str(suite["task_root_env"])
    task_root_required = task_root_env == "PHENO_DEEPSWE_TASK_ROOT"
    raw = os.environ.get(task_root_env)
    resolved = Path(raw).expanduser() if raw else None
    present = bool(resolved and resolved.is_dir())
    return PierPreflight(
        schema_version="pheno.deepswe.preflight.v1",
        runner=runner,
        binary_path=binary_path,
        binary_found=binary_found,
        binary_version=binary_version,
        minimum_runner_version=min_version,
        version_satisfied=version_satisfied,
        task_root_env=task_root_env,
        task_root_required=task_root_required,
        task_root_value=raw,
        task_root_resolved=resolved,
        task_root_present=present,
    )


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load DeepSWE suite config.

    Args:
        path: Optional override path. Defaults to ``CONFIG_DIR/deepswe.yaml``.

    Returns:
        Parsed config dict, empty dict if file is empty.

    """
    return (
        yaml.safe_load(
            (path or CONFIG_DIR / "deepswe.yaml").read_text(encoding="utf-8")
        )
        or {}
    )


def build_manifest(
    config: dict[str, Any],
    *,
    model_alias: str,
    subset: int,
    environment: str,
    execute: bool,
    preflight: PierPreflight | None = None,
) -> dict[str, Any]:
    """Build a DeepSWE execution manifest.

    Args:
        config: Loaded suite config.
        model_alias: Model alias enabled for DeepSWE.
        subset: Number of tasks requested (1..n_tasks).
        environment: Execution environment, must be ``docker``.
        execute: Whether manifest intends execution.
        preflight: Optional preflight to validate and embed.

    Returns:
        Manifest dict ready for ``write_manifest`` or ``execute``.

    Raises:
        ValueError: If ``model_alias`` or environment is invalid, or
            preflight/runtime preconditions for execution fail.

    """
    suite: dict[str, Any] = config["suite"]
    require_local_alias(model_alias)
    if environment != "docker":
        raise ValueError(
            "DeepSWE cloud environments are disabled; use --env docker with a local Pheno endpoint"
        )
    if model_alias not in config["models"]:
        raise ValueError(f"model is not enabled for DeepSWE: {model_alias}")
    if subset < 1 or subset > int(suite["n_tasks"]):
        raise ValueError(f"subset must be between 1 and {suite['n_tasks']}")
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "suite": suite["id"],
        "n_tasks_total": suite["n_tasks"],
        "n_tasks_requested": subset,
        "model_alias": model_alias,
        "agent": suite["agent"],
        "runner": suite["runner"],
        "minimum_runner_version": suite["min_pier_version"],
        "task_root_env": suite["task_root_env"],
        "environment": environment,
        "run_mode": "execute" if execute else "dry_run",
        "provider_cost_usd": 0,
        # A runner manifest is not a verified benchmark result.  Keep this
        # explicit so downstream aggregators cannot treat execution intent as
        # semantic success.
        "scoreable": False,
        "review_required": True,
        "verification_status": "not_run",
        "created_at": datetime.now(UTC).isoformat(),
        "integrity": {**config["policy"], "no_training_on_eval_tasks": True},
    }
    if preflight is not None:
        manifest["preflight"] = preflight.as_dict()
        if execute and not preflight.binary_found:
            raise ValueError(
                f"{preflight.runner} binary not on PATH (set PHENO_PIER_BIN); required for execute mode"
            )
        if execute and preflight.version_satisfied is False:
            raise ValueError(
                f"{preflight.runner} {preflight.binary_version} does not satisfy "
                f">={preflight.minimum_runner_version}; upgrade Pier before executing"
            )
        if execute and preflight.task_root_required and not preflight.task_root_present:
            raise ValueError(
                f"set {preflight.task_root_env} to an existing DeepSWE tasks directory "
                f"(currently {preflight.task_root_value!r})"
            )
    if execute:
        runtime = docker_runtime_preflight()
        manifest["runtime_preflight"] = runtime
        if not runtime.get("reachable"):
            raise ValueError(
                "Docker-compatible runtime is not reachable; refusing DeepSWE execution: "
                + str(runtime.get("reason", "unknown runtime failure"))
            )
    return manifest


def write_manifest(manifest: dict[str, Any], root: Path | None = None) -> Path:
    """Persist a manifest to ``bench/results/deepswe``.

    Args:
        manifest: Manifest dict from ``build_manifest``.
        root: Optional override output root.

    Returns:
        Path to the written JSON file.

    """
    output_root = root or PHENO_ROOT / "bench" / "results" / "deepswe"
    output_root.mkdir(parents=True, exist_ok=True)
    name = (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid.uuid4().hex[:8]
        + ".json"
    )
    path = output_root / name
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def execute(manifest: dict[str, Any]) -> int:
    """Execute a DeepSWE run via the Pier runner.

    Args:
        manifest: Manifest dict containing runner and task-root metadata.

    Returns:
        Runner process return code.

    Raises:
        ValueError: If ``binary_found`` is false, version is unsatisfied,
            or task root is missing.

    """
    require_runtime_alias(str(manifest["model_alias"]))
    preflight_dict: dict[str, Any] = manifest.get("preflight") or {}
    if not preflight_dict.get("binary_found"):
        raise ValueError(
            f"{manifest['runner']} binary not on PATH (set PHENO_PIER_BIN)"
        )
    if preflight_dict.get("version_satisfied") is False:
        raise ValueError(
            f"{manifest['runner']} {preflight_dict.get('binary_version')} does not satisfy "
            f">={manifest['minimum_runner_version']}; upgrade Pier before executing"
        )
    task_root = preflight_dict.get("task_root_value") or os.environ.get(
        str(manifest["task_root_env"]), ""
    )
    resolved = preflight_dict.get("task_root_resolved")
    if resolved and Path(str(resolved)).is_dir():
        task_root_path = Path(str(resolved))
    elif task_root:
        task_root_path = Path(str(task_root))
    else:
        raise ValueError(
            f"set {manifest['task_root_env']} to an existing DeepSWE tasks directory"
        )
    if not task_root_path.is_dir():
        raise ValueError(
            f"{manifest['task_root_env']}={task_root} does not exist; acquire the DeepSWE corpus before executing"
        )
    runner = (
        preflight_dict.get("binary_path")
        or os.environ.get("PHENO_PIER_BIN")
        or str(manifest["runner"])
    )
    command = _runner_command(
        runner,
        "run",
        "-p",
        str(task_root_path),
        "--agent",
        str(manifest["agent"]),
        "--model",
        "openai/" + str(manifest["model_alias"]),
        "--n-tasks",
        str(manifest["n_tasks_requested"]),
        "--sample-seed",
        "0",
        "--env",
        str(manifest["environment"]),
    )
    env = local_env(
        os.environ.get("PHENO_SERVE_BASE_URL", "http://127.0.0.1:21080/v1"),
        api_key="local-no-key",
    )
    module_root = os.environ.get("PHENO_PIER_PYTHONPATH")
    if module_root and Path(module_root).is_dir():
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = module_root + (os.pathsep + existing if existing else "")
    return subprocess.run(command, cwd=PHENO_ROOT, env=env, check=False).returncode
