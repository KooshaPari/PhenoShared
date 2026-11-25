"""Lines of Code Counter Module.

Count logical lines of Python code and enforce LOC guardrails.
"""

from __future__ import annotations

import json
import sys
import tokenize
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DEFAULT_EXCLUDES = (
    ".git",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    "htmlcov",
    "examples",
    "tests",
    "docs",
    "__pycache__",
)

DEFAULT_INCLUDES = (
    "src",
    "lib",
    "config",
    "scripts",
    "cli",
)


@dataclass
class LocSummary:
    total_loc: int
    threshold: int
    exceeded: bool
    files_counted: int
    include_paths: Sequence[str]
    excluded_paths: Sequence[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def iter_python_files(
    root: Path,
    includes: Iterable[str],
    excludes: Iterable[str],
) -> Iterable[Path]:
    exclude_set = {root / Path(p) for p in excludes}
    exclude_prefixes = tuple(exclude_set)
    include_entries = tuple(includes) or DEFAULT_INCLUDES
    visited: set[Path] = set()

    for include in include_entries:
        target = (root / include).resolve()
        if not target.exists():
            continue
        if target.is_file() and target.suffix == ".py":
            candidates = (target,)
        elif target.is_dir():
            candidates = (path for path in target.rglob("*.py") if path.is_file())
        else:
            continue
        for path in candidates:
            if any(path.is_relative_to(prefix) for prefix in exclude_prefixes):
                continue
            if path in visited:
                continue
            visited.add(path)
            yield path


def count_file_loc(path: Path) -> int:
    """Count logical lines of code for a Python file."""
    try:
        with tokenize.open(path) as handle:
            tokens = tokenize.generate_tokens(handle.readline)
            logical_lines: set[int] = set()
            for token_type, _, start, _, _ in tokens:
                if token_type in {
                    tokenize.ENCODING,
                    tokenize.ENDMARKER,
                    tokenize.NL,
                    tokenize.NEWLINE,
                    tokenize.COMMENT,
                }:
                    continue
                logical_lines.add(start[0])
            return len(logical_lines)
    except (SyntaxError, tokenize.TokenError):  # pragma: no cover - guardrail
        # Fall back to a simple textual scan if tokenization fails.
        approx_loc = 0
        with path.open(encoding="utf-8", errors="ignore") as handle:
            for raw_line in handle:
                stripped = raw_line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                approx_loc += 1
        print(
            f"WARNING: Tokenization failed for {path}; falling back to heuristic line counting.",
            file=sys.stderr,
        )
        return approx_loc


def compute_loc(
    root: Path,
    includes: Iterable[str],
    excludes: Iterable[str],
) -> tuple[int, int]:
    total = 0
    counted_files = 0
    for file_path in iter_python_files(root, includes, excludes):
        total += count_file_loc(file_path)
        counted_files += 1
    return total, counted_files


def count_loc(
    root: Path,
    includes: Iterable[str] | None = None,
    excludes: Iterable[str] | None = None,
    threshold: int = 8500,
) -> LocSummary:
    """Count lines of code in a project."""
    excludes = list(excludes) if excludes else list(DEFAULT_EXCLUDES)
    includes = list(includes) if includes else list(DEFAULT_INCLUDES)

    total_loc, counted_files = compute_loc(root, includes, excludes)
    return LocSummary(
        total_loc=total_loc,
        threshold=threshold,
        exceeded=total_loc > threshold,
        files_counted=counted_files,
        include_paths=tuple(sorted(set(includes))),
        excluded_paths=tuple(sorted(set(excludes))),
    )
