#!/usr/bin/env python3
"""Goal 3 step 5 (LOCAL): merge sample + census labels into final census stats.

Covers every core (non-OPENING) unit exactly once. Outputs:
  goal3/labels_all.jsonl          (unit_id, heuristic, m3, confidence, modifiers)
  goal3/tiering_stats_census.json (unweighted census numbers)
"""
import json
import os
from collections import Counter

G3 = "/Users/kooshapari/Exports/analysis/goal3"


def main():
    units = {}
    with open(os.path.join(G3, "units_redacted.jsonl"), encoding="utf-8") as f:
        for line in f:
            u = json.loads(line)
            units[u["unit_id"]] = u

    labels = {}
    dupes = 0
    for d in ("labels", "labels2"):
        dd = os.path.join(G3, d)
        if not os.path.isdir(dd):
            continue
        for fn in sorted(os.listdir(dd)):
            if not fn.endswith(".jsonl"):
                continue
            with open(os.path.join(dd, fn), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    if r["unit_id"] in labels:
                        dupes += 1
                    labels[r["unit_id"]] = r

    core = {k: v for k, v in units.items() if v["heuristic_label"] != "OPENING"}
    missing = [k for k in core if k not in labels]
    extra = [k for k in labels if k not in core]

    rows = []
    dist, conf, mods = Counter(), Counter(), Counter()
    agree_h = Counter()
    total_h = Counter()
    for uid, u in core.items():
        lab = labels.get(uid)
        if not lab:
            continue
        h = u["heuristic_label"]
        total_h[h] += 1
        if h == lab["label"]:
            agree_h[h] += 1
        dist[lab["label"]] += 1
        conf[lab.get("confidence", "med")] += 1
        for m in lab.get("modifiers", []):
            mods[m] += 1
        rows.append({"unit_id": uid, "heuristic": h, "m3": lab["label"],
                     "confidence": lab.get("confidence", "med"), "modifiers": lab.get("modifiers", [])})

    with open(os.path.join(G3, "labels_all.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    n = len(rows)
    lexical_ok = sum(agree_h.values())
    t1 = lexical_ok / max(1, n)
    t3 = sum(1 for r in rows if r["m3"] in ("ESCALATE", "UNKNOWN") or r["confidence"] == "low") / max(1, n)
    t2 = max(0.0, 1 - t1 - t3)

    out = {
        "core_units": len(core),
        "labeled": n,
        "missing_labels": len(missing),
        "extra_labels": len(extra),
        "dupes_seen": dupes,
        "m3_label_distribution": dict(dist.most_common()),
        "confidence": dict(conf.most_common()),
        "modifiers": dict(mods.most_common()),
        "tier1_lexical_agreement_share": round(t1, 4),
        "tier3_ambiguous_or_lowconf_share": round(t3, 4),
        "tier2_context_required_share": round(t2, 4),
        "per_heuristic_agreement": {h: f"{agree_h[h]}/{total_h[h]} ({agree_h[h]/total_h[h]:.0%})" for h in sorted(total_h, key=lambda x: -total_h[x])},
    }
    with open(os.path.join(G3, "tiering_stats_census.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
