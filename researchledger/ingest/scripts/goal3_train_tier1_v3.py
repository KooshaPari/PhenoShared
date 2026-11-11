#!/usr/bin/env python3
"""Goal 3 step 8 (LOCAL): tier-1 v3 — context features + OTHER merge + calibration.

Changes vs v2:
  1. adds a MiniLM embedding of the PREVIOUS assistant message (conversation context)
  2. merges rare classes (REJECT/PHATIC/IGNORE/UNKNOWN) into OTHER
  3. 3-way conversation split (train / calibration / eval); Platt calibration
Evaluates on the same held-out test conversations; emits tier-1 v3 eval +
operating curve + tier-load simulation.
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
                "true_label": lab,
                "feats": [1.0 if u["features"].get(k) else 0.0 for k in FEATS]
                         + [min(u["features"].get("wc", 0), 200) / 50.0],
            })

    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer("all-MiniLM-L6-v2")
    emb_txt = st.encode([r["text"] for r in rows], batch_size=256, convert_to_numpy=True, normalize_embeddings=True)
    emb_ctx = st.encode([r["ctx"] for r in rows], batch_size=256, convert_to_numpy=True, normalize_embeddings=True)

    convs = sorted({r["conv"] for r in rows})
    rng = np.random.RandomState(7)
    rng.shuffle(convs)
    n = len(convs)
    cal_convs = set(convs[: n // 5])
    eval_convs = set(convs[n // 5: 2 * n // 5])
    train_idx = [i for i, r in enumerate(rows) if r["conv"] not in cal_convs | eval_convs]
    cal_idx = [i for i, r in enumerate(rows) if r["conv"] in cal_convs]
    eval_idx = [i for i, r in enumerate(rows) if r["conv"] in eval_convs]

    word_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=8000, min_df=2)
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=8000, min_df=3)
    word_vec.fit([rows[i]["text"] for i in train_idx])
    char_vec.fit([rows[i]["text"] for i in train_idx])

    def feats(idxs):
        Xw = word_vec.transform([rows[i]["text"] for i in idxs])
        Xc = char_vec.transform([rows[i]["text"] for i in idxs])
        F = csr_matrix(np.array([rows[i]["feats"] for i in idxs]))
        E = csr_matrix(np.hstack([emb_txt[idxs], emb_ctx[idxs]]))
        return hstack([Xw, Xc, F, E])

    X_tr, X_cal, X_ev = feats(train_idx), feats(cal_idx), feats(eval_idx)
    y_tr = np.array([rows[i]["label"] for i in train_idx])
    y_cal = np.array([rows[i]["label"] for i in cal_idx])
    y_ev = np.array([rows[i]["label"] for i in eval_idx])

    base = LogisticRegression(max_iter=3000, C=8.0)
    base.fit(X_tr, y_tr)

    # temperature scaling on the calibration conversations (version-proof, no sklearn calibrator API)
    def nll(T, proba, y, classes):
        p = np.clip(proba ** (1.0 / T), 1e-12, 1.0)
        p = p / p.sum(axis=1, keepdims=True)
        idx = {c: i for i, c in enumerate(classes)}
        return -np.log(p[np.arange(len(y)), [idx[v] for v in y]]).mean()

    proba_cal = base.predict_proba(X_cal)
    temperatures = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
    T = min(temperatures, key=lambda t: nll(t, proba_cal, y_cal, base.classes_))

    proba = base.predict_proba(X_ev) ** (1.0 / T)
    proba = proba / proba.sum(axis=1, keepdims=True)
    classes = base.classes_
    pred = classes[np.argmax(proba, axis=1)]
    conf = proba.max(axis=1)

    acc = accuracy_score(y_ev, pred)
    rep = classification_report(y_ev, pred, output_dict=True, zero_division=0)

    curve = []
    for thr in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99):
        mask = conf >= thr
        curve.append({
            "threshold": thr,
            "coverage": round(float(mask.mean()), 4),
            "precision": round(float((pred[mask] == y_ev[mask]).mean()), 4) if mask.any() else None,
        })

    out = {
        "variant": "v3: +assistant-context embedding, OTHER-merge, Platt-calibrated LR",
        "train/cal/eval units": [len(train_idx), len(cal_idx), len(eval_idx)],
        "label_space": list(classes),
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(rep["macro avg"]["f1-score"]), 4),
        "weighted_f1": round(float(rep["weighted avg"]["f1-score"]), 4),
        "per_label": {k: {"p": round(v["precision"], 3), "r": round(v["recall"], 3),
                          "f1": round(v["f1-score"], 3), "n": int(v["support"])}
                      for k, v in rep.items() if isinstance(v, dict) and "f1-score" in v},
        "operating_curve": curve,
        "temperature": T,
        "note": "eval set = 20% of conversations, never seen in train or calibration",
    }
    with open(os.path.join(G3, "tier1v3_eval.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(os.path.join(G3, "tier1_operating_curve_v3.json"), "w", encoding="utf-8") as f:
        json.dump(curve, f, indent=2)
    joblib.dump({"model": base, "temperature": T, "word_vec": word_vec, "char_vec": char_vec,
                 "feats": FEATS, "rare_to_other": sorted(RARE_TO_OTHER)},
                os.path.join(G3, "tier1v3_model.joblib"))

    print(json.dumps({"accuracy": out["accuracy"], "macro_f1": out["macro_f1"],
                      "operating_curve": curve}, indent=2))


if __name__ == "__main__":
    main()
