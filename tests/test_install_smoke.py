"""FR-T1-001: Core install / import smoke (mirrors scripts/smoke_install.sh).

Harbor / portage are intentionally out of scope for this module — CI installs
only ``.[dev]``. Submodule absence is allowed (same as the shell smoke).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _prefer_repo_packages() -> None:
    """Avoid ``kernels/qwen3.5-0.8b/python/bench.py`` shadowing the bench package.

    Codegen tests may put the kernel python dir on ``sys.path``; clear that
    shadow so ``import bench`` resolves to the installed / repo package.
    """
    root = Path(__file__).resolve().parents[1]
    cleaned: list[str] = []
    for entry in sys.path:
        normalized = entry.replace("\\", "/")
        if "kernels/qwen3.5-0.8b/python" in normalized:
            continue
        cleaned.append(entry)
    sys.path[:] = cleaned
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    for name in ("bench", "pheno", "verifier"):
        sys.modules.pop(name, None)


def test_yaml_and_requests_importable() -> None:
    import requests
    import yaml

    assert yaml.__version__
    assert requests.__version__


def test_core_packages_importable() -> None:
    _prefer_repo_packages()
    import bench
    import pheno
    import verifier

    assert "kernels/qwen3.5-0.8b" not in (getattr(bench, "__file__", "") or "")
    assert bench.__version__
    assert pheno.__version__
    assert verifier.__name__ == "verifier"


def test_bench_cli_help_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "bench", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_bench_self_test_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "bench", "self-test"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS" in proc.stdout
