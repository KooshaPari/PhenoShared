#!/usr/bin/env python3
"""
extract_entities.py — populate the canonical `entities` / `item_entities` tables.

WHY THIS EXISTS (2026-10-22, D-25)
-----------------------------------
The research ledger's schema has always declared `entities` and `item_entities`
with a full contract:

    entities(id, kind CHECK IN (person,company,project,product,repo,topic),
             name, normalized_name, attributes_json)
    item_entities(item_id, entity_id, role, confidence, evidence,
                  PRIMARY KEY(item_id, entity_id, role))

`items` holds 940,934 rows. `entities` and `item_entities` hold ZERO. Every
other stage of the pipeline is populated (migrated_* tables are complete:
claude 786/10885, chatgpt 786/10885, gemini 761). The entity stage is the one
designed-but-never-run phase, and no script in the tree inserts into `entities`
— I grepped every .py for `INTO entities` and got zero hits.

So this script implements the missing stage.

WHAT IT EXTRACTS (deliberately conservative)
---------------------------------------------
Only entity classes that can be extracted from structured fields WITHOUT
inventing facts:

  person   items.author            — a human/agent author name
  repo     items.url matching a VCS host path, plus the repo slug
  project  items.title when it is a worktree/project path
  company  org-like tokens in urls (github.com/<org>, etc.)

Deliberately NOT extracted: free-text NER over message bodies. Guessing that a
string in a chat log is a person or a company is how a ledger becomes fiction.
If a class cannot be read off a structured field with a citation, it is not
extracted. `evidence` records the exact field and value that justified the
link, so every row is auditable back to its source.

CONFIDENCE
----------
  high    — the value is the field itself, unmodified (items.author)
  medium  — the value is a component of a structured field (repo slug from a
            url, org from a host path)
  low     — heuristic (a title that parses as a path)

IDEMPOTENCE
-----------
INSERT OR IGNORE on the uq_entities_norm unique index, and on the
item_entities primary key. Re-running is safe and converges.

USAGE
  python3 extract_entities.py                    # default db
  python3 extract_entities.py --db PATH
  python3 extract_entities.py --dry-run          # report only, no writes
  python3 extract_entities.py --limit N          # sample N items
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

DEFAULT_DB = os.path.expanduser("~/Exports/analysis/research_ledger.sqlite")

# Host -> organization-ish prefix. Only these produce a 'company' entity, and
# only from a URL path segment, never from free text.
HOSTS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "codeberg.org",
    "huggingface.co",
)

# A repo path segment: owner/repo, optionally with .git
REPO_RE = re.compile(r"^(?P<owner>[A-Za-z0-9._-]+)/(?P<repo>[A-Za-z0-9._-]+?)(?:\.git)?$")
# A filesystem-ish project path
PATHISH_RE = re.compile(r"^/[\w./-]+/([\w.-]+)/?$")

# Values that are placeholders, not names.
STOP_NAMES = {
    "", "unknown", "none", "null", "n/a", "na", "-", "user", "assistant",
    "system", "tool", "function", "me", "you", "assistant ", "human",
}


def norm(name: str) -> str:
    """normalized_name: casefolded, whitespace-collapsed, trimmed."""
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def clean(raw: str) -> str | None:
    """Trim a raw value to a usable entity name, or None if it is not one."""
    if not raw:
        return None
    s = re.sub(r"\s+", " ", raw).strip()
    # strip a trailing email address form: "Name <a@b.c>"
    m = re.match(r"^(?P<n>[^<>]+?)\s*<[^>]+>$", s)
    if m:
        s = m.group("n").strip()
    s = s.strip(" \t\"'`")
    if not s or norm(s) in STOP_NAMES:
        return None
    if len(s) > 200:
        return None
    return s


def candidates_for_item(row) -> list[tuple[str, str, str, str, str]]:
    """Return (kind, name, role, confidence, evidence) tuples for one item.

    Only structured fields are consulted: author, url, title.
    """
    out = []
    author, title, url = row

    # person — the author field IS the name.
    nm = clean(author)
    if nm:
        out.append(("person", nm, "author", "high",
                    json.dumps({"field": "items.author", "value": nm})))

    # repo / company — from a url.
    if url:
        try:
            from urllib.parse import urlparse
            p = urlparse(url)
        except Exception:
            p = None
        if p is not None:
            host = (p.netloc or "").lower()
            segs = [s for s in (p.path or "").split("/") if s]
            if host in HOSTS and segs:
                org = clean(segs[0])
                if org:
                    out.append(("company", org, "host_org", "medium",
                                json.dumps({"field": "items.url", "value": url,
                                            "host": host, "org": org})))
                if len(segs) >= 2:
                    m = REPO_RE.match(f"{segs[0]}/{segs[1]}")
                    if m:
                        owner = clean(m.group("owner"))
                        repo = clean(m.group("repo"))
                        if owner and repo:
                            out.append(("repo", f"{owner}/{repo}", "repo", "medium",
                                        json.dumps({"field": "items.url", "value": url,
                                                    "repo": f"{owner}/{repo}"})))

    # project — a title that is a path.
    if title and ("/" in title):
        m = PATHISH_RE.match(title.strip())
        if m:
            nm = clean(m.group(1))
            if nm:
                out.append(("project", nm, "project", "low",
                            json.dumps({"field": "items.title", "value": title,
                                        "project": nm})))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-id", type=int, default=0,
                    help="only consider items with id >= MIN_ID (the low ids are "
                         "often sparsely populated, so a plain LIMIT samples the "
                         "emptiest rows rather than a representative slice)")
    ap.add_argument("--sample", type=int, default=0,
                    help="process a random sample of N items spread across the table")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"extract_entities: db not found: {args.db}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(args.db, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()

    sql = "SELECT id, author, title, url FROM items"
    if args.min_id:
        sql += f" WHERE id >= {int(args.min_id)}"
    if args.sample:
        # A random spread, not the first N: the low ids are sparsely populated
        # so a plain LIMIT samples the emptiest rows, not a representative slice.
        total = cur.execute("SELECT count(*) FROM items").fetchone()[0]
        n = min(int(args.sample), total)
        sql = ("SELECT id, author, title, url FROM items WHERE id IN "
               f"(SELECT id FROM items ORDER BY RANDOM() LIMIT {n})")
    elif args.limit:
        sql += f" LIMIT {int(args.limit)}"

    t0 = time.time()
    n_items = 0
    n_links = 0
    kinds: dict[str, int] = {}

    if args.dry_run:
        for row in cur.execute(sql):
            n_items += 1
            for kind, name, role, conf, ev in candidates_for_item(row[1:]):
                n_links += 1
                kinds[kind] = kinds.get(kind, 0) + 1
        print(f"[dry-run] items scanned   : {n_items:,}")
        print(f"[dry-run] links derived   : {n_links:,}")
        print(f"[dry-run] by kind         : {kinds}")
        print(f"[dry-run] elapsed         : {time.time() - t0:.1f}s")
        return 0

    # Batch: collect rows, then upsert entities and links.
    ent_id: dict[tuple[str, str], int] = {}
    batch: list[tuple] = []
    ent_batch: list[tuple] = []

    def flush_entities():
        """Insert entities and learn their ids, in one transaction.

        Uses a SEPARATE cursor. Reusing `cur` here would reset the outer
        `for row in cur.execute(sql)` cursor, silently truncating the scan —
        which is exactly what happened: the first version reported "items
        scanned: 32,478" against a 940,934-row table and exited cleanly.
        """
        nonlocal ent_batch
        if not ent_batch:
            return
        wcur = conn.cursor()
        wcur.executemany(
            "INSERT OR IGNORE INTO entities(kind,name,normalized_name,attributes_json) "
            "VALUES(?,?,?,?)", ent_batch)
        conn.commit()
        want = [(k, n) for (k, n, *_ ) in ent_batch]
        for kind, name in want:
            if (kind, name) in ent_id:
                continue
            r = wcur.execute(
                "SELECT id FROM entities WHERE kind=? AND normalized_name=?", (kind, name)).fetchone()
            if r:
                ent_id[(kind, name)] = r[0]
        ent_batch = []

    for row in cur.execute(sql):
        n_items += 1
        item_id = row[0]
        for kind, name, role, conf, ev in candidates_for_item(row[1:]):
            nlink = norm(name)
            if (kind, nlink) not in ent_id:
                ent_batch.append((kind, name, nlink, "{}"))
                if len(ent_batch) >= 500:
                    flush_entities()
            batch.append((item_id, kind, nlink, role, conf, ev))
            kinds[kind] = kinds.get(kind, 0) + 1
            n_links += 1
        if len(batch) >= 1000:
            # entities must exist before links reference them
            flush_entities()
            lcur = conn.cursor()
            ids = []
            for (iid, kind, nlink, role, conf, ev) in batch:
                eid = ent_id.get((kind, nlink))
                if eid is None:
                    r = lcur.execute("SELECT id FROM entities WHERE kind=? AND normalized_name=?",
                                    (kind, nlink)).fetchone()
                    if r:
                        eid = r[0]
                        ent_id[(kind, nlink)] = eid
                if eid is not None:
                    ids.append((iid, eid, role, conf, ev))
            lcur.executemany(
                "INSERT OR IGNORE INTO item_entities(item_id,entity_id,role,confidence,evidence) "
                "VALUES(?,?,?,?,?)", ids)
            conn.commit()
            batch = []
    flush_entities()
    fcur = conn.cursor()
    ids = []
    for (iid, kind, nlink, role, conf, ev) in batch:
        eid = ent_id.get((kind, nlink))
        if eid is None:
            r = fcur.execute("SELECT id FROM entities WHERE kind=? AND normalized_name=?",
                            (kind, nlink)).fetchone()
            if r:
                eid = r[0]
        if eid is not None:
            ids.append((iid, eid, role, conf, ev))
    if ids:
        fcur.executemany(
            "INSERT OR IGNORE INTO item_entities(item_id,entity_id,role,confidence,evidence) "
            "VALUES(?,?,?,?,?)", ids)
        conn.commit()

    el = time.time() - t0
    n_ent = cur.execute("SELECT count(*) FROM entities").fetchone()[0]
    n_ie = cur.execute("SELECT count(*) FROM item_entities").fetchone()[0]
    print(f"extract_entities: items scanned : {n_items:,}")
    print(f"extract_entities: links derived : {n_links:,}  by kind: {kinds}")
    print(f"extract_entities: entities      : {n_ent:,}")
    print(f"extract_entities: item_entities : {n_ie:,}")
    print(f"extract_entities: elapsed       : {el:.1f}s")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
