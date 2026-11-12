#!/usr/bin/env python3
"""Score the citation-precision sample: do the register's citations point at the right intent?

Inputs:  precision_labeled.json (verdicts filled) + precision_key.json (channel, link role,
         relation, fidelity per row, withheld from the labeller).
Output:  precision_scored.json

Two figures are reported, never one:
  strict precision = supported / judgeable
  lenient precision = (supported + partial) / judgeable
  judgeable = supported + partial + unsupported  (unresolvable is excluded and counted)

The denominator is 2,252 ORIGIN LINKS, not the 1,938 distinct cited units. Those are different
quantities and must not be interchanged: one unit can carry several links.

Usage: precision_score.py [--require-complete]
  exit 0  scored
  exit 3  precision_labeled.json is absent or has null verdicts (nothing scored, file says NOT_RUN)
  exit 2  --require-complete passed and the sample is incomplete
"""
import json, math, os, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = os.path.join(HERE, "precision_labeled.json")
KEY = os.path.join(HERE, "precision_key.json")
OUT = os.path.join(HERE, "precision_scored.json")
Z = 1.959963984540054
VERDICTS = ["supported", "partial", "unsupported", "unresolvable"]


def wilson(k, n, z=Z):
    if n == 0:
        return None
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def main():
    require = "--require-complete" in sys.argv
    if not os.path.exists(SHEET):
        print("NOT_RUN: %s is absent" % os.path.basename(SHEET))
        return 2 if require else 3
    doc = json.load(open(SHEET, encoding="utf-8"))
    items = doc["items"]
    nulls = [i["idx"] for i in items if not i.get("verdict")]
    if nulls:
        print("NOT_RUN: %d of %d verdicts are null (first: %r)" % (len(nulls), len(items), nulls[:5]))
        return 2 if require else 3
    bad = [i["idx"] for i in items if i["verdict"] not in VERDICTS]
    if bad:
        raise SystemExit("DRIFT: illegal verdict values at idx %r" % bad[:5])
    if sorted(i["idx"] for i in items) != list(range(len(items))):
        raise SystemExit("DRIFT: idx set is not 0..n-1")

    counts = {v: sum(1 for i in items if i["verdict"] == v) for v in VERDICTS}
    n = len(items)
    judgeable = counts["supported"] + counts["partial"] + counts["unsupported"]
    strict = counts["supported"] / judgeable if judgeable else None
    lenient = ((counts["supported"] + counts["partial"]) / judgeable) if judgeable else None

    key = {}
    if os.path.exists(KEY):
        kd = json.load(open(KEY, encoding="utf-8"))
        key = {r["idx"]: r for r in (kd.get("rows") or [])}
    population = doc.get("population") or {}

    def by(field):
        groups = {}
        for it in items:
            g = str(key.get(it["idx"], {}).get(field, "UNKNOWN"))
            groups.setdefault(g, {"n": 0, "supported": 0, "partial": 0,
                                  "unsupported": 0, "unresolvable": 0})
            groups[g]["n"] += 1
            groups[g][it["verdict"]] += 1
        for g, v in groups.items():
            j = v["supported"] + v["partial"] + v["unsupported"]
            v["strict_precision"] = (v["supported"] / j) if j else None
            v["lenient_precision"] = ((v["supported"] + v["partial"]) / j) if j else None
        return groups

    out = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "precision_score.py",
        "question": "of the citations the register counted, what share point at a source unit that "
                    "actually carries the intent?",
        "labeller": doc.get("labeller"),
        "n": n,
        "counts": counts,
        "judgeable": judgeable,
        "unresolvable_excluded": counts["unresolvable"],
        "precision": {
            "strict": {"value": strict, "wilson_95": wilson(counts["supported"], judgeable),
                       "definition": "supported / (supported + partial + unsupported)"},
            "lenient": {"value": lenient,
                        "wilson_95": wilson(counts["supported"] + counts["partial"], judgeable),
                        "definition": "(supported + partial) / (supported + partial + unsupported)"},
        },
        "denominator": {
            "sampled_from": population.get("cited_pairs"),
            "unit_of_measure": "origin links (one unit can carry several links)",
            "distinct_cited_units_elsewhere": 1938,
            "warning": "2,252 origin links and 1,938 distinct cited units are different quantities; "
                       "a precision measured over links must not be multiplied into a unit count",
        },
        "by_channel": by("channel"),
        "by_relation": by("relation"),
        "by_link_role": by("link_role"),
        "retrieval_failure_modes": [{"idx": i["idx"], "verdict": i["verdict"], "why": i.get("why", "")}
                                    for i in items if i["verdict"] != "supported"],
        "caveats": {
            "single_labeller": "one model labeller produced all 60 verdicts; no second pass exists",
            "n_60": "n=60 links sampled from %r; a Wilson interval is reported but the sample is "
                    "not stratified by channel" % population.get("cited_pairs"),
            "quote_fidelity_is_not_precision": "ask_link_verification.json measures whether the "
                                               "quoted words appear in the cited utterance (strict "
                                               "97.08%, folded 99.13%). That is a precondition, not "
                                               "a measure of whether the utterance belongs to the "
                                               "intent, which is what this file measures",
            "partial_is_not_free": "the lenient figure credits a unit that states only part of the "
                                   "claim or fits a sibling ask equally well; quote both, never the "
                                   "lenient one alone",
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")

    print("n=%d judgeable=%d unresolvable=%d" % (n, judgeable, counts["unresolvable"]))
    for v in VERDICTS:
        print("  %-13s %d" % (v, counts[v]))
    if strict is not None:
        s, l = out["precision"]["strict"], out["precision"]["lenient"]
        print("strict  precision %.3f  wilson95 [%.3f, %.3f]" % (s["value"], s["wilson_95"][0], s["wilson_95"][1]))
        print("lenient precision %.3f  wilson95 [%.3f, %.3f]" % (l["value"], l["wilson_95"][0], l["wilson_95"][1]))
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
