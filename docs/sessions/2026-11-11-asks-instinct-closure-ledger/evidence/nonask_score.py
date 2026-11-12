#!/usr/bin/env python3
"""Score the non-ask-cue probe and rebuild the union coverage figure in one consistent frame.

Inputs, all committed:
  nonask_label_sheet.json       clause + shuffled candidates + hand labels + speaker
  nonask_candidates.json        same pairs with rank and cosine (scorer only)
  recall_scored.json            the ask-cue rate: 8/60 capture@5
  coverage_consistency.json     the consistent structural pair: 1,938 / 43,648

WHY THIS EXISTS. Two separate defects made the old headline unusable:

  1. The published 8.0% pairs a SUMMED numerator with a DEDUPLICATED denominator
     (coverage_consistency.py measures the fair repair at 4.44%).
  2. Union coverage was quoted as a lower bound because 32,891 uncited non-ask-cue units
     had never been sampled. This script samples them.

It refuses to mix frames: every term below comes from frame A (set union of raw strings),
which is the frame coverage_consistency.py establishes and the frame both semantic probes
already sample.

INTERVAL DISCIPLINE. The union figure combines three independently estimated quantities.
The script adds the bounds rather than pretending to a joint interval, and labels the result
`range_from_independent_bounds`, not `ci`. A joint interval would need the joint distribution,
which nobody has measured.
"""
from __future__ import annotations

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = os.path.join(HERE, "nonask_label_sheet.json")
PAIRS = os.path.join(HERE, "nonask_candidates.json")
ASK_SCORED = os.path.join(HERE, "recall_scored.json")
CONSIST = os.path.join(HERE, "coverage_consistency.json")
OUT = os.path.join(HERE, "nonask_scored.json")

Z = 1.959964


def wilson(k: int, n: int) -> tuple[float, float]:
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
    rank_of = {p["idx"]: {c["ask"]: (c["rank"], c["cosine"]) for c in p["candidates"]}
               for p in pairs["pairs"]}

    n = len(sheet["items"])
    counts = {"M": 0, "W": 0, "N": 0}
    at1 = 0
    ranks = {"M": [], "W": []}
    by_speaker: dict[str, dict] = {}
    by_channel: dict[str, dict] = {}
    captures = []
    for it in sheet["items"]:
        g = it.get("grade", "N")
        counts[g] = counts.get(g, 0) + 1
        sp = it.get("speaker_pass2", "unknown")
        b = by_speaker.setdefault(sp, {"n": 0, "M": 0, "W": 0, "N": 0})
        b["n"] += 1
        b[g] += 1
        key = "+".join(it.get("channel") or []) or "UNMATCHED"
        by_channel.setdefault(key, {"n": 0, "M": 0, "W": 0, "N": 0})
        by_channel[key]["n"] += 1
        by_channel[key][g] += 1
        if g in ("M", "W"):
            r, cos = rank_of[it["idx"]][it["captured_by"]]
            ranks[g].append(r)
            if r == 1 and g == "M":
                at1 += 1
            captures.append({"idx": it["idx"], "grade": g, "ask": it["captured_by"],
                             "rank": r, "cosine": cos, "speaker": sp, "why": it["why"]})

    strict, lenient = counts["M"], counts["M"] + counts["W"]
    s_lo, s_hi = wilson(strict, n)
    l_lo, l_hi = wilson(lenient, n)
    c1_lo, c1_hi = wilson(at1, n)

    # ---- the three terms of the union, all frame A ----
    cons = json.load(open(CONSIST))["frame_a_set_union"]
    ask = json.load(open(ASK_SCORED))["capture_at_5"]["strict"]
    total_units = cons["units"]
    cited = cons["cited"]
    ask_pop, non_pop = cons["uncited_ask_cue"], cons["uncited_non_ask_cue"]

    ask_cap = ask_pop * ask["k"] / ask["n"]
    non_cap = non_pop * strict / n
    nonzero = (cited + ask_cap + non_cap) / total_units
    low = (cited + ask_pop * ask["wilson95"][0] + non_pop * s_lo) / total_units
    high = (cited + ask_pop * ask["wilson95"][1] + non_pop * s_hi) / total_units

    out = {
        "generated_at_utc": sheet["generated_at_utc"],
        "labelled_at_utc": sheet.get("labelled_at_utc"),
        "labeller": sheet.get("labeller"),
        "seed": sheet["seed"],
        "topk": sheet["topk"],
        "sample_size": n,
        "population": non_pop,
        "label_counts": counts,
        "capture_at_5": {
            "strict": {"k": strict, "n": n, "rate": round(strict / n, 4),
                       "wilson95": [round(s_lo, 4), round(s_hi, 4)]},
            "lenient": {"k": lenient, "n": n, "rate": round(lenient / n, 4),
                        "wilson95": [round(l_lo, 4), round(l_hi, 4)]},
        },
        "capture_at_1_strict": {"k": at1, "n": n, "rate": round(at1 / n, 4),
                                "wilson95": [round(c1_lo, 4), round(c1_hi, 4)]},
        "capture_ranks": {g: sorted(v) for g, v in ranks.items()},
        "by_speaker_pass2": by_speaker,
        "by_channel": by_channel,
        "speaker_pass1_aggregate_lost": sheet.get("speaker_pass1_aggregate_lost"),
        "label_restore_note": sheet.get("restore_note"),
        "captures": captures,
        "union_frame_a": {
            "total_units": total_units,
            "structural_cited": cited,
            "ask_cue_population": ask_pop, "ask_cue_rate": ask["k"] / ask["n"],
            "ask_cue_captures": round(ask_cap),
            "non_ask_population": non_pop, "non_ask_rate": strict / n,
            "non_ask_captures": round(non_cap),
            "coverage_pct_point": round(100 * nonzero, 2),
            "range_from_independent_bounds": [round(100 * low, 2), round(100 * high, 2)],
            "interval_caveat": ("the bounds add each term's own 95% Wilson limit independently; "
                                "this is a sensitivity range, not a joint confidence interval"),
        },
        "verdict": ("The non-ask-cue bucket is captured at a much lower rate than the ask-cue "
                    "bucket, so the register's coverage does not rise much: the union figure in "
                    "frame A is ~9.6%. The bucket is also mostly not operator speech - 47 of the 60 "
                    "sampled clauses come from agent-harness exports and two independent speaker "
                    "passes put the non-operator share at 62-75% - so its low rate says more about "
                    "what the unit population contains than about what the register missed."),
        "limitations": [
            "single labeller, not independent",
            "capture@5 is recall of the k=5 retrieval system, not ultimate recall",
            "n=60 per bucket; the by_speaker split is a post-hoc subset with tiny n and is explanatory only",
            "the union range adds independent bounds and is not a joint interval",
        ],
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)

    print(f"n={n} labels={counts} speakers={ {k: v['n'] for k, v in by_speaker.items()} }")
    print(f"capture@5 strict {strict}/{n} = {strict/n:.1%} [{s_lo:.1%}, {s_hi:.1%}]")
    print(f"capture@5 lenient {lenient}/{n} = {lenient/n:.1%} [{l_lo:.1%}, {l_hi:.1%}]")
    print(f"capture@1 strict {at1}/{n} = {at1/n:.1%} [{c1_lo:.1%}, {c1_hi:.1%}]")
    print(f"ranks M={sorted(ranks['M'])} W={sorted(ranks['W'])}")
    for sp, b in sorted(by_speaker.items()):
        print(f"  {sp:9s} n={b['n']:3d}  M={b['M']}  W={b['W']}  N={b['N']}")
    for c, b in sorted(by_channel.items()):
        print(f"  ch {c:18s} n={b['n']:3d}")
    print(f"\nunion frame A: {cited} cited + {round(ask_cap)} ask-cue + "
          f"{round(non_cap)} non-ask-cue = {100*nonzero:.2f}% of {total_units}")
    print(f"  range [ {100*low:.2f}%, {100*high:.2f}% ] (independent bounds)")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
