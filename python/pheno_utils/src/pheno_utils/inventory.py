"""Public API Inventory Module.

Scans kit __init__.py files and collects exported symbols.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def find_init_files(root: Path) -> list[Path]:
    """Find all __init__.py files in a project."""
    inits: list[Path] = []
    for p in root.rglob("__init__.py"):
        # Skip virtual envs and build artifacts
        if any(
            seg in p.parts for seg in [".venv", "venv", "build", "dist", "__pycache__", ".egg-info"]
        ):
            continue
        # Only include paths that appear to be kits or their packages
        if any(
            seg.endswith(("-kit", "_kit")) or seg in ("pydevkit", "authkit-client")
            for seg in p.parts
        ):
            inits.append(p)
    return inits


def extract_exports(init_path: Path) -> dict[str, Any]:
    """Extract exported symbols from an __init__.py file."""
    data: dict[str, Any] = {
        "path": str(init_path),
        "module": ".".join(init_path.with_suffix("").parts[-4:]),
        "all": [],
        "imports": [],
        "names": [],
        "version": None,
    }
    try:
        src = init_path.read_text()
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                # __all__ collection
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            data["all"] = [
                                elt.s for elt in node.value.elts if isinstance(elt, ast.Str)
                            ]
                # __version__ capture
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__version__":
                        if isinstance(node.value, ast.Str):
                            data["version"] = node.value.s
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                data["imports"].append({"from": module, "names": names})
            elif isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                if not node.name.startswith("_"):
                    data["names"].append(node.name)
    except Exception as e:
        data["error"] = str(e)
    return data


def build_inventory(root: Path) -> dict[str, Any]:
    """Build a public API inventory for a project."""
    result: dict[str, Any] = {
        "kits": {},
        "summary": {},
    }
    inits = find_init_files(root)
    for init in inits:
        kit_dir = None
        for part in init.parts:
            if (
                part.endswith("-kit")
                or part.endswith("_kit")
                or part in ("pydevkit", "authkit-client")
            ):
                kit_dir = part
        kit_key = kit_dir or "unknown"
        result["kits"].setdefault(kit_key, []).append(extract_exports(init))

    # Summary counts
    total_symbols = 0
    per_kit_counts: dict[str, int] = {}
    for kit, entries in result["kits"].items():
        count = 0
        for entry in entries:
            count += len(entry.get("all", [])) or len(entry.get("names", []))
        per_kit_counts[kit] = count
        total_symbols += count

    result["summary"] = {
        "total_kits": len(result["kits"]),
        "total_symbols": total_symbols,
        "per_kit_export_counts": per_kit_counts,
    }
    return result


def inventory_to_markdown(inventory: dict[str, Any]) -> str:
    """Convert inventory to markdown format."""
    lines = ["# Public API Inventory\n"]

    summary = inventory.get("summary", {})
    lines.append(f"**Total Kits:** {summary.get('total_kits', 0)}  ")
    lines.append(f"**Total Symbols:** {summary.get('total_symbols', 0)}\n")

    for kit, entries in sorted(inventory.get("kits", {}).items()):
        lines.append(f"## {kit}\n")
        for entry in entries:
            module = entry.get("module", "unknown")
            lines.append(f"### `{module}`\n")

            if entry.get("version"):
                lines.append(f"**Version:** {entry['version']}\n")

            if entry.get("all"):
                lines.append("**__all__ exports:**\n")
                for sym in entry["all"]:
                    lines.append(f"- `{sym}`")
                lines.append("")

            if entry.get("names"):
                lines.append("**Public names:**\n")
                for name in entry["names"][:20]:  # Limit to first 20
                    lines.append(f"- `{name}`")
                if len(entry["names"]) > 20:
                    lines.append(f"- ... and {len(entry['names']) - 20} more")
                lines.append("")

    return "\n".join(lines)
