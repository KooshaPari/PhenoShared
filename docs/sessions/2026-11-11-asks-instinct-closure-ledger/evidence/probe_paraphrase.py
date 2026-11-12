#!/usr/bin/env python3
"""Which local embedding model can actually match a paraphrase? Measured, not assumed.

WHY. `semantic_coverage_probe.py` needs an embedding model, and the obvious choices
are not interchangeable. Every similarity figure in this ledger has been challenged
once already, and each retraction came from asserting a confident number from an
unchecked tool. So the model is selected by a test with a known answer rather than
by reputation, and the test is committed alongside the choice.

THE TEST. Twelve sentences forming six paraphrase pairs. Each pair is written to
share meaning while deliberately avoiding shared wording -- "never publish a number
without a checked-in artifact" / "no figure may go out unless a committed script
backs it" -- because lexical overlap would let a bag-of-words method pass. Five
distractors (cats, linker disk, rust parser, weather, lunch) are mixed in.

THE METRIC IS TOP-1 RETRIEVAL, not a threshold margin. A margin over the whole
matrix can be broken by two sentences that are legitimately related without being a
paraphrase, which makes min-max margin the wrong instrument. The operational
question downstream is "does the correct ask rank first for this clause?", so that
is what is scored. Chance top-1 over 17 candidates is 1/17 = 5.9%.

CAVEAT RECORDED, NOT HIDDEN. Twelve pairs is a small probe. Applying the rule of
three, 12/12 corresponds to a 95% lower bound near 0.78, so this establishes gross
separation and cannot certify accuracy to the last percent. The real calibration is
the hand-labelled sample in semantic_coverage_probe.py.

Candidates are run through llama.cpp's llama-embedding, which is present on this
host with models pulled on demand; no Python ML stack is installed and none is
needed. Both candidates are f16, so quantisation noise is not a confound.
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np

BIN = "/opt/homebrew/bin/llama-embedding"
SEP = "<#sep#>"

CANDIDATES = [
    ("nomic-embed-text-v1.5 f16 raw", "nomic-ai/nomic-embed-text-v1.5-GGUF",
     "nomic-embed-text-v1.5.f16.gguf", ""),
    ("nomic-embed-text-v1.5 f16 clustering:", "nomic-ai/nomic-embed-text-v1.5-GGUF",
     "nomic-embed-text-v1.5.f16.gguf", "clustering: "),
    ("bge-small-en-v1.5 f16 raw", "CompendiumLabs/bge-small-en-v1.5-gguf",
     "bge-small-en-v1.5-f16.gguf", ""),
]

SENTENCES = [
    "never publish a number without a checked-in artifact",
    "no figure may go out unless a committed script backs it",
    "keep the migration switched off until the data exists",
    "the import must not proceed before the evidence is in place",
    "run the database in read-only mode",
    "the database connection must not permit writes",
    "the repo is public so no host addresses in commits",
    "do not put internal hostnames in a publicly visible repository",
    "if the detector recall is below ninety percent withhold the headline",
    "a coverage figure should not be reported when the method misses more than one in ten",
    "delete branches that nobody is working on",
    "push the abandoned branch work and remove it from disk",
    "cats are mammals",
    "the linker ran out of disk space",
    "rewrite the parser in rust this weekend",
    "it rained all afternoon",
    "I ate a sandwich for lunch",
]
PAIRS = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9), (10, 11)]


def embed(repo: str, fname: str, prefix: str) -> np.ndarray:
    body = SEP.join(prefix + s for s in SENTENCES)
    p = subprocess.run(
        [BIN, "-hf", repo, "--hf-file", fname, "-p", body,
         "--embd-separator", SEP, "--embd-output-format", "array", "-t", "8"],
        capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        raise SystemExit(f"{repo} failed: {p.stderr[-300:]}")
    d = np.array(json.loads(p.stdout), dtype=np.float64)
    if d.shape[0] != len(SENTENCES):
        raise SystemExit(f"{repo}: {d.shape[0]} vectors for {len(SENTENCES)} sentences")
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def score(M: np.ndarray) -> dict:
    S = M @ M.T
    np.fill_diagonal(S, -9.0)
    ranks, margin_pairs = [], []
    for i, j in PAIRS:
        for a, b in ((i, j), (j, i)):
            order = np.argsort(-S[a])
            ranks.append(int(np.where(order == b)[0][0]) + 1)
    intra = [S[i, j] for i, j in PAIRS]
    cross = [S[i, j] for i in range(12) for j in range(12)
             if i < j and (i, j) not in PAIRS]
    return {
        "top1_hits": sum(1 for r in ranks if r == 1),
        "of": len(ranks),
        "ranks": ranks,
        "intra_min": round(min(intra), 4),
        "cross_max": round(max(cross), 4),
        "minmax_margin": round(min(intra) - max(cross), 4),
    }


def main() -> int:
    print(f"{len(SENTENCES)} sentences, {len(PAIRS)} paraphrase pairs, "
          f"chance top-1 = {1/(len(SENTENCES)-1)*100:.1f}%\n")
    out = {"sentences": SENTENCES, "pairs": PAIRS, "candidates": {}}
    for name, repo, fname, prefix in CANDIDATES:
        M = embed(repo, fname, prefix)
        s = score(M)
        out["candidates"][name] = s
        print(f"{name}\n  top1 {s['top1_hits']}/{s['of']}  ranks {s['ranks']}")
        print(f"  intra_min {s['intra_min']:+.3f}  cross_max {s['cross_max']:+.3f}  "
              f"margin {s['minmax_margin']:+.3f}")
    best = max(out["candidates"], key=lambda k: out["candidates"][k]["top1_hits"])
    out["selected"] = best
    out["why"] = ("highest top-1 retrieval; min-max margin is reported but is not the "
                  "selection criterion because legitimately-related non-paraphrases "
                  "inflate cross_max")
    print(f"\nselected: {best}")
    with open(sys.argv[1] if len(sys.argv) > 1 else "probe_paraphrase.json", "w") as fh:
        json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
