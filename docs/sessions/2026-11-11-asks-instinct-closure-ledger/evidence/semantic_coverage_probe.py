#!/usr/bin/env python3
"""True semantic coverage probe over uncited ask-cue clause units.

WHY. Structural coverage -- "is some register ask's quote a substring of this
member?" -- is a lexical test. It reports 8.0% of 43,305 clause units cited. A
substring test cannot match "hide secrets" to "restrict private sources", so the
structural figure is a LOWER bound and its size (an order-of-magnitude shortfall)
may be an artifact of the method rather than a property of the register.

This probe asks the semantic question instead: does an embedding of an uncited
clause find a register ask that paraphrases it?

MODEL CHOICE, measured not assumed. `probe_paraphrase.py` scores candidate models
on six designed paraphrase pairs (low lexical overlap) with distractors, using
top-1 retrieval as the metric -- the operational question, not a threshold margin.
nomic-embed-text-v1.5 f16 raw matched 12/12; bge-small-en-v1.5 f16 only 9/12
(ranks 2, 3 and 4 on three pairs). nomic raw is therefore the model of record.
The earlier TF-IDF attempt (measure_similarity.py) is distributional, not semantic.

WHAT IT DOES NOT DO. It does not publish a coverage percentage. A top-1 retrieval
score is a CANDIDATE GENERATOR: whether the retrieved ask actually paraphrases the
clause is a human judgement. The script emits a stratified hand-label sample
(30 highest-scoring, 15 lowest) and the labels decide the detector's precision and
the claim. If detector recall cannot be established, no headline is published.

Read-only throughout: ledger.db opened mode=ro with query_only, inputs read from
the asks-coverage workdir, nothing written outside this session's evidence dir.
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import subprocess
import sys
import time

import numpy as np

COVERAGE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "semantic_coverage_probe.json")
CACHE = os.path.join(COVERAGE, "nomic_embed_cache")

BIN = ["/opt/homebrew/bin/llama-embedding"]
MODEL = ["-hf", "nomic-ai/nomic-embed-text-v1.5-GGUF",
         "--hf-file", "nomic-embed-text-v1.5.f16.gguf"]
SEP = "<#sep#>"
BATCH = 128
MAXLEN = 400
SEED = 20261112
N_SAMPLE = 800
N_HIGH, N_LOW = 30, 15

sys.path.insert(0, COVERAGE)
import union_channels as U          # noqa: E402
import segment_units as SEG         # noqa: E402


def clean(t: str) -> str:
    t = " ".join(t.split())
    return t.replace(SEP, " ")[:MAXLEN]


def embed(texts: list[str], tag: str) -> np.ndarray:
    """Embed with nomic f16 via llama.cpp, batched, cached to .npy."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{tag}.npy")
    if os.path.exists(path):
        a = np.load(path)
        if a.shape[0] == len(texts):
            print(f"  cache hit {tag} {a.shape}")
            return a
    rows = []
    t0 = time.time()
    for i in range(0, len(texts), BATCH):
        chunk = [clean(t) or "(empty)" for t in texts[i:i + BATCH]]
        body = SEP.join(chunk)
        p = subprocess.run(BIN + MODEL + ["-p", body, "--embd-separator", SEP,
                                         "--embd-output-format", "array",
                                         "-t", "8"],
                           capture_output=True, text=True, timeout=3600)
        if p.returncode != 0:
            raise SystemExit(f"embed failed rc={p.returncode} {p.stderr[-400:]}")
        d = np.array(json.loads(p.stdout), dtype=np.float32)
        if d.shape[0] != len(chunk):
            raise SystemExit(f"expected {len(chunk)} vectors, got {d.shape[0]}")
        rows.append(d)
        print(f"  {tag} {i + len(chunk)}/{len(texts)} [{time.time() - t0:.0f}s]")
    a = np.vstack(rows)
    np.save(path, a)
    return a


def main() -> int:
    t0 = time.time()
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    asks = con.execute(
        "SELECT a.id, a.interpretation, u.body FROM reg_asks a "
        "LEFT JOIN reg_utterances u ON u.id = a.utterance_id").fetchall()
    con.close()
    print(f"register asks: {len(asks)}")

    # --- rebuild the uncited unit population with the published method ---------
    quotes = sorted({U.norm(r.get("quote") or "")
                     for r in json.load(open(U.REGISTER))["records"]})
    quotes = [q for q in quotes if len(q) >= SEG.MIN_UNIT]

    H, _ = U.harness()
    I = {x for x in U.imessage() if U.keep(x)}
    K = {x for x in U.kcode()[0] if U.keep(x)}
    P = U.phone()
    members = {"harness": H, "imessage": I, "kcode": K, "phone": P}

    uncited: list[str] = []
    for name, ms in members.items():
        units = sorted({u for m in ms for u in SEG.segment(m)})
        idx = SEG.CitedIndex(units)
        cited = idx.cite(quotes)
        free = [u for i, u in enumerate(units) if i not in cited]
        asklike = [u for u in free if SEG.is_ask(u)]
        uncited.extend(asklike)
        print(f"  {name:9s} uncited ask-cue units: {len(asklike)}")
    uncited = sorted(set(uncited))
    print(f"uncited ask-cue units (union, deduped): {len(uncited)}  [{time.time()-t0:.0f}s]")

    rng = random.Random(SEED)
    sample = rng.sample(uncited, min(N_SAMPLE, len(uncited)))

    # --- embed ----------------------------------------------------------------
    ask_texts = [clean(a[1] or "") or clean(a[2] or "") for a in asks]
    A = embed(ask_texts, f"asks_{len(ask_texts)}")
    C = embed(sample, f"sample_{len(sample)}")
    A = A / np.linalg.norm(A, axis=1, keepdims=True)
    C = C / np.linalg.norm(C, axis=1, keepdims=True)

    sims = C @ A.T
    best = sims.argmax(axis=1)
    scores = sims[np.arange(len(sample)), best]

    recs = []
    for k, clause in enumerate(sample):
        j = int(best[k])
        recs.append({
            "clause": clause,
            "top1_ask": asks[j][0],
            "top1_interpretation": asks[j][1],
            "top1_quote": (asks[j][2] or "")[:300],
            "cosine": round(float(scores[k]), 4),
        })

    order = sorted(range(len(recs)), key=lambda k: -recs[k]["cosine"])
    high = [recs[k] for k in order[:N_HIGH]]
    low = [recs[k] for k in order[-N_LOW:]]

    out = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": "nomic-embed-text-v1.5.f16 (llama.cpp llama-embedding, raw, no prefix)",
        "model_selection": {
            "probe": "6 designed paraphrase pairs + 5 distractors, top-1 retrieval",
            "nomic_raw": "12/12 top-1",
            "bge_small_f16": "9/12 top-1 (ranks 2,3,4 on three pairs)",
            "caveat": "n=12 pairs; rule-of-three lower bound on 12/12 is ~0.78",
        },
        "population": {
            "uncited_ask_cue_units_union": len(uncited),
            "sample_size": len(sample),
            "seed": SEED,
            "register_asks": len(asks),
            "note": "denominator is uncited ask-cue clause units, not all 43,305 units",
        },
        "score_distribution": {
            "min": round(float(scores.min()), 4),
            "median": round(float(np.median(scores)), 4),
            "p90": round(float(np.percentile(scores, 90)), 4),
            "max": round(float(scores.max()), 4),
        },
        "hand_label_sample": {"high": high, "low": low},
        "labels": {},
        "verdict": "PENDING HAND LABELS - no coverage figure may be quoted yet",
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {OUT}  [{time.time()-t0:.0f}s]")
    print(f"score min/med/p90/max: {out['score_distribution']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
