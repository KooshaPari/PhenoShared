#!/usr/bin/env python3
"""Measure agreement between the two independent labellers on all three bucket sheets.

Inputs per bucket: the first labeller's labels and the second labeller's labels.
Output: inter_labeller_agreement.json

Reported per bucket:
  - raw agreement over six classes (operator/agent/tool/system/peer/other)
  - Cohen's kappa over six classes
  - raw agreement and Cohen's kappa over the two-class collapse operator / non-operator,
    which is the distinction the coverage estimate actually uses
  - each labeller's operator share, so the reader can see whether disagreement moves
    the headline figure
  - the disagreement list (idx + short preview), so a human can adjudicate

A missing second-labeller file is reported as NOT_RUN, never as agreement.

Usage: inter_labeller_agreement.py [--require-all]
  exit 0  all three buckets measured
  exit 3  at least one bucket NOT_RUN (partial run; the JSON says which)
  exit 2  --require-all was passed and a bucket is missing
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "inter_labeller_agreement.json")
CLASSES = ["operator", "agent", "tool", "system", "peer", "other"]
NONOP = ["agent", "tool", "system", "peer", "other"]

# bucket -> (first labeller reader, second labeller reader)
SPEC = [
    ("cited",
     ("cited_labels.json", "items", "speaker",
      "first labeller (cited_speaker_sheet; cited_labels.json assembled from cited_labels_partial.tsv + chunks 20-39/40-59)"),
     ("cited_labels_l2.json", "items", "speaker",
      "second independent labeller (cited_labels_l2.json)")),
    ("uncited_ask_cue",
     ("askcue_labels.json", "items", "speaker",
      "first labeller (askcue_labels.json)"),
     ("askcue_labels_l2.json", "items", "speaker",
      "second independent labeller (askcue_labels_l2.json)")),
    ("uncited_non_ask_cue",
     ("nonask_label_sheet.json", "items", "speaker_pass2",
      "first labeller (nonask_label_sheet.json:speaker_pass2)"),
     ("nonask_labels_l2.json", "items", "speaker",
      "second independent labeller (nonask_labels_l2.json)")),
]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def index_by_idx(doc, key):
    out = {}
    for item in doc:
        idx = item.get("idx")
        val = item.get(key)
        if idx is None:
            raise SystemExit("DRIFT: item without idx in %s" % key)
        if idx in out:
            raise SystemExit("DRIFT: duplicate idx %r" % idx)
        out[idx] = (val, item.get("clause", ""))
    return out


def kappa(pairs, classes):
    n = len(pairs)
    if n == 0:
        return None, None
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    pe = 0.0
    for c in classes:
        p1 = sum(1 for a, _ in pairs if a == c) / n
        p2 = sum(1 for _, b in pairs if b == c) / n
        pe += p1 * p2
    if abs(1.0 - pe) < 1e-12:
        return po, None  # degenerate: one labeller used a single class for everything
    return po, (po - pe) / (1.0 - pe)


def collapse(val):
    if val in CLASSES:
        return "operator" if val == "operator" else "non_operator"
    return "unknown"


def measure(l1_spec, l2_spec):
    f1, k1, c1, who1 = l1_spec
    f2, k2, c2, who2 = l2_spec
    p1, p2 = os.path.join(HERE, f1), os.path.join(HERE, f2)
    missing = [p for p in (p1, p2) if not os.path.exists(p)]
    if missing:
        return {"status": "NOT_RUN",
                "missing_files": [os.path.basename(p) for p in missing],
                "labellers": [who1, who2]}

    a = index_by_idx(load(p1)[k1], c1)
    b = index_by_idx(load(p2)[k2], c2)
    if set(a) != set(b):
        raise SystemExit("DRIFT: idx sets differ between %s and %s" % (f1, f2))

    idxs = sorted(a)
    pairs = [(a[i][0], b[i][0]) for i in idxs]
    six_po, six_k = kappa(pairs, CLASSES)
    two = [(collapse(x), collapse(y)) for x, y in pairs]
    two_po, two_k = kappa(two, ["operator", "non_operator"])

    op1 = sum(1 for x, _ in pairs if x == "operator")
    op2 = sum(1 for _, y in pairs if y == "operator")
    n = len(pairs)

    conf = {c: {d: 0 for d in CLASSES} for c in CLASSES}
    for x, y in pairs:
        conf[str(x)][str(y)] = conf.get(str(x), {}).get(str(y), 0) + 1

    dis = [{"idx": i, "l1": a[i][0], "l2": b[i][0],
            "preview": " ".join(a[i][1].split())[:90]}
           for i in idxs if a[i][0] != b[i][0]]

    return {
        "status": "MEASURED",
        "labellers": [who1, who2],
        "n_paired": n,
        "six_class": {
            "raw_agreement": six_po,
            "cohen_kappa": six_k,
            "confusion_l1_rows_by_l2_cols": conf,
        },
        "operator_vs_rest": {
            "raw_agreement": two_po,
            "cohen_kappa": two_k,
            "note": "this two-class collapse is the distinction the coverage estimate uses",
        },
        "operator_share": {
            "labeller_1": {"count": op1, "of": n, "share": op1 / n},
            "labeller_2": {"count": op2, "of": n, "share": op2 / n},
            "absolute_difference_pp": round(abs(op1 - op2) / n * 100.0, 2),
        },
        "disagreements": dis,
        "n_disagreements": len(dis),
    }


def interpret(six_k, two_k):
    """Plain-language reading of one kappa."""
    k = two_k if two_k is not None else six_k
    if k is None:
        return "undefined (degenerate marginals)"
    if k >= 0.81:
        return "almost perfect"
    if k >= 0.61:
        return "substantial"
    if k >= 0.41:
        return "moderate"
    if k >= 0.21:
        return "fair"
    if k >= 0.01:
        return "slight"
    return "no better than chance"


def main():
    require_all = "--require-all" in sys.argv
    buckets = []
    for name, l1, l2 in SPEC:
        r = measure(l1, l2)
        r["bucket"] = name
        buckets.append(r)

    measured = [b for b in buckets if b["status"] == "MEASURED"]
    pooled_pairs = []
    if len(measured) == len(buckets):
        for name, l1, l2 in SPEC:
            a = index_by_idx(load(os.path.join(HERE, l1[0]))[l1[1]], l1[2])
            b = index_by_idx(load(os.path.join(HERE, l2[0]))[l2[1]], l2[2])
            pooled_pairs += [(a[i][0], b[i][0]) for i in sorted(a)]
    pooled = None
    if pooled_pairs:
        po6, k6 = kappa(pooled_pairs, CLASSES)
        pt, kt = kappa([(collapse(x), collapse(y)) for x, y in pooled_pairs],
                       ["operator", "non_operator"])
        pooled = {"n_paired": len(pooled_pairs),
                  "six_class": {"raw_agreement": po6, "cohen_kappa": k6},
                  "operator_vs_rest": {"raw_agreement": pt, "cohen_kappa": kt},
                  "note": "pooling across buckets is descriptive only; the three samples "
                          "are not one random sample of the corpus"}

    out = {
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "inter_labeller_agreement.py",
        "question": "do two independent labellers, reading the same 60 clauses per bucket, "
                    "assign the same authorship?",
        "readings": {b["bucket"]: interpret(b["six_class"]["cohen_kappa"],
                                            b["operator_vs_rest"]["cohen_kappa"])
                     for b in measured},
        "per_bucket": buckets,
        "pooled": pooled,
        "caveats": {
            "labellers_not_identical_in_kind": "labeller 1 and labeller 2 are both model "
                                               "labellers working from the same rubric; "
                                               "agreement measures rubric reproducibility, "
                                               "not human ground truth",
            "no_adjudication_yet": "disagreeing clauses are listed, not resolved; the "
                                   "coverage figure is not corrected by this file",
            "chance_correction": "Cohen's kappa is reported alongside raw agreement because "
                                 "raw agreement alone is inflated when one class dominates "
                                 "(operator is 38-97% of a bucket)",
            "small_n": "n=60 per bucket; kappa intervals are wide and are not computed here",
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")

    for b in buckets:
        if b["status"] != "MEASURED":
            print("%-20s NOT_RUN  missing=%s" % (b["bucket"], b["missing_files"]))
            continue
        print("%-20s n=%d 6-class po=%.3f k=%.3f | op-vs-rest po=%.3f k=%.3f | "
              "op share L1=%.3f L2=%.3f | disagreements=%d"
              % (b["bucket"], b["n_paired"],
                 b["six_class"]["raw_agreement"], b["six_class"]["cohen_kappa"] or float("nan"),
                 b["operator_vs_rest"]["raw_agreement"],
                 b["operator_vs_rest"]["cohen_kappa"] or float("nan"),
                 b["operator_share"]["labeller_1"]["share"],
                 b["operator_share"]["labeller_2"]["share"],
                 b["n_disagreements"]))
    if pooled:
        print("pooled n=%d 6-class po=%.3f k=%.3f | op-vs-rest po=%.3f k=%.3f"
              % (pooled["n_paired"], pooled["six_class"]["raw_agreement"],
                 pooled["six_class"]["cohen_kappa"],
                 pooled["operator_vs_rest"]["raw_agreement"],
                 pooled["operator_vs_rest"]["cohen_kappa"]))
    print("wrote %s" % OUT)

    if len(measured) != len(buckets):
        print("PARTIAL: %d of %d buckets measured" % (len(measured), len(buckets)))
        return 2 if require_all else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
