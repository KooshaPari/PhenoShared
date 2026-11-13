#!/usr/bin/env python3
"""Generate the ask inventory asset for the cockpit.

Purpose: make the ask register visible on example.com WITHOUT touching
the gated D1 path and WITHOUT asserting any review.

Two hard rules, both non-negotiable:

1. NO VERBATIM TEXT. `original_text` holds private iMessage quotes. It is
   dropped here entirely. Only the derived `interpretation` is published.
   (An earlier defect in this project served private ask text over HTTP; this
   file must never repeat it.)

2. NO ASSERTION OF REVIEW. Every row is published with
   verified_state = "Pending review". Nothing is marked reviewed. The inventory
   is an index of recorded asks, not a ledger of approved ones.

Paths are fixed relative to this script, so no path ever comes from the command
line or the environment. An earlier version read argv and was flagged by
SonarCloud as a path-traversal risk (C Security Rating on new code); removing the
user-supplied path removes the vulnerability rather than suppressing the warning.

Input:  web/public/asks/source.json   (copy of asks.json; gitignored, not committed)
Output: web/public/asks/inventory.json (committed)

Usage:
    cp <path-to>/asks.json web/public/asks/source.json
    python3 web/scripts/gen-inventory.py
"""
import json
import os

STATE_NOTE = "Unreviewed inventory"
PENDING = "Pending review"

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))          # web/scripts -> web -> repo
ASSET_DIR = os.path.join(REPO, "web", "public", "asks")
SRC = os.path.join(ASSET_DIR, "source.json")
OUT = os.path.join(ASSET_DIR, "inventory.json")

# Extra containment check: never read or write outside the asset directory even
# if the tree is moved or symlinked. Cheap, and it makes the invariant explicit.
for p in (SRC, OUT):
    if os.path.dirname(os.path.realpath(p)) != os.path.realpath(ASSET_DIR):
        raise SystemExit(f"refusing to operate outside {ASSET_DIR}: {p}")

# Fields that must never reach a published asset.
FORBIDDEN = ("original_text",)


def build(doc):
    rows = []
    for n, a in enumerate(doc["asks"], 1):
        r = {
            # numeric id preserves the route's existing keyset cursor contract
            "id": n,
            "ask_id": a["id"],
            "interpretation": a["interpretation"],
            "first_asked_at": a["first_asked_at"],
            "reported_state": a["reported_state"],
            "verified_state": PENDING,
            "task_links_json": "[]",
            "source_refs_json": json.dumps(
                [{"kind": s.get("kind"), "at": s.get("at")}
                 for s in a.get("source_refs_json", [])]
            ),
            "reconciled_at": None,
            "updated_at": a["updated_at"],
            "group": a["group"],
            "kind": a["kind"],
            "issue_ref": a.get("issue_ref"),
            "issue_level": a.get("issue_level"),
            "theme_key": a.get("theme_key"),
        }
        for bad in FORBIDDEN:
            if bad in r:
                raise SystemExit(f"refusing to publish {bad}")
        rows.append(r)
    return {
        "schema": "asks-inventory/1",
        "generated_at": doc["generated_at"],
        "state": STATE_NOTE,
        "note": (
            "Every ask here is recorded, not reviewed. verified_state is "
            "'Pending review' for all rows and nothing is marked reviewed. "
            "This index is not a completion ledger and must not be read as one. "
            "Verbatim message text is deliberately excluded."
        ),
        "count": len(rows),
        "rollups": {
            "by_group": doc["rollups"]["by_group"],
            "by_kind": doc["rollups"]["by_kind"],
            "by_issue_level": doc["rollups"].get("by_issue_level", {}),
            "recurring_theme_count": doc["rollups"]["recurring_theme_count"],
        },
        "asks": rows,
    }


def main():
    if not os.path.exists(SRC):
        raise SystemExit(
            f"missing {SRC}\n"
            "copy the traceability dataset there first:\n"
            "  cp <repos>/phenotype-registry/imessage-asks/asks.json web/public/asks/source.json"
        )
    with open(SRC) as fh:
        doc = json.load(fh)
    out = build(doc)
    body = json.dumps(out, separators=(",", ":"))
    for bad in FORBIDDEN:
        if bad in body:
            raise SystemExit(f"refusing to write: {bad} present in output")
    with open(OUT, "w") as fh:
        fh.write(body + "\n")
    print(f"wrote {OUT}: {out['count']} asks, {len(body)//1024} KB")
    print("contains 'original_text':", "original_text" in body)


if __name__ == "__main__":
    main()
