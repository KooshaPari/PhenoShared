#!/usr/bin/env python3
"""render_verdict_tree.py - render VERDICT-TREE.md from STATUS.json.

WHY THIS EXISTS
---------------
The cross-harness progress-tree rule says the machine-readable JSON is the SOURCE and
the Markdown is RENDERED from it. In the first version of this tree the Markdown was
hand-written and the rollup was hand-counted, and the hand-count was wrong in every one
of the four dimensions. Hand-copying was the failure. This script removes the option.

Usage:
    python3 render_verdict_tree.py            # writes VERDICT-TREE.md
    python3 render_verdict_tree.py --check    # exits 1 if the file is stale

The --check mode is the useful one in CI or a pre-commit hook: it fails if
VERDICT-TREE.md no longer matches STATUS.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "RESEARCH_LEDGER_STATUS.json"
MD_PATH = ROOT / "VERDICT-TREE.md"

GLYPH = {
    "PASS": "\u2713",
    "FAIL": "\u2717",
    "NOT_RUN": "\u2026",
    "UNKNOWN": "?",
    "STALE": "S",
    "BLOCKED": "B",
    "NOT_APPLICABLE": "N/A",
}
DIMS = ["impl", "use", "valid", "assur"]
DIM_LABEL = {"impl": "IMPL", "use": "USE", "valid": "VALID", "assur": "ASSUR"}


def render(doc: dict) -> str:
    L: list[str] = []
    subj = doc["subject"]
    L.append("# Research Ledger — Intent × Dimension Verdict Tree")
    L.append("")
    L.append("> **RENDERED FILE — DO NOT EDIT BY HAND.**")
    L.append("> Source of truth: `STATUS.json`. Regenerate with `python3 render_verdict_tree.py`.")
    L.append(f"> Source digest: `sha256:{doc.get('_source_sha256', 'n/a')}`")
    L.append("")
    L.append(f"**Generated:** {doc.get('generated_at_utc', 'n/a')}")
    L.append(f"**Subject:** {subj.get('title')} — `{subj.get('path')}`")
    L.append(f"**HEAD:** `{subj.get('head')}` · commits {subj.get('commit_count')} · "
             f"tracked files {subj.get('tracked_files')} · dirty {subj.get('dirty')}")
    L.append(f"**Governing rule:** `{doc.get('governing_rule')}`")
    L.append("")
    L.append(f"> {doc.get('rule_note')}")
    L.append("")
    L.append("## Vocabulary")
    L.append("")
    for k, v in doc.get("vocabulary", {}).items():
        desc = v
        for g in GLYPH.values():
            if desc.startswith(g):
                desc = desc[len(g):].lstrip(" \u2014-").strip()
                break
        L.append(f"- `{k}` = {GLYPH.get(k, '?')} — {desc}")
    L.append("")
    L.append("Dimensions never collapse: **IMPL** exists at source · **USE** invocable from "
             "outside · **VALID** executed with a cited witness · **ASSUR** witness is "
             "independent, fresh, traceable.")
    L.append("")
    L.append("## Tree")
    L.append("")
    L.append("```")
    L.append(f"{'':50} {'  '.join(DIM_LABEL[d] for d in DIMS)}   citation")
    for n in doc["intents"]:
        _row(L, n, 0)
    L.append("```")
    L.append("")
    L.append("## Rollup (derived counts — never percentages)")
    L.append("")
    L.append("```")
    L.append(f"{'':10} " + "".join(f"{DIM_LABEL[d]:>6}" for d in DIMS))
    order = ["PASS", "FAIL", "NOT_RUN", "UNKNOWN", "STALE", "BLOCKED", "NOT_APPLICABLE"]
    for v in order:
        cells = "".join(f"{doc['rollup_counts'][d].get(v, 0):>6}" for d in DIMS)
        if cells.strip(" 0"):
            L.append(f"{GLYPH[v]} {v:<8}" + cells)
    L.append("```")
    L.append("")
    L.append("> Counts only. A percentage here would be fabricated — partial evidence "
             "converted into a rate that hides the gap.")
    L.append("")
    neighbour = ROOT / "STATUS.json"
    if neighbour.exists():
        try:
            nd = json.loads(neighbour.read_text())
            nkeys = sorted(k for k in nd if not k.startswith("_"))
        except Exception:
            nkeys = []
        if nkeys:
            L.append("## Adjacent sidecar (different agent, not rendered here)")
            L.append("")
            L.append(f"`STATUS.json` in this directory belongs to a different agent and is "
                     f"**deliberately not rendered into this tree**. Its keys: "
                     f"{', '.join('`'+k+'`' for k in nkeys)}. Read that file directly; "
                     f"omitting them here is a file-boundary, not a data loss.")
            L.append("")
    if doc.get("open_items"):
        L.append("## Open items")
        L.append("")
        L.append("| ID | Item | Verdict | Why |")
        L.append("|----|------|---------|-----|")
        for it in doc["open_items"]:
            why = it.get("note") or it.get("cause") or it.get("blocked_by") or ""
            cls = it.get("class")
            if cls:
                why = f"{why} [{cls}]" if why else cls
            L.append(f"| {it.get('id')} | {it.get('item')} | {GLYPH.get(it.get('verdict'),'?')} "
                     f"{it.get('verdict')} | {why} |")
        L.append("")
    return "\n".join(L) + "\n"


def _row(L: list[str], n: dict, depth: int) -> None:
    pad = "  " * depth
    name = f"{pad}{n.get('id','')} {n.get('title','')}"
    name = name[:49]
    cells = "  ".join(f"{GLYPH.get(n.get('dimensions',{}).get(d), '?'):>5}" for d in DIMS)
    cite = n.get("citation") or ""
    note = n.get("note")
    if note:
        cite = f"{cite}  NOTE: {note}" if cite else f"NOTE: {note}"
    L.append(f"{name:<50} {cells}   {cite}"[:200])
    for c in n.get("children", []):
        _row(L, c, depth + 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if VERDICT-TREE.md does not match STATUS.json")
    a = ap.parse_args()

    raw = JSON_PATH.read_bytes()
    doc = json.loads(raw)
    doc["_source_sha256"] = hashlib.sha256(raw).hexdigest()
    rendered = render(doc)

    if a.check:
        current = MD_PATH.read_text(encoding="utf-8") if MD_PATH.exists() else ""
        if current != rendered:
            print(f"STALE: {MD_PATH.name} does not match {JSON_PATH.name}", file=sys.stderr)
            return 1
        print(f"OK: {MD_PATH.name} matches {JSON_PATH.name}")
        return 0

    MD_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {MD_PATH.name} ({len(rendered)} bytes) from {JSON_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
