#!/usr/bin/env python3
"""Goal 3 step 9 (LOCAL): tier-1 v4 — stronger base encoder + fold ensemble.

- stronger base model: sentence-transformers/all-mpnet-base-v2 (768-d, local)
- engineered training signal: 5-fold conversation-split OUT-OF-FOLD ensemble
  (every unit is evaluated by a model that never saw its conversation), plus a
  final deployment model trained on all data
- features: word 1-2gram tfidf + char 3-5gram tfidf + lexical booleans +
  mpnet(user text) + mpnet(previous assistant text)

Outputs: goal3/tier1v4_oof_eval.json, goal3/tier1_operating_curve_v4.json,
goal3/tier1v4_model.joblib
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
RARE_TO_OTHER = {"REJECT", "PHATIC", "IGNORE", "UNKNOWN", "DEFER", "ESCALATE"}
ENCODER = "sentence-transformers/all-mpnet-base-v2"
N_FOLDS = 5


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
            lab = r["m3"]
            rows.append({
                "conv": r["unit_id"].split(":")[1],
                "text": (u["user_excerpt"] or "").lower(),
                "ctx": (u["assistant_prev_excerpt"] or "").lower(),
                "label": "OTHER" if lab in RARE_TO_OTHER else lab,
                "feats": [1.0 if u["features"].get(k) else 0.0 for k in FEATS]
                         + [min(u["features"].get("wc", 0), 200) / 50.0],
            })

    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(ENCODER)
    emb_txt = st.encode([r["text"] for r in rows], batch_size=128,
                        convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
    emb_ctx = st.encode([r["ctx"] for r in rows], batch_size=128,
                        convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
    F = csr_matrix(np.array([r["feats"] for r in rows]))
    E = csr_matrix(np.hstack([emb_txt, emb_ctx]))
    y = np.array([r["label"] for r in rows])
    texts = [r["text"] for r in rows]

    convs = sorted({r["conv"] for r in rows})
    rng = np.random.RandomState(7)
    rng.shuffle(convs)
    fold_of = {c: i % N_FOLDS for i, c in enumerate(convs)}
    fold_ids = np.array([fold_of[r["conv"]] for r in rows])

    classes = np.unique(y)
    # OOF with explicit class alignment across folds
    oof = np.zeros((len(rows), len(classes)))
    col = {c: i for i, c in enumerate(classes)}
    for fold in range(N_FOLDS):
        tr = fold_ids != fold
        te = ~tr
        wv = TfidfVectorizer(ngram_range=(1, 2), max_features=8000, min_df=2)
        cv = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=8000, min_df=3)
        Xw_tr = wv.fit_transform(np.array(texts)[tr])
        Xc_tr = cv.fit_transform(np.array(texts)[tr])
        clf = LogisticRegression(max_iter=3000, C=8.0)
        clf.fit(hstack([Xw_tr, Xc_tr, F[tr], E[tr]]), y[tr])
        proba = clf.predict_proba(hstack([wv.transform(np.array(texts)[te]),
                                          cv.transform(np.array(texts)[te]),
                                          F[te], E[te]]))
        for j, c in enumerate(clf.classes_):
            oof[te, col[c]] = proba[:, j]
    oof = oof / oof.sum(axis=1, keepdims=True)

    pred = classes[np.argmax(oof, axis=1)]
    conf = oof.max(axis=1)
    acc = accuracy_score(y, pred)
    rep = classification_report(y, pred, output_dict=True, zero_division=0)

    curve = []
    for thr in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99):
        mask = conf >= thr
        curve.append({"threshold": thr,
                      "coverage": round(float(mask.mean()), 4),
                      "precision": round(float((pred[mask] == y[mask]).mean()), 4) if mask.any() else None})

    out = {
        "variant": "v4: mpnet-base encoder + 5-fold conversation OOF ensemble (LR)",
        "encoder": ENCODER,
        "units": len(rows),
        "folds": N_FOLDS,
        "accuracy_oof": round(float(acc), 4),
        "macro_f1_oof": round(float(rep["macro avg"]["f1-score"]), 4),
        "weighted_f1_oof": round(float(rep["weighted avg"]["f1-score"]), 4),
        "per_label": {k: {"p": round(v["precision"], 3), "r": round(v["recall"], 3),
                          "f1": round(v["f1-score"], 3), "n": int(v["support"])}
                      for k, v in rep.items() if isinstance(v, dict) and "f1-score" in v},
        "operating_curve_oof": curve,
        "note": "OOF = every unit predicted by models trained on the other 4 folds; full-population eval",
    }
    with open(os.path.join(G3, "tier1v4_oof_eval.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(os.path.join(G3, "tier1_operating_curve_v4.json"), "w", encoding="utf-8") as f:
        json.dump(curve, f, indent=2)

    # final deployment model on all data
    wv = TfidfVectorizer(ngram_range=(1, 2), max_features=8000, min_df=2)
    cv = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=8000, min_df=3)
    Xw = wv.fit_transform(np.array(texts))
    Xc = cv.fit_transform(np.array(texts))
    clf = LogisticRegression(max_iter=3000, C=8.0)
    clf.fit(hstack([Xw, Xc, F, E]), y)
    joblib.dump({"model": clf, "word_vec": wv, "char_vec": cv, "feats": FEATS,
                 "encoder": ENCODER, "classes": list(classes),
                 "rare_to_other": sorted(RARE_TO_OTHER)},
                os.path.join(G3, "tier1v4_model.joblib"))

    print(json.dumps({"accuracy_oof": out["accuracy_oof"],
                      "macro_f1_oof": out["macro_f1_oof"],
                      "curve": curve}, indent=2))


if __name__ == "__main__":
    main()
