#!/usr/bin/env python3
"""Score the ask-cue classifier against hand labels and derive what it can support.

Reports
  precision      share of PRED_ASK units actually labelled ASK
  ask rate in    share of PRED_NOT units actually labelled ASK -> the classifier's miss rate
  the rejected   stratum
  estimated      population of true ask units, combining both strata
  recall         share of true asks the classifier catches
  coverage band  harness ask-unit citation coverage under the estimated true denominator

Why this matters: segment_units.py gates its TIGHTER denominator on this classifier. If
precision and recall are weak, that denominator is not a measurement and its coverage
figure must not be published. This script is what decides that, rather than assertion.
"""
from __future__ import annotations

import json
import sys

BASE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
UNITS = f"{BASE}/granularity_units.json"
SAMPLE = f"{BASE}/ask_rule_sample.json"
LABELS = f"{BASE}/ask_rule_labels.json"
OUT = f"{BASE}/ask_rule_validation.json"


def main() -> int:
    u = json.load(open(UNITS))
    s = json.load(open(SAMPLE))
    lab = json.load(open(LABELS))["labels"]
    rows = s["rows"]
    pop_ask = s["population"]["pred_ask"]
    pop_not = s["population"]["pred_not"]
    pop_total = pop_ask + pop_not

    def tally(stratum: str) -> dict[str, int]:
        c: dict[str, int] = {}
        for i, r in enumerate(rows, 1):
            if r["stratum"] != stratum:
                continue
            c[lab[str(i)]] = c.get(lab[str(i)], 0) + 1
        return c

    a = tally("PRED_ASK")
    n = tally("PRED_NOT")
    na = sum(a.values())
    nn = sum(n.values())
    precision = a.get("ASK", 0) / na
    miss_rate = n.get("ASK", 0) / nn

    true_ask = pop_ask * precision + pop_not * miss_rate
    recall = (pop_ask * precision) / true_ask

    # cited ask units: 129 passed the gate. Correct for the gate's precision and add the
    # expected true asks inside the cited-but-rejected units, using the rejected stratum's
    # ask rate. Both terms carry sampling error, so the result is a band, not a point.
    cited_gated = u["cited_units_harness_ask_only"]
    cited_harness = u["per_channel"]["harness"]["cited_units"]
    cited_ungated = cited_harness - cited_gated
    est_cited_true = cited_gated * precision + cited_ungated * miss_rate
    cov_lo = est_cited_true / true_ask
    cov_hi = (cited_gated + cited_ungated * miss_rate) / true_ask
    point = u["per_channel"]["harness"]["cited_units"] / u["per_channel"]["harness"]["distinct_units"]

    print(f"PRED_ASK stratum  n={na}  {a}")
    print(f"PRED_NOT stratum  n={nn}  {n}")
    print(f"\nprecision                        {precision:.3f}"
          f"  ({a.get('ASK',0)}/{na})")
    print(f"miss rate in rejected stratum    {miss_rate:.3f}"
          f"  ({n.get('ASK',0)}/{nn})")
    print(f"estimated true ask units         {true_ask:.0f}  of {pop_total} units"
          f" = {true_ask/pop_total*100:.1f}%")
    print(f"recall                           {recall:.3f}")
    print(f"\ngated denominator (published?)   {pop_ask} units")
    print(f"  vs estimated true asks         {true_ask:.0f}  -> understates by "
          f"{(1-pop_ask/true_ask)*100:.1f}%")
    print(f"\nharness ask-unit coverage, point estimate on the gated denominator: "
          f"{cited_gated/pop_ask*100:.1f}%")
    print(f"harness ask-unit coverage, corrected for gate error: "
          f"{cov_lo*100:.1f}% - {cov_hi*100:.1f}%")
    print(f"harness all-unit coverage (no classifier, mechanical): {point*100:.1f}%")

    verdict = ("REJECT for publication" if (precision < 0.9 or recall < 0.9)
               else "usable with the stated error")
    print(f"\nverdict: {verdict}  (precision {precision:.2f}, recall {recall:.2f})")
    print("  -> publish the ALL_UNITS figure, which needs no classifier, and report the")
    print("     ask-normalised figure only as a labelled estimate with this error.")

    json.dump({
        "seed": s["seed"],
        "strata": {"PRED_ASK": a, "PRED_NOT": n},
        "n": {"PRED_ASK": na, "PRED_NOT": nn},
        "population": {"pred_ask": pop_ask, "pred_not": pop_not},
        "precision": round(precision, 3),
        "miss_rate_rejected_stratum": round(miss_rate, 3),
        "estimated_true_ask_units": round(true_ask),
        "estimated_true_ask_share_pct": round(true_ask / pop_total * 100, 1),
        "recall": round(recall, 3),
        "coverage_gated_pct": round(cited_gated / pop_ask * 100, 1),
        "coverage_corrected_pct_range": [round(cov_lo * 100, 1), round(cov_hi * 100, 1)],
        "coverage_all_units_pct": round(point * 100, 1),
        "verdict": verdict,
        "limits": ("single coder; units judged without parent message, which biases terse "
                   "fragments toward NOT_ASK; iMessage and KCode not sampled"),
    }, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
