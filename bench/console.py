"""Console / progress output for the runner (spec §Q4 cross-references).

Degrades gracefully when `rich` is not installed (production environments
sometimes strip optional deps). Public surface:

* `Console` — a thin wrapper around either a `rich.console.Console` or a
  `print()`-backed fallback. Both expose `status()`, `info()`, `warn()`,
  `error()`, `progress()` and `rule()`.
* `ProgressBar` — a with-block-able progress context manager; in rich mode
  it shows a per-task bar with elapsed/remaining; otherwise it just logs
  every N items.

The module is intentionally side-effect free outside the main thread: any
TUI refresh happens inside a background thread that the harness owns.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

try:
    from rich.console import Console as _RichConsole
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )

    _HAS_RICH = True
except Exception:  # pragma: no cover - exercised when rich missing
    _HAS_RICH = False


class Console:
    """Lightweight console abstraction with rich-degradation."""

    def __init__(self, *, force_plain: bool = False, file: Any = None) -> None:
        self._force_plain = force_plain
        self._file = file or sys.stdout
        self._owns_rich = _HAS_RICH and not force_plain
        self._inner: Any = None
        if self._owns_rich:
            self._inner = _RichConsole(
                file=self._file, force_terminal=False, safe_box=True
            )

    @property
    def has_rich(self) -> bool:
        """Return True if the console owns a live Rich instance (else plain text)."""
        return self._owns_rich

    # -- text output --------------------------------------------------

    def info(self, message: str, *, end: str = "\n") -> None:
        """Print an info-level message (cyan in rich mode)."""
        self._emit("info", message, color="cyan", end=end)

    def warn(self, message: str, *, end: str = "\n") -> None:
        """Print a warning-level message (yellow in rich mode)."""
        self._emit("warn", message, color="yellow", end=end)

    def error(self, message: str, *, end: str = "\n") -> None:
        """Print an error-level message (red in rich mode)."""
        self._emit("error", message, color="red", end=end)

    def success(self, message: str, *, end: str = "\n") -> None:
        """Print a success-level message (green in rich mode)."""
        self._emit("success", message, color="green", end=end)

    def rule(self, title: str = "") -> None:
        """Print a horizontal rule with the given title (or a plain line in plain mode)."""
        if self._owns_rich:
            self._inner.rule(title)
            return
        bar = "─" * max(8, len(title) + 4)
        print(f"{bar} {title} {bar}", file=self._file)

    def status(self, message: str) -> _StatusContext:
        """Context-manager 'spinner' output (degrades to a print + flush)."""
        if self._owns_rich:
            return _RichStatusContext(self._inner, message)
        return _PlainStatusContext(self._file, message)

    def _emit(
        self, level: str, message: str, *, color: str = "white", end: str = "\n"
    ) -> None:
        if self._owns_rich:
            style = {
                "info": "cyan",
                "warn": "yellow",
                "error": "bold red",
                "success": "bold green",
            }.get(level, color)
            self._inner.print(f"[{style}]{message}[/{style}]")
            return
        prefix = {"info": "[i]", "warn": "[!]", "error": "[x]", "success": "[+]"}.get(
            level, "[*]"
        )
        try:
            self._file.write(f"{prefix} {message}")
            if end:
                self._file.write(end)
            self._file.flush()
        except Exception:  # nosec B110
            pass

    # -- progress -----------------------------------------------------

    @contextmanager
    def progress(
        self, total: int, *, description: str = "tasks"
    ) -> Iterator[ProgressBar]:
        """Yield a ``ProgressBar`` context manager for the given total."""
        bar = ProgressBar(total=total, description=description, console=self)
        try:
            with bar:
                yield bar
        finally:
            pass


# ---------------------------------------------------------------------------
# Status context-manager backends
# ---------------------------------------------------------------------------


class _StatusContext:
    """Abstract base class for the spinner's ``with`` block."""

    def __enter__(self) -> _StatusContext:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        pass


class _RichStatusContext(_StatusContext):
    def __init__(self, inner: Any, message: str) -> None:
        self._inner = inner
        self._status: Any = None
        self._message = message

    def __enter__(self) -> _RichStatusContext:
        self._status = self._inner.status(self._message)
        self._status.__enter__()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        if self._status is not None:
            self._status.__exit__(exc_type, exc, tb)


class _PlainStatusContext(_StatusContext):
    def __init__(self, file: Any, message: str) -> None:
        self._file = file
        self._message = message
        self._t0 = 0.0

    def __enter__(self) -> _PlainStatusContext:
        self._t0 = time.monotonic()
        try:
            self._file.write(f"[~] {self._message}")
            self._file.flush()
        except Exception:  # nosec B110
            pass
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        try:
            dt = time.monotonic() - self._t0
            self._file.write(f" done in {dt:.2f}s\n")
            self._file.flush()
        except Exception:  # nosec B110
            pass


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------


class ProgressBar:
    """Per-task progress context manager (rich when available, else heartbeat)."""

    def __init__(
        self, *, total: int, description: str = "tasks", console: Console | None = None
    ) -> None:
        """Construct a progress bar with the given total and optional console."""
        self.total = max(0, int(total))
        self.description = description
        self._console = console
        self._progress: Any = None
        self._task_id: Any = None
        self._completed = 0
        self._t0 = 0.0
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop = threading.Event()

    def __enter__(self) -> ProgressBar:
        """Start the progress display (rich bar or heartbeat thread)."""
        self._t0 = time.monotonic()
        if self._console is not None and self._console.has_rich:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn(f"[progress.description]{self.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                TextColumn("eta"),
                TimeRemainingColumn(),
                console=self._console._inner,
                transient=False,
            )
            self._progress.__enter__()
            self._task_id = self._progress.add_task(self.description, total=self.total)
            return self
        # Plain mode: start heartbeat.
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat, daemon=True)
        self._heartbeat_thread.start()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None:
        """Stop the progress display; join the heartbeat thread if any."""
        if self._progress is not None:
            try:
                self._progress.__exit__(exc_type, exc, tb)
            except Exception:  # nosec B110
                pass
        self._heartbeat_stop.set()
        if self._heartbeat_thread is not None:
            try:
                self._heartbeat_thread.join(timeout=1.0)
            except Exception:  # nosec B110
                pass

    def advance(self, step: int = 1) -> None:
        """Increment the bar by `step` completed items."""
        self._completed += int(step)
        if self._progress is not None and self._task_id is not None:
            try:
                self._progress.advance(self._task_id, step)
            except Exception:  # nosec B110
                pass

    def update(self, completed: int | None = None, total: int | None = None) -> None:
        """Update the bar to an explicit completed count / total."""
        if completed is not None:
            delta = completed - self._completed
            if delta > 0:
                self.advance(delta)
            self._completed = completed
        if self._progress is not None:
            try:
                kw: dict[str, Any] = {}
                if total is not None:
                    kw["total"] = total
                if self._task_id is not None:
                    self._progress.update(self._task_id, completed=completed, **kw)
            except Exception:  # nosec B110
                pass

    def _heartbeat(self) -> None:
        # Print progress every 5s in plain mode.
        while not self._heartbeat_stop.wait(5.0):
            try:
                if self.total <= 0:
                    pct = 100.0
                else:
                    pct = min(100.0, self._completed * 100.0 / self.total)
                sys.stderr.write(
                    f"[{self.description}] {self._completed}/{self.total} ({pct:.1f}%)\n"
                )
                sys.stderr.flush()
            except Exception:  # nosec B110
                pass


# ---------------------------------------------------------------------------
# Auto fallback
# ---------------------------------------------------------------------------


_NO_COLOR = os.environ.get("NO_COLOR") is not None


def make_console(*, force_plain: bool | None = None) -> Console:
    """Build a Console honoring `NO_COLOR` and the `force_plain` flag."""
    if force_plain is None:
        force_plain = _NO_COLOR or not sys.stdout.isatty()
    return Console(force_plain=bool(force_plain))


__all__ = ["Console", "ProgressBar", "make_console"]
