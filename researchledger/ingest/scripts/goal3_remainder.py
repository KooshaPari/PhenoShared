#!/usr/bin/env python3
"""Goal 3 step 4 (LOCAL): emit batches for the REMAINING unlabeled core units.

Census pass: everything in units_redacted.jsonl that is not an OPENING and was
not part of the 452-unit stratified sample gets labeled by M3 (redacted only).
"""
import json
import os

G3 = "/Users/kooshapari/Exports/analysis/goal3"
N_BATCHES = 8


def main():
    labeled = set()
    for i in range(4):
        with open(os.path.join(G3, "labels", f"l{i:02d}.jsonl"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    labeled.add(json.loads(line)["unit_id"])

    remaining = []
    with open(os.path.join(G3, "units_redacted.jsonl"), encoding="utf-8") as f:
        for line in f:
            u = json.loads(line)
            if u["heuristic_label"] == "OPENING":
                continue
            if u["unit_id"] in labeled:
                continue
            remaining.append({
                "unit_id": u["unit_id"],
                "user_excerpt": u["user_excerpt"],
                "assistant_prev_excerpt": u["assistant_prev_excerpt"],
            })

    outdir = os.path.join(G3, "label_batches2")
    os.makedirs(outdir, exist_ok=True)
    per = (len(remaining) + N_BATCHES - 1) // N_BATCHES
    manifest = []
    for i in range(N_BATCHES):
        chunk = remaining[i * per:(i + 1) * per]
        if not chunk:
            continue
        path = os.path.join(outdir, f"r{i:02d}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for u in chunk:
                f.write(json.dumps(u, ensure_ascii=False) + "\n")
        manifest.append({"batch": f"r{i:02d}", "n": len(chunk), "path": path})

    with open(os.path.join(G3, "label_batches2_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"already_labeled": len(labeled), "remaining": len(remaining), "batches": manifest}, f, indent=2)
    print(json.dumps({"already_labeled": len(labeled), "remaining": len(remaining), "batches": manifest}, indent=2))


if __name__ == "__main__":
    main()
