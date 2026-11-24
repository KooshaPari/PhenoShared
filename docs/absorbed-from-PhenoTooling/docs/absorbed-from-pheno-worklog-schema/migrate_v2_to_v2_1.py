"""Migrate WORKLOG.md files to canonical v2.1 (11-col).

ADR-015 / ADR-023 / ADR-025: Adds the `device:` column to all rows. v2.0
(10-col lowercase) input gets the device column inserted at position 9.
v1 (6-col capital) and v1+device (7-col capital + trailing device) inputs
are remapped to v2.1 semantics (see _migrate_v1_to_v21). v2.1 input is a
no-op (idempotent). v2.0 / v1 / v1+device legacy rows keep the device
cell empty unless the source already had one set (v1+device only).

Usage:
    # Migrate a single file (auto-detects v2.0, v1, v1+device)
    python migrate_v2_to_v2_1.py path/to/WORKLOG.md

    # Migrate all WORKLOG.md files in a directory tree
    python migrate_v2_to_v2_1.py --repo path/to/repo

    # Dry-run (no writes)
    python migrate_v2_to_v2_1.py --dry-run path/to/WORKLOG.md

    # Force-migrate even if file is already v2.1
    python migrate_v2_to_v2_1.py --force path/to/WORKLOG.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# v2.0 header (10-col) — the trigger for migration
V20_HEADER = [
    "task_id", "date", "repo", "category", "title",
    "commit_sha", "pr_number", "status", "author", "notes",
]
# v2.1 header (11-col) — the target
V21_HEADER = V20_HEADER[:9] + ["device"] + V20_HEADER[9:]

# v1 header (6-col, capital, legacy) — source: pheno-worklog-schema
# schema.py WORKLOG_COLUMNS.
V1_HEADER = ["Date", "Task ID", "Layer", "Action", "Files", "Notes"]
# v1+device header (7-col, capital + trailing device) — pre-v2.1 hybrid
# tolerated variant (used in pheno-config, pheno-context, pheno-otel,
# pheno-port-adapter; see L5-103.5 sweep summary 2026-06-18).
V1P_HEADER = V1_HEADER + ["device"]

# Semantic mapping for v1 (and v1+device) → v2.1:
#   v1 col 0 (Date)        → v2.1 col 1 (date)
#   v1 col 1 (Task ID)     → v2.1 col 0 (task_id)
#   v1 col 2 (Layer)       → v2.1 col 3 (category)
#   v1 col 3 (Action)      → v2.1 col 4 (title)
#   v1 col 4 (Files)       → v2.1 col 10 (notes, prefixed with "files: ")
#   v1 col 5 (Notes)       → v2.1 col 10 (notes, appended)
#   v1+device col 6 (device) → v2.1 col 9 (device) — only present in v1+device
#   v2.1 empty cols        → v2.1 cols 2/5/6/7/8 (repo, commit_sha,
#                            pr_number, status, author) — unknown in v1
# Files and Notes are combined into the v2.1 notes cell as
# "files: <files> + <notes>" (or just the non-empty half). ' + ' is
# used (not ' | ') because '|' is the markdown table column delimiter
# and would corrupt the table structure.

# Separator row (visual divider between header and data).
# Must contain at least one `---` so that stray `| ` lines don't get
# mistaken for separators.
_SEPARATOR_RE = re.compile(r"^\s*\|[\s|:\-]*---[\s|:\-]*$")


def is_v21(text: str) -> bool:
    """Return True if text contains a v2.1 (11-col) header."""
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip().lower() for c in s.strip("|").split("|")]
        if cells == V21_HEADER:
            return True
    return False


def is_v20(text: str) -> bool:
    """Return True if text contains a v2.0 (10-col) header."""
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip().lower() for c in s.strip("|").split("|")]
        if cells == V20_HEADER:
            return True
    return False


def is_v1(text: str) -> bool:
    """Return True if text contains a v1 (6-col, capital) header."""
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells == V1_HEADER:
            return True
    return False


def is_v1p(text: str) -> bool:
    """Return True if text contains a v1+device (7-col) header.

    The v1+device hybrid is a pre-v2.1 tolerated variant used in 4 fleet
    files (pheno-config, pheno-context, pheno-otel, pheno-port-adapter).
    Migration to canonical v2.1 preserves the trailing `device` value.
    """
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells == V1P_HEADER:
            return True
    return False


def detect_format(text: str) -> str:
    """Detect the worklog format.

    Returns one of: 'v21', 'v20', 'v1p', 'v1', 'none'.
    Order of checks: v2.1 (most strict) > v2.0 > v1+device > v1 > none.
    'none' means the file is not a recognized worklog schema (e.g. it
    may be a sprint board, an empty file, or a free-form markdown doc).
    """
    if is_v21(text):
        return "v21"
    if is_v20(text):
        return "v20"
    if is_v1p(text):
        return "v1p"
    if is_v1(text):
        return "v1"
    return "none"


def _migrate_v1_to_v21(cells: List[str], has_device: bool) -> List[str]:
    """Map a v1 (6-col) or v1+device (7-col) data row to a v2.1 (11-col) row.

    cells: 6 cells (v1) or 7 cells (v1+device).
    has_device: True if the source has the trailing device cell.
    Returns 11 cells in canonical v2.1 order:
        [task_id, date, repo, category, title, commit_sha, pr_number,
         status, author, device, notes]
    """
    date_v, task_id, layer, action, files_, notes = cells[:6]
    device = cells[6] if has_device else ""
    parts = []
    if files_:
        parts.append(f"files: {files_}")
    if notes:
        parts.append(notes)
    # Use ' + ' (not ' | ') to combine Files + Notes into the single
    # v2.1 notes cell. The '|' character would conflict with the markdown
    # table column delimiter; '+' is unambiguous in the markdown table
    # grammar and round-trips correctly through the v2.1 parser.
    notes_v21 = " + ".join(parts) if parts else ""
    return [
        task_id,    # task_id    (v2.1 col 0)
        date_v,     # date       (v2.1 col 1)
        "",         # repo       (v2.1 col 2 — unknown in v1)
        layer,      # category   (v2.1 col 3)
        action,     # title      (v2.1 col 4)
        "",         # commit_sha (v2.1 col 5 — unknown in v1)
        "",         # pr_number  (v2.1 col 6 — unknown in v1)
        "",         # status     (v2.1 col 7 — unknown in v1)
        "",         # author     (v2.1 col 8 — unknown in v1)
        device,     # device     (v2.1 col 9)
        notes_v21,  # notes      (v2.1 col 10)
    ]


def _migrate_v1_text(text: str, has_device: bool) -> Tuple[str, int]:
    """Migrate a v1 (6-col) or v1+device (7-col) text to canonical v2.1.

    Returns (new_text, rows_migrated).
    """
    old_header = V1P_HEADER if has_device else V1_HEADER
    lines = text.splitlines()
    out_lines: List[str] = []
    rows_migrated = 0
    sep_with_spaces = True
    for line in lines:
        s = line.strip()
        if s.startswith("|"):
            if "---" in s:
                sep_with_spaces = " " in s
                break
    n_cols = 11
    new_sep = ("| " + " | ".join(["---"] * n_cols) + " |") if sep_with_spaces \
        else ("|" + "|".join(["---"] * n_cols) + "|")
    new_header_line = ("| " + " | ".join(V21_HEADER) + " |") if sep_with_spaces \
        else ("|" + "|".join(V21_HEADER) + "|")
    in_table = False
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            out_lines.append(line)
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells == old_header:
            out_lines.append(new_header_line)
            in_table = True
            continue
        if in_table and _SEPARATOR_RE.match(s):
            out_lines.append(new_sep)
            continue
        if in_table and len(cells) >= 6:
            new_cells = _migrate_v1_to_v21(cells, has_device)
            out_lines.append(
                ("| " + " | ".join(new_cells) + " |") if sep_with_spaces
                else ("|" + "|".join(new_cells) + "|")
            )
            rows_migrated += 1
            continue
        out_lines.append(line)
    return ("\n".join(out_lines) + ("\n" if text.endswith("\n") else ""),
            rows_migrated)


def migrate_text(text: str) -> Tuple[str, int]:
    """In-place migration to canonical v2.1 (11-col).

    Supports source formats: v2.0 (10-col lowercase), v1 (6-col capital),
    v1+device (7-col capital + trailing device). v2.1 input is a no-op.
    v2.0 input has the device column inserted at position 9.
    v1 / v1+device input has columns remapped to v2.1 semantics
    (see _migrate_v1_to_v21).

    Returns (new_text, rows_migrated).
    Idempotent: if text is already v2.1, returns (text, 0).
    If text is not a recognized worklog format, returns (text, 0).
    """
    if is_v21(text):
        return text, 0
    if is_v20(text):
        return _migrate_v20_text(text)
    if is_v1p(text):
        return _migrate_v1_text(text, has_device=True)
    if is_v1(text):
        return _migrate_v1_text(text, has_device=False)
    return text, 0


def _migrate_v20_text(text: str) -> Tuple[str, int]:
    """Migrate a v2.0 (10-col) text to v2.1 (11-col) by inserting the device column at position 9."""

    lines = text.splitlines()
    out_lines: List[str] = []
    rows_migrated = 0
    in_table = False
    # Detect the separator style of the input (with or without spaces)
    # so the output matches the source file's formatting.
    sep_with_spaces = True  # default
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells == V20_HEADER:
            continue
        if _SEPARATOR_RE.match(s) and any("---" in c for c in cells):
            sep_with_spaces = " " in s
            break
    new_sep = "| " + " | ".join(["---"] * 11) + " |" if sep_with_spaces \
        else "|" + "|".join(["---"] * 11) + "|"
    new_header = "| " + " | ".join(V21_HEADER) + " |" if sep_with_spaces \
        else "|" + "|".join(V21_HEADER) + "|"

    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            out_lines.append(line)
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        lc = [c.lower() for c in cells]
        if lc == V20_HEADER:
            # Replace header with v2.1 (preserving source separator style)
            out_lines.append(new_header)
            in_table = True
            continue
        if in_table and _SEPARATOR_RE.match(s):
            # Replace separator with 11 dashes (preserving source style)
            out_lines.append(new_sep)
            continue
        if in_table and len(cells) == 10:
            # Insert empty device cell at position 9
            new_cells = cells[:9] + [""] + cells[9:]
            out_lines.append("| " + " | ".join(new_cells) + " |")
            rows_migrated += 1
            continue
        out_lines.append(line)

    return "\n".join(out_lines) + ("\n" if text.endswith("\n") else ""), rows_migrated


def migrate_file(path: Path, force: bool = False, dry_run: bool = False) -> int:
    """Migrate a single WORKLOG.md file in place.

    Returns the number of rows migrated.

    With force=True, an already-v2.1 file is also "migrated" (counted as
    having been touched). The output is identical to the input in that
    case, so no write occurs.
    """
    text = path.read_text()
    fmt = detect_format(text)
    if fmt == "none":
        return 0
    if fmt == "v21" and not force:
        return 0
    new_text, n = migrate_text(text)
    if n == 0 and force and is_v21(text):
        # Force-migrate on an already-v2.1 file: count rows without
        # rewriting (output is identical to input).
        n = sum(1 for line in text.splitlines()
                if line.strip().startswith("|")
                and not _SEPARATOR_RE.match(line.strip())
                and [c.strip().lower() for c in line.strip().strip("|").split("|")] != V21_HEADER)
    if not dry_run and new_text != text:
        path.write_text(new_text)
    return n


def migrate_repo(root: Path, force: bool = False, dry_run: bool = False) -> Tuple[int, int]:
    """Walk a repo and migrate all WORKLOG.md files.

    Returns (files_migrated, total_rows_migrated).
    """
    files_migrated = 0
    total_rows = 0
    for wl in root.rglob("WORKLOG.md"):
        n = migrate_file(wl, force=force, dry_run=dry_run)
        if n > 0:
            files_migrated += 1
            total_rows += n
            print(f"  migrated {n:3d} rows: {wl.relative_to(root)}")
    return files_migrated, total_rows


def main() -> int:
    p = argparse.ArgumentParser(
        description="Migrate WORKLOG.md to canonical v2.1 (11-col). "
                    "Auto-detects v2.0 (10-col lowercase), v1 (6-col capital), "
                    "and v1+device (7-col capital + device) source formats."
    )
    p.add_argument("path", help="Path to WORKLOG.md or a repo root (with --repo)")
    p.add_argument("--repo", action="store_true",
                   help="Treat path as repo root; walk all WORKLOG.md under it")
    p.add_argument("--force", action="store_true",
                   help="Force-migrate even if file is already v2.1")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would change but don't write")
    args = p.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"ERROR: {target} does not exist", file=sys.stderr)
        return 1

    if args.repo or target.is_dir():
        n_files, n_rows = migrate_repo(target, force=args.force, dry_run=args.dry_run)
        if n_files == 0:
            print(f"No v2.0/v1/v1+device WORKLOG.md files found under {target}")
            return 0
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Migrated {n_rows} rows across {n_files} files")
        return 0

    n = migrate_file(target, force=args.force, dry_run=args.dry_run)
    if n == 0:
        fmt = detect_format(target.read_text())
        if fmt == "v21":
            print(f"{target}: already v2.1 (use --force to re-migrate)")
        elif fmt == "none":
            print(f"{target}: no recognized worklog header found, skipping")
        else:
            print(f"{target}: detected {fmt} but no rows migrated (use --force to re-migrate)")
        return 0
    fmt = detect_format(target.read_text()) if args.dry_run else None
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Migrated {n} rows in {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
