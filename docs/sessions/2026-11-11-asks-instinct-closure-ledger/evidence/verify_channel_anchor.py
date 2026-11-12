#!/usr/bin/env python3
"""Prove or disprove register anchoring, from the register's OWN provenance.

Reads ledger.db read-only. Answers three questions with counts, no percentages
unless a denominator is printed beside them:

  1. Is reg_utterances a real verbatim message store, and which channel is it?
  2. Are register `quote` values anchored in it (exact / substring / unanchored)?
  3. How much of that channel does the register actually cite?

Run: python3 verify_channel_anchor.py
"""
from __future__ import annotations

import json
import random
import re
import sqlite3
import sys

LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")
REGISTER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
            "/asks-ledger/register.json")
SUBSTANTIVE = 12


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    c = con.cursor()

    print("== tables ==")
    for (t,) in c.execute("select name from sqlite_master where type='table' order by name"):
        n = c.execute(f"select count(*) from '{t}'").fetchone()[0]
        print(f"  {t:22s} {n}")

    print("\n== reg_utterances shape ==")
    print("  roles:", dict(c.execute("select role,count(*) from reg_utterances group by role")))
    print("  conversations:", c.execute(
        "select count(distinct conversation_id) from reg_utterances").fetchone()[0])
    print("  sessions:", c.execute("select count(distinct session_id) from reg_utterances").fetchone()[0])
    print("  exact_body:", dict(c.execute(
        "select exact_body,count(*) from reg_utterances group by exact_body")))
    for (cid,) in c.execute("select distinct conversation_id from reg_utterances"):
        print("  conv id:", cid)
    print("  ts form:", c.execute("select ts from reg_utterances limit 1").fetchone()[0])

    bodies = [b for (b,) in c.execute(
        "select body from reg_utterances where role='user'")]
    user_norm = [norm(b) for b in bodies]
    user_norm = [u for u in user_norm if u]
    substantive = sorted({u for u in user_norm if len(u) >= SUBSTANTIVE})
    print(f"\n  user messages={len(bodies)} distinct={len(set(user_norm))} "
          f"substantive(>={SUBSTANTIVE})={len(substantive)}")

    reg = json.load(open(REGISTER))["records"]
    quotes = [norm(r.get("quote") or "") for r in reg]
    quotes = [q for q in quotes if q]
    uset = set(user_norm)
    blob = "\n".join(user_norm)

    exact = sum(1 for q in quotes if q in uset)
    substr = sum(1 for q in quotes if q not in uset and q in blob)
    unanch = len(quotes) - exact - substr
    n = len(quotes)
    print(f"\n== anchoring (denominator = {n} non-empty quotes) ==")
    print(f"  exact user utterance   : {exact} ({exact/n*100:.1f}%)")
    print(f"  substring of utterance : {substr} ({substr/n*100:.1f}%)")
    print(f"  ANCHORED               : {exact+substr} ({(exact+substr)/n*100:.1f}%)")
    print(f"  unanchored             : {unanch} ({unanch/n*100:.1f}%)")

    long_q = {q for q in quotes if len(q) >= SUBSTANTIVE}
    cited = [d for d in substantive if any(q in d for q in long_q)]
    uncited = [d for d in substantive if not any(q in d for q in long_q)]
    print(f"\n== own-channel capture (denominator = {len(substantive)} substantive utterances) ==")
    print(f"  cited by a >={SUBSTANTIVE}-char quote : {len(cited)} "
          f"({len(cited)/len(substantive)*100:.1f}%)")
    print(f"  uncited                              : {len(uncited)} "
          f"({len(uncited)/len(substantive)*100:.1f}%)")

    print("\n== 12 sampled uncited (to estimate how many are real asks) ==")
    for d in random.Random(11).sample(uncited, min(12, len(uncited))):
        print("  -", d[:150])

    print("\n== ask -> message link ==")
    print("  reg_ask_messages distinct asks:",
          c.execute("select count(distinct ask_id) from reg_ask_messages").fetchone()[0],
          "of", len(reg))
    print("  relation values:",
          dict(c.execute("select relation,count(*) from reg_ask_messages group by relation")))
    print("  reg_provenance.method:",
          dict(c.execute("select method,count(*) from reg_provenance group by method")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
