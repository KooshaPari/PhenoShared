"""
Validation and import testing for vendored packages.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def validate_vendored(
    vendor_dir: Path, packages: Iterable[str] | None = None,
) -> dict[str, tuple[bool, str]]:
    """
    Validate vendored packages by checking for core files.
    """
    if not vendor_dir.exists():
        return {"vendor_dir": (False, "Vendor directory does not exist")}

    if packages is None:
        candidates = [
            entry.name
            for entry in vendor_dir.iterdir()
            if entry.is_dir() and not entry.name.startswith("_")
        ]
    else:
        candidates = list(packages)

    results: dict[str, tuple[bool, str]] = {}

    for pkg_name in candidates:
        pkg_path = vendor_dir / pkg_name
        if not pkg_path.exists():
            results[pkg_name] = (False, "Package directory not found")
            continue

        python_files = list(pkg_path.rglob("*.py"))
        if not python_files:
            results[pkg_name] = (False, "No Python files found")
            continue

        init_file = pkg_path / "__init__.py"
        if not init_file.exists():
            results[pkg_name] = (False, "No __init__.py found")
            continue

        results[pkg_name] = (True, f"Valid ({len(python_files)} Python files)")

    return results


def test_imports(
    vendor_dir: Path, packages: Iterable[str] | None = None,
) -> dict[str, tuple[bool, str]]:
    """
    Test importing each vendored package.
    """
    str(vendor_dir)

    selected = (
        [
            entry.name
            for entry in vendor_dir.iterdir()
            if entry.is_dir() and not entry.name.startswith("_")
        ]
        if packages is None
        else list(packages)
    )

    results: dict[str, tuple[bool, str]] = {}

    for pkg_name in selected:
        try:
            spec = importlib.util.spec_from_file_location(
                pkg_name, vendor_dir / pkg_name / "__init__.py",
            )
            if spec is None or spec.loader is None:
                results[pkg_name] = (False, "Module spec not found")
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            origin = getattr(module, "__file__", "unknown")
            results[pkg_name] = (True, f"Import successful (from {origin})")
        except Exception as exc:  # pragma: no cover - defensive import
            results[pkg_name] = (False, f"Import failed: {exc}")

    return results


__all__ = ["test_imports", "validate_vendored"]
