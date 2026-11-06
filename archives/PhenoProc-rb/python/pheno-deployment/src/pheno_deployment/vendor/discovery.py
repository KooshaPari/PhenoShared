"""
Package discovery helpers.
"""

from __future__ import annotations

from pathlib import Path

from .config import PACKAGE_MAPPINGS, candidate_pheno_sdk_paths
from .models import PackageInfo


def resolve_pheno_sdk_root(project_root: Path, pheno_sdk_root: Path | None = None) -> Path:
    """
    Determine the pheno-sdk root directory.
    """
    if pheno_sdk_root:
        resolved = Path(pheno_sdk_root).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Specified pheno-sdk root not found: {resolved}")
        return resolved

    for candidate in candidate_pheno_sdk_paths(project_root):
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not find pheno-sdk. Set PHENO_SDK_ROOT environment variable or pass pheno_sdk_root parameter.",
    )


def scan_packages(
    pheno_sdk_root: Path, mappings: dict[str, str] | None = None,
) -> dict[str, PackageInfo]:
    """
    Inspect the pheno-sdk tree and gather package availability.
    """
    mappings = mappings or PACKAGE_MAPPINGS
    packages: dict[str, PackageInfo] = {}

    for dir_name, module_name in mappings.items():
        source_path = pheno_sdk_root / dir_name

        pkg_info = PackageInfo(
            dir_name=dir_name,
            module_name=module_name,
            source_path=source_path,
        )

        if source_path.exists():
            pkg_info.is_available = True
            pkg_info.has_setup = any(
                (source_path / candidate).exists()
                for candidate in ("setup.py", "setup.cfg", "pyproject.toml")
            )

            if pkg_info.has_setup:
                python_files = list(source_path.rglob("*.py"))
                pkg_info.python_files_count = len(python_files)
                pkg_info.size_bytes = sum(path.stat().st_size for path in python_files)

        packages[module_name] = pkg_info

    return packages


def detect_used_packages(project_root: Path, packages: dict[str, PackageInfo]) -> set[str]:
    """
    Detect which packages are referenced by the project.
    """
    used_packages: set[str] = set()
    project_root = project_root.resolve()

    req_file = project_root / "requirements.txt"
    if req_file.exists():
        content = req_file.read_text()
        for module_name, info in packages.items():
            if f"pheno-sdk/{info.dir_name}" in content:
                used_packages.add(module_name)

    for py_file in project_root.rglob("*.py"):
        if "pheno_vendor" in str(py_file) or ".venv" in str(py_file):
            continue

        try:
            source = py_file.read_text()
        except Exception:
            continue

        for module_name in packages:
            if f"import {module_name}" in source or f"from {module_name}" in source:
                used_packages.add(module_name)

    return used_packages


__all__ = ["detect_used_packages", "resolve_pheno_sdk_root", "scan_packages"]
