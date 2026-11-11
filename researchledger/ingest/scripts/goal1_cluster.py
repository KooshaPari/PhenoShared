#!/usr/bin/env python3
"""
GOAL 1c — Local topic clustering. LOCAL ONLY (model runs on-device; only
model WEIGHTS are downloaded from HF — no content leaves the machine).

Reads analysis/goal1/digests.jsonl (already REDACTED), embeds with
all-MiniLM-L6-v2, runs KMeans, writes:
  clusters.json          {cluster_id, member ids, top terms}
  cluster_inputs/cNN.tsv per-cluster redacted digests (for cluster markdown)
  cluster_stats.md       size table
"""
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

G1 = os.path.expanduser("~/Exports/analysis/goal1")
CI = os.path.join(G1, "cluster_inputs")
os.makedirs(CI, exist_ok=True)

K = 30
SEED = 42
MAX_EMB_CHARS = 1200

STOP = set("""a an the and or but if then else for while of in on at to from by with
without is are was were be been being it its this that these those i you he she we they
me my your his her our their am as so not no do does did done have has had will would
can could should may might must about into over under again more most less least what
which who whom when where why how all any both each few own same too very s t just don now
let lets please thanks thank hi hello hey ok okay yes sure good great like need want use
using used one two new also get got make made""".split())

def tok(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower())
            if len(w) > 2 and w not in STOP]

def main():
    rows = []
    with open(os.path.join(G1, "digests.jsonl"), encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))

    # cluster input text = title + digest (redacted already)
    texts = []
    for r in rows:
        t = (r.get("title_r") or "") + "\n" + (r.get("digest_r") or "")
        texts.append(t[:MAX_EMB_CHARS])

    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    import numpy as np

    print("Loading all-MiniLM-L6-v2 (download on first use)...", flush=True)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(texts, batch_size=64, show_progress_bar=True,
                       normalize_embeddings=True)
    print("embedded:", emb.shape, flush=True)

    km = KMeans(n_clusters=K, random_state=SEED, n_init=10, max_iter=300)
    labels = km.fit_predict(emb)

    by_c = defaultdict(list)
    for r, lab in zip(rows, labels):
        by_c[int(lab)].append(r)

    # top terms per cluster (tf over members vs corpus)
    df = Counter()
    for t in texts:
        for w in set(tok(t)):
            df[w] += 1
    N = len(texts)

    clusters = []
    for cid in sorted(by_c, key=lambda c: -len(by_c[c])):
        members = by_c[cid]
        tf = Counter()
        for r in members:
            t = (r.get("title_r") or "") + " " + (r.get("digest_r") or "")
            tf.update(tok(t))
        scored = [(w, cnt * (math.log(N) - math.log(max(df[w], 1)))
                   ) for w, cnt in tf.most_common(400)
                  if df[w] >= 3]
        scored.sort(key=lambda x: -x[1])
        top = [w for w, _ in scored[:12]]
        src = Counter(r.get("source") for r in members)
        rt = Counter(r.get("record_type") for r in members)
        clusters.append({
            "cluster_id": cid, "size": len(members),
            "top_terms": top,
            "sources": dict(src), "record_types": dict(rt),
            "members": [{"conv_id": r["conv_id"], "title_r": r.get("title_r"),
                         "created_at": r.get("created_at"),
                         "source": r.get("source")} for r in members],
        })
        # per-cluster digest file for markdown generation
        with open(os.path.join(CI, f"c{cid:02d}.tsv"), "w", encoding="utf-8") as f:
            for r in members:
                body = ((r.get("title_r") or "") + "\n" +
                        (r.get("digest_r") or "")).replace("\t", " ").replace("\n", " \\n ")
                f.write(f"{r['conv_id']}\t{r.get('created_at')}\t{body[:1400]}\n")

    with open(os.path.join(G1, "clusters.json"), "w", encoding="utf-8") as f:
        json.dump({"k": K, "seed": SEED, "model": "all-MiniLM-L6-v2",
                   "clusters": clusters}, f, indent=2, ensure_ascii=False)

    lines = [f"# Cluster stats (k={K}, all-MiniLM-L6-v2, seed={SEED})", ""]
    for c in clusters:
        lines.append(f"- c{c['cluster_id']:02d}: {c['size']} | "
                     f"{', '.join(c['top_terms'][:8])}")
    with open(os.path.join(G1, "cluster_stats.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"OK: {len(clusters)} clusters -> clusters.json + cluster_inputs/")

if __name__ == "__main__":
    main()
