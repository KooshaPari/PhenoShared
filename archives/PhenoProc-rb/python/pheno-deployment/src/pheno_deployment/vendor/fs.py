"""
Filesystem helpers for vendoring.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from .config import EXCLUDE_PATTERNS

if TYPE_CHECKING:
    from pathlib import Path

    from .models import PackageInfo


def copy_package(pkg_info: PackageInfo, dest_root: Path) -> None:
    """
    Copy a package into the vendor directory.
    """
    dest_path = dest_root / pkg_info.module_name
    source_pkg_path = pkg_info.source_path / pkg_info.module_name

    if not source_pkg_path.exists():
        src_layout = pkg_info.source_path / "src" / pkg_info.module_name
        source_pkg_path = src_layout if src_layout.exists() else pkg_info.source_path

    if source_pkg_path.is_dir():
        shutil.copytree(
            source_pkg_path,
            dest_path,
            ignore=shutil.ignore_patterns(*EXCLUDE_PATTERNS),
            dirs_exist_ok=True,
        )

    for meta_file in ("setup.py", "setup.cfg", "pyproject.toml", "README.md", "LICENSE"):
        meta_src = pkg_info.source_path / meta_file
        if meta_src.exists():
            dest_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(meta_src, dest_path / meta_file)


def handle_kinfra(pheno_sdk_root: Path, vendor_dir: Path) -> None:
    """
    Copy the special KInfra package if present.
    """
    kinfra_path = pheno_sdk_root / "KInfra"
    if not kinfra_path.exists():
        return

    if kinfra_path.is_symlink():
        kinfra_path = kinfra_path.resolve()

    kinfra_python = kinfra_path / "libraries/python"
    if not kinfra_python.exists():
        return

    dest_path = vendor_dir / "kinfra"
    package_path = kinfra_python / "kinfra"

    if package_path.exists():
        shutil.copytree(
            package_path,
            dest_path,
            ignore=shutil.ignore_patterns(*EXCLUDE_PATTERNS),
            dirs_exist_ok=True,
        )

    for meta_file in ("setup.py", "pyproject.toml", "README.md"):
        meta_src = kinfra_python / meta_file
        if meta_src.exists():
            dest_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(meta_src, dest_path / meta_file)


__all__ = ["copy_package", "handle_kinfra"]
