"""Test-harness helpers for skipping tests that require external tooling.

Centralizes the conditional-skip patterns so individual tests can drop
their bespoke inline ``pytest.importorskip`` / ``pytest.mark.skipif``
blocks. Each helper is a thin boolean expression of the underlying
capability (binary on PATH, module importable, etc.) and is intended
to be used as a ``reason=`` argument to ``pytest.mark.skipif``.

Usage::

    from tests._harness import skipif_no_docker, skipif_no_mlx, skipif_no_harbor

    @skipif_no_docker
    def test_container_x(): ...

    @skipif_no_mlx
    def test_mlx_y(): ...

    @skipif_no_harbor
    def test_harbor_z(): ...
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

DOTENV_PATH = Path(__file__).resolve().parent.parent / ".envrc"
FALLBACK_MARKER = "FALLBACK_TESTS_DEFAULT_INSECURE"


def _has_docker() -> bool:
    """``docker`` on PATH and the daemon responds to ``docker info``."""
    if shutil.which("docker") is None:
        return False
    # The daemon ping is a cheap smoke check; do not raise if it fails.
    try:
        import subprocess

        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _has_mlx() -> bool:
    """Apple Silicon + the ``mlx`` package importable."""
    import platform

    if platform.machine() != "arm64" or sys.platform != "darwin":
        return False
    try:
        import mlx.core  # noqa: F401

        return True
    except (ImportError, AttributeError):
        return False


def _has_harbor(version: str = "0.1.42") -> bool:
    """``harbor_cli`` importable with a version >= the requested min."""
    try:
        import harbor_cli
    except ImportError:
        return False
    installed = getattr(harbor_cli, "__version__", "0.0.0")
    try:
        from packaging.version import Version

        return Version(installed) >= Version(version)
    except Exception:
        return bool(str(installed).strip())


def _env_truthy(name: str) -> bool:
    """Return True if the named env var is set to a truthy value."""
    import os

    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


# Reusable skipif markers --------------------------------------------------------

skipif_no_docker = pytest.mark.skipif(
    not _has_docker(),
    reason="docker not available on PATH or daemon unreachable",
)
skipif_no_mlx = pytest.mark.skipif(
    not _has_mlx(),
    reason="mlx requires Apple Silicon (darwin/arm64) + mlx package installed",
)
skipif_no_harbor = pytest.mark.skipif(
    not _has_harbor(),
    reason="harbor_cli>=0.1.42 not installed",
)
skipif_insecure_default = pytest.mark.skipif(
    not _env_truthy(FALLBACK_MARKER),
    reason=f"set {FALLBACK_MARKER}=1 to run tests that exercise insecure defaults",
)
skipif_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Unix-only test (resource module or /bin/bash required)",
)
skipif_non_macos = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="macOS-only test (launchd scripts)",
)


def describe() -> Mapping[str, bool]:
    """Return a snapshot of the gating decisions for diagnostics.

    Useful in a CI summary or for ``pytest --collect-only`` output.
    """
    return {
        "docker": _has_docker(),
        "mlx": _has_mlx(),
        "harbor": _has_harbor(),
        "insecure_default": _env_truthy(FALLBACK_MARKER),
        "windows": sys.platform == "win32",
        "non_macos": sys.platform != "darwin",
    }
