"""Importable wrapper for the repository's legacy hyphenated runner script."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _legacy_script_path() -> Path:
    source_runner = Path(__file__).resolve().parents[3] / "scripts" / "run-harness.py"
    packaged_runner = Path(__file__).resolve().parents[1] / "_legacy_runner.py"
    for candidate in (source_runner, packaged_runner):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("helios-harness legacy runner was not packaged")


def _legacy_module() -> ModuleType:
    script = _legacy_script_path()
    spec = importlib.util.spec_from_file_location("helios_harness_legacy_runner", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load harness runner: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    """Run the canonical harness CLI."""
    _legacy_module().main()


def run_runner(repo: str, profile: str, out: str, args) -> None:
    """Expose the runner seam for integration tests and adapters."""
    _legacy_module().run_runner(repo, profile, out, args)
