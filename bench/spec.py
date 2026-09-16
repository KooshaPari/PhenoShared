"""Parser for the spec document — extracts suite metadata as machine-readable source-of-truth."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

try:
    import yaml

    _HAS_YAML = True
except Exception:  # pragma: no cover
    _HAS_YAML = False


@dataclass
class ParsedSuite:
    """One row extracted from the spec's §2 table."""

    name: str
    source_url: str
    format: str
    subset: str
    rationale: str
    extra: dict[str, Any]


@dataclass
class SpecFacts:
    """Top-level facts harvested from the spec."""

    doc_id: str
    version: str
    date: str
    status: str
    suites: list[ParsedSuite]
    metrics: list[str]


_FENCE_RE = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)
_TABLE_ROW_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*$")
_SECTION_RE = re.compile(r"^##\s+\d+\.(.+?)\s*$")


def _strip_md_table_row(row: str) -> list[str]:
    """Strip leading/trailing pipes; skip separator rows; return raw cells."""
    if not row.startswith("|"):
        return []
    inner = row[1:-1] if row.endswith("|") else row[1:]
    cells = [c.strip() for c in inner.split("|")]
    if cells and all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
        return []
    return cells


def _parse_suite_table(markdown: str) -> list[ParsedSuite]:
    """Parse the spec §2 markdown table into ParsedSuite rows.

    The spec table starts with `| # | Suite | ...`, so we detect the header and
    map columns by name. This tolerates both 5- and 6-column variants.
    """
    suites: list[ParsedSuite] = []
    lines = markdown.splitlines()
    in_target = False
    cols: dict[str, int] | None = None
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("## ") and "Suite selection" in line:
            in_target = True
            cols = None
            continue
        if not in_target:
            continue
        if line.startswith("## ") and "Suite selection" not in line:
            in_target = False
            break
        cells = _strip_md_table_row(line)
        if not cells:
            continue
        # Header row: find column indices by name, lowering header text.
        if cols is None:
            normalized = [c.lower().strip() for c in cells]
            if "suite" not in normalized and "source url" not in normalized:
                # not the suite table header (e.g. caveats table)
                continue
            cols = {c.lower(): i for i, c in enumerate(normalized)}
            # Common header variants
            cols.setdefault("source url", cols.get("source_url", -1))
            cols.setdefault("source", cols.get("source_url", -1))
            continue
        idx_name = cols.get("suite", -1)
        idx_url = cols.get("source url", cols.get("source_url", cols.get("source", -1)))
        idx_fmt = cols.get("format", -1)
        idx_subset = (
            cols.get("subset")
            or cols.get("subset for 5–10 min")
            or cols.get("subset for 5-10 min")
            or -1
        )
        idx_rationale = -1
        for key, idx in cols.items():
            if key.startswith("why") or key.startswith("rationale"):
                idx_rationale = idx
                break
        if idx_name < 0 or idx_url < 0:
            continue
        # Pull values with safe defaults.
        name_cell = cells[idx_name] if 0 <= idx_name < len(cells) else ""
        if name_cell.startswith("**"):
            m = re.search(r"\*\*(.+?)\*\*", name_cell)
            if m:
                name_cell = m.group(1)
        source_url = cells[idx_url] if 0 <= idx_url < len(cells) else ""
        fmt = cells[idx_fmt] if 0 <= idx_fmt < len(cells) else ""
        subset = cells[idx_subset] if 0 <= idx_subset < len(cells) else ""
        rationale = cells[idx_rationale] if 0 <= idx_rationale < len(cells) else ""
        suites.append(
            ParsedSuite(
                name=name_cell,
                source_url=source_url,
                format=fmt,
                subset=subset,
                rationale=rationale,
                extra={"row_index": cells[0] if cells else ""},
            )
        )
    return suites


def _list_metric_names(markdown: str) -> list[str]:
    """Extract listed metrics from §4 (lines beginning with backtick metric names)."""
    in_metrics = False
    names: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## ") and "Metrics matrix" in line:
            in_metrics = True
            continue
        if in_metrics and line.startswith("## "):
            break
        if in_metrics and line.lstrip().startswith("- `"):
            m = re.search(r"`([a-zA-Z_@0-9.\-/]+)`", line)
            if m:
                names.append(m.group(1))
    return names


def parse_spec(markdown: str) -> SpecFacts:
    """Parse the spec markdown text and return its key facts.

    Use `parse_spec_file` for the convenience wrapper that reads from disk.
    """
    doc_id = ""
    version = ""
    date = ""
    status = ""
    for raw in markdown.splitlines():
        line = raw.strip()
        # Strip the leading bold marker so that the value is the literal field.
        if line.startswith("**Doc ID:**"):
            doc_id = line[len("**Doc ID:**") :].strip()
        elif line.startswith("**Version:**"):
            version = line[len("**Version:**") :].strip()
        elif line.startswith("**Date:**"):
            date = line[len("**Date:**") :].strip()
        elif line.startswith("**Status:**"):
            status = line[len("**Status:**") :].strip()

    suites = _parse_suite_table(markdown)
    metrics = _list_metric_names(markdown)
    return SpecFacts(
        doc_id=doc_id,
        version=version,
        date=date,
        status=status,
        suites=suites,
        metrics=metrics,
    )


def parse_spec_file(path: str | Path) -> SpecFacts:
    """Read a spec file from disk and return its parsed facts."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    return parse_spec(p.read_text(encoding="utf-8"))


def to_yaml(facts: SpecFacts) -> str:
    """Serialize SpecFacts as YAML (requires pyyaml at runtime)."""
    if not _HAS_YAML:  # pragma: no cover
        raise RuntimeError("PyYAML is required for YAML serialization")
    payload = {
        "doc_id": facts.doc_id,
        "version": facts.version,
        "date": facts.date,
        "status": facts.status,
        "suites": [
            {
                "name": s.name,
                "source_url": s.source_url,
                "format": s.format,
                "subset": s.subset,
                "rationale": s.rationale,
                **s.extra,
            }
            for s in facts.suites
        ],
        "metrics": facts.metrics,
    }
    return cast(str, yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))


def spec_anchors(markdown: str) -> list[tuple[str, str]]:
    """Return (header_text, anchor) pairs for the spec sections, ordered as encountered."""
    anchors: list[tuple[str, str]] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            title = line.lstrip("# ").strip()
            anchor = (
                re.sub(r"\s+", "-", re.sub(r"[^a-zA-Z0-9\s-]", "", title))
                .strip("-")
                .lower()
            )
            anchors.append((title, anchor))
    return anchors
