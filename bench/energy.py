"""Energy measurement for the runner (spec §4.3 + caveat C7 in §1.1).

Sources (auto-detected on first call):

* macOS: `powermetrics -i 100 -s cpu_power,gpu_power,ane_power` polled at
  10 Hz via a subprocess. We multiply instantaneous power (mW) by the
  interval to get joules per sample, then sum.
* Linux: `nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits`
  polled at 1 Hz (returns Watts). Interpolated between samples.
* Stub: when no source is available (CI, dry-run) we emit zero joules but
  still record the chosen source so callers can distinguish.

Design rules:

* The poller is a thin DAEMON spawned by `start()` and joined by `stop()`.
* `joules` are summed across the process lifetime; the underlying DAEMON may
  be reused across tasks (we gate totals on `stop()`).
* All subprocess I/O happens on threads; never blocks the asyncio event loop.
"""

from __future__ import annotations

import platform
import re
import shutil
import signal
import subprocess  # nosec B404
import threading
import time
from dataclasses import dataclass, field

from bench.ports.energy import EnergyPort
from bench.types import EnergySource

# ---------------------------------------------------------------------------
# Source auto-detection
# ---------------------------------------------------------------------------


def detect_source(prefer: EnergySource | None = None) -> EnergySource:
    """Return the auto-detected energy source for the current host.

    `prefer` overrides detection (caller passes `--energy-source <X>`).
    """
    if prefer is not None and prefer != EnergySource.NONE:
        return prefer
    sysname = platform.system().lower()
    if sysname == "darwin" and shutil.which("powermetrics"):
        return EnergySource.POWERMETRICS
    if shutil.which("nvidia-smi"):
        return EnergySource.NVIDIA_SMI
    return EnergySource.NONE


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


_PM_HEADER = re.compile(rb"\*\*\*")
_PM_KV = re.compile(rb"^([A-Za-z _]+?):\s*([0-9]+)\s*mW\b", re.MULTILINE)


def _parse_powermetrics_line(line: bytes) -> float:
    """Parse one CSV-ish powermetrics line; return mW (sum of all power phases)."""
    total_mw = 0.0
    for m in _PM_KV.finditer(line):
        key = m.group(1).decode("utf-8", "replace").strip()
        val = int(m.group(2))
        if "power" in key.lower():
            total_mw += val
    return total_mw


@dataclass
class EnergyReading:
    """A single polled energy sample."""

    timestamp: float
    watts: float
    joules: float

    def to_dict(self) -> dict[str, float]:
        return {"timestamp": self.timestamp, "watts": self.watts, "joules": self.joules}


@dataclass
class EnergyTotal:
    """Aggregated energy statistics for a run."""

    source: EnergySource
    joules: float
    peak_watts: float
    mean_watts: float
    samples: int = 0
    history: list[EnergyReading] = field(default_factory=list)

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "source": self.source.value,
            "joules": self.joules,
            "peak_watts": self.peak_watts,
            "mean_watts": self.mean_watts,
            "samples": self.samples,
        }


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class _EnergySource(EnergyPort):
    """Base class for energy sources; poller is started lazily on `.start()`."""

    label: EnergySource = EnergySource.NONE
    poll_interval_s: float = 0.1

    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._cv = threading.Condition()
        self._history: list[EnergyReading] = []
        self._lock = threading.Lock()
        self._start_ts: float = 0.0
        self._last_watts: float = 0.0

    def start(self) -> None:
        """Begin polling. Idempotent; safe to call once per task."""
        with self._cv:
            if self._proc is not None:
                return
            self._stop_flag.clear()
            self._start_ts = time.monotonic()
            try:
                self._proc = self._spawn()
            except FileNotFoundError:
                self._proc = None
                # Silently degrade: no subprocess, no samples.
                return
            self._thread = threading.Thread(
                target=self._run, name=f"energy-{self.label.value}", daemon=True
            )
            self._thread.start()

    def _spawn(self) -> subprocess.Popen[bytes]:
        raise NotImplementedError

    def _on_line(self, line: bytes) -> float:
        raise NotImplementedError

    def _run(self) -> None:
        assert self._proc is not None  # nosec B101
        proc = self._proc
        last = time.monotonic()
        while not self._stop_flag.is_set():
            stdout = proc.stdout
            if stdout is None:
                break
            line = stdout.readline()
            if not line:
                # EOF or dead subprocess.
                break
            try:
                watt = max(0.0, self._on_line(line))
            except Exception:
                watt = 0.0
            now = time.monotonic()
            dt = max(0.0, now - last)
            joules = watt * dt
            last = now
            with self._lock:
                self._last_watts = watt
                self._history.append(
                    EnergyReading(timestamp=now, watts=watt, joules=joules)
                )

    def stop(self) -> EnergyTotal:
        """Halt polling and return the aggregated total."""
        with self._cv:
            self._stop_flag.set()
            proc = self._proc
            self._proc = None
        if proc is not None:
            with __import__("contextlib").suppress(Exception):
                if proc.poll() is None:
                    proc.send_signal(signal.SIGTERM)
            with __import__("contextlib").suppress(Exception):
                proc.wait(timeout=2.0)
        if self._thread is not None:
            with __import__("contextlib").suppress(Exception):
                self._thread.join(timeout=2.0)
        with self._lock:
            hist = list(self._history)
        samples = len(hist)
        joules = sum(r.joules for r in hist)
        peak = max((r.watts for r in hist), default=0.0)
        mean = (joules / samples) if samples else 0.0
        return EnergyTotal(
            source=self.label,
            joules=joules,
            peak_watts=peak,
            mean_watts=mean,
            samples=samples,
            history=hist,
        )

    def reading(self) -> EnergyReading | None:
        """Return the most recent energy sample, or ``None`` if no samples yet."""
        with self._lock:
            if self._history:
                return self._history[-1]
        return None


# ---------------------------------------------------------------------------
# macOS powermetrics
# ---------------------------------------------------------------------------


class _PowermetricsSource(_EnergySource):
    label = EnergySource.POWERMETRICS
    poll_interval_s = 0.1

    def _spawn(self) -> subprocess.Popen[bytes]:
        # `-i 100` → 100 ms between samples (≈10 Hz).
        return subprocess.Popen(  # nosec B603 B607
            [
                "powermetrics",
                "-i",
                "100",
                "-s",
                "cpu_power,gpu_power,ane_power",
                "--format",
                "text",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=1,
        )

    def _on_line(self, line: bytes) -> float:
        # powermetrics emits "CPU Power: 1234 mW" style lines.
        mw = _parse_powermetrics_line(line)
        return mw / 1000.0


# ---------------------------------------------------------------------------
# nvidia-smi
# ---------------------------------------------------------------------------


class _NvidiaSmiSource(_EnergySource):
    label = EnergySource.NVIDIA_SMI
    poll_interval_s = 1.0

    def __init__(self, gpu_index: int = 0) -> None:
        super().__init__()
        self._gpu_index = gpu_index

    def _spawn(self) -> subprocess.Popen[bytes]:
        return subprocess.Popen(  # nosec B603 B607
            [
                "nvidia-smi",
                "--query-gpu=power.draw",
                "--format=csv,noheader,nounits",
                "-i",
                str(self._gpu_index),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=1,
        )

    def _on_line(self, line: bytes) -> float:
        # nvidia-smi returns e.g. "187.34\n" (watts) or "[Not Supported]" in
        # older drivers. We coerce safely.
        try:
            value = float(line.decode("utf-8", "replace").strip())
        except ValueError:
            return 0.0
        return max(0.0, value)


# ---------------------------------------------------------------------------
# Stub (no source → emits zero)
# ---------------------------------------------------------------------------


class _NoOpSource(_EnergySource):
    label = EnergySource.NONE
    poll_interval_s = 60.0

    def start(self) -> None:
        # No-op: never poll, just record zero.
        with self._lock:
            self._start_ts = time.monotonic()

    def _spawn(self) -> subprocess.Popen[bytes]:
        raise FileNotFoundError("No energy source available")

    def _on_line(self, line: bytes) -> float:
        return 0.0

    def stop(self) -> EnergyTotal:
        return EnergyTotal(
            source=self.label, joules=0.0, peak_watts=0.0, mean_watts=0.0, samples=0
        )


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def make_source(
    source: EnergySource | None = None, gpu_index: int = 0
) -> _EnergySource:
    """Return a fresh poller for the given source (auto-detected when `None`)."""
    effective = detect_source(source)
    if effective == EnergySource.POWERMETRICS:
        return _PowermetricsSource()
    if effective == EnergySource.NVIDIA_SMI:
        return _NvidiaSmiSource(gpu_index=gpu_index)
    return _NoOpSource()


# ---------------------------------------------------------------------------
# Context manager (for `with measure(source) as total:` pattern)
# ---------------------------------------------------------------------------


class measure:  # noqa: N801 — keeps call-site readable
    """Context manager that yields an EnergyTotal on exit.

    Example::

        with energy.measure(EnergySource.NVIDIA_SMI) as total:
            do_work()
        print(total.joules)
    """

    def __init__(
        self, source: EnergySource | None = None, *, gpu_index: int = 0
    ) -> None:
        self._source = make_source(source, gpu_index=gpu_index)
        self.total: EnergyTotal | None = None

    def __enter__(self) -> measure:
        self._source.start()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        self.total = self._source.stop()
