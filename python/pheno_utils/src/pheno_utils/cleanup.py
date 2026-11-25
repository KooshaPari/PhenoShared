"""Repository Cleanup Validation Module.

Validates repository hygiene by checking for stray build artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

DEFAULT_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
    "architecture-results",
}

DEFAULT_LARGE_FILE_THRESHOLD = 1_000_000
DEFAULT_LARGE_FILE_ALLOW = {"docs/atlas_reports/", "docs/atlas_data/"}


@dataclass
class CleanupIssue:
    category: str
    message: str
    samples: list[str]


def _should_skip(path: Path, skip_dirs: set[str] | None = None) -> bool:
    skip_dirs = skip_dirs or DEFAULT_SKIP_DIRS
    return any(part in skip_dirs for part in path.parts)


def find_pycache(root: Path, skip_dirs: set[str] | None = None) -> list[CleanupIssue]:
    offenders = [
        str(path.relative_to(root))
        for path in root.rglob("__pycache__")
        if not _should_skip(path, skip_dirs)
    ]
    if offenders:
        return [
            CleanupIssue(
                "cache_directories",
                "__pycache__ directories present",
                offenders[:20],
            ),
        ]
    return []


def find_pyc(root: Path, skip_dirs: set[str] | None = None) -> list[CleanupIssue]:
    offenders = [
        str(path.relative_to(root))
        for path in root.rglob("*.pyc")
        if not _should_skip(path, skip_dirs)
    ]
    if offenders:
        return [CleanupIssue("compiled_python", "*.pyc files present", offenders[:20])]
    return []


def find_misc(root: Path, skip_dirs: set[str] | None = None) -> list[CleanupIssue]:
    issues: list[CleanupIssue] = []
    patterns = {"*.log": "Log files committed", "*.tmp": "Temporary files committed"}
    for pattern, message in patterns.items():
        offenders = [
            str(path.relative_to(root))
            for path in root.rglob(pattern)
            if not _should_skip(path, skip_dirs)
        ]
        if offenders:
            issues.append(CleanupIssue("temporary_files", message, offenders[:20]))
    ds_store = [
        str(path.relative_to(root))
        for path in root.rglob(".DS_Store")
        if not _should_skip(path, skip_dirs)
    ]
    if ds_store:
        issues.append(CleanupIssue("os_artifacts", ".DS_Store files present", ds_store[:20]))
    return issues


def find_large_files(
    root: Path,
    threshold: int,
    allow_patterns: set[str] | None = None,
    skip_dirs: set[str] | None = None,
) -> list[CleanupIssue]:
    allow_patterns = allow_patterns or DEFAULT_LARGE_FILE_ALLOW
    offenders: list[str] = []
    for path in root.rglob("*"):
        if path.is_dir() or _should_skip(path, skip_dirs):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size <= threshold:
            continue
        rel = str(path.relative_to(root))
        if any(rel.startswith(prefix) for prefix in allow_patterns):
            continue
        offenders.append(f"{rel} ({size / 1024:.1f} KiB)")
    if offenders:
        return [
            CleanupIssue(
                "large_files",
                f"Files exceed {threshold // 1024} KiB limit",
                offenders[:20],
            )
        ]
    return []


def validate_cleanup(
    root: Path,
    threshold: int = DEFAULT_LARGE_FILE_THRESHOLD,
    allow_patterns: set[str] | None = None,
    skip_dirs: set[str] | None = None,
) -> dict[str, object]:
    """Validate repository for stray build artifacts."""
    skip_dirs = skip_dirs or DEFAULT_SKIP_DIRS
    issues = []
    issues.extend(find_pycache(root, skip_dirs))
    issues.extend(find_pyc(root, skip_dirs))
    issues.extend(find_misc(root, skip_dirs))
    issues.extend(find_large_files(root, threshold, allow_patterns, skip_dirs))
    return {
        "status": "clean" if not issues else "needs_cleanup",
        "issue_count": len(issues),
        "issues": [asdict(issue) for issue in issues],
    }


def format_report(report: dict[str, object]) -> str:
    """Format cleanup validation report."""
    lines = ["Cleanup Validation Results", "=" * 32]
    lines.append(f"Status: {report['status']}")
    lines.append(f"Issue count: {report['issue_count']}")
    for issue in report.get("issues", []):
        lines.append(f"- [{issue['category']}] {issue['message']}")
        for sample in issue.get("samples", []):
            lines.append(f"    • {sample}")
    return "\n".join(lines)
