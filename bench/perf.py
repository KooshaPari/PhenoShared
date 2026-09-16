"""Perf (RSS / GPU mem / tokens-per-sec) measurement for the runner.

Implements spec rule §4:

* `peak_RSS_MB` from `resource.getrusage(RUSAGE_SELF).ru_maxrss`
  (Linux: KB; macOS: bytes — we coerce to MB).
* `peak_GPU_mem_MB` via:

  - macOS: `torch.mps.driver_allocated_memory()` (PyTorch ≥ 2.0 Metal) when
    PyTorch is importable; otherwise `0.0` (CUDA Metal memory probe absent).
  - linux/win: `nvidia-smi --query-gpu=memory.used` parsed to MB.

* `tokens_per_sec_throughput` = `sum(completion_tokens) / total_wall_clock_s`.

All helpers are thread-safe (no shared mutable state) so the asyncio worker
loop can call them concurrently from `run_sync()` workers.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass, field

_RUSAGE_KEY = "ru_maxrss"


def _read_max_rss() -> int:
    """Return raw `ru_maxrss` from the current process.

    Returns 0 on hosts where the `resource` module does not expose
    `getrusage` / `RUSAGE_SELF` (e.g., Windows builds of CPython).
    """
    try:
        import resource
    except ImportError:  # pragma: no cover - Windows
        return 0

    rusage_fn = getattr(resource, "getrusage", None)
    rusage_self = getattr(resource, "RUSAGE_SELF", 0)
    if rusage_fn is None or rusage_self == 0:
        return 0
    usage = rusage_fn(rusage_self)
    return int(getattr(usage, _RUSAGE_KEY, 0) or 0)


def peak_rss_mb() -> float:
    """Peak RSS in MB.

    macOS `getrusage` reports bytes; Linux reports KB. We auto-coerce via
    `sys.platform` to keep the helper cross-platform.
    """
    raw = _read_max_rss()
    if raw <= 0:
        return 0.0
    if sys.platform == "darwin":
        mb = raw / (1024.0 * 1024.0)
    else:
        mb = raw / 1024.0
    return float(mb)


def nvidia_smi_mem_mb(gpu_index: int = 0) -> float:
    """Query `nvidia-smi` for current `memory.used` of `gpu_index` in MB.

    Returns `0.0` when nvidia-smi is unavailable or the GPU is unsupported.
    """
    if not shutil.which("nvidia-smi"):
        return 0.0
    try:
        out = subprocess.check_output(  # nosec B603 B607
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
                "-i",
                str(gpu_index),
            ],
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
    except Exception:
        return 0.0
    try:
        value_mib = float(out.decode("utf-8", "replace").strip())
    except ValueError:
        return 0.0
    return value_mib


def macos_metal_mem_mb() -> float:
    """Peak Metal GPU memory in MB (Apple Silicon).

    Implemented by spawning a *fresh* Python subprocess that imports torch and
    probes `torch.mps.driver_allocated_memory()`. The subprocess is required
    because importing torch in-process can trigger fatal aborts or hangs on
    some hosts (libomp clashes, broken wheel) — running it isolated lets us
    always recover with `0.0` rather than crash the harness.

    The probe script is intentionally tiny so subprocess startup dominates.
    Set ``BENCH_DISABLE_METAL_PROBE=1`` to bypass entirely (e.g. in CI hosts
    where torch import is known to hang or abort).
    """
    if sys.platform != "darwin":
        return 0.0
    if os.environ.get("BENCH_DISABLE_METAL_PROBE"):
        return 0.0
    script = (
        "import sys\n"
        "try:\n"
        "    import torch\n"
        "    mps = getattr(torch.backends, 'mps', None)\n"
        "    if mps is None or not mps.is_available():\n"
        "        print(0.0); sys.exit(0)\n"
        "    alloc = torch.mps.driver_allocated_memory()\n"
        "    print(float(alloc) / (1024.0 * 1024.0))\n"
        "except Exception:\n"
        "    print(0.0)\n"
    )
    try:
        proc = subprocess.Popen(  # nosec B603
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"PATH": os.environ.get("PATH", "")},
            start_new_session=True,
        )
    except (OSError, ValueError):
        return 0.0
    try:
        stdout, _ = proc.communicate(timeout=1.5)
    except subprocess.TimeoutExpired:
        # Kill the entire process group so torch import cannot wedge us.
        try:
            import signal  # local import: Windows lacks os.killpg

            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            with contextlib.suppress(Exception):
                proc.kill()
        with contextlib.suppress(Exception):
            proc.wait(timeout=1.0)
        return 0.0
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill()
        return 0.0
    if proc.returncode != 0:
        return 0.0
    out = (stdout or b"").decode("utf-8", "replace").strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def peak_gpu_mem_mb(*, gpu_index: int = 0) -> float:
    """Return peak GPU memory in MB; auto-detects source.

    Order:

    1. macOS Metal (subprocess probe).
    2. nvidia-smi (in-process `subprocess.check_output`).
    """
    if sys.platform == "darwin":
        mb = macos_metal_mem_mb()
        if mb > 0:
            return mb
    return nvidia_smi_mem_mb(gpu_index=gpu_index)


@dataclass
class PerfReading:
    """Per-task perf reading."""

    task_id: str
    peak_rss_mb: float
    peak_gpu_mem_mb: float
    prompt_tokens: int
    completion_tokens: int
    duration_s: float

    @property
    def tokens_per_sec(self) -> float:
        """Throughput in completion-tokens/sec."""
        if self.duration_s <= 0:
            return 0.0
        return float(self.completion_tokens) / float(self.duration_s)

    @property
    def total_tokens(self) -> int:
        """Prompt + completion tokens."""
        return int(self.prompt_tokens) + int(self.completion_tokens)

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "task_id": self.task_id,
            "peak_rss_mb": self.peak_rss_mb,
            "peak_gpu_mem_mb": self.peak_gpu_mem_mb,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "duration_s": self.duration_s,
            "tokens_per_sec": self.tokens_per_sec,
            "total_tokens": self.total_tokens,
        }


@dataclass
class PerfSnapshot:
    """Whole-run perf aggregate."""

    peak_rss_mb: float
    peak_gpu_mem_mb: float
    total_prompt_tokens: int
    total_completion_tokens: int
    wall_clock_s: float
    throughput_tok_per_s: float
    readings: list[PerfReading] = field(default_factory=list)

    def to_dict(self) -> dict[str, float | int | list[dict[str, float | int | str]]]:
        return {
            "peak_rss_mb": self.peak_rss_mb,
            "peak_gpu_mem_mb": self.peak_gpu_mem_mb,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "wall_clock_s": self.wall_clock_s,
            "throughput_tok_per_s": self.throughput_tok_per_s,
            "readings": [r.to_dict() for r in self.readings],
        }


def measure_task(
    task_id: str,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    duration_s: float,
    gpu_index: int = 0,
) -> PerfReading:
    """Snapshot one task's perf. Returns `PerfReading` with derived throughput."""
    return PerfReading(
        task_id=task_id,
        peak_rss_mb=peak_rss_mb(),
        peak_gpu_mem_mb=peak_gpu_mem_mb(gpu_index=gpu_index),
        prompt_tokens=int(prompt_tokens),
        completion_tokens=int(completion_tokens),
        duration_s=float(duration_s),
    )


def aggregate(readings: list[PerfReading], *, wall_clock_s: float) -> PerfSnapshot:
    """Aggregate a list of per-task readings into a run-level snapshot."""
    total_pt = sum(int(r.prompt_tokens) for r in readings)
    total_ct = sum(int(r.completion_tokens) for r in readings)
    peak_rss = max((r.peak_rss_mb for r in readings), default=0.0)
    peak_gpu = max((r.peak_gpu_mem_mb for r in readings), default=0.0)
    tps = (total_ct / wall_clock_s) if wall_clock_s > 0 else 0.0
    return PerfSnapshot(
        peak_rss_mb=peak_rss,
        peak_gpu_mem_mb=peak_gpu,
        total_prompt_tokens=total_pt,
        total_completion_tokens=total_ct,
        wall_clock_s=float(wall_clock_s),
        throughput_tok_per_s=float(tps),
        readings=list(readings),
    )


# Convenience helper used by `executor.py` for direct timing.
class TimedSection:
    """Context manager that records wall-clock duration and resource peaks."""

    def __init__(self, *, task_id: str, gpu_index: int = 0) -> None:
        self.task_id = task_id
        self.gpu_index = gpu_index
        self.duration_s: float = 0.0
        self._t0: float = 0.0

    def __enter__(self) -> TimedSection:
        self._t0 = time.monotonic()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        self.duration_s = time.monotonic() - self._t0

    def to_reading(
        self, *, prompt_tokens: int = 0, completion_tokens: int = 0
    ) -> PerfReading:
        """Build a PerfReading from this section after the section closes."""
        return measure_task(
            self.task_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_s=self.duration_s,
            gpu_index=self.gpu_index,
        )
