#!/usr/bin/env python3
"""Goal 3 step 3 (LOCAL): join M3 labels with units, estimate tiering.

Outputs goal3/tiering_stats.json and goal3/tiering_report.md seed data:
  - M3 label distribution (stratum-weighted to full population)
  - lexical (tier-1 heuristic) vs M3 agreement per label
  - predictability shares for the 3-tier split
  - modifiers
"""
import json
import os
from collections import Counter, defaultdict

G3 = "/Users/kooshapari/Exports/analysis/goal3"

# stratum sizes from the full heuristic run
STRATUM_POP = {
    "UNKNOWN": 1464, "ELABORATE": 792, "OPENING": 585, "REJECT": 313,
    "NEW_TASK": 172, "ASK_WHY": 143, "APPROVE": 38, "TIGHTEN": 22,
    "DEFER": 14, "CORRECT": 8, "REDIRECT": 5, "PHATIC": 1,
}


def main():
    units = {}
    with open(os.path.join(G3, "units_redacted.jsonl"), encoding="utf-8") as f:
        for line in f:
            u = json.loads(line)
            units[u["unit_id"]] = u

    labels = []
    for i in range(4):
        p = os.path.join(G3, "labels", f"l{i:02d}.jsonl")
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    labels.append(json.loads(line))

    joined = []
    for lab in labels:
        u = units.get(lab["unit_id"])
        if not u:
            continue
        h = u["heuristic_label"]
        pop = STRATUM_POP.get(h, 0)
        joined.append({
            "unit_id": lab["unit_id"], "heuristic": h, "m3": lab["label"],
            "confidence": lab.get("confidence", "med"), "modifiers": lab.get("modifiers", []),
            "weight": pop / max(1, sum(1 for j in joined if j["heuristic"] == h) + 1),  # fixed below
        })

    # proper stratum weights: N_h / n_h(sampled with label h)
    sampled = Counter(j["heuristic"] for j in joined)
    for j in joined:
        j["weight"] = STRATUM_POP.get(j["heuristic"], 0) / max(1, sampled[j["heuristic"]])

    total_w = sum(j["weight"] for j in joined)
    dist = Counter()
    mods = Counter()
    conf = Counter()
    agree = Counter()      # per-heuristic-label agreement with M3
    total_by_h = Counter()
    for j in joined:
        dist[j["m3"]] += j["weight"]
        conf[j["confidence"]] += j["weight"]
        for m in j["modifiers"]:
            mods[m] += j["weight"]
        total_by_h[j["heuristic"]] += 1
        if j["heuristic"] == j["m3"]:
            agree[j["heuristic"]] += 1

    # Tier math (population-weighted):
    # tier1_share: lexical heuristic agrees with M3 (excluding OPENING/UNKNOWN strata)
    core = [j for j in joined if j["heuristic"] not in ("OPENING", "UNKNOWN")]
    core_w = sum(j["weight"] for j in core)
    agree_w = sum(j["weight"] for j in core if j["heuristic"] == j["m3"])
    t1 = agree_w / max(1e-9, core_w)
    # tier3_share: M3 says ESCALATE/UNKNOWN or confidence=low
    t3 = sum(j["weight"] for j in core if j["m3"] in ("ESCALATE", "UNKNOWN") or j["confidence"] == "low") / max(1e-9, core_w)
    t2 = max(0.0, 1 - t1 - t3)

    out = {
        "sample_units_labeled": len(joined),
        "population_estimate_units": round(total_w),
        "m3_label_distribution_weighted": {k: round(v) for k, v in dist.most_common()},
        "confidence_weighted": {k: round(v) for k, v in conf.most_common()},
        "modifiers_weighted": {k: round(v) for k, v in mods.most_common()},
        "tier1_lexical_agreement_share_core": round(t1, 4),
        "tier3_ambiguous_or_lowconf_share_core": round(t3, 4),
        "tier2_context_required_share_core": round(t2, 4),
        "per_heuristic_agreement": {h: f"{agree[h]}/{total_by_h[h]} ({agree[h]/total_by_h[h]:.0%})" for h in sorted(total_by_h, key=lambda x: -total_by_h[x])},
    }
    with open(os.path.join(G3, "tiering_stats.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    # redacted per-label examples for the report
    examples = defaultdict(list)
    for j in joined:
        u = units[j["unit_id"]]
        if len(examples[j["m3"]]) < 3:
            examples[j["m3"]].append({"unit": j["unit_id"][:20], "user": u["user_excerpt"][:180], "heur": j["heuristic"], "conf": j["confidence"]})
    with open(os.path.join(G3, "label_examples.json"), "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2, ensure_ascii=False)

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
