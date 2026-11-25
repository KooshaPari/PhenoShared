#!/usr/bin/env python3
"""Goal 3 step 7 (LOCAL): tier-1 v2 — add local MiniLM embedding features.

Embeds each core unit's redacted user excerpt with all-MiniLM-L6-v2 (local),
then retrains logistic regression on [word tfidf | char tfidf | lexical feats |
embedding]. Also emits a coverage/precision operating curve for tier routing.
Outputs: goal3/tier1v2_eval.json, goal3/tier1_operating_curve.json,
goal3/tier1v2_model.joblib.
"""
import json
import os

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

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
                "feats": [1.0 if u["features"].get(k) else 0.0 for k in FEATS]
                         + [min(u["features"].get("wc", 0), 200) / 50.0],
            })

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode([r["text"] for r in rows], batch_size=256,
                       convert_to_numpy=True, normalize_embeddings=True)

    convs = sorted({r["conv"] for r in rows})
    rng = np.random.RandomState(7)
    rng.shuffle(convs)
    test_convs = set(convs[: max(1, int(len(convs) * 0.2))])
    tr_idx = [i for i, r in enumerate(rows) if r["conv"] not in test_convs]
    te_idx = [i for i, r in enumerate(rows) if r["conv"] in test_convs]
    tr = [rows[i] for i in tr_idx]
    te = [rows[i] for i in te_idx]

    word_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=8000, min_df=2)
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=8000, min_df=3)
    Xw_tr = word_vec.fit_transform([r["text"] for r in tr])
    Xc_tr = char_vec.fit_transform([r["text"] for r in tr])
    Xw_te = word_vec.transform([r["text"] for r in te])
    Xc_te = char_vec.transform([r["text"] for r in te])

    F_tr = csr_matrix(np.array([r["feats"] for r in tr]))
    F_te = csr_matrix(np.array([r["feats"] for r in te]))
    E_tr = csr_matrix(emb[tr_idx])
    E_te = csr_matrix(emb[te_idx])

    X_tr = hstack([Xw_tr, Xc_tr, F_tr, E_tr])
    X_te = hstack([Xw_te, Xc_te, F_te, E_te])
    y_tr = np.array([r["label"] for r in tr])
    y_te = np.array([r["label"] for r in te])

    natural = os.environ.get("T1_NATURAL") == "1"
    suffix = "_natural" if natural else ""
    clf = LogisticRegression(max_iter=3000, class_weight=None if natural else "balanced", C=8.0)
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)
    classes = clf.classes_
    pred = classes[np.argmax(proba, axis=1)]
    conf = proba.max(axis=1)

    acc = accuracy_score(y_te, pred)
    rep = classification_report(y_te, pred, output_dict=True, zero_division=0)

    curve = []
    for thr in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99):
        mask = conf >= thr
        cov = float(mask.mean())
        prec = float((pred[mask] == y_te[mask]).mean()) if mask.any() else float("nan")
        curve.append({"threshold": thr, "coverage": round(cov, 4),
                      "precision": round(prec, 4)})

    out = {
        "variant": "word+char+lexical+minilm-embedding LR" + (" (natural priors)" if natural else " (balanced)"),
        "train_units": len(tr), "test_units": len(te),
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(rep["macro avg"]["f1-score"]), 4),
        "weighted_f1": round(float(rep["weighted avg"]["f1-score"]), 4),
        "per_label": {k: {"p": round(v["precision"], 3), "r": round(v["recall"], 3),
                          "f1": round(v["f1-score"], 3), "n": int(v["support"])}
                      for k, v in rep.items() if isinstance(v, dict) and "f1-score" in v},
        "operating_curve": curve,
    }
    with open(os.path.join(G3, f"tier1v2{suffix}_eval.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(os.path.join(G3, f"tier1_operating_curve{suffix}.json"), "w", encoding="utf-8") as f:
        json.dump(curve, f, indent=2)
    joblib.dump({"model": clf, "word_vec": word_vec, "char_vec": char_vec, "feats": FEATS},
                os.path.join(G3, f"tier1v2{suffix}_model.joblib"))
    print(json.dumps({"accuracy": out["accuracy"], "macro_f1": out["macro_f1"],
                      "operating_curve": curve}, indent=2))


if __name__ == "__main__":
    main()
