#!/usr/bin/env python3
"""Goal 1 (LOCAL): embed redacted chunks with all-MiniLM-L6-v2.

Reads goal1/chunks_redacted.jsonl, encodes text_r locally, saves:
  goal1/embeddings_minilm.npy   (N x 384 float32)
  goal1/embeddings_index.jsonl  (chunk_id, row, source, conv_id, created_at)
Nothing leaves this machine. Needs sentence-transformers in a venv.
"""
import json
import os

import numpy as np
from sentence_transformers import SentenceTransformer

G1 = "/Users/kooshapari/Exports/analysis/goal1"
BATCH = 256


def main():
    ids, meta, texts = [], [], []
    with open(os.path.join(G1, "chunks_redacted.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            t = (r.get("text_r") or "").strip()
            if not t:
                continue
            ids.append(r["chunk_id"])
            meta.append((r.get("source", ""), r.get("conv_id", ""), (r.get("created_at") or "")[:19]))
            texts.append(t[:2000])

    model = SentenceTransformer("all-MiniLM-L6-v2")
    vecs = model.encode(texts, batch_size=BATCH, show_progress_bar=True,
                        convert_to_numpy=True, normalize_embeddings=True)

    np.save(os.path.join(G1, "embeddings_minilm.npy"), vecs.astype(np.float32))
    with open(os.path.join(G1, "embeddings_index.jsonl"), "w", encoding="utf-8") as f:
        for i, cid in enumerate(ids):
            f.write(json.dumps({"chunk_id": cid, "row": i, "source": meta[i][0],
                                "conv_id": meta[i][1], "created_at": meta[i][2]}) + "\n")
    print(json.dumps({"embedded": len(ids), "dim": int(vecs.shape[1])}))


if __name__ == "__main__":
    main()
