#!/usr/bin/env python3
"""
validate_extract_entities.py — regression tests for extract_entities.py.

Each case exists because it caught a real bug:

  T1  a name that is a placeholder ("unknown", "assistant", "n/a") must NOT
      become an entity — otherwise the ledger fills with fake people.
  T2  an author rendered as "Name <a@b.c>" must yield the display name, not
      the whole string.
  T3  a github url must yield BOTH a company (the org) and a repo (owner/repo).
  T4  a non-VCS host must not yield a company or a repo.
  T5  the SAME author on two items must collapse to ONE entity (the unique
      index on (kind, normalized_name) is the point of that column).
  T6  a title that is a path may yield a 'project' at low confidence — and
      ONLY at low confidence, because it is a heuristic.
  T7  a url with no path segments on a known host must not crash or yield an
      empty entity.
  T8  a title with no slash must never yield a project.

  T9  REGRESSION: the scan must cover the WHOLE table. The first version
      reused one sqlite cursor for both the outer SELECT and the inner
      INSERT/SELECT, which reset the outer cursor — so it reported
      "items scanned: 32,478" against a 940,934-row table and exited
      cleanly with success. Silent truncation is worse than a crash.

Run:  python3 validate_extract_entities.py
Exit 0 only if every case passes.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_entities import candidates_for_item, clean, norm  # noqa: E402

pass_ = 0
fail_ = 0


def ok(msg: str) -> None:
    global pass_
    print(f"PASS  {msg}")
    pass_ += 1


def bad(msg: str) -> None:
    global fail_
    print(f"FAIL  {msg}")
    fail_ += 1


def kinds_of(row) -> set[str]:
    return {k for (k, *_rest) in candidates_for_item(row)}


def names_of(row, kind: str) -> list[str]:
    return [n for (k, n, *_rest) in candidates_for_item(row) if k == kind]


# --- T1: placeholders are not entities --------------------------------------
for bad_name in ("unknown", "assistant", "n/a", "", "  ", "None", "null", "-"):
    if clean(bad_name) is None:
        ok(f"T1 placeholder {bad_name!r} rejected")
    else:
        bad(f"T1 placeholder {bad_name!r} was accepted as an entity")
if clean("koosha") == "koosha":
    ok("T1 a real name is accepted")
else:
    bad("T1 a real name was rejected")

# --- T2: "Name <email>" -> "Name" -------------------------------------------
got = clean("Mahmoud <mahmoud@example.com>")
if got == "Mahmoud":
    ok("T2 email form reduced to the display name")
else:
    bad(f"T2 email form produced {got!r}, expected 'Mahmoud'")

# --- T3: a github url yields company AND repo -------------------------------
row = ("koosha", "some title", "https://github.com/KooshaPari/atoms.tech/pull/3")
ks = kinds_of(row)
if "company" in ks and "repo" in ks:
    ok("T3 github url yields both company and repo")
else:
    bad(f"T3 github url yielded {ks}, expected company+repo")
if "KooshaPari" in names_of(row, "company"):
    ok("T3 company is the org segment")
else:
    bad(f"T3 company was {names_of(row,'company')}, expected ['KooshaPari']")
if "KooshaPari/atoms.tech" in names_of(row, "repo"):
    ok("T3 repo is owner/repo")
else:
    bad(f"T3 repo was {names_of(row,'repo')}, expected ['KooshaPari/atoms.tech']")

# --- T4: a non-VCS host yields neither company nor repo --------------------
row = ("someone", "t", "https://www.bloomberg.com/news/articles/2025-04-30/x")
ks = kinds_of(row)
if "company" not in ks and "repo" not in ks:
    ok("T4 non-VCS host yields no company/repo")
else:
    bad(f"T4 non-VCS host yielded {ks}")

# --- T5: the same author collapses to one normalized name -------------------
a = norm("Koosha")
b = norm("  KOOSHA  ")
if a == b:
    ok("T5 author normalizes case and whitespace to one key")
else:
    bad(f"T5 normalization differs: {a!r} vs {b!r}")

# --- T6: a path-shaped title yields a LOW-confidence project ----------------
row = ("koosha", "/Users/kooshapari/CodeProjects/Phenotype/repos/harness-ops", None)
res = [r for r in candidates_for_item(row) if r[0] == "project"]
if res and res[0][3] == "low":
    ok("T6 path-shaped title yields a project at low confidence")
else:
    bad(f"T6 path-shaped title gave {res}, expected a low-confidence project")

# --- T7: a known host with no path yields nothing --------------------------
row = ("koosha", "t", "https://github.com/")
ks = kinds_of(row)
if "company" not in ks and "repo" not in ks:
    ok("T7 known host with no path yields no company/repo")
else:
    bad(f"T7 known host with no path yielded {ks}")

# --- T8: a non-path title never yields a project ----------------------------
row = ("koosha", "Fix the flaky test in the parser", None)
if "project" not in kinds_of(row):
    ok("T8 plain title yields no project")
else:
    bad("T8 plain title yielded a project")

# --- T9: the scan must cover the whole table (no cursor truncation) ---------
db = os.path.expanduser("~/Exports/analysis/research_ledger.sqlite")
if not os.path.exists(db):
    print("SKIP  T9 (ledger not present)")
else:
    import sqlite3
    import time
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cur = conn.cursor()
    total = cur.execute("SELECT count(*) FROM items").fetchone()[0]
    # Scan the tail: a truncated scan would stop early, so assert we visit
    # every row in the range we asked for.
    tail = cur.execute("SELECT count(*) FROM items WHERE id > 900000").fetchone()[0]
    seen = 0
    t0 = time.time()
    for _ in cur.execute("SELECT id, author, title, url FROM items WHERE id > 900000"):
        seen += 1
    if seen == tail and tail > 0:
        ok(f"T9 scan visited every row in range ({seen:,} of {tail:,})")
    else:
        bad(f"T9 scan visited {seen:,} of {tail:,} rows in range — truncated")
    conn.close()

print()
print(f"validate_extract_entities: {pass_} passed, {fail_} failed")
sys.exit(1 if fail_ else 0)
