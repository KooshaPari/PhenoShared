"""Quickstart: pheno-worklog-schema

Run with::

    python examples/quickstart.py

Builds a v2.1 WORKLOG.md table inline, parses it back, and validates every
row. Demonstrates the public API without touching any actual repo file.
"""

from __future__ import annotations

from pathlib import Path

from pheno_worklog_schema import (
    COLUMN_NAMES,
    WORKLOG_COLUMNS,
    parse_worklog,
    validate_row,
    to_jsonl,
    stats,
)


SAMPLE_TABLE = """| Date       | Task ID    | Layer     | Action | Files        | Notes                  | Status     | Author   | Device       | Pr |
|------------|------------|-----------|--------|--------------|------------------------|------------|----------|--------------|----|
| 2026-06-18 | V4-1.2.3   | L1        | commit | WORKLOG.md   | example row            | done       | koosha   | macbook      | 0  |
| 2026-06-18 | V4-1.2.4   | L3        | doc    | SPEC.md      | tier 0 spec            | done       | koosha   | macbook      | 0  |
| 2026-06-18 | V20-1.9    | V20       | doc    | README.md    | crutch verification    | for_review | koosha   | heavy-runner | 42 |
"""


def main() -> None:
    print(f"COLUMN_NAMES = {COLUMN_NAMES}")
    print(f"WORKLOG_COLUMNS = {WORKLOG_COLUMNS}")
    print()

    entries = parse_worklog(SAMPLE_TABLE)
    print(f"parsed {len(entries)} entries")
    for entry in entries:
        cols = [getattr(entry, name) for name in WORKLOG_COLUMNS]
        errs = validate_row(cols)
        print(f"  {entry.task_id} layer={entry.layer} status={entry.status} errs={errs}")

    print()
    print("jsonl:", to_jsonl(entries)[:1], "...")
    print("stats:", stats(entries))


if __name__ == "__main__":
    main()