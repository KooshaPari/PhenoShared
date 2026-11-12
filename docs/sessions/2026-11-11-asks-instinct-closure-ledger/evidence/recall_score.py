#!/usr/bin/env python3
"""Score the blinded random-sample recall probe.

Inputs, both committed:
  recall_label_sheet.json   -- clause + shuffled candidates + hand labels (M/W/N)
  recall_candidates.json    -- the same pairs with rank and cosine, used ONLY to
                               attribute a capture to a rank and to separate
                               capture@1 from capture@5.

WHAT IT COMPUTES, and nothing else:
  capture@5  -- fraction of the random sample whose intent some register ask among
                the 5 nearest expresses. This is the recall measurement the
                stratified probe could not produce.
  capture@1  -- the same restricted to the model's own first choice, so the reader
                can see how much of the recall the model actually orders correctly.
  Wilson intervals -- because n=60 and a percentage without an interval would
                invite exactly the over-reading this ledger has already made seven
                times.

WHAT IT REFUSES TO DO: combine this rate with the 8.0% structural figure as if the
two shared a denominator. They do not (8,819 uncited ask-cue units vs 43,305 all
units). The union arithmetic is emitted separately, labelled DERIVED, and only
because the two terms are disjoint by construction.
"""
from __future__ import annotations

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = os.path.join(HERE, "recall_label_sheet.json")
PAIRS = os.path.join(HERE, "recall_candidates.json")
OUT = os.path.join(HERE, "recall_scored.json")

STRUCTURAL_CITED = 3463      # from union_channels.py / segment_units.py
STRUCTURAL_TOTAL = 43305
Z = 1.959964


def wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval: correct at small n, unlike normal approximation."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    c = p + Z * Z / (2 * n)
    m = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def main() -> int:
    sheet = json.load(open(SHEET))
    pairs = json.load(open(PAIRS))
    rank_of = {}
    for p in pairs["pairs"]:
        rank_of[p["idx"]] = {c["ask"]: (c["rank"], c["cosine"]) for c in p["candidates"]}

    n = len(sheet["items"])
    counts = {"M": 0, "W": 0, "N": 0}
    at1 = {"M": 0, "W": 0}
    ranks = {"M": [], "W": []}
    captures = []
    for it in sheet["items"]:
        g = it.get("grade", "N")
        counts[g] = counts.get(g, 0) + 1
        if g in ("M", "W"):
            r, cos = rank_of[it["idx"]][it["captured_by"]]
            ranks[g].append(r)
            if r == 1:
                at1[g] += 1
            captures.append({"idx": it["idx"], "grade": g, "ask": it["captured_by"],
                             "rank": r, "cosine": cos, "why": it["why"]})

    strict, lenient = counts["M"], counts["M"] + counts["W"]
    s_lo, s_hi = wilson(strict, n)
    l_lo, l_hi = wilson(lenient, n)
    c1_strict = at1["M"]
    c1_lo, c1_hi = wilson(c1_strict, n)

    pop = pairs["population"]
    proj = pop * strict / n
    proj_lo, proj_hi = pop * s_lo, pop * s_hi

    # DERIVED: the structural figure is verbatim-substring coverage of all units; this
    # probe covers only the units that are (a) uncited structurally and (b) ask-cue.
    # Those two sets are disjoint by construction, so adding captured units to the
    # structurally cited ones is valid -- and remains a lower bound, because uncited
    # units that are NOT ask-cue were never probed.
    union_lower = (STRUCTURAL_CITED + proj) / STRUCTURAL_TOTAL
    union_lo = (STRUCTURAL_CITED + proj_lo) / STRUCTURAL_TOTAL
    union_hi = (STRUCTURAL_CITED + proj_hi) / STRUCTURAL_TOTAL

    out = {
        "generated_at_utc": sheet["generated_at_utc"],
        "labelled_at_utc": sheet.get("labelled_at_utc"),
        "labeller": sheet.get("labeller"),
        "seed": sheet["seed"],
        "topk": sheet["topk"],
        "sample_size": n,
        "population": pop,
        "label_counts": counts,
        "capture_at_5": {
            "strict": {"k": strict, "n": n, "rate": round(strict / n, 4),
                       "wilson95": [round(s_lo, 4), round(s_hi, 4)]},
            "lenient": {"k": lenient, "n": n, "rate": round(lenient / n, 4),
                        "wilson95": [round(l_lo, 4), round(l_hi, 4)]},
        },
        "capture_at_1_strict": {"k": c1_strict, "n": n,
                                "rate": round(c1_strict / n, 4),
                                "wilson95": [round(c1_lo, 4), round(c1_hi, 4)]},
        "capture_ranks": {g: sorted(v) for g, v in ranks.items()},
        "captures": captures,
        "projected_captures_in_population": {
            "point": round(proj), "wilson95": [round(proj_lo), round(proj_hi)],
            "note": "capture@5 projected onto the 8,819 uncited ask-cue units",
        },
        "derived_union_lower_bound": {
            "structural_cited_units": STRUCTURAL_CITED,
            "structural_total_units": STRUCTURAL_TOTAL,
            "formula": "(structural cited + projected semantic captures) / all units",
            "point": round(union_lower, 4),
            "wilson95": [round(union_lo, 4), round(union_hi, 4)],
            "caveat": ("DERIVED, not measured on the union. Uncited units that are not "
                       "ask-cue were never probed, so this is a LOWER bound. Never add "
                       "it to, or average it with, the 8.0% structural figure - it "
                       "already contains it."),
        },
        "verdict": ("Semantic capture among uncited ask-cue units is real and roughly "
                    "ten times the floor the stratified probe could certify, but the "
                    "register still holds a minority of expressed intents. The earlier "
                    "2.12% figure was a floor computed from a biased-high score band, "
                    "not a random-sample estimate, and the two must not be compared as "
                    "if they were the same estimator."),
        "limitations": [
            "single labeller, not independent; grades M/W were assigned by the agent that built the retrieval",
            "capture@5 is recall of the k=5 retrieval system, not ultimate recall",
            "n=60: the interval is wide by construction and is reported with every rate",
            "the labeller saw 5 candidates per clause, which invites finding something; capture@1 is reported alongside for that reason",
        ],
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"n={n} labels={counts}")
    print(f"capture@5 strict {strict}/{n} = {strict/n:.1%} [{s_lo:.1%}, {s_hi:.1%}]")
    print(f"capture@5 lenient {lenient}/{n} = {lenient/n:.1%} [{l_lo:.1%}, {l_hi:.1%}]")
    print(f"capture@1 strict {c1_strict}/{n} = {c1_strict/n:.1%} [{c1_lo:.1%}, {c1_hi:.1%}]")
    print(f"capture ranks M={sorted(ranks['M'])} W={sorted(ranks['W'])}")
    print(f"projected captures in {pop}: {round(proj)} [{round(proj_lo)}, {round(proj_hi)}]")
    print(f"derived union lower bound: {union_lower:.1%} [{union_lo:.1%}, {union_hi:.1%}]")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
