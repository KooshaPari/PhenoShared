"""Container runner for SWE-agent style benchmarks (Harbor-style contract).

Wraps the Docker/Podman CLI to build the task's Dockerfile, run the agent,
and capture the standard Harbor reward file + CTRF JSONL + run.log.

Spec reference: docs/superpowers/specs/2026-07-16-benchmark-harness.md §2
rows 1-3 (DeepSWE, terminal-bench, SWE-bench) and §3.2 (Harbor port).

Spec rule 3: if Docker is not available, raise `ContainerNotAvailableError`.
The runner catches that and downgrades to stub-mode (synthetic task results).

.. deprecated::
    This bespoke module is deprecated as of 2026-07-21. The canonical
    container runner lives in ``portage/src/harbor/environments/`` with
    9 production-grade environments (docker, langsmith, daytona, e2b,
    modal, runloop, apple_container, gke, openshift, novita). Use
    ``harbor run --env <name>`` to invoke them.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ContainerNotAvailableError(RuntimeError):
    """Raised when Docker/Podman isn't installed or the daemon is down."""


class ContainerRunError(RuntimeError):
    """Raised when a container run fails (build error, timeout, etc.)."""


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------


@dataclass
class ContainerBackend:
    """Resolved container CLI (docker or podman)."""

    name: str  # "docker" or "podman"
    binary: str  # full path to the CLI

    def __str__(self) -> str:
        return self.name


def detect_backend() -> ContainerBackend | None:
    """Return the first available container backend, or None if neither is present."""
    for name in ("docker", "podman"):
        binary = shutil.which(name)
        if not binary:
            continue
        try:
            # Cheap liveness probe — `version` is read-only and daemon-independent
            # for podman rootless. For docker it requires the daemon, so this can
            # fail with a connection error — caught and treated as unavailable.
            res = subprocess.run(  # nosec B603
                [binary, "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
        if res.returncode != 0:
            continue
        return ContainerBackend(name=name, binary=binary)
    return None


# ---------------------------------------------------------------------------
# Reward file contract (Harbor-style)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RewardContract:
    """Standard Harbor reward shape: `reward.json` + `reward.txt`.

    Captured under `<logs_dir>/verifier/`. Spec §3.3 row "Wire format
    (rewards)" matches this exactly.
    """

    reward: float  # 0.0 .. 1.0
    details: dict[str, Any] = field(default_factory=dict)
    raw_json: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, path: Path) -> RewardContract:
        """Load from a Harbor-style `reward.json` file."""
        payload = json.loads(path.read_text(encoding="utf-8"))
        reward = float(payload.get("reward", payload.get("score", 0.0)))
        details = payload.get("details", {})
        if not isinstance(details, dict):
            details = {"value": details}
        return cls(reward=reward, details=details, raw_json=payload)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task reward record to a JSON-friendly dict."""
        return {
            "reward": self.reward,
            "details": dict(self.details),
        }


# ---------------------------------------------------------------------------
# Container runner
# ---------------------------------------------------------------------------


@dataclass
class ContainerRunResult:
    """Outcome of one container execution."""

    task_id: str
    backend: str  # "docker" / "podman" / "stub"
    exit_code: int
    duration_s: float
    reward: RewardContract | None
    ctrf_path: Path | None = None
    run_log_path: Path | None = None
    stdout: str = ""
    stderr: str = ""
    stub: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize the container-run result to a JSON-friendly dict."""
        return {
            "task_id": self.task_id,
            "backend": self.backend,
            "exit_code": self.exit_code,
            "duration_s": self.duration_s,
            "reward": self.reward.to_dict() if self.reward else None,
            "ctrf_path": str(self.ctrf_path) if self.ctrf_path else None,
            "run_log_path": str(self.run_log_path) if self.run_log_path else None,
            "stub": self.stub,
        }


class ContainerRunner:
    """Build + run + capture Harbor-style reward contracts.

    Usage:
        runner = ContainerRunner(workspace=Path("/tmp/pheno-bench-runs"))
        try:
            result = runner.run(task_id="ifeval-001", dockerfile=Path("./Dockerfile"))
        except ContainerNotAvailableError:
            ...  # downgrade to stub-mode at the caller
    """

    def __init__(
        self,
        workspace: Path | str | None = None,
        *,
        backend: ContainerBackend | None = None,
        image_tag_prefix: str = "pheno-bench",
        timeout_s: float = 600.0,
        network: str = "none",
    ) -> None:
        self.workspace = (
            Path(workspace)
            if workspace
            else Path.home() / ".cache" / "pheno-bench" / "runs"
        )
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.backend = backend if backend is not None else detect_backend()
        self.image_tag_prefix = image_tag_prefix
        self.timeout_s = float(timeout_s)
        self.network = network

    @property
    def is_available(self) -> bool:
        """True if a real container backend (docker/podman) is available."""
        return self.backend is not None

    def ensure_available(self) -> ContainerBackend:
        """Return the active backend or raise `ContainerNotAvailableError`."""
        if self.backend is None:
            raise ContainerNotAvailableError(
                "Neither docker nor podman is available; "
                "downgrade to stub-mode at the caller."
            )
        return self.backend

    # ------------------------------------------------------------------
    # Build / run a single task
    # ------------------------------------------------------------------

    def build(
        self, task_id: str, dockerfile: Path | str, context: Path | str | None = None
    ) -> str:
        """Build an image for `task_id` from `dockerfile`. Returns the image tag."""
        backend = self.ensure_available()
        df_path = Path(dockerfile)
        ctx_path = Path(context) if context else df_path.parent
        if not df_path.exists():
            raise ContainerRunError(f"Dockerfile not found: {df_path}")
        tag = f"{self.image_tag_prefix}:{task_id}-{uuid.uuid4().hex[:8]}"
        cmd = [backend.binary, "build", "-f", str(df_path), "-t", tag, str(ctx_path)]
        res = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout_s, check=False
        )  # nosec B603
        if res.returncode != 0:
            raise ContainerRunError(
                f"{backend.name} build failed (exit={res.returncode}): {res.stderr[:500]}"
            )
        return tag

    def run_task(
        self,
        task_id: str,
        *,
        image: str | None = None,
        dockerfile: Path | str | None = None,
        context: Path | str | None = None,
        env: dict[str, str] | None = None,
        command: list[str] | None = None,
        mounts: list[tuple[Path, str]] | None = None,
    ) -> ContainerRunResult:
        """Run one task in a container and capture the reward/CTRF/run.log trio.

        Either `image` (already built) or `dockerfile` (build on the fly) must
        be supplied. The container is expected to write:
          - <logs_dir>/verifier/reward.json (Harbor contract)
          - <logs_dir>/ctrf-report.jsonl (CTRF JSONL)
          - <logs_dir>/run.log
        """
        backend = self.ensure_available()
        run_id = uuid.uuid4().hex[:12]
        logs_dir = self.workspace / task_id / run_id
        logs_dir.mkdir(parents=True, exist_ok=True)

        if image is None:
            if dockerfile is None:
                raise ContainerRunError(
                    "Either `image` or `dockerfile` must be provided"
                )
            image = self.build(task_id, dockerfile, context)

        verifier_dir = logs_dir / "verifier"
        verifier_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            backend.binary,
            "run",
            "--rm",
            "--network",
            self.network,
            "-v",
            f"{verifier_dir}:/logs/verifier",
            "-v",
            f"{logs_dir}:/logs",
        ]
        for host, target in mounts or []:
            cmd.extend(["-v", f"{host}:{target}"])
        for k, v in (env or {}).items():
            cmd.extend(["-e", f"{k}={v}"])
        cmd.append(image)
        cmd.extend(command or ["/bin/sh", "-c", "echo 'no command provided' && exit 0"])

        start = time.time()
        try:
            proc = subprocess.run(  # nosec B603
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ContainerRunError(
                f"{backend.name} run timed out after {self.timeout_s}s for task {task_id}"
            ) from exc
        elapsed = time.time() - start

        # Capture run.log (stdout/stderr best-effort merge)
        run_log = logs_dir / "run.log"
        run_log.write_text(
            f"=== stdout ===\n{proc.stdout}\n=== stderr ===\n{proc.stderr}\n",
            encoding="utf-8",
        )

        # Capture CTRF JSONL if the container emitted one
        ctrf_path = logs_dir / "ctrf-report.jsonl"
        if not ctrf_path.exists():
            # Best-effort: emit a single CTRF row synthesised from the run exit code
            self._write_synthetic_ctrf(ctrf_path, task_id, proc.returncode)

        # Capture reward.json if present
        reward_path = verifier_dir / "reward.json"
        reward: RewardContract | None = None
        if reward_path.exists():
            try:
                reward = RewardContract.from_path(reward_path)
            except Exception:  # noqa: BLE001 - defensive
                reward = None
        else:
            # Best-effort: derive a binary reward from exit code
            reward = RewardContract(
                reward=1.0 if proc.returncode == 0 else 0.0,
                details={"exit_code": proc.returncode, "synthetic": True},
            )
            reward_path.write_text(
                json.dumps(reward.to_dict(), indent=2), encoding="utf-8"
            )

        return ContainerRunResult(  # type: ignore[call-arg]
            task_id=task_id,
            backend=backend.name,
            exit_code=proc.returncode,
            wall_clock_s=elapsed,
            reward=reward,
            ctrf_path=ctrf_path if ctrf_path.exists() else None,
            run_log_path=run_log if run_log.exists() else None,
            stdout=proc.stdout,
            stderr=proc.stderr,
            stub=False,
        )

    # ------------------------------------------------------------------
    # Stub-mode (no Docker available) — return a synthetic reward
    # ------------------------------------------------------------------

    def stub_run(
        self, task_id: str, *, pass_probability: float = 0.5
    ) -> ContainerRunResult:
        """Return a synthetic `ContainerRunResult` when Docker isn't available.

        `pass_probability` is consulted so test suites can pin the outcome.
        """
        import random as _random

        reward_value = 1.0 if _random.random() < pass_probability else 0.0  # nosec B311
        logs_dir = self.workspace / task_id / "stub"
        logs_dir.mkdir(parents=True, exist_ok=True)
        reward_path = logs_dir / "verifier" / "reward.json"
        reward_path.parent.mkdir(parents=True, exist_ok=True)
        reward_path.write_text(
            json.dumps({"reward": reward_value, "details": {"stub": True}}),
            encoding="utf-8",
        )
        run_log = logs_dir / "run.log"
        run_log.write_text(
            f"[stub-mode] container runner unavailable; task={task_id} reward={reward_value}\n",
            encoding="utf-8",
        )
        ctrf_path = logs_dir / "ctrf-report.jsonl"
        self._write_synthetic_ctrf(
            ctrf_path, task_id, 0 if reward_value == 1.0 else 1, stub=True
        )
        return ContainerRunResult(  # type: ignore[call-arg]
            task_id=task_id,
            backend="stub",
            exit_code=0 if reward_value == 1.0 else 1,
            wall_clock_s=0.0,
            reward=RewardContract(
                reward=reward_value,
                details={"stub": True},
            ),
            ctrf_path=ctrf_path,
            run_log_path=run_log,
            stub=True,
        )

    @staticmethod
    def _write_synthetic_ctrf(
        path: Path, task_id: str, exit_code: int, stub: bool = False
    ) -> None:
        """Emit a minimal CTRF JSONL row for a single task."""
        record = {
            "source_format": "ctrf",
            "results": [
                {
                    "name": task_id,
                    "status": "passed" if exit_code == 0 else "failed",
                    "duration": 0,
                    "message": "synthetic" if stub else "container exit code mapping",
                    "trace": "",
                }
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Convenience: a single-shot run-or-stub helper used by every SWE suite
# ---------------------------------------------------------------------------


def run_or_stub(
    runner: ContainerRunner,
    task_id: str,
    *,
    dockerfile: Path | str | None = None,
    image: str | None = None,
) -> ContainerRunResult:
    """Run a container task if Docker is available, else return a stub result."""
    if not runner.is_available:
        return runner.stub_run(task_id)
    try:
        return runner.run_task(task_id, image=image, dockerfile=dockerfile)
    except ContainerNotAvailableError:
        return runner.stub_run(task_id)


__all__ = [
    "ContainerBackend",
    "ContainerNotAvailableError",
    "ContainerRunError",
    "ContainerRunResult",
    "ContainerRunner",
    "RewardContract",
    "detect_backend",
    "run_or_stub",
]
