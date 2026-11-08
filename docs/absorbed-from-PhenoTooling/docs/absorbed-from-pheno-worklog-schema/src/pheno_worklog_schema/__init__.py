"""pheno-worklog-schema: WORKLOG.md schema + validator for Phenotype repos.

Implements §77.4 of `FLEET_100TASK_DAG_V4.md` and ADR-032 (JSONL audit
trail emission).

Public API:
- WorklogEntry: dataclass
- parse_worklog(path_or_text): list of WorklogEntry
- validate_row(cols): list of error messages (V2 10-col)
- validate_entry(entry): list of error messages (V1 6-col)
- to_jsonl(entries): list of JSONL strings (full WorklogEntry dump)
- emit_jsonl(worklog, output, derived_at=None, tool_version=None) -> int:
  JSONL audit trail emission (ADR-032 § "JSONL audit trail")
- worklog_entry_to_json(entry, derived_at, tool_version) -> str:
  Convert one WorklogEntry to an ADR-032-compliant JSONL line
- stats(entries): dict of counts
- add_entry(path, entry): updated markdown text
- WORKLOG_COLUMNS, EXPECTED_COLUMNS, COLUMN_NAMES, TASK_ID_RE
- init_worklog: scaffold-kit entrypoint (V6 PR-6) that materializes a starter
  WORKLOG.md with the V2 column set.
"""

from pathlib import Path
from typing import Any, Union

from pheno_worklog_schema.schema import (
    WorklogEntry,
    parse_worklog,
    validate_row,
    validate_entry,
    to_jsonl,
    stats,
    add_entry,
    WORKLOG_COLUMNS,
    EXPECTED_COLUMNS,
    COLUMN_NAMES,
    TASK_ID_RE,
    CANONICAL_LAYERS,
    CANONICAL_LAYERS_OR_SIDE,
    CANONICAL_ACTIONS,
    CANONICAL_STATUS,
)
from pheno_worklog_schema.emit_jsonl import (
    emit_jsonl,
    worklog_entry_to_json,
    JSONL_FIELDS,
)


def init_worklog(repo_dir: Union[str, Path], **kwargs: Any) -> dict[str, Any]:
    """Scaffold-kit entrypoint (V6 PR-6): drop a starter WORKLOG.md."""
    root = Path(repo_dir).expanduser().resolve()
    if not root.exists():
        return {"ok": False, "error": f"Repository directory does not exist: {root}"}

    worklog = root / "WORKLOG.md"
    if worklog.exists():
        return {
            "ok": True,
            "repo_dir": str(root),
            "worklog": str(worklog),
            "already_present": True,
        }

    header = (
        "# WORKLOG\n\n"
        "| " + " | ".join(COLUMN_NAMES) + " |\n"
        "| " + " | ".join("---" for _ in COLUMN_NAMES) + " |\n"
    )
    try:
        worklog.write_text(header, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    return {
        "ok": True,
        "repo_dir": str(root),
        "worklog": str(worklog),
        "already_present": False,
    }


__version__ = "0.2.0"

__all__ = [
    "WorklogEntry",
    "parse_worklog",
    "validate_row",
    "validate_entry",
    "to_jsonl",
    "emit_jsonl",
    "worklog_entry_to_json",
    "JSONL_FIELDS",
    "stats",
    "add_entry",
    "WORKLOG_COLUMNS",
    "EXPECTED_COLUMNS",
    "COLUMN_NAMES",
    "TASK_ID_RE",
    "CANONICAL_LAYERS",
    "CANONICAL_LAYERS_OR_SIDE",
    "CANONICAL_ACTIONS",
    "CANONICAL_STATUS",
    "init_worklog",
]
