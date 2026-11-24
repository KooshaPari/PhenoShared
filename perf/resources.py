"""Portable process, system, and NVIDIA GPU resource sampling.

``psutil`` is optional. NVIDIA telemetry uses ``nvidia-smi`` when available,
keeping this module usable without a Python NVML dependency.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - host dependent
    psutil = None


@dataclass(frozen=True)
class GpuSample:
    """One GPU's telemetry at a sampling instant."""

    index: int
    utilization_percent: float | None = None
    memory_used_mib: float | None = None
    memory_total_mib: float | None = None
    power_watts: float | None = None


@dataclass(frozen=True)
class ResourceSample:
    """Resource values observed at one monotonic timestamp."""

    timestamp: float
    process_cpu_percent: float | None = None
    process_rss_bytes: int | None = None
    system_cpu_percent: float | None = None
    system_ram_used_bytes: int | None = None
    system_ram_percent: float | None = None
    gpus: tuple[GpuSample, ...] = field(default_factory=tuple)


def _number(value: str) -> float | None:
    value = value.strip()
    if not value or value.lower() in {"n/a", "na", "[not supported]"}:
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _stats(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "peak": None}
    return {"mean": sum(values) / len(values), "peak": max(values)}


class ResourceSampler:
    """Sample host and NVIDIA resources on a background thread."""

    def __init__(
        self,
        interval: float = 1.0,
        pid: int | None = None,
        include_gpu: bool = True,
        nvidia_smi: str | None = None,
        command_timeout: float = 2.0,
    ) -> None:
        if interval <= 0:
            raise ValueError("interval must be greater than zero")
        if command_timeout <= 0:
            raise ValueError("command_timeout must be greater than zero")
        self.interval = float(interval)
        self.pid = os.getpid() if pid is None else int(pid)
        self.include_gpu = bool(include_gpu)
        self.command_timeout = float(command_timeout)
        self._nvidia_smi = self._resolve_nvidia_smi(nvidia_smi)
        self._samples: list[ResourceSample] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._process: Any = None
        if psutil is not None:
            try:
                self._process = psutil.Process(self.pid)
            except (psutil.Error, OSError, ValueError):
                self._process = None

    @staticmethod
    def _resolve_nvidia_smi(value: str | None) -> str | None:
        if value:
            return value
        return shutil.which("nvidia-smi")

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def gpu_available(self) -> bool:
        return self.include_gpu and self._nvidia_smi is not None

    @property
    def samples(self) -> tuple[ResourceSample, ...]:
        with self._lock:
            return tuple(self._samples)

    def start(self) -> ResourceSampler:
        """Start sampling and return this sampler."""
        if self.running:
            return self
        self._stop_event.clear()
        if self._process is not None:
            try:
                self._process.cpu_percent(interval=None)
            except (psutil.Error, OSError):
                self._process = None
        if psutil is not None:
            psutil.cpu_percent(interval=None)
        self._thread = threading.Thread(
            target=self._run,
            name=f"resource-sampler-{self.pid}",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self, timeout: float | None = None) -> Mapping[str, Any]:
        """Stop sampling, wait for the worker, and return its summary."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)
        return self.summary()

    def __enter__(self) -> ResourceSampler:
        return self.start()

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.stop()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.collect()
            self._stop_event.wait(self.interval)

    def collect(self) -> ResourceSample:
        """Collect and retain one sample synchronously."""
        process_cpu: float | None = None
        process_rss: int | None = None
        system_cpu: float | None = None
        system_ram_used: int | None = None
        system_ram_percent: float | None = None
        if self._process is not None:
            try:
                process_cpu = float(self._process.cpu_percent(interval=None))
                process_rss = int(self._process.memory_info().rss)
            except (psutil.Error, OSError):
                self._process = None
        if psutil is not None:
            try:
                system_cpu = float(psutil.cpu_percent(interval=None))
                ram = psutil.virtual_memory()
                system_ram_used = int(ram.used)
                system_ram_percent = float(ram.percent)
            except (psutil.Error, OSError):
                pass
        sample = ResourceSample(
            timestamp=time.monotonic(),
            process_cpu_percent=process_cpu,
            process_rss_bytes=process_rss,
            system_cpu_percent=system_cpu,
            system_ram_used_bytes=system_ram_used,
            system_ram_percent=system_ram_percent,
            gpus=self._sample_gpus(),
        )
        with self._lock:
            self._samples.append(sample)
        return sample

    def _sample_gpus(self) -> tuple[GpuSample, ...]:
        if not self.gpu_available:
            return ()
        command = [
            self._nvidia_smi,
            "--query-gpu=index,utilization.gpu,memory.used,memory.total,power.draw",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(
                command,  # type: ignore[arg-type]
                capture_output=True,
                text=True,
                timeout=self.command_timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return ()
        if result.returncode != 0:
            return ()
        samples: list[GpuSample] = []
        for line in result.stdout.splitlines():
            columns = [column.strip() for column in line.split(",")]
            if len(columns) != 5:
                continue
            index = _number(columns[0])
            if index is None:
                continue
            samples.append(
                GpuSample(
                    index=int(index),
                    utilization_percent=_number(columns[1]),
                    memory_used_mib=_number(columns[2]),
                    memory_total_mib=_number(columns[3]),
                    power_watts=_number(columns[4]),
                )
            )
        return tuple(samples)

    def summary(self) -> dict[str, Any]:
        """Return sample count plus mean and peak values for each metric."""
        samples = self.samples

        def values(name: str) -> list[float]:
            return [
                float(value)
                for sample in samples
                if (value := getattr(sample, name)) is not None
            ]

        gpu_indexes = sorted({gpu.index for sample in samples for gpu in sample.gpus})
        gpu_summary: dict[str, dict[str, dict[str, float | None]]] = {}
        for index in gpu_indexes:
            gpu_summary[str(index)] = {}
            for name in (
                "utilization_percent",
                "memory_used_mib",
                "memory_total_mib",
                "power_watts",
            ):
                gpu_values = [
                    float(value)
                    for sample in samples
                    for gpu in sample.gpus
                    if gpu.index == index and (value := getattr(gpu, name)) is not None
                ]
                gpu_summary[str(index)][name] = _stats(gpu_values)
        return {
            "sample_count": len(samples),
            "process_cpu_percent": _stats(values("process_cpu_percent")),
            "process_rss_bytes": _stats(values("process_rss_bytes")),
            "system_cpu_percent": _stats(values("system_cpu_percent")),
            "system_ram_used_bytes": _stats(values("system_ram_used_bytes")),
            "system_ram_percent": _stats(values("system_ram_percent")),
            "gpus": gpu_summary,
        }

    def measure_collect_overhead(self, iterations: int = 3) -> dict[str, float | None]:
        """Measure synchronous probe cost in isolation, in milliseconds.

        This is instrumentation cost, not inference cost. It is intentionally
        reported separately so short-request results are not misinterpreted.
        """
        if iterations < 1:
            raise ValueError("iterations must be at least 1")
        samples = []
        for _ in range(iterations):
            started = time.perf_counter()
            self.collect()
            samples.append((time.perf_counter() - started) * 1000.0)
        return {"mean_ms": sum(samples) / len(samples), "max_ms": max(samples)}

    def as_dicts(self) -> list[dict[str, Any]]:
        """Return JSON-serializable copies of retained samples."""
        return [asdict(sample) for sample in self.samples]


__all__ = ["GpuSample", "ResourceSample", "ResourceSampler"]
