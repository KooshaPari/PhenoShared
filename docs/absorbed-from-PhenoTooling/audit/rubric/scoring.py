#!/usr/bin/env python3
"""Score a repo against the unified rubric. Usage:
    python3 scoring.py <scorecard.json>   # scorecard has criteria[] with status per id
"""
import json, sys, math
from collections import defaultdict

W = {"satisfied": 1.0, "partial": 0.5, "missing": 0.0}
CONF = {"satisfied": 0.95, "partial": 0.6, "missing": 0.9}

def score(rubric_path, audit_path):
    rubric = json.load(open(rubric_path))
    audit = json.load(open(audit_path))
    aud = {c["id"]: c for c in audit.get("criteria", [])}
    dom_scores = defaultdict(list)
    scored = skipped = 0
    for c in rubric["criteria"]:
        a = aud.get(c["id"])
        if not a: skipped += 1; continue
        st = a.get("status", "reference")
        if st not in W: skipped += 1; continue
        w = a.get("weight", 1.0)
        s = W[st] * w
        conf = a.get("confidence", CONF[st])
        dom_scores[c["domain"]].append((s, w, conf))
        scored += 1
    out = {"scored": scored, "skipped_reference_or_unmatched": skipped, "domains": {}}
    tw = tn = 0.0
    for dom, vals in sorted(dom_scores.items()):
        num = sum(s for s, w, cf in vals)
        den = sum(w for s, w, cf in vals) or 1.0
        pct = 100.0 * num / den
        # Wilson-style 95% CI proxy via confidence-weighted variance
        var = sum((cf - (num/den))**2 for s, w, cf in vals) / max(len(vals)-1, 1)
        ci = 1.96 * math.sqrt(max(var, 0.0) / len(vals))
        out["domains"][dom] = {"pct": round(pct, 2), "n": len(vals), "ci95": round(100*ci, 2)}
        tw += num; tn += den
    out["overall_pct"] = round(100.0 * tw / (tn or 1.0), 2)
    out["grade"] = ("A+" if out["overall_pct"] >= 97 else "A" if out["overall_pct"] >= 93 else
                    "B+" if out["overall_pct"] >= 87 else "B" if out["overall_pct"] >= 80 else
                    "C" if out["overall_pct"] >= 70 else "D" if out["overall_pct"] >= 60 else "F")
    return out

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    print(json.dumps(score(sys.argv[1], sys.argv[2]), indent=2))
