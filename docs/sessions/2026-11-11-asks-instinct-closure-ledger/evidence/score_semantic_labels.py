#!/usr/bin/env python3
"""Recompute every published semantic-probe figure from the probe output and the labels.

WHY A SEPARATE SCORER. The point of this file is that no number in VERDICT.md is
typed by hand. It reads `semantic_coverage_probe.json` (what the model produced) and
`semantic_label_review.json` (what a human decided), and derives the only claims made:

  1. detector precision in the high band, strict (M only) and lenient (M or W);
  2. detector behaviour in the low band, which bounds false negatives there;
  3. a LOWER BOUND on semantically-captured uncited clauses, which is the only
     coverage-flavoured statement this design supports.

WHY THERE IS NO SEMANTIC COVERAGE PERCENTAGE. A coverage estimate needs the
detector's recall as well as its precision. Recall cannot be measured here: only 45
of 800 pairs were labelled, so matches below the top-30 cut are uncounted, and with
high-band precision short of certainty, extrapolation would multiply a weak detector
by an unknown miss rate. The scheduled task required withholding the headline if
recall could not be established; this is that condition. The lower bound is
published instead because it is true regardless of recall.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "semantic_coverage_probe.json")
LABELS = os.path.join(HERE, "semantic_label_review.json")
OUT = os.path.join(HERE, "semantic_scored.json")


def main() -> int:
    probe = json.load(open(PROBE))
    labels = json.load(open(LABELS))
    n_sample = probe["population"]["sample_size"]

    res: dict = {"derived_at_utc": probe["generated_at_utc"],
                 "inputs": {"probe": os.path.basename(PROBE),
                            "labels": os.path.basename(LABELS)},
                 "population": probe["population"]}

    def band(name: str) -> dict:
        items = labels["bands"][name]["labels"]
        n = len(items)
        c = {k: sum(1 for i in items if i["label"] == k) for k in ("M", "W", "N")}
        strict = c["M"] / n
        lenient = (c["M"] + c["W"]) / n
        return {"n": n, "counts": c,
                "precision_strict": round(strict, 4),
                "precision_lenient": round(lenient, 4),
                "cosine_range": labels["bands"][name]["cosine_range"]}

    high, low = band("high"), band("low")
    res["high_band"] = high
    res["low_band"] = low

    # Every pair in the high band sits above the 30th-highest score of 800, so the
    # high band is by construction 30/800 of the sample. Confirmed from the probe.
    hs = probe["hand_label_sample"]["high"]
    n_above = sum(1 for r in hs if r["cosine"] >= min(x["cosine"] for x in hs))
    res["high_band_share_of_sample"] = round(n_above / n_sample, 4)

    # Lower bound: confirmed matches among the 800 sampled uncited clauses. Lower
    # bounds are valid under unmeasured recall because misses are simply not counted.
    res["confirmed_captured_uncited"] = {
        "strict": high["counts"]["M"],
        "lenient_including_weak": high["counts"]["M"] + high["counts"]["W"],
        "of_sample": n_sample,
        "lower_bound_pct_strict": round(high["counts"]["M"] / n_sample * 100, 2),
        "lower_bound_pct_lenient": round((high["counts"]["M"] + high["counts"]["W"])
                                        / n_sample * 100, 2),
        "reads_as": ("at least this share of uncited ask-cue clauses are captured by a "
                     "register ask; not a coverage rate, a floor"),
    }

    res["withheld"] = {
        "semantic_coverage_pct": "NOT PUBLISHED",
        "reason": ("recall unmeasured: 45 of 800 labelled, matches below the top-30 cut "
                   "uncounted, and high-band precision is below certainty so "
                   "extrapolation would compound a weak detector with an unknown miss rate"),
        "condition_that_would_unblock_it": ("label a random (not stratified) sample of "
                                            "the 800 so recall is estimated on the same "
                                            "distribution, or add a second rater and a "
                                            "larger high band"),
    }

    res["does_not_change"] = {
        "structural_coverage_all_units_pct": 8.0,
        "note": ("different denominator (all 43,305 clause units); these two figures must "
                 "never be added or presented as a single coverage number"),
    }

    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1)

    print(f"high band n={high['n']} {high['counts']} "
          f"precision strict={high['precision_strict']:.3f} lenient={high['precision_lenient']:.3f}")
    print(f"low  band n={low['n']} {low['counts']} precision strict={low['precision_strict']:.3f}")
    print(f"lower bound: {res['confirmed_captured_uncited']['strict']}/{n_sample} = "
          f"{res['confirmed_captured_uncited']['lower_bound_pct_strict']}% strict, "
          f"{res['confirmed_captured_uncited']['lower_bound_pct_lenient']}% lenient")
    print(f"semantic coverage: {res['withheld']['semantic_coverage_pct']}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
