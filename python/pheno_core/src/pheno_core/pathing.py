"""Path management utilities for Pheno-SDK integrations.

Production-grade, deterministic helpers to place required project roots on
sys.path without relying on ad-hoc, per-file hacks.

Design goals:
- Avoid name collisions (prefer this package name over ambiguous 'src.*').
- Idempotent: safe to call multiple times.
- Deterministic order: project src first, then sibling SDKs, then extras.
- Zero exceptions on failure: log/debug messages okay; callers proceed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def _insert_path(p: Path, *, before: bool = True) -> bool:
    """Insert path into sys.path if it exists and isn't already present.

    Returns True if inserted, False otherwise.
    """
    try:
        rp = str(p)
        if not p.exists():
            return False
        if rp in sys.path:
            return False
        if before:
            sys.path.insert(0, rp)
        else:
            sys.path.append(rp)
        return True
    except Exception:
        return False


def _find_upwards(start: Path, names: Iterable[str]) -> list[Path]:
    """Search upwards from start for any of the given directory names.

    Returns a list of matching directories in closest-first order.
    """
    results: list[Path] = []
    for parent in [start, *list(start.parents)]:
        for n in names:
            cand = parent / n
            if cand.exists():
                results.append(cand)
    # Remove duplicates while preserving order
    seen: set[str] = set()
    ordered: list[Path] = []
    for p in results:
        s = str(p)
        if s not in seen:
            seen.add(s)
            ordered.append(p)
    return ordered


def ensure_project_src_on_path(project_root: Path | None = None) -> bool:
    """Ensure the caller project's src directory is importable.

    Returns True if a src path was added or already present.
    """
    try:
        project_root = project_root or Path(__file__).resolve().parents[3]
        src = project_root / "src"
        return _insert_path(src, before=True)
    except Exception:
        return False


def ensure_pheno_sdk_on_path(hints: Iterable[Path] | None = None) -> bool:
    """Ensure the pheno-sdk repository root and its src are importable.

    Returns True if any path was added or already present.
    """
    inserted = False
    candidates: list[Path] = []
    try:
        here = Path.cwd()
        candidates.extend(_find_upwards(here, ["pheno-sdk"]))
    except Exception:
        pass
    if hints:
        for h in hints:
            if h:
                candidates.append(h)
    # Known common layouts (explicit)
    try:
        home = Path.home()
        candidates.extend(
            [
                home / "temp-PRODVERCEL" / "485" / "kush" / "pheno-sdk",
                Path("/Users/<REDACTED>/temp-PRODVERCEL/485/kush/pheno-sdk"),
            ],
        )
    except Exception:
        pass

    # Insert repo root first (for tools, configs), then src
    ordered_unique: list[Path] = []
    seen: set[str] = set()
    for c in candidates:
        for p in (c, c / "src"):
            s = str(p)
            if p.exists() and s not in seen:
                seen.add(s)
                ordered_unique.append(p)

    for p in ordered_unique:
        inserted = _insert_path(p, before=False) or inserted
    return inserted


def ensure_kinfra_on_path(hints: Iterable[Path] | None = None) -> bool:
    """
    Ensure KInfra library directory is importable if present.
    """
    inserted = False
    candidates: list[Path] = []
    try:
        here = Path.cwd()
        candidates.extend(_find_upwards(here, ["KInfra"]))
    except Exception:
        pass
    if hints:
        candidates.extend([h for h in hints if h])

    # Likely locations
    more: list[Path] = []
    try:
        for cand in candidates:
            more.append(cand / "libraries" / "python")
        home = Path.home()
        more.append(
            home
            / "temp-PRODVERCEL"
            / "485"
            / "kush"
            / "pheno-sdk"
            / "KInfra"
            / "libraries"
            / "python",
        )
    except Exception:
        pass

    for p in candidates + more:
        inserted = _insert_path(p, before=False) or inserted
    return inserted


def bootstrap(project_root: Path | None = None) -> None:
    """Perform standard path bootstrapping for repos that integrate Pheno-SDK.

    Order of operations:
      1) Ensure project src is first (import your own code)
      2) Ensure KInfra (optional)
      3) Ensure pheno-sdk (tools/configs/etc.)
    """
    ensure_project_src_on_path(project_root)
    ensure_kinfra_on_path()
    ensure_pheno_sdk_on_path()
