#!/usr/bin/env python3
"""
GOAL 1b — Redaction + per-record digests. LOCAL ONLY.

Reads goal1/messages.jsonl + normalized.jsonl, writes:
  digests.jsonl         {conv_id, source, record_type, created_at, turns,
                         title_r, digest_r}  — REDACTED, safe for M3/topic work
  chunks_redacted.jsonl ~1500-char chunks with {source, conv_id, msg_id,
                         role, created_at, text_r, chunk_idx, chunk_id}
  redaction_stats.json  counts per rule

Rules (privacy split — strip before any hosted model sees text):
  emails, phones, API keys/tokens, IPs, URLs' query strings, street
  addresses, the account's own full_name + email local-parts, Slack/GitHub
  style ids, credit-card-like numbers.
Name handling is heuristic (regex + known account name); documented as
best-effort in redaction_stats.json.
"""
import json
import os
import re
from collections import Counter

G1 = os.path.expanduser("~/Exports/analysis/goal1")
CL = os.path.expanduser("~/Exports/claude-20261010/raw")

# ---- gather account identity locally (never emitted) ----
_identity = {"names": [], "emails": []}
try:
    with open(os.path.join(CL, "light_metadata-000/users.json"), encoding="utf-8") as f:
        for u in json.load(f):
            if u.get("full_name"):
                _identity["names"].append(u["full_name"])
            if u.get("email_address"):
                _identity["emails"].append(u["email_address"])
                local = u["email_address"].split("@")[0]
                if len(local) >= 4:
                    _identity["names"].append(local)
except Exception:
    pass

RULES = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    ("key", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
                       r"|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}"
                       r"|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
                       r"|Bearer\s+[A-Za-z0-9._-]{16,})"), "[KEY]"),
    ("hexkey", re.compile(r"\b(?:[A-Fa-f0-9]{40,64}|[A-Za-z0-9+/]{40,}={0,2})"), "[HEXKEY]"),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[-. (]*)?\d{3}[-. )]*\d{3}[-. ]*\d{4}(?!\d)"), "[PHONE]"),
    ("ip", re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"), "[IP]"),
    ("cc", re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)"), "[CC]"),
    ("address", re.compile(r"\b\d{1,6}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s+"
                           r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Lane|Ln|Dr|Drive|Way|Ct|Court)\.?\b"),
     "[ADDRESS]"),
    ("url_query", re.compile(r"(https?://[^\s\"'<>\]]+)\?([^\s\"'<>\]]+)"), r"\1?[QUERY]"),
    # Brand term. Round-16 add: case-insensitive substring match on the
    # company name 'phenotype'. Verified across all 484 + 66 occurrences in
    # chunks_redacted.jsonl / digests.jsonl: 100% are company references
    # (resume bullets, JIRA org, bundle IDs com.phenotype.healthsync, repo
    # names like phenotype-hub, URLs https://phenotype.us, wandb project
    # "[NAME]-phenotype"). Zero derivatives (phenotypic/phenotypes) exist
    # in the corpus, and biology prose uses 'phenotypic' not bare
    # 'phenotype' — so a bare substring match would not destroy legitimate
    # biology text in this dataset.
    ("brand", re.compile(r"phenotype", re.I), "[BRAND]"),
]

# name patterns: known identity names (longest first) + "my name is X"
# Round-16 fix: added bare first name + bare surname + possessive + terminal-username suffix
# so the partial-redaction artifact '[NAME]@Kooshas-Laptop' no longer leaks the first name.
# Sort-by-length-descending is already in place (line below) so the longest match wins
# and 'Koosha Paridehpour' still matches before 'Koosha' / 'Paridehpour' do.
_name_res = []
for n in sorted(set(_identity["names"] + [
    "Paridehpour",  # bare surname (academic/medical context)
    "Koosha's",     # possessive (e.g. "Koosha's Apple")
    "Kooshas-",     # terminal username compound (e.g. "Kooshas-Laptop")
    "Koosha",       # bare first name (e.g. "Project Koosha")
]), key=len, reverse=True):
    if len(n) >= 4:
        _name_res.append((re.compile(re.escape(n), re.I), "[NAME]"))
_name_res.append((re.compile(r"\b(?:my name is|i am|i'm|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"),
                  lambda m: "[NAME] " + ""))  # replaced below

def redact(text, stats):
    if not text:
        return ""
    out = text
    # known names first (longest first)
    for rx, repl in _name_res[:-1]:
        out, c = rx.subn(repl, out)
        if c:
            stats["name_identity"] += c
    # "my name is X" — drop the name only
    def _nm(m):
        stats["name_pattern"] += 1
        return m.group(0).replace(m.group(1), "[NAME]")
    out = _name_res[-1][0].sub(_nm, out)
    for name, rx, repl in RULES:
        if name == "url_query":
            out, c = rx.subn(repl, out)
        else:
            out, c = rx.subn(repl, out)
        if c:
            stats[name] += c
    return out

def digest_for(conv_id, rows, title, limit=1400):
    humans = [r for r in rows if r["role"] in ("human", "user")]
    assists = [r for r in rows if r["role"] in ("assistant", "model")]
    picks = []
    picks += humans[:2]
    picks += assists[:1]
    picks += humans[-1:]
    if not any((r.get("text") or "").strip() for r in picks):
        # non-chat roles (project_doc / memory_file / activity) or chatless rows
        picks = [r for r in rows if (r.get("text") or "").strip()][:3] or picks
    seen = set()
    parts = []
    if title:
        parts.append("TITLE: " + title)
    for r in picks:
        k = id(r)
        if k in seen:
            continue
        seen.add(k)
        t = (r["text"] or "").strip()
        if t:
            parts.append(f"[{r['role']}] " + t[:600])
    d = "\n".join(parts)
    return d[:limit]

CHUNK = 1500
CHUNK_OVERLAP = 200

def main():
    stats = Counter()
    norm = {}
    with open(os.path.join(G1, "normalized.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            norm.setdefault(r["id"], r)

    by_conv = {}
    with open(os.path.join(G1, "messages.jsonl"), encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            by_conv.setdefault(m["conv_id"], []).append(m)

    n_dig = 0
    with open(os.path.join(G1, "digests.jsonl"), "w", encoding="utf-8") as fout:
        for rid, r in norm.items():
            rows = by_conv.get(rid, [])
            if not rows and r.get("record_type") not in (
                    "conversation", "design_chat", "activity"):
                continue  # projects/memories w/o messages skipped from clustering
            title = r.get("title")
            d = digest_for(rid, rows, title)
            if not d.strip():
                # structural fallback for content-stripped records
                r2 = r or {}
                d = (f"[NO CONTENT AVAILABLE: source={r2.get('source')} "
                     f"record_type={r2.get('record_type')} turns={r2.get('turns')} "
                     f"created={r2.get('created_at')} updated={r2.get('updated_at')}]")
            dr = redact(d, stats)
            fout.write(json.dumps({
                "conv_id": rid, "source": r.get("source") or (rows[0]["source"] if rows else None),
                "record_type": r.get("record_type"), "created_at": r.get("created_at"),
                "turns": r.get("turns"), "title_r": redact(title or "", stats),
                "digest_r": dr}, ensure_ascii=False) + "\n")
            n_dig += 1

    n_chunks = 0
    with open(os.path.join(G1, "chunks_redacted.jsonl"), "w", encoding="utf-8") as fout:
        with open(os.path.join(G1, "messages.jsonl"), encoding="utf-8") as f:
            for line in f:
                m = json.loads(line)
                t = m.get("text") or ""
                if not t.strip():
                    continue
                # chunk with overlap on word boundaries
                start = 0
                idx = 0
                while start < len(t):
                    end = min(len(t), start + CHUNK)
                    piece = t[start:end]
                    pr = redact(piece, stats)
                    fout.write(json.dumps({
                        "chunk_id": f"{m['conv_id']}:{m['msg_id']}:{idx}",
                        "source": m["source"], "conv_id": m["conv_id"],
                        "msg_id": m["msg_id"], "role": m["role"],
                        "created_at": m.get("created_at"), "chunk_idx": idx,
                        "text_r": pr}, ensure_ascii=False) + "\n")
                    n_chunks += 1
                    idx += 1
                    if end >= len(t):
                        break
                    start = end - CHUNK_OVERLAP

    with open(os.path.join(G1, "redaction_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"rules": dict(stats),
                   "identity_names_loaded": len(_identity["names"]),
                   "identity_names_hardcoded": ["Paridehpour", "Koosha's", "Kooshas-", "Koosha"],
                   "identity_names_total": len(_identity["names"]) + 4,
                   "digests": n_dig, "chunks": n_chunks,
                   "note": "name redaction is heuristic (known account name + "
                           "first-person patterns + hardcoded bare-name/surname); not a guarantee"},
                  f, indent=2)
    print(json.dumps({"digests": n_dig, "chunks": n_chunks, "stats": dict(stats)}, indent=2))

if __name__ == "__main__":
    main()
