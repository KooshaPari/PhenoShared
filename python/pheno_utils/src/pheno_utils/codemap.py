"""Code Map Generation Module.

Generate code maps showing pheno namespace references.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_manifest(root: Path) -> dict[str, Any]:
    """Load the phen namespace manifest if available."""
    manifest_path = root / "tools" / "phen_namespace_manifest.json"
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def find_python_imports(root: Path) -> tuple[Counter, dict[str, list[str]]]:
    """Find all Python imports referencing pheno.*"""
    src_root = root / "src"
    if not src_root.exists():
        src_root = root

    per_top_level: Counter = Counter()
    samples: dict[str, list[str]] = defaultdict(list)

    for path in src_root.rglob("*.py"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "from pheno" not in text and "import pheno" not in text:
            continue
        top_level = rel.parts[1] if len(rel.parts) > 1 else rel.parts[0]
        per_top_level[top_level] += 1
        if len(samples[top_level]) < 5:
            for line in text.splitlines():
                if "from pheno" in line or "import pheno" in line:
                    samples[top_level].append(f"{rel}:{line.strip()}")
                    if len(samples[top_level]) >= 5:
                        break
    return per_top_level, samples


def find_docs_references(root: Path) -> list[str]:
    """Find documentation references to src/pheno."""
    docs_root = root / "docs"
    if not docs_root.exists():
        return []

    matches: list[str] = []
    for path in docs_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "src/pheno" in text:
            matches.append(str(path.relative_to(root)))
    return matches


def generate_codemap(root: Path) -> dict[str, Any]:
    """Generate a comprehensive code map."""
    manifest = load_manifest(root)
    pkg_counts, samples = find_python_imports(root)
    doc_paths = find_docs_references(root)

    return {
        "manifest": manifest,
        "import_counts": dict(pkg_counts.most_common()),
        "import_samples": dict(samples),
        "docs_references": doc_paths,
    }


def format_codemap(report: dict[str, Any]) -> str:
    """Format code map as human-readable text."""
    lines = ["=== Pheno Code Map ===", ""]

    manifest = report.get("manifest", {})
    if manifest:
        lines.append("=== Packaging Manifest Targets ===")
        for file_name, sections in manifest.items():
            lines.append(f"{file_name}:")
            if isinstance(sections, dict):
                for section, value in sections.items():
                    if isinstance(value, list):
                        for entry in value:
                            replace = entry.get("replace_with", "?")
                            line = entry.get("line", "?")
                            lines.append(f"  - [{section}] {line} -> {replace}")
                    elif isinstance(value, dict):
                        info = ", ".join(f"{k}={v}" for k, v in value.items())
                        lines.append(f"  - [{section}] {info}")
            else:
                lines.append(f"  - raw: {sections}")
        lines.append("")

    import_counts = report.get("import_counts", {})
    if import_counts:
        lines.append("=== Python Import Counts (pheno.*) ===")
        for top, count in sorted(import_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"{top}: {count} files")
        lines.append("")

    doc_refs = report.get("docs_references", [])
    if doc_refs:
        lines.append("=== Documentation References to src/pheno ===")
        for doc in sorted(doc_refs):
            lines.append(f"  - {doc}")
        lines.append("")

    return "\n".join(lines)
