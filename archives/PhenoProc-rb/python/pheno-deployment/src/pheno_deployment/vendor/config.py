"""
Static configuration for vendoring operations.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_MAPPINGS: dict[str, str] = {
    "pydevkit": "pydevkit",
    "adapter-kit": "adapter_kit",
    "stream-kit": "stream_kit",
    "storage-kit": "storage_kit",
    "db-kit": "db_kit",
    "mcp-QA": "pheno.mcp.qa",
    "process-monitor-sdk": "process_monitor",
    "tui-kit": "tui_kit",
    "workflow-kit": "workflow_kit",
    "event-kit": "event_kit",
    "deploy-kit": "deploy_kit",
    "observability-kit": "observability_kit",
    "cli-builder-kit": "cli_builder",
    "filewatch-kit": "filewatch_kit",
    "mcp-sdk-kit": "mcp_sdk_kit",
}

EXCLUDE_PATTERNS: set[str] = {
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    ".mypy_cache",
    "*.egg-info",
    ".git",
    ".github",
    "tests",
    "docs",
    "examples",
    ".venv",
    "venv",
    "node_modules",
}


def candidate_pheno_sdk_paths(project_root: Path) -> list[Path]:
    """
    Return potential pheno-sdk locations relative to a project.
    """
    return [
        project_root.parent / "pheno-sdk",
        Path.home() / "temp-PRODVERCEL/485/kush/pheno-sdk",
        Path("/Users/kooshapari/temp-PRODVERCEL/485/kush/pheno-sdk"),
    ]


DEFAULT_VENDOR_DIR = "pheno_vendor"

__all__ = [
    "DEFAULT_VENDOR_DIR",
    "EXCLUDE_PATTERNS",
    "PACKAGE_MAPPINGS",
    "candidate_pheno_sdk_paths",
]
