"""Schema for `WORKLOG.md` for Phenotype repos.

Implements §77.4 of `FLEET_100TASK_DAG_V4.md` and ADR-015 v2.1 (device: column).

Three formats are supported:

**V1 (6-column, legacy):**
    | Date | Task ID | Layer | Action | Files | Notes |

**V2.0 (10-column, fleet-automation friendly):**
    | task_id | date | repo | category | title | commit_sha | pr_number | status | author | notes |

**V2.1 (11-column, current — adds device-fit gate per ADR-015/ADR-023):**
    | task_id | date | repo | category | title | commit_sha | pr_number | status | author | device | notes |

Public API:
- WorklogEntry: dataclass
- parse_worklog(path_or_text): list of WorklogEntry (auto-detects v1 / v2.0 / v2.1)
- validate_row(cols): list of error messages
- validate_entry(entry): list of error messages
- to_jsonl(entries): list of JSONL strings
- stats(entries): dict of counts (incl. by_device, missing_device per ADR-023)
- add_entry(path, entry): updated markdown text (emits v2.1 header)
- WORKLOG_COLUMNS, EXPECTED_COLUMNS, EXPECTED_COLUMNS_V20, COLUMN_NAMES, TASK_ID_RE
- CANONICAL_DEVICES: tuple of allowed device values
"""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, List, Optional, Sequence, Union

# V1 (6-column) schema
WORKLOG_COLUMNS = ["Date", "Task ID", "Layer", "Action", "Files", "Notes"]

# V2.0 (10-column) schema — kept for legacy readers
EXPECTED_COLUMNS_V20 = [
    "task_id", "date", "repo", "category", "title",
    "commit_sha", "pr_number", "status", "author", "notes",
]

# V2.1 (11-column) schema — adds `device:` per ADR-015 + ADR-023
EXPECTED_COLUMNS = [
    "task_id", "date", "repo", "category", "title",
    "commit_sha", "pr_number", "status", "author", "device", "notes",
]
COLUMN_NAMES = EXPECTED_COLUMNS

# Allowed device values per ADR-023 (device-fit gate).
# Empty string is permitted for legacy v2.0 entries (will be flagged by
# `stats()` as "missing-device" but is not a hard validation error).
CANONICAL_DEVICES = (
    "",              # legacy v2.0 entries (counted in stats.missing_device)
    "macbook",       # light work: plan, ADR, small PR, dogfood (default for most)
    "heavy-runner",  # heavy work: full cargo test --workspace, iOS Sim, Docker-in-Docker, Unity head, >10min build/test
    "subagent",      # work performed by a subagent (dispatch-mcp / forge / muse)
    "ci",            # work performed by a CI runner
)

# Regex for V*-DAG task IDs:
#   V4-1.2.3        (numeric, dots allowed in subsequent parts)
#   V11-CC-5        (side-dag letter)
#   V6-EXT-2-1      (V6-EXT-2 tier)
TASK_ID_RE = re.compile(r"^V\d+-[A-Z0-9]+(?:[.\-][A-Z0-9]+)*$")

# Canonical layers
CANONICAL_LAYERS = (
    "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9",
    "L10", "L11", "L12", "L13", "L14", "L15", "L16",
)
SIDE_DAGS = tuple(f"Side-{c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ") \
    + tuple(f"Side-{a}{b}" for a in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for b in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
CANONICAL_LAYERS_OR_SIDE = CANONICAL_LAYERS + SIDE_DAGS + ("Meta",)

# Canonical actions
CANONICAL_ACTIONS = (
    "commit", "merge", "close", "archive", "doc", "plan", "deploy", "release",
)

# Canonical status values for V2
CANONICAL_STATUS = (
    "open", "in_progress", "merged", "closed", "abandoned", "deferred",
)

# Date validation regex (ISO-8601 YYYY-MM-DD)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# --- V1 (6-col) dataclass ---------------------------------------------------

@dataclass
class WorklogEntry:
    """A WORKLOG.md entry. Supports V1, V2.0, and V2.1 schemas.

    V1 fields (required): date, task_id, layer, action, files, notes
    V2.0 fields (optional): repo, category, title, commit_sha, pr_number,
                            status, author
    V2.1 fields (optional, ADR-015/ADR-023): device

    `category` is a free-form string for V2 (e.g. "L1-Stabilize",
    "Side-A-lib", "V12-crutch").

    `device` is one of CANONICAL_DEVICES. Empty string "" is allowed for
    legacy v2.0 entries and is counted in stats()["missing_device"].
    """
    # V1 fields
    date: Union[date, str]
    task_id: str
    layer: str = "L?"
    action: str = "commit"
    files: List[str] = field(default_factory=list)
    notes: str = ""
    # V2.0 fields (optional)
    repo: str = ""
    category: str = ""
    title: str = ""
    commit_sha: Optional[str] = None
    pr_number: Optional[int] = None
    status: str = "open"
    author: str = ""
    # V2.1 field (optional, ADR-015/ADR-023 device-fit gate)
    device: str = ""


# --- V1 validation ----------------------------------------------------------

def validate_entry(entry: WorklogEntry) -> List[str]:
    """Validate a V1 WorklogEntry. Return a list of error messages (empty if valid)."""
    errors: List[str] = []
    if not TASK_ID_RE.match(entry.task_id):
        errors.append(f"Task ID {entry.task_id!r} does not match {TASK_ID_RE.pattern}")
    if entry.layer not in CANONICAL_LAYERS_OR_SIDE:
        errors.append(
            f"Layer {entry.layer!r} is not canonical. Allowed: {', '.join(CANONICAL_LAYERS_OR_SIDE[:10])}, ..."
        )
    if entry.action not in CANONICAL_ACTIONS:
        errors.append(
            f"Action {entry.action!r} is not canonical. Allowed: {', '.join(CANONICAL_ACTIONS)}"
        )
    if not entry.files:
        errors.append("Files is empty (must list at least one path)")
    return errors


# --- V2 row validation ------------------------------------------------------

def validate_row(cols: Sequence[str]) -> List[str]:
    """Validate a V2.1 (11-column) row. Accepts V2.0 (10-col) with a soft warning.

    Expected columns (11):
        task_id, date, repo, category, title, commit_sha,
        pr_number, status, author, device, notes

    v2.0 (10-col) rows are accepted for backwards compat. They are not
    a hard error; stats() will report them under "missing_device".

    v2.1 (11-col) rows are validated strictly: device must be in
    CANONICAL_DEVICES (or "" for legacy compat — this is the only case
    where an empty device is permitted at row-validate time).
    """
    errors: List[str] = []
    if len(cols) not in (10, 11):
        errors.append(f"row has {len(cols)} columns, expected 10 (v2.0) or 11 (v2.1)")
        return errors

    # v2.0 compatibility: pad with empty device in position 9
    if len(cols) == 10:
        cols = list(cols[:9]) + [""] + list(cols[9:])

    task_id, date_str, _repo, _cat, _title, _sha, pr, status, _author, device, _notes = cols
    if not TASK_ID_RE.match(task_id):
        errors.append(f"task_id {task_id!r} does not match V*-N.N.N pattern")
    if not _DATE_RE.match(date_str):
        errors.append(f"date {date_str!r} is not ISO-8601 YYYY-MM-DD")
    if status and status not in CANONICAL_STATUS:
        errors.append(f"status {status!r} is not in {CANONICAL_STATUS}")
    if pr and not pr.isdigit():
        errors.append(f"pr_number {pr!r} is not an integer")
    if device and device not in CANONICAL_DEVICES:
        errors.append(
            f"device {device!r} is not in CANONICAL_DEVICES. "
            f"Allowed: macbook | heavy-runner | subagent | ci | (empty for legacy v2.0)"
        )
    return errors


# --- V1 parser --------------------------------------------------------------

def _parse_worklog_text_v1(text: str) -> List[WorklogEntry]:
    """Parse WORKLOG.md v1 (6-column) text content."""
    entries: List[WorklogEntry] = []
    header_cols: Optional[List[str]] = None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            header_cols = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.match(r"^:?-+:?$", c) for c in cells):
            continue
        if header_cols is None:
            header_cols = cells
            if header_cols[:6] != WORKLOG_COLUMNS:
                header_cols = None
            continue
        if len(cells) < 6:
            continue
        try:
            entry = WorklogEntry(
                date=date.fromisoformat(cells[0]),
                task_id=cells[1],
                layer=cells[2],
                action=cells[3].lower(),
                files=[f.strip() for f in cells[4].split(",") if f.strip()],
                notes=cells[5],
            )
            entries.append(entry)
        except (ValueError, IndexError):
            continue
    return entries


# --- V2 parser --------------------------------------------------------------

def _parse_worklog_text_v2(text: str) -> List[WorklogEntry]:
    """Parse WORKLOG.md v2.0 (10-col) or v2.1 (11-col) text content.

    Auto-detects format by column count. Returns WorklogEntry objects with
    `device` field populated for v2.1 rows and "" for v2.0 rows.

    Emits a ``DeprecationWarning`` when a v2.0 (10-col) format is detected.
    """
    entries: List[WorklogEntry] = []
    header_cols: Optional[List[str]] = None
    _v20_warning_emitted = False
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            header_cols = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.match(r"^:?-+:?$", c) for c in cells):
            continue
        if header_cols is None:
            header_cols = cells
            lc = [c.lower() for c in header_cols]
            if lc != [c.lower() for c in EXPECTED_COLUMNS] and \
               lc != [c.lower() for c in EXPECTED_COLUMNS_V20]:
                header_cols = None
                continue
            # Emit deprecation warning for v2.0 (10-col) format
            if len(header_cols) == 10 and lc == [c.lower() for c in EXPECTED_COLUMNS_V20]:
                if not _v20_warning_emitted:
                    warnings.warn(
                        "v2.0 (10-col) WORKLOG.md format is deprecated. "
                        "Migrate to v2.1 (11-col) by 2026-06-22. "
                        "See SPEC-v2.1.md or run migrate_v2_to_v2_1.py.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    _v20_warning_emitted = True
            continue
        if len(cells) < 10:
            continue
        try:
            is_v21 = len(cells) >= 11
            pr_val = int(cells[6]) if cells[6] else None
            if is_v21:
                entry = WorklogEntry(
                    date=date.fromisoformat(cells[1]),
                    task_id=cells[0],
                    layer=cells[3] or "L?",
                    action="merge" if cells[7] == "merged" else "commit",
                    files=[],
                    notes=cells[10],
                    repo=cells[2],
                    category=cells[3],
                    title=cells[4],
                    commit_sha=cells[5] or None,
                    pr_number=pr_val,
                    status=cells[7] or "open",
                    author=cells[8],
                    device=cells[9],
                )
            else:
                entry = WorklogEntry(
                    date=date.fromisoformat(cells[1]),
                    task_id=cells[0],
                    layer=cells[3] or "L?",
                    action="merge" if cells[7] == "merged" else "commit",
                    files=[],
                    notes=cells[9],
                    repo=cells[2],
                    category=cells[3],
                    title=cells[4],
                    commit_sha=cells[5] or None,
                    pr_number=pr_val,
                    status=cells[7] or "open",
                    author=cells[8],
                    device="",
                )
            entries.append(entry)
        except (ValueError, IndexError):
            continue
    return entries


def _is_v2_header_line(line: str) -> bool:
    """Return True if `line` is a v2 (v2.0 10-col or v2.1 11-col) header.

    A v2 header row starts with `|`, has 10 or 11 cells after stripping
    whitespace, and the first cell is `task_id` (case-insensitive).
    This is column-count + first-cell based so it accepts BOTH
    ``| task_id | date | ...`` (with surrounding spaces) and
    ``|task_id|date|...`` (no spaces) — both formats are produced by
    `migrate_v2_to_v2_1.py` depending on the `sep_with_spaces` toggle.

    The previous literal-string check
    (``if "| task_id" in text.lower()``) was too strict and rejected
    the no-space variant, causing the substrate's own WORKLOG.md (which
    the migration script writes without spaces) to parse to 0 entries
    — a silent bug masked by a vacuous test (see PR-3 / L5-103.x).
    """
    s = line.strip()
    if not s.startswith("|"):
        return False
    cells = [c.strip().lower() for c in s.strip("|").split("|")]
    if len(cells) not in (10, 11):
        return False
    return cells[0] == "task_id"


def _has_v2_header(text: str) -> bool:
    """Return True if `text` contains a v2 (v2.0 / v2.1) header row."""
    return any(_is_v2_header_line(line) for line in text.splitlines())


def parse_worklog(source: Union[str, Path]) -> List[WorklogEntry]:
    """Parse a WORKLOG.md file (or text) and return entries.

    Auto-detects v1 (6-col), v2.0 (10-col), or v2.1 (11-col) format from
    the header. Accepts both spaced (``| task_id | ...``) and
    unspaced (``|task_id|...``) header styles (per L5-103.x fix).
    """
    if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and Path(source).exists()):
        text = Path(source).read_text()
    else:
        text = source
    # Try v2 first (covers both v2.0 and v2.1 — they share the 10-col
    # header prefix). Detection is by column count + first cell, so it
    # accepts BOTH spaced and unspaced header styles.
    if _has_v2_header(text):
        v2_entries = _parse_worklog_text_v2(text)
        if v2_entries:
            return v2_entries
    return _parse_worklog_text_v1(text)


# --- Serializers ------------------------------------------------------------

def to_jsonl(entries: Sequence[WorklogEntry]) -> List[str]:
    """Serialize a list of WorklogEntry to JSONL strings."""
    out: List[str] = []
    for e in entries:
        d = asdict(e)
        # Convert date to string
        if isinstance(d.get("date"), date):
            d["date"] = d["date"].isoformat()
        out.append(json.dumps(d, default=str))
    return out


def stats(entries: Sequence[WorklogEntry]) -> dict:
    """Compute aggregate statistics over a list of WorklogEntry.

    v2.1 additions (ADR-015/ADR-023 device-fit gate):
    - by_device: count of entries per device value
    - missing_device: count of entries with device="" (legacy v2.0 rows)
    """
    by_status: dict = {}
    by_repo: dict = {}
    by_layer: dict = {}
    by_device: dict = {}
    missing_device = 0
    for e in entries:
        by_status[e.status] = by_status.get(e.status, 0) + 1
        if e.repo:
            by_repo[e.repo] = by_repo.get(e.repo, 0) + 1
        if e.layer:
            by_layer[e.layer] = by_layer.get(e.layer, 0) + 1
        by_device[e.device] = by_device.get(e.device, 0) + 1
        if not e.device:
            missing_device += 1
    return {
        "total": len(entries),
        "by_status": by_status,
        "by_repo": by_repo,
        "by_layer": by_layer,
        "by_device": by_device,
        "missing_device": missing_device,
    }


def add_entry(worklog_path: Path, new_entry: WorklogEntry) -> str:
    """Append a V2.1 (11-col) entry to an existing WORKLOG.md and return the text.

    The file must already have a v2 header (v2.0 or v2.1); otherwise the
    helper inserts a fresh v2.1 header at the end.
    """
    path = Path(worklog_path)
    text = path.read_text() if path.exists() else ""
    row = [
        new_entry.task_id,
        new_entry.date if isinstance(new_entry.date, str) else new_entry.date.isoformat(),
        new_entry.repo,
        new_entry.category,
        new_entry.title,
        new_entry.commit_sha or "",
        str(new_entry.pr_number) if new_entry.pr_number else "",
        new_entry.status,
        new_entry.author,
        new_entry.device,  # v2.1: device-fit gate (ADR-015/ADR-023)
        new_entry.notes,
    ]
    row_str = "|" + "|".join(row) + "|"  # match migrate_v2_to_v2_1.py no-space default
    if not _has_v2_header(text):
        # Insert a fresh v2.1 header at end. Default to no-space style
        # (matches migrate_v2_to_v2_1.py default and the substrate's
        # own WORKLOG.md convention).
        header = "|" + "|".join(EXPECTED_COLUMNS) + "|\n"
        sep = "|" + "|".join(["---"] * 11) + "|\n"
        text = text.rstrip() + "\n\n" + header + sep + row_str + "\n"
    else:
        # Append before any trailing non-table text. Match the
        # existing file's row style (spaced vs. unspaced) so we
        # don't introduce a second style into the same file.
        spaced = any(
            line.strip().startswith("| ") and " | " in line
            for line in text.splitlines()
            if line.strip().startswith("|")
        )
        if spaced:
            row_str = "| " + " | ".join(row) + " |"
        else:
            row_str = "|" + "|".join(row) + "|"
        text = text.rstrip() + "\n" + row_str + "\n"
    return text
