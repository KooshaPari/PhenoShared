#!/usr/bin/env python3
"""Consistency audit of the published union coverage figure.

WHAT THIS CHECKS. The published headline is `3,463 / 43,305 = 8.0%`. Those two numbers are
produced by two different reductions of the same data:

  denominator  43,305  = sum(per-channel units) - eaten, i.e. a DEDUPLICATED union
  numerator    3,463   = sum(per-channel cited), i.e. NOT deduplicated

`segment_units.py` computes `total_cited = sum(cited.values())` straight after building the
denominator with pairwise containment subtraction. Nothing subtracts the cited units that the
dedupe removed. So a unit cited in two channels is counted twice in the numerator while being
counted once in the denominator, and the ratio is inflated.

This script measures both frames and prints the consistent pairs:

  FRAME A (set union of raw strings)   -- simplest, fully reproducible
  FRAME B (containment dedupe)         -- the published denominator's own rule

Neither is "the" truth; they are two defensible dedupes. What is not defensible is pairing one
reduction's numerator with the other's denominator, which is what 8.0% does.

Read-only. Writes coverage_consistency.json only.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
COVERAGE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
PUBLISHED = os.path.join(HERE, "granularity_units.json")
OUT = os.path.join(HERE, "coverage_consistency.json")

sys.path.insert(0, COVERAGE)
sys.path.insert(0, HERE)
import union_channels as U            # noqa: E402
import segment_units as SEG           # noqa: E402


def main() -> int:
    t0 = time.time()
    quotes = sorted({U.norm(r.get("quote") or "")
                     for r in json.load(open(U.REGISTER))["records"]})
    quotes = [q for q in quotes if len(q) >= SEG.MIN_UNIT]

    H, _ = U.harness()
    I = {x for x in U.imessage() if U.keep(x)}
    K = {x for x in U.kcode()[0] if U.keep(x)}
    P = U.phone()
    members = {"harness": H, "imessage": I, "kcode": K, "phone": P}
    order = ["harness", "imessage", "kcode", "phone"]

    units: dict[str, list[str]] = {}
    cited_u: dict[str, set[str]] = {}
    per_channel = {}
    for n, ms in members.items():
        units[n] = sorted({u for m in ms for u in SEG.segment(m)})
        idx = SEG.CitedIndex(units[n])
        cited_u[n] = {units[n][i] for i in idx.cite(quotes)}
        per_channel[n] = {"members": len(ms), "distinct_units": len(units[n]),
                          "cited_units": len(cited_u[n]),
                          "coverage_pct": round(100 * len(cited_u[n]) / len(units[n]), 1)}
        print(f"  {n:9s} units {len(units[n]):6d}  cited {len(cited_u[n]):5d}  "
              f"({per_channel[n]['coverage_pct']}%)  [{time.time()-t0:.0f}s]")

    # ---------- FRAME A: plain set union ----------
    a_units = set().union(*units.values())
    a_cited = set().union(*cited_u.values())
    a_ask = {u for u in a_units - a_cited if SEG.is_ask(u)}
    a_non = {u for u in a_units - a_cited if not SEG.is_ask(u)}

    # ---------- FRAME B: containment dedupe, the published denominator's rule ----------
    blob = lambda s: "\n".join(sorted(s))  # noqa: E731  (same helper segment_units uses)
    blobs = {n: blob(units[n]) for n in order}
    eaten = eaten_cited = 0
    pair_overlap = {}
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            e = sum(1 for x in sorted(units[a], key=len, reverse=True) if x in blobs[b])
            ec = sum(1 for x in sorted(cited_u[a], key=len, reverse=True) if x in blobs[b])
            pair_overlap[f"{a}_in_{b}"] = {"units": e, "cited": ec}
            eaten += e
            eaten_cited += ec
    b_units = sum(len(units[n]) for n in order) - eaten
    b_cited = sum(len(cited_u[n]) for n in order) - eaten_cited

    pub = json.load(open(PUBLISHED))
    pub_units, pub_cited = pub["union_units"], pub["cited_units_total"]
    drift = {n: per_channel[n]["distinct_units"] - pub["per_channel"][n]["distinct_units"]
             for n in order if per_channel[n]["distinct_units"]
             != pub["per_channel"][n]["distinct_units"]}

    out = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "question": ("is the published union coverage ratio a consistent pair of numbers?"),
        "published": {"numerator": pub_cited, "denominator": pub_units,
                      "pct": round(100 * pub_cited / pub_units, 2),
                      "defect": ("numerator is a SUM across channels; denominator is a "
                                 "DEDUPLICATED union. Cited units removed by the dedupe are "
                                 "still counted in the numerator.")},
        "per_channel": per_channel,
        "frame_a_set_union": {
            "units": len(a_units), "cited": len(a_cited),
            "coverage_pct": round(100 * len(a_cited) / len(a_units), 2),
            "uncited": len(a_units) - len(a_cited),
            "uncited_ask_cue": len(a_ask), "uncited_non_ask_cue": len(a_non),
            "note": "reproduces the populations the semantic probes sample",
        },
        "frame_b_containment": {
            "units": b_units, "cited": b_cited,
            "coverage_pct": round(100 * b_cited / b_units, 2),
            "eaten_units": eaten, "eaten_cited": eaten_cited,
            "pair_overlap": pair_overlap,
            "note": "same rule as the published denominator, with the numerator reduced the "
                    "same way; this is the fair repair of the published pair",
        },
        "double_counted": {
            "sum_cited": sum(len(cited_u[n]) for n in order),
            "distinct_cited": len(a_cited),
            "duplicate_citations": sum(len(cited_u[n]) for n in order) - len(a_cited),
            "largest_source": "imessage_in_phone",
            "imessage_in_phone_cited": pair_overlap["imessage_in_phone"]["cited"],
        },
        "input_drift": {
            "per_channel_unit_delta_vs_published": drift,
            "published_union_units": pub_units,
            "rebuilt_containment_union": b_units,
            "note": ("this rebuild differs from the published run by "
                     f"{b_units - pub_units} units; the deltas above name the channel "
                     "responsible. Reported, not hidden."),
        },
        "verdict": ("The published 8.0% is not a consistent ratio. The fair repair is "
                    f"{len(a_cited)}/{len(a_units)} = "
                    f"{100*len(a_cited)/len(a_units):.2f}% (set union) or {b_cited}/{b_units} = "
                    f"{100*b_cited/b_units:.2f}% (containment). Per-channel and harness-only "
                    "rows are unaffected: each uses one channel in both terms."),
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)

    print(f"\npublished      {pub_cited:6d}/{pub_units:6d} = {100*pub_cited/pub_units:5.2f}%")
    print(f"frame A (set)  {len(a_cited):6d}/{len(a_units):6d} = "
          f"{100*len(a_cited)/len(a_units):5.2f}%")
    print(f"frame B (cont) {b_cited:6d}/{b_units:6d} = {100*b_cited/b_units:5.2f}%")
    print(f"duplicate citations removed: "
          f"{sum(len(cited_u[n]) for n in order) - len(a_cited)}")
    print(f"frame A populations: uncited {len(a_units)-len(a_cited)}, "
          f"ask-cue {len(a_ask)}, non-ask {len(a_non)}")
    print(f"drift vs published per channel: {drift or 'none'}")
    print(f"wrote {OUT}  [{time.time()-t0:.0f}s]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
