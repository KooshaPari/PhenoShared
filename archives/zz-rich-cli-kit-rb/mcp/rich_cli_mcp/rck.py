"""Thin subprocess wrapper around the `rck` binary.

Agents call this via FastMCP tools; we shell out to the Rust CLI so that the
actual kitty-graphics escape sequences are emitted by a single source of truth.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


class RckUnavailable(RuntimeError):
    """Raised when the `rck` binary cannot be located."""


def _is_runnable(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    if os.name == "nt":
        return True
    return os.access(path, os.X_OK)


def _candidate_paths(base: str) -> list[str]:
    if os.name == "nt" and not base.lower().endswith(".exe"):
        return [base, f"{base}.exe"]
    return [base]


@dataclass
class Capabilities:
    graphics: bool
    sixel: bool
    truecolor: bool
    unicode_width: int
    terminal: str
    is_tty: bool
    hyperlinks: bool = False
    clipboard: bool = False
    task_markers: bool = False
    kitty_keyboard: bool = False
    in_tmux: bool = False

    @classmethod
    def plain(cls) -> "Capabilities":
        return cls(False, False, False, 1, "unknown", False)


def find_rck() -> str:
    """Locate the `rck` binary.

    Resolution order: `RCK_BIN` env → `rck` on PATH → debug build in repo.
    """
    env = os.environ.get("RCK_BIN")
    if env:
        for candidate in _candidate_paths(env):
            if _is_runnable(candidate):
                return candidate
    found = shutil.which("rck")
    if found:
        return found
    # Dev fallback — repo-local debug build.
    here = os.path.dirname(os.path.abspath(__file__))
    base = os.path.normpath(os.path.join(here, "..", "..", "target", "debug", "rck"))
    for candidate in _candidate_paths(base):
        if _is_runnable(candidate):
            return candidate
    raise RckUnavailable(
        "`rck` binary not found. Install with `cargo build --release` in rich-cli-kit/ "
        "or set RCK_BIN."
    )


def detect() -> Capabilities:
    try:
        bin_ = find_rck()
    except RckUnavailable:
        return Capabilities.plain()
    proc = subprocess.run([bin_, "detect"], capture_output=True, text=True, timeout=5)
    if proc.returncode != 0:
        return Capabilities.plain()
    data = json.loads(proc.stdout)
    return Capabilities(
        graphics=bool(data.get("graphics")),
        sixel=bool(data.get("sixel")),
        truecolor=bool(data.get("truecolor")),
        unicode_width=int(data.get("unicode_width", 1)),
        terminal=str(data.get("terminal", "unknown")),
        is_tty=bool(data.get("is_tty")),
        hyperlinks=bool(data.get("hyperlinks", False)),
        clipboard=bool(data.get("clipboard", False)),
        task_markers=bool(data.get("task_markers", False)),
        kitty_keyboard=bool(data.get("kitty_keyboard", False)),
        in_tmux=bool(data.get("in_tmux", False)),
    )


def run_image(path: str, alt: Optional[str] = None) -> bytes:
    bin_ = find_rck()
    args = [bin_, "image", path]
    if alt:
        args += ["--alt", alt]
    proc = subprocess.run(args, capture_output=True, timeout=30)
    proc.check_returncode()
    return proc.stdout


def run_progress(ratio: float, label: Optional[str] = None, ascii_: bool = False) -> bytes:
    bin_ = find_rck()
    args = [bin_, "progress", f"{ratio}"]
    if label:
        args += ["--label", label]
    if ascii_:
        args += ["--ascii"]
    proc = subprocess.run(args, capture_output=True, timeout=5)
    proc.check_returncode()
    return proc.stdout


def run_panel(title: str, body: str, border: str = "rounded") -> bytes:
    bin_ = find_rck()
    args = [bin_, "panel", "--title", title, "--file", "-", "--border", border]
    proc = subprocess.run(args, input=body.encode("utf-8"), capture_output=True, timeout=5)
    proc.check_returncode()
    return proc.stdout


def run_link(url: str, text: str) -> bytes:
    bin_ = find_rck()
    proc = subprocess.run([bin_, "link", url, text], capture_output=True, timeout=5)
    proc.check_returncode()
    return proc.stdout


def run_copy(content: str) -> bytes:
    bin_ = find_rck()
    proc = subprocess.run(
        [bin_, "copy", "--stdin"],
        input=content.encode("utf-8"),
        capture_output=True,
        timeout=5,
    )
    proc.check_returncode()
    return proc.stdout


def run_task_marker(phase: str, exit_code: int = 0, task_id: Optional[str] = None) -> bytes:
    """phase ∈ {'start', 'end'}."""
    bin_ = find_rck()
    if phase == "start":
        args = [bin_, "task-start"]
        if task_id:
            args += ["--id", task_id]
    elif phase == "end":
        args = [bin_, "task-end", "--exit", str(exit_code)]
    else:
        raise ValueError(f"unknown phase: {phase}")
    proc = subprocess.run(args, capture_output=True, timeout=5)
    proc.check_returncode()
    return proc.stdout


def run_ask(question: str, timeout: float = 120.0) -> tuple[int, str]:
    """Run `rck ask` interactively. Returns (exit_code, stdout).

    Exit code: 0 = yes, 1 = no, 2 = cancelled.
    When stdin is not a TTY, the child uses its plain-stdin fallback.
    """
    bin_ = find_rck()
    proc = subprocess.run([bin_, "ask", question], capture_output=True, timeout=timeout)
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace")


def run_pick(prompt: str, choices: list[str], timeout: float = 120.0) -> tuple[int, str]:
    bin_ = find_rck()
    proc = subprocess.run([bin_, "pick", prompt, *choices], capture_output=True, timeout=timeout)
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace").rstrip("\n")


def run_input(prompt: str, timeout: float = 120.0) -> tuple[int, str]:
    bin_ = find_rck()
    proc = subprocess.run([bin_, "input", prompt], capture_output=True, timeout=timeout)
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace").rstrip("\n")
