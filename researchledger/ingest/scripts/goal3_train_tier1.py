#!/usr/bin/env python3
"""Goal 3 step 6 (LOCAL): train the tier-1 cheap classifier on the census labels.

Features: lexical booleans (already computed) + word 1-2 gram TF-IDF + char 3-5
gram TF-IDF of the redacted user excerpt. Split by conversation to avoid
leakage. Reports accuracy, macro-F1, per-label metrics, and the deployable
tier-1 coverage at >=95% precision. Saves the model.
"""
import json
import os
import re
from collections import defaultdict

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline

G3 = "/Users/kooshapari/Exports/analysis/goal3"
FEATS = ["wc", "is_question", "has_negation", "starts_redirect", "imperative",
         "approve_cue", "reject_cue", "defer_cue", "tighten_cue", "correct_cue",
         "why_cue", "thanks_cue", "urgent_cue", "frustration_cue"]


def main():
    units = {}
    with open(os.path.join(G3, "units_redacted.jsonl"), encoding="utf-8") as f:
        for line in f:
            u = json.loads(line)
            units[u["unit_id"]] = u

    rows = []
    with open(os.path.join(G3, "labels_all.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            u = units.get(r["unit_id"])
            if not u:
                continue
            rows.append({
                "unit_id": r["unit_id"],
                "conv": r["unit_id"].split(":")[1],
                "text": (u["user_excerpt"] or "").lower(),
                "label": r["m3"],
                "feats": [1.0 if u["features"].get(k) else 0.0 for k in FEATS] + [min(u["features"].get("wc", 0), 200) / 50.0],
            })

    # conversation-level split (deterministic)
    convs = sorted({r["conv"] for r in rows})
    rng = np.random.RandomState(7)
    rng.shuffle(convs)
    n_test_conv = max(1, int(len(convs) * 0.2))
    test_convs = set(convs[:n_test_conv])
    tr = [r for r in rows if r["conv"] not in test_convs]
    te = [r for r in rows if r["conv"] in test_convs]

    word_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=8000, min_df=2)
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=8000, min_df=3)
    Xw_tr = word_vec.fit_transform([r["text"] for r in tr])
    Xc_tr = char_vec.fit_transform([r["text"] for r in tr])
    Xw_te = word_vec.transform([r["text"] for r in te])
    Xc_te = char_vec.transform([r["text"] for r in te])

    from scipy.sparse import csr_matrix
    F_tr = csr_matrix(np.array([r["feats"] for r in tr]))
    F_te = csr_matrix(np.array([r["feats"] for r in te]))
    X_tr = hstack([Xw_tr, Xc_tr, F_tr])
    X_te = hstack([Xw_te, Xc_te, F_te])

    y_tr = np.array([r["label"] for r in tr])
    y_te = np.array([r["label"] for r in te])

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=4.0)
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)
    classes = clf.classes_
    pred = classes[np.argmax(proba, axis=1)]
    conf_max = proba.max(axis=1)

    acc = accuracy_score(y_te, pred)
    rep = classification_report(y_te, pred, output_dict=True, zero_division=0)

    # deployable coverage at precision thresholds
    thr_stats = {}
    for thr in (0.90, 0.95, 0.99):
        mask = conf_max >= thr
        cov = mask.mean()
        prec = (pred[mask] == y_te[mask]).mean() if mask.any() else float("nan")
        thr_stats[f"conf>={thr}"] = {"coverage": round(float(cov), 4),
                                     "precision_on_covered": round(float(prec), 4)}

    out = {
        "train_units": len(tr), "test_units": len(te),
        "test_conversations": len(test_convs),
        "test_label_distribution": {k: int(v) for k, v in zip(*np.unique(y_te, return_counts=True))},
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(rep["macro avg"]["f1-score"]), 4),
        "weighted_f1": round(float(rep["weighted avg"]["f1-score"]), 4),
        "per_label": {k: {"p": round(v["precision"], 3), "r": round(v["recall"], 3),
                          "f1": round(v["f1-score"], 3), "n": int(v["support"])}
                      for k, v in rep.items() if isinstance(v, dict) and "f1-score" in v},
        "deployable_tier1": thr_stats,
    }
    with open(os.path.join(G3, "tier1_eval.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    import joblib
    joblib.dump({"model": clf, "word_vec": word_vec, "char_vec": char_vec, "feats": FEATS},
                os.path.join(G3, "tier1_model.joblib"))
    print(json.dumps({k: out[k] for k in ("train_units", "test_units", "accuracy", "macro_f1", "deployable_tier1")}, indent=2))


if __name__ == "__main__":
    main()
