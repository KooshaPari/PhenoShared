#!/usr/bin/env python3
"""build_dash_aggregate.py - Build a tiny, dashboard-safe aggregate SQLite.

Reads the 16 GB unified corpus `research_ledger.sqlite` STRICTLY via the
existing read-only public CLI `ask_research_ledger.py` (mode=ro URI), runs
a curated list of cheap aggregate presets, and writes one table per preset
into `dash_aggregate.sqlite`. Build is atomic (write-to-temp then rename) and
fully re-runnable.

Hard constraints honoured:
  * Never imports sqlite3 against the corpus. Only `ask_research_ledger.py`
    touches it, and only through its `--preset` + `--format csv` interface.
  * Never touches the corpus or its sealed backup with a write-capable handle.
  * Does not modify corpus_guard.py, migrators, builders, tests, or .gitignore.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone


HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(HERE, "ask_research_ledger.py")
CORPUS = os.path.expanduser("~/Exports/analysis/research_ledger.sqlite")
DEFAULT_OUT = os.path.join(HERE, "dash_aggregate.sqlite")

# Presets that must show up in the dashboard aggregate.
# Order matters only for the printed summary; it's a static, dependency-free
# materialisation of values the dashboard would otherwise recompute on every
# query against the 16 GB corpus.
PRESETS = [
    "counts",
    "by-source",
    "by-day",
    "by-model",
    "by-author",
    "by-confidence",
    "tokens-by-model",
    "attachments-by-kind",
    "dedupe-stats",
    "fts-coverage",
]

# Per-preset CLI timeout (seconds). Whole-corpus scans (tokens-by-model) took
# ~51s on this hardware; double that for headroom.
TIMEOUTS = {p: 600 for p in PRESETS}


def safe_ident(name: str) -> str:
    """Map an arbitrary preset name to a valid SQLite table identifier."""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
    if not s or not (s[0].isalpha() or s[0] == "_"):
        s = "t_" + s
    return s.lower()


def run_preset(preset: str, timeout: int) -> tuple[list[str], list[tuple], str | None]:
    """Invoke the read-only CLI and parse CSV output. Returns (cols, rows, error)."""
    cmd = [
        sys.executable,
        CLI,
        "--db", CORPUS,
        "--preset", preset,
        "--format", "csv",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return [], [], f"timeout after {timeout}s"

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip().splitlines()
        return [], [], f"exit {proc.returncode}: " + (msg[-1] if msg else "no output")

    reader = csv.reader(io.StringIO(proc.stdout))
    rows = [r for r in reader if r]
    if not rows:
        return [], [], None
    header, *data = rows
    cols = [c.strip() for c in header]
    norm = [tuple((c if c != "" else None) for c in r) for r in data]
    return cols, norm, None


def quote_ident(name: str) -> str:
    """Double-quote a SQLite identifier, escaping embedded double quotes."""
    return '"' + name.replace('"', '""') + '"'


def dedup_cols(cols: list[str]) -> list[str]:
    """Rename duplicate column names so CREATE TABLE accepts them.

    Some presets (e.g. attachments-by-kind) select the same logical field
    twice from different joined tables. csv.DictReader would collapse
    them anyway, and sqlite refuses a CREATE TABLE with duplicate column
    names. Append _2, _3, ... to the duplicates while keeping the first
    occurrence as-is.
    """
    seen: dict[str, int] = {}
    out: list[str] = []
    for c in cols:
        n = seen.get(c, 0)
        out.append(c if n == 0 else f"{c}_{n + 1}")
        seen[c] = n + 1
    return out


def write_table(cur: sqlite3.Cursor, table: str, cols: list[str], rows: list[tuple]) -> None:
    """Create + populate one aggregate table. Dedupes column names."""
    cols = dedup_cols(cols)
    col_ddl = ", ".join(f"{quote_ident(c)} TEXT" for c in cols)
    cur.execute(f'CREATE TABLE {quote_ident(table)} ({col_ddl})')
    if not rows:
        return
    placeholders = ",".join("?" for _ in cols)
    insert = f'INSERT INTO {quote_ident(table)} VALUES ({placeholders})'
    cur.executemany(insert, rows)


def build(out_path: str, dry_run: bool) -> int:
    if not os.path.exists(CORPUS):
        print(f"corpus missing: {CORPUS}", file=sys.stderr)
        return 2

    print(f"corpus: {CORPUS}")
    print(f"corpus size: {os.path.getsize(CORPUS):,} bytes")
    print(f"output: {os.path.abspath(out_path)}")
    print(f"presets to materialise ({len(PRESETS)}):")
    for p in PRESETS:
        print(f"  - {p} (table {safe_ident(p)!r}, timeout {TIMEOUTS[p]}s)")

    if dry_run:
        print("\n--dry-run: not running presets, not writing output.")
        return 0

    out_abs = os.path.abspath(out_path)
    tmp = out_abs + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)

    rows_by_preset: dict[str, list[tuple]] = {}
    cols_by_preset: dict[str, list[str]] = {}
    skipped: dict[str, str] = {}

    print("\nrunning presets:")
    for preset in PRESETS:
        t0 = time.monotonic()
        cols, rows, err = run_preset(preset, TIMEOUTS[preset])
        dt = time.monotonic() - t0
        if err is not None:
            print(f"  {preset:25s} SKIP ({dt:.1f}s)  {err}")
            skipped[preset] = err
            continue
        rows_by_preset[preset] = rows
        cols_by_preset[preset] = cols
        print(f"  {preset:25s} OK    ({dt:.1f}s)  rows={len(rows):,}")

    # Build the aggregate DB in a temp file, then atomically rename over.
    print(f"\nwriting {tmp} ...")
    with sqlite3.connect(tmp) as conn:
        cur = conn.cursor()
        for preset in PRESETS:
            if preset in skipped:
                continue
            write_table(cur, safe_ident(preset), cols_by_preset[preset], rows_by_preset[preset])

        # _meta: build provenance and per-preset status.
        cur.execute(
            "CREATE TABLE _meta (key TEXT PRIMARY KEY, value TEXT)"
        )
        cur.executemany(
            "INSERT INTO _meta VALUES (?, ?)",
            [
                ("build_started_utc", _ISO()),
                ("source_corpus_path", CORPUS),
                ("source_corpus_bytes", str(os.path.getsize(CORPUS))),
                ("cli_invocation", "ask_research_ledger.py --preset X --format csv"),
                ("preset_count", str(len(PRESETS))),
                ("preset_list", ",".join(PRESETS)),
            ],
        )
        for preset in PRESETS:
            cur.execute(
                "INSERT INTO _meta VALUES (?, ?)",
                (
                    f"rows.{safe_ident(preset)}",
                    str(len(rows_by_preset.get(preset, []))),
                ),
            )
        for preset, err in skipped.items():
            cur.execute(
                "INSERT INTO _meta VALUES (?, ?)",
                (f"skipped.{safe_ident(preset)}", err),
            )
        # closed_at filled at end so we know the build completed
        cur.execute("INSERT INTO _meta VALUES (?, ?)", ("build_closed_utc", _ISO()))
        conn.commit()

    os.replace(tmp, out_abs)
    size = os.path.getsize(out_abs)
    print(f"\natomically renamed -> {out_abs}")

    print("\nsummary:")
    print(f"  file            {out_abs}")
    print(f"  size            {size:,} bytes ({size / 1024 / 1024:.2f} MiB)")
    for preset in PRESETS:
        table = safe_ident(preset)
        if preset in skipped:
            print(f"  table {table:18s} SKIPPED  ({skipped[preset]})")
        else:
            print(
                f"  table {table:18s} rows={len(rows_by_preset[preset]):,}"
            )

    return 0


def _ISO() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help="output SQLite path (default: dash_aggregate.sqlite next to this script)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would happen; do not run presets, do not write anything",
    )
    args = ap.parse_args()
    return build(args.out, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
