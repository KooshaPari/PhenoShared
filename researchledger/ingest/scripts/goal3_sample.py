#!/usr/bin/env python3
"""Goal 3 step 2 (LOCAL): stratified sample + batch files for hosted labeling.

Takes units_redacted.jsonl, stratifies by heuristic label (all rare labels kept,
capped samples of common ones), shuffles with a fixed seed, and writes batch
files for M3 labelers. Input units are already redacted; nothing raw leaves.
"""
import json
import os
import random

G3 = "/Users/kooshapari/Exports/analysis/goal3"
BATCHES = os.path.join(G3, "label_batches")

CAPS = {
    "APPROVE": 60, "REJECT": 100, "NEW_TASK": 60, "ASK_WHY": 60,
    "ELABORATE": 60, "UNKNOWN": 84, "OPENING": 0,  # OPENING excluded: no reaction context
}
# rare labels kept in full
RARE = ["DEFER", "CORRECT", "REDIRECT", "PHATIC", "TIGHTEN"]


def main():
    os.makedirs(BATCHES, exist_ok=True)
    units = []
    with open(os.path.join(G3, "units_redacted.jsonl"), encoding="utf-8") as f:
        for line in f:
            units.append(json.loads(line))

    by_label = {}
    for u in units:
        by_label.setdefault(u["heuristic_label"], []).append(u)

    sample = []
    for lab, cap in CAPS.items():
        pool = by_label.get(lab, [])
        random.seed(42)
        if cap == 0:
            continue
        random.shuffle(pool)
        sample.extend(pool[:cap])
    for lab in RARE:
        sample.extend(by_label.get(lab, []))

    random.seed(7)
    random.shuffle(sample)

    n_batches = 4
    per = (len(sample) + n_batches - 1) // n_batches
    manifest = []
    for i in range(n_batches):
        chunk = sample[i * per:(i + 1) * per]
        if not chunk:
            continue
        path = os.path.join(BATCHES, f"b{i:02d}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for u in chunk:
                f.write(json.dumps({
                    "unit_id": u["unit_id"],
                    "user_excerpt": u["user_excerpt"],
                    "assistant_prev_excerpt": u["assistant_prev_excerpt"],
                }, ensure_ascii=False) + "\n")
        manifest.append({"batch": f"b{i:02d}", "n": len(chunk), "path": path})

    with open(os.path.join(G3, "label_batches_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"total_units": len(sample), "batches": manifest}, f, indent=2)
    print(json.dumps({"total_sampled": len(sample), "batches": manifest}, indent=2))


if __name__ == "__main__":
    main()
