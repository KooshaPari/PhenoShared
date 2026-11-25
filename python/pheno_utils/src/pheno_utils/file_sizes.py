"""File Size Checker Module.

Enforces file size limits to prevent monster files and maintain code quality.
"""

from __future__ import annotations

from pathlib import Path

# Directories to exclude
EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "archive",
    "build",
    "dist",
}

# Files to exclude (generated code, etc.)
EXCLUDE_PATTERNS = {
    "generated",
    "schema_public_latest.py",
}


def count_lines(file_path: Path) -> int:
    """Count lines of code in a file (excluding blank lines and comments)."""
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except (UnicodeDecodeError, PermissionError):
        return 0

    loc = 0
    in_multiline_comment = False

    for line in lines:
        stripped = line.strip()

        # Skip blank lines
        if not stripped:
            continue

        # Handle multiline comments (docstrings)
        if '"""' in stripped or "'''" in stripped:
            if in_multiline_comment:
                in_multiline_comment = False
                continue
            in_multiline_comment = True
            # If docstring starts and ends on same line, don't skip
            if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                in_multiline_comment = False
            continue

        if in_multiline_comment:
            continue

        # Skip single-line comments
        if stripped.startswith("#"):
            continue

        loc += 1

    return loc


def should_exclude(file_path: Path) -> bool:
    """Check if file should be excluded from size check."""
    # Check if in excluded directory
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return True

    # Check if matches excluded pattern
    return any(pattern in str(file_path) for pattern in EXCLUDE_PATTERNS)


def get_python_files(directory: Path) -> list[Path]:
    """Get all Python files in directory, excluding exempted files."""
    return [f for f in directory.rglob("*.py") if not should_exclude(f)]


def check_file_sizes(
    directory: Path,
    max_loc: int = 500,
    target_loc: int = 350,
    strict: bool = False,
) -> tuple[list[tuple[Path, int]], list[tuple[Path, int]]]:
    """
    Check file sizes against limits.

    Returns:
        Tuple of (violations, warnings)
        Violations: Files exceeding hard limit
        Warnings: Files exceeding target
    """
    python_files = get_python_files(directory)
    violations = []
    warnings = []

    for file_path in python_files:
        loc = count_lines(file_path)

        if loc > max_loc:
            violations.append((file_path, loc))
        elif loc > target_loc:
            warnings.append((file_path, loc))

    return violations, warnings


def format_report(
    violations: list[tuple[Path, int]],
    warnings: list[tuple[Path, int]],
    max_loc: int,
    target_loc: int,
    root_path: Path | None = None,
) -> str:
    """Format file size report."""
    lines = []

    lines.append("=" * 80)
    lines.append("FILE SIZE REPORT")
    lines.append("=" * 80)
    lines.append(f"Target: {target_loc} LOC")
    lines.append(f"Hard Limit: {max_loc} LOC")
    lines.append("")

    if violations:
        lines.append(f"❌ VIOLATIONS ({len(violations)} files exceed hard limit):")
        lines.append("-" * 80)
        for file_path, loc in sorted(violations, key=lambda x: x[1], reverse=True):
            if root_path:
                try:
                    relative_path = file_path.relative_to(root_path)
                except ValueError:
                    relative_path = file_path
            else:
                relative_path = file_path
            excess = loc - max_loc
            lines.append(f"  {relative_path}")
            lines.append(f"    {loc} LOC (exceeds limit by {excess} lines)")
        lines.append("")

    if warnings:
        lines.append(f"⚠️  WARNINGS ({len(warnings)} files exceed target):")
        lines.append("-" * 80)
        for file_path, loc in sorted(warnings, key=lambda x: x[1], reverse=True):
            if root_path:
                try:
                    relative_path = file_path.relative_to(root_path)
                except ValueError:
                    relative_path = file_path
            else:
                relative_path = file_path
            excess = loc - target_loc
            lines.append(f"  {relative_path}")
            lines.append(f"    {loc} LOC (exceeds target by {excess} lines)")
        lines.append("")

    if not violations and not warnings:
        lines.append("✅ All files within size limits!")
        lines.append("")

    lines.append("=" * 80)
    lines.append("RECOMMENDATIONS:")
    lines.append("=" * 80)
    lines.append("1. Split large files by concern (entities, use cases, adapters)")
    lines.append("2. Extract common patterns to base classes or utilities")
    lines.append("3. Move generated code to separate files")
    lines.append("4. Document exceptions in tests/architecture/EXCEPTIONS.md")
    lines.append("")

    return "\n".join(lines)
