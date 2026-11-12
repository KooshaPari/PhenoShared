#!/usr/bin/env python3
"""Distributional similarity between register entries and corpus intents.

No exact/substring matching: this scores token-level TF-IDF cosine, so a
paraphrase that reuses the register's vocabulary can still score. It is still a
LEXICAL method (it cannot match "hide secrets" to "restrict private sources"),
and is labelled distributional-lexical, not semantic.

Corpus filters are identical to collapse_intents.py so the counts are
comparable to the earlier collapse.

Outputs similarity_results.json plus printable adjudication samples.
"""
from __future__ import annotations

import json
import math
import random
import re
import sys
from collections import defaultdict

BASE = "/Users/kooshapari/CodeProjects/temp/asks-coverage"
FILES = [
    ("jcode", f"{BASE}/jcode-occurrences.jsonl"),
    ("codex", f"{BASE}/codex_user_turns_v2.jsonl"),
]
REGISTER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
            "/asks-ledger/register.json")

WS = re.compile(r"\s+")
FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$")
EDGE_PUNCT = " \t\r\n`*_~#>-–—:;,.!?\"'()[]{}<>|/\\"
TOKEN = re.compile(r"[a-z0-9][a-z0-9'_.+/-]*")

STOP = frozenset("""a an the and or but if then than that this these those i me my we our you your it its
is are was were be been being do does did doing have has had having will would should could can may might
must shall of in on at to for from by with as into about over after before under above between out up down
not no so just now very also more most some any all each every other such only own same too s t don t
please let lets go going get got make made want need like use used using one two three way thing things
ok okay yes yeah sure hi hello thanks thank hey there here what which who whom when where why how
""".split())


def normalize(text: str) -> str:
    t = text.strip()
    t = FENCE.sub("", t)
    t = t.lower()
    t = WS.sub(" ", t)
    return t.strip(EDGE_PUNCT)


def content_tokens(norm: str) -> list[str]:
    return [t for t in TOKEN.findall(norm) if len(t) > 1 and t not in STOP]


def load_corpus() -> dict[str, str]:
    """Identical filters to collapse_intents.py. Returns norm -> raw sample."""
    distinct: dict[str, str] = {}
    for label, path in FILES:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("is_injected") is True:
                    continue
                if "is_human" in rec and rec.get("is_human") is not True:
                    continue
                text = rec.get("text") or ""
                chars = rec.get("chars")
                if chars is None:
                    chars = len(text)
                norm = normalize(text)
                if chars < 12 or len(norm) < 12:
                    continue
                if norm not in distinct:
                    distinct[norm] = text.strip().replace("\n", " ")[:200]
    return distinct


def build_index(docs: list[str]):
    """Return (idf, postings, doc_norm, doc_tokens)."""
    n = len(docs)
    tokenized = [content_tokens(d) for d in docs]
    df: dict[str, int] = defaultdict(int)
    for toks in tokenized:
        for t in set(toks):
            df[t] += 1
    idf = {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}

    postings: dict[str, list[tuple[int, float]]] = defaultdict(list)
    doc_norm = [0.0] * n
    for i, toks in enumerate(tokenized):
        if not toks:
            continue
        tf: dict[str, int] = defaultdict(int)
        for t in toks:
            tf[t] += 1
        sq = 0.0
        for t, c in tf.items():
            w = (1.0 + math.log(c)) * idf.get(t, 0.0)
            postings[t].append((i, w))
            sq += w * w
        doc_norm[i] = math.sqrt(sq) or 1.0
    return idf, postings, doc_norm, tokenized


def best_match(query: str, idf, postings, doc_norm):
    toks = content_tokens(query)
    if not toks:
        return 0.0, -1
    tf: dict[str, int] = defaultdict(int)
    for t in toks:
        tf[t] += 1
    qw: dict[str, float] = {}
    sq = 0.0
    for t, c in tf.items():
        if t not in idf:
            continue
        w = (1.0 + math.log(c)) * idf[t]
        qw[t] = w
        sq += w * w
    if not qw:
        return 0.0, -1
    qn = math.sqrt(sq) or 1.0

    acc: dict[int, float] = defaultdict(float)
    for t, w in qw.items():
        for i, dw in postings[t]:
            acc[i] += w * dw
    if not acc:
        return 0.0, -1
    best_i, best_s = -1, 0.0
    for i, dot in acc.items():
        s = dot / (qn * doc_norm[i])
        if s > best_s:
            best_i, best_s = i, s
    return best_s, best_i


def main() -> int:
    corpus = load_corpus()
    docs = sorted(corpus)
    print(f"corpus distinct intents: {len(docs)}", file=sys.stderr)
    idf, postings, doc_norm, doc_tokens = build_index(docs)
    uniq_tokens = {t for toks in doc_tokens for t in toks}
    print(f"vocabulary: {len(uniq_tokens)}", file=sys.stderr)

    reg = json.load(open(REGISTER))["records"]
    seen: set[str] = set()
    items = []
    for r in reg:
        a = normalize(r.get("ask") or "")
        q = normalize(r.get("quote") or "")
        key = a or q
        if not key or key in seen:
            continue
        seen.add(key)
        items.append((r.get("asked_at", ""), a, q))
    print(f"register distinct entries: {len(items)}", file=sys.stderr)

    results = []
    for i, (asked_at, ask, quote) in enumerate(items):
        s_ask, i_ask = best_match(ask, idf, postings, doc_norm) if ask else (0.0, -1)
        s_q, i_q = best_match(quote, idf, postings, doc_norm) if quote else (0.0, -1)
        s = max(s_ask, s_q)
        j = i_ask if s_ask >= s_q else i_q
        results.append({
            "asked_at": asked_at,
            "ask": ask[:200],
            "quote": quote[:200],
            "score_ask": round(s_ask, 4),
            "score_quote": round(s_q, 4),
            "score": round(s, 4),
            "corpus_match": docs[j][:240] if j >= 0 else "",
        })
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{len(items)}", file=sys.stderr)

    scores = sorted(r["score"] for r in results)
    hist = {}
    for lo in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        hist[f">={lo:.1f}"] = sum(1 for s in scores if s >= lo)

    n = len(results)
    summary = {
        "method": "token-level TF-IDF cosine, best match over distinct corpus intents",
        "labelled_as": "distributional-lexical, NOT semantic",
        "corpus_distinct_intents": len(docs),
        "register_distinct_entries": n,
        "score_histogram": hist,
        "score_median": scores[n // 2] if n else 0,
        "score_p90": scores[int(n * 0.9)] if n else 0,
        "score_max": scores[-1] if n else 0,
    }
    print(json.dumps(summary, indent=2))

    # Adjudication samples: deterministic random, high band vs low band.
    rng = random.Random(20261112)
    high = [r for r in results if r["score"] >= 0.40]
    mid = [r for r in results if 0.25 <= r["score"] < 0.40]
    low = [r for r in results if r["score"] < 0.25]

    def sample(label, pool, k=12):
        print(f"\n{'='*70}\n{label} (pool={len(pool)})\n{'='*70}")
        for r in rng.sample(pool, min(k, len(pool))):
            print(f"\nscore={r['score']}")
            print(f"  REGISTER ask : {r['ask'][:170]}")
            print(f"  REGISTER quot: {r['quote'][:170]}")
            print(f"  CORPUS match : {r['corpus_match'][:170]}")

    sample("HIGH BAND >=0.40", high)
    sample("MID BAND 0.25-0.40", mid)
    sample("LOW BAND <0.25", low)

    out = f"{BASE}/similarity_results.json"
    with open(out, "w") as fh:
        json.dump({"summary": summary, "results": results}, fh)
    print(f"\nwrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
