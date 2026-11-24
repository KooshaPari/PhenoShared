#!/usr/bin/env python3
"""Goal 1h (LOCAL): assemble deliverable markdown from candidate files.

Reads (already-redacted) goal1 candidates and emits:
  goal1/facts_preferences.md  — curated facts/preferences/conventions with provenance
  goal1/resumable.md         — resumable-value vs ephemeral review lists
No LLM involved; deterministic filtering and ranking only.
"""
import json
import os
import re
from collections import Counter, defaultdict

G1 = "/Users/kooshapari/Exports/analysis/goal1"

JUNK_PREFIX = re.compile(
    r"^(to use|note:|usage:|here(?:'s| is)|let me|i will|i'll|the (code|script|file|command|output|error)|this (is|means|will)|in (summary|conclusion)|as (an|a) (ai|assistant)|certainly|sure[,!]|great question|thanks for)\b",
    re.I)


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def main():
    # ---------- facts_preferences.md ----------
    by_kind = defaultdict(list)
    seen = defaultdict(set)
    counts = Counter()
    with open(os.path.join(G1, "facts_candidates.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            k = r["kind"]
            counts[k] += 1
            s = r["sentence"].strip()
            if len(s) < 25 or len(s) > 400 or JUNK_PREFIX.match(s):
                continue
            n = norm(s)
            if n in seen[k]:
                continue
            seen[k].add(n)
            by_kind[k].append(r)

    KIND_ORDER = ["preference", "fact", "convention", "instruction", "tooling"]
    CAPS = {"preference": 150, "fact": 100, "convention": 150, "instruction": 120, "tooling": 50}
    lines = [
        "# Goal 1 — Facts, preferences, conventions (with provenance)",
        "",
        "Source: `facts_candidates.jsonl` (extracted locally from REDACTED chunks; regex-candidate sentences, curated by deterministic filters).",
        f"Raw candidates: {sum(counts.values())} — " + ", ".join(f"{k}={counts[k]}" for k in KIND_ORDER),
        "Provenance format: `[conv_id prefix · date · sender]`. These are candidates for a PhenoRegistry-style facts store; **human review required before treating any line as ground truth** — regex extraction favors recall over precision.",
        "",
    ]
    for k in KIND_ORDER:
        rows = by_kind.get(k, [])
        lines.append(f"## {k.capitalize()}s — {len(rows)} curated of {counts[k]} candidates")
        lines.append("")
        for r in rows[: CAPS[k]]:
            d = (r["created_at"] or "")[:10]
            lines.append(f"- {r['sentence']} `[{r['conv_id'][:8]} · {d} · {r['role']}]`")
        if len(rows) > CAPS[k]:
            lines.append(f"- … {len(rows) - CAPS[k]} more in `facts_candidates.jsonl` filtered by kind={k}")
        lines.append("")
    with open(os.path.join(G1, "facts_preferences.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---------- resumable.md ----------
    d = json.load(open(os.path.join(G1, "resumable_vs_ephemeral.json"), encoding="utf-8"))
    res = d["resumable"]
    res.sort(key=lambda r: -r["score"])
    rl = [
        "# Goal 1 — Resumable value vs ephemeral (DELETION-CANDIDATE REVIEW ONLY — nothing deleted)",
        "",
        f"Counts: {json.dumps(d.get('counts', {}))}",
        f"Note: {d.get('note', '')}",
        "",
        f"## Resumable conversations ({len(res)}) — ranked by score",
        "",
        "| score | title (redacted) | created | reasons | id |",
        "|---|---|---|---|---|",
    ]
    for r in res:
        rl.append(f"| {r['score']} | {r.get('title_r', '')[:80]} | {(r.get('created') or '')[:10]} | {'; '.join(r.get('reasons', []))} | `{r['id'][:8]}` |")

    for sect, key in [("Ephemeral candidates", "ephemeral_candidates"),
                      ("Needs manual review", "review_needed"),
                      ("Content-stripped shells", "content_stripped_review")]:
        items = d.get(key, [])
        rl += ["", f"## {sect} ({len(items)})", ""]
        for r in items[:200]:
            rl.append(f"- [{r.get('score', 0)}] {r.get('title_r', '')[:80]} · {(r.get('created') or '')[:10]} · {'; '.join(r.get('reasons', []))} · `{r['id'][:8]}`")
        if len(items) > 200:
            rl.append(f"- … {len(items) - 200} more in `resumable_vs_ephemeral.json`")
    with open(os.path.join(G1, "resumable.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(rl))

    print(json.dumps({
        "facts_preferences_kinds": {k: len(by_kind.get(k, [])) for k in KIND_ORDER},
        "resumable_rows": len(res),
        "ephemeral": len(d.get("ephemeral_candidates", [])),
        "review": len(d.get("review_needed", [])),
        "stripped": len(d.get("content_stripped_review", [])),
    }, indent=2))


if __name__ == "__main__":
    main()
