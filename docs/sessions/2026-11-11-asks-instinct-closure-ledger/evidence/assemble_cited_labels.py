#!/usr/bin/env python3
"""Assemble `cited_labels.json` from the three partial label files.

WHY THIS EXISTS. The 60-clause cited-side sheet had to be labelled in three passes: a single
60-item lane failed at the transport layer four times across two routes, losing everything each
time. The lanes that finally completed wrote one file per 20 items, so the merge is mechanical
and is done by a committed script rather than by hand -- the labels themselves were never
re-judged here, only concatenated.

INPUTS (all in this directory):
  cited_labels_partial.tsv   idx<TAB>speaker<TAB>why   for idx 0-19
  cited_chunk_20_39.json     {"items":[{idx,clause,speaker,why}]}
  cited_chunk_40_59.json     {"items":[{idx,clause,speaker,why}]}
  cited_speaker_sheet.json   the sheet, for the canonical clause strings

OUTPUT: cited_labels.json with 60 items, idx 0..59, clause copied from the SHEET (not from the
partials) so a transcription slip in a partial cannot change what was judged.

The script refuses to write a partial file: it asserts the union is exactly 0..59 with no gaps,
no duplicates, and every speaker in the allowed set.
"""
from __future__ import annotations

import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWED = {"operator", "agent", "tool", "system", "peer", "other"}


def main() -> int:
    sheet = json.load(open(os.path.join(HERE, "cited_speaker_sheet.json")))
    clauses = {it["idx"]: it["clause"] for it in sheet["items"]}

    rows: dict[int, tuple[str, str]] = {}

    tsv = os.path.join(HERE, "cited_labels_partial.tsv")
    with open(tsv) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            idx_s, speaker, why = line.split("\t", 2)
            rows[int(idx_s)] = (speaker.strip(), why.strip())

    for name in ("cited_chunk_20_39.json", "cited_chunk_40_59.json"):
        for it in json.load(open(os.path.join(HERE, name)))["items"]:
            idx = it["idx"]
            if idx in rows:
                raise SystemExit(f"DUPLICATE idx {idx} (from {name})")
            rows[idx] = (it["speaker"].strip(), it["why"].strip())

    missing = sorted(set(range(60)) - set(rows))
    if missing:
        raise SystemExit(f"INCOMPLETE: missing idx {missing}")
    bad = {i: s for i, (s, _) in rows.items() if s not in ALLOWED}
    if bad:
        raise SystemExit(f"BAD SPEAKER values: {bad}")
    empty = [i for i, (_, w) in rows.items() if not w]
    if empty:
        raise SystemExit(f"EMPTY why at idx {empty}")

    items = [{"idx": i, "clause": clauses[i], "speaker": rows[i][0], "why": rows[i][1]}
             for i in range(60)]

    out = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "labeller": "three lane passes: partial.tsv (0-19) + chunk_20_39 + chunk_40_59; assembled mechanically",
        "n": 60,
        "assembly_note": ("Labels were produced in three separate label passes because a single "
                          "60-item lane failed at the transport layer. This script concatenates "
                          "them; it does not re-judge or repair any label."),
        "items": items,
    }
    path = os.path.join(HERE, "cited_labels.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)

    from collections import Counter
    print(f"wrote {path}")
    print("counts:", dict(Counter(i["speaker"] for i in items)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
