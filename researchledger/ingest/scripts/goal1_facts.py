#!/usr/bin/env python3
"""
GOAL 1e — facts/preferences CANDIDATE extraction. LOCAL ONLY.
Scans chunks_redacted.jsonl (already redacted) for first-person preference /
standing-fact / convention sentences. Emits candidates only — a hosted model
reviews them afterward; inputs stay redacted.

Output: analysis/goal1/facts_candidates.jsonl
  {chunk_id, conv_id, msg_id, role, created_at, kind, pattern, sentence}
Also facts_candidates_stats.json {kind counts, n_candidates}.
"""
import json
import os
import re
from collections import Counter

G1 = os.path.expanduser("~/Exports/analysis/goal1")

# kind -> (regex, description)
PATTERNS = [
    ("preference", re.compile(
        r"\b(?:i|i'd|i’d) (?:always|never|usually|prefer|tend to|like|dislike|hate|"
        r"want|don't want|do not want|can't stand|can’t stand)\b", re.I)),
    ("instruction", re.compile(
        r"\b(?:please )?(?:always|never|don't|do not|stop|make sure|be sure to|"
        r"remember (?:to|that)|from now on|going forward|keep doing|don’t)\b", re.I)),
    ("convention", re.compile(
        r"\b(?:use|use the|switch to|migrate to|stick with|standardize on|"
        r"i use|we use|we always|our convention|naming convention|prefer to use)\b", re.I)),
    ("fact", re.compile(
        r"\b(?:my name is|i am|i’m|i am a|i’m a|i study|i work|i go to|i live in|"
        r"i'm currently|i am currently|my (?:school|university|major|job|employer)|"
        r"i attend|i'm from|i’m from)\b", re.I)),
    ("tooling", re.compile(
        r"\b(?:i use|using|switch(ed)? to|set up|installed|configured with)\b.{0,60}"
        r"\b(?:vscode|neovim|nvim|vim|emacs|jetbrains|docker|kubernetes|nix|"
        r"homebrew|brew|pnpm|npm|yarn|cargo|uv|zsh|fish|tmux|wezterm|iterable|"
        r"raycast|alfred|obsidian|notion|figma)\b", re.I)),
]

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
MAX_SENT = 400

def main():
    out = open(os.path.join(G1, "facts_candidates.jsonl"), "w", encoding="utf-8")
    stats = Counter()
    n = 0
    seen = set()
    with open(os.path.join(G1, "chunks_redacted.jsonl"), encoding="utf-8") as f:
        for line in f:
            ch = json.loads(line)
            text = ch.get("text_r") or ""
            if not text:
                continue
            for sent in SENT_SPLIT.split(text):
                s = sent.strip()
                if len(s) < 15 or len(s) > MAX_SENT:
                    continue
                for kind, rx in PATTERNS:
                    if rx.search(s):
                        key = (ch["conv_id"], s[:120])
                        if key in seen:
                            continue
                        seen.add(key)
                        out.write(json.dumps({
                            "chunk_id": ch["chunk_id"], "conv_id": ch["conv_id"],
                            "msg_id": ch["msg_id"], "role": ch["role"],
                            "created_at": ch.get("created_at"), "kind": kind,
                            "pattern": rx.pattern[:60], "sentence": s},
                            ensure_ascii=False) + "\n")
                        stats[kind] += 1
                        n += 1
                        break
    out.close()
    with open(os.path.join(G1, "facts_candidates_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"n_candidates": n, "by_kind": dict(stats)}, f, indent=2)
    print(json.dumps({"candidates": n, "by_kind": dict(stats)}, indent=2))

if __name__ == "__main__":
    main()
