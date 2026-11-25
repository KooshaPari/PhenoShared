#!/usr/bin/env python3
"""Check docstring coverage for eval/verifier/pheno/evidence — 91.5% gate.

Target 91.5% (260/284) of public modules/functions/classes have docstrings.
Reports missing docstrings and exits 1 if below threshold.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

TARGET = 91.5
ROOTS = ["eval", "verifier", "pheno/evidence"]
THRESHOLD_FILES = 0  # ratchet: 91.5% gate (260/284)


def _has_docstring(node: ast.AST) -> bool:
    doc = ast.get_docstring(node)
    return bool(doc and doc.strip())


def scan_file(path: Path) -> tuple[int, int]:
    """Return (total_defs, with_docstring) for one file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception:
        return 0, 0
    total = 0
    with_doc = 0
    # module docstring
    total += 1
    if _has_docstring(tree):
        with_doc += 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # skip private
            if node.name.startswith("_") and not node.name.startswith("__"):
                continue
            total += 1
            if _has_docstring(node):
                with_doc += 1
    return total, with_doc


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    totals = 0
    covered = 0
    missing: list[str] = []
    for root in ROOTS:
        for path in (repo / root).rglob("*.py"):
            if "__pycache__" in str(path) or ".venv" in str(path):
                continue
            t, c = scan_file(path)
            totals += t
            covered += c
            if t - c > 0:
                # Report file with missing docstrings
                missing.append(f"{path.relative_to(repo)}: {c}/{t}")
    pct = (covered / totals * 100) if totals else 100.0
    print(f"Docstring coverage: {covered}/{totals} ({pct:.1f}%) target {TARGET}%")
    for m in missing[:20]:
        print(f"  {m}")
    if len(missing) > 20:
        print(f"  ... and {len(missing) - 20} more files with gaps")
    if pct < TARGET:
        print(f"FAIL: below {TARGET}% gate")
        return 1
    print(f"PASS: docstring coverage {pct:.1f}% >= {TARGET}% (260/284 gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
