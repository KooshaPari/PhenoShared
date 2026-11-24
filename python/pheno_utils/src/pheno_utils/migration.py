"""Import Migration Module.

Auto-migration for consolidating pheno-sdk imports.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# Mapping of old kit imports to new consolidated paths
KIT_IMPORT_MAPPINGS: dict[str, str] = {
    # TUI kit specific mappings (order matters - more specific first)
    r"from\s+tui_kit\.([a-zA-Z_][a-zA-Z0-9_.]*)\s+import": ("from pheno.ui.tui.\1 import"),
    r"from\s+tui_kit\s+import": "from pheno.ui.tui import",
    r"import\s+tui_kit": "import pheno.ui.tui as tui_kit",
    # Core areas
    r"from\s+db_kit\s+import": "from pheno.data.db import",
    r"from\s+observability_kit\s+import": "from pheno.infra.observability import",
    r"from\s+stream_kit\s+import": "from pheno.web.streaming import",
    r"from\s+adapter_kit\s+import": "from pheno.core.adapters import",
    r"from\s+config_kit\s+import": "from pheno.core.config import",
    r"from\s+event_kit\s+import": "from pheno.data.events import",
    r"from\s+vector_kit\s+import": "from pheno.data.vectors import",
    r"from\s+storage_kit\s+import": "from pheno.data.storage import",
    r"from\s+workflow_kit\s+import": "from pheno.ai.workflows import",
    r"from\s+orchestrator_kit\s+import": "from pheno.ai.orchestrator import",
    # SDK imports
    r"from\s+pheno\.sdk\.([a-zA-Z_][a-zA-Z0-9_.]*)\s+import": ("from pheno.\1 import"),
    r"import\s+pheno\.sdk": "import pheno",
}

FILE_PATTERNS = (".py", ".pyi")


def migrate_file(path: Path, mappings: dict[str, str] | None = None) -> tuple[int, str]:
    """Migrate imports in a single file.

    Returns:
        Tuple of (number of changes, new content)
    """
    mappings = mappings or KIT_IMPORT_MAPPINGS
    text = path.read_text(encoding="utf-8", errors="ignore")
    original = text
    for pattern, replacement in mappings.items():
        text = re.sub(pattern, replacement, text)

    changes = 1 if text != original else 0
    return changes, text


def scan_and_migrate(
    root: Path,
    mappings: dict[str, str] | None = None,
    apply: bool = False,
) -> Iterator[tuple[Path, int]]:
    """Scan directory and migrate imports.

    Yields tuples of (file_path, number_of_changes)
    """
    mappings = mappings or KIT_IMPORT_MAPPINGS
    changed = 0
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in FILE_PATTERNS:
            try:
                n_changes, new_content = migrate_file(p, mappings)
                if n_changes > 0:
                    if apply:
                        p.write_text(new_content, encoding="utf-8")
                    yield p, n_changes
                    changed += n_changes
            except Exception:
                continue


def generate_migration_plan(
    root: Path,
    mappings: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Generate a migration plan without applying changes."""
    mappings = mappings or KIT_IMPORT_MAPPINGS
    plan: dict[str, list[str]] = {pattern: [] for pattern in mappings.keys()}

    for p in root.rglob("*.py"):
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            for pattern in mappings.keys():
                if re.search(pattern, content):
                    rel_path = str(p.relative_to(root))
                    plan[pattern].append(rel_path)
        except Exception:
            continue

    # Remove empty patterns
    return {k: v for k, v in plan.items() if v}
