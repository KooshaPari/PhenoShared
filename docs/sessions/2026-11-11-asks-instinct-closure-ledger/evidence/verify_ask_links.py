#!/usr/bin/env python3
"""Verify every reg_ask_messages link: does the ask's quote appear in the message
it claims as its origin?

The earlier audit carried "118 suspect ask->message links". That was a count of
something else; this measures the links themselves.

Read-only. Writes ask_link_verification.json.

Two normalisation passes are reported, because the register's `quote` field is
serialised inconsistently:

  strict    : whitespace collapse + lowercase + edge punctuation strip
  fold      : strict, plus literal escape sequences (\\n, \\t, \\\\), curly
              quotes folded, and multi-part quotes split on ' / ' with every
              part required

The gap between the two passes is a measure of quote-serialisation damage, not of
link correctness.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys

LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")
REGISTER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
            "/asks-ledger/register.json")
OUT = ("/Users/kooshapari/CodeProjects/temp/asks-coverage"
       "/ask_link_verification.json")

WS = re.compile(r"\s+")
EDGE = " \t\r\n`*_~#>-–—:;,.!?\"'()[]{}<>|/\\"
MINQ = 8


def fold(s: str) -> str:
    s = (s or "")
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\\n", " "), ("\\t", " "), ("\\\\", "\\"), ("\\", "")):
        s = s.replace(a, b)
    return s


def norm(s: str, folding: bool) -> str:
    t = (fold(s) if folding else (s or "")).strip().lower()
    t = WS.sub(" ", t)
    return t.strip(EDGE)


def main() -> int:
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    cur = con.cursor()

    interp = {a: i for a, i in cur.execute(
        "select id, interpretation from reg_asks")}
    links = {a: m for a, m in cur.execute(
        "select ask_id, message_id from reg_ask_messages")}

    # `reg_ask_messages.message_id` is a MIXED-NAMESPACE column: 2,229 rows hold a
    # `phonemsg-<ULID>` (which joins reg_utterances.message_id) and 23 hold a
    # `UTT-NNNNNN` (which joins reg_utterances.id). Resolving only through
    # message_id reports those 23 as untestable, not as wrong. Resolve both ways.
    by_mid = {m: b for m, b in cur.execute(
        "select message_id, body from reg_utterances")}
    by_id = {u: b for u, b in cur.execute(
        "select id, body from reg_utterances")}
    resolved_by = {}

    def resolve(mid: str) -> tuple[str, str]:
        if mid in by_mid:
            resolved_by["phonemsg"] = resolved_by.get("phonemsg", 0) + 1
            return by_mid[mid], "phonemsg"
        if mid in by_id:
            resolved_by["utt"] = resolved_by.get("utt", 0) + 1
            return by_id[mid], "utt"
        resolved_by["absent"] = resolved_by.get("absent", 0) + 1
        return "", "absent"

    result: dict = {}
    for folding in (False, True):
        label = "fold" if folding else "strict"
        quotes: dict[str, list[str]] = {}
        for r in json.load(open(REGISTER))["records"]:
            quotes.setdefault(norm(r.get("ask") or "", folding),
                              []).append(norm(r.get("quote") or "", folding))
        ok = bad = skip = 0
        bads = []
        for ask, i in interp.items():
            q = next((x for x in quotes.get(norm(i, folding), [])
                      if len(x) >= MINQ), None)
            b = norm(resolve(links.get(ask, ""))[0], folding)
            if q is None or not b:
                skip += 1
                continue
            parts = [p.strip() for p in q.split(" / ") if len(p.strip()) >= MINQ]
            if q in b or (parts and all(p in b for p in parts)):
                ok += 1
            else:
                bad += 1
                bads.append(ask)
        result[label] = {
            "verified": ok, "mismatched": bad, "untestable": skip,
            "fidelity_pct": round(ok / (ok + bad) * 100, 2) if ok + bad else None,
            "mismatched_asks": bads,
        }
        print(f"{label:6s}: verified {ok:4d}  mismatched {bad:3d}  "
              f"untestable {skip:3d}  fidelity "
              f"{result[label]['fidelity_pct']}%")

    # characterise the residual: is it a wrong link, or damaged quoting?
    folding = True
    quotes = {}
    for r in json.load(open(REGISTER))["records"]:
        quotes.setdefault(norm(r.get("ask") or "", folding),
                          []).append(norm(r.get("quote") or "", folding))
    shared: dict[int, int] = {}
    for ask in result["fold"]["mismatched_asks"]:
        q = next((x for x in quotes.get(norm(interp[ask], folding), [])
                  if len(x) >= MINQ), "")
        b = norm(resolve(links.get(ask, ""))[0], folding)
        best = 0
        for L in (60, 40, 25):
            if L > min(len(b), len(q)):
                continue
            if any(q[i:i + L] in b for i in range(0, len(q) - L + 1)):
                best = L
                break
        shared[best] = shared.get(best, 0) + 1
    result["residual_shared_run_chars"] = {str(k): v for k, v in sorted(shared.items())}
    result["link_resolution"] = resolved_by
    print(f"\nlink resolution by namespace: {resolved_by}")
    print(f"\nresidual by longest shared run: {result['residual_shared_run_chars']}")
    print("  (a shared run >= 25 chars means the link points at the right message "
          "and the quote is damaged; 0 means a genuinely different message)")

    json.dump(result, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
