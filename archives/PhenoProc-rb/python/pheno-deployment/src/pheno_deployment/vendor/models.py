"""
Core dataclasses for vendoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class PackageInfo:
    """
    Metadata for a pheno-sdk package.
    """

    dir_name: str
    module_name: str
    source_path: Path
    is_available: bool = False
    has_setup: bool = False
    python_files_count: int = 0
    size_bytes: int = 0


__all__ = ["PackageInfo"]
