#!/usr/bin/env python3
"""Build a blind sampling sheet for CITATION PRECISION.

The existing `ask_link_verification.json` measures QUOTE FIDELITY: the quoted
text is present in the message the link names. That is a different question
from precision, which asks whether a cited unit belongs to the intent it was
counted under.

Source of the link rows (no register jsonl exists in the session dir):

  ledger.db / reg_ask_messages   (ask_id, message_id, role, seq, ts, relation)
  ledger.db / reg_asks           (id, interpretation, ...)
  ledger.db / reg_utterances     (id, conversation_id, message_id, body, role)

`reg_ask_messages.message_id` is a mixed namespace: most rows hold a
`phonemsg-<ULID>` that joins `reg_utterances.message_id`; 23 rows hold a
`UTT-NNNNNN` that joins `reg_utterances.id`. Both are resolved, exactly as
`verify_ask_links.py` does.

Writes precision_sheet.json (blind) and precision_key.json (withheld).
Read-only against the ledger.
"""
from __future__ import annotations

import json
import os
import random
import re
import sqlite3
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")
REGISTER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
            "/asks-ledger/register.json")
SHEET = os.path.join(HERE, "precision_sheet.json")
KEY = os.path.join(HERE, "precision_key.json")

SEED = 20261112
N = 60
UNIT_CHARS = 600
CLAIM_CHARS = 400

RUBRIC = ("verdict is exactly one of: supported = the unit's words plainly carry "
          "the ask's claim, and no other ask in the register fits it better; "
          "partial = the unit is on the same subject but states only part of the "
          "claim, or fits a sibling ask about equally well; unsupported = the unit "
          "is on a different subject, or is an agent/tool/system utterance rather "
          "than an operator one, or the claim is not in the text; unresolvable = "
          "the text is too truncated, garbled, or ambiguous to judge.")

# --- normalisation copied from verify_ask_links.py (same measurement) --------
WS = re.compile(r"\s+")
EDGE = " \t\r\n`*_~#>-–—:;,.!?\"'()[]{}<>|/\\"
MINQ = 8


def fold(s: str) -> str:
    s = s or ""
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'),
                 ("\u201d", '"'), ("\\n", " "), ("\\t", " "), ("\\\\", "\\"),
                 ("\\", "")):
        s = s.replace(a, b)
    return s


def norm(s: str, folding: bool) -> str:
    t = (fold(s) if folding else (s or "")).strip().lower()
    t = WS.sub(" ", t)
    return t.strip(EDGE)


def fidelity(quote: str, body: str) -> tuple[bool | None, bool | None]:
    """Return (strict_ok, fold_ok); None where untestable."""
    out = []
    for folding in (False, True):
        q = norm(quote, folding)
        b = norm(body, folding)
        if len(q) < MINQ or not b:
            out.append(None)
            continue
        parts = [p.strip() for p in q.split(" / ") if len(p.strip()) >= MINQ]
        out.append(bool(q in b or (parts and all(p in b for p in parts))))
    return out[0], out[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def channel_of(conversation_id: str) -> str:
    cid = conversation_id or ""
    if cid.startswith("phoneconv-"):
        return "phone"
    if cid.startswith("chatdb"):
        return "chatdb"
    return "unknown"


def main() -> int:
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")
    cur = con.cursor()

    asks = {a: i for a, i in cur.execute(
        "select id, interpretation from reg_asks")}
    utt_by_mid = {}
    utt_by_id = {}
    for uid, mid, cid, body, role in cur.execute(
            "select id, message_id, conversation_id, body, role "
            "from reg_utterances"):
        utt_by_id[uid] = (uid, cid, body, role)
        if mid:
            utt_by_mid[mid] = (uid, cid, body, role)

    links = cur.execute(
        "select ask_id, message_id, role, seq, ts, relation "
        "from reg_ask_messages order by ask_id, message_id").fetchall()

    # quote lookup: register.json `ask` -> quoted text
    quotes: dict[str, list[str]] = {}
    for r in json.load(open(REGISTER))["records"]:
        quotes.setdefault(r.get("ask") or "", []).append(r.get("quote") or "")

    def quote_for(claim: str) -> str:
        for folding in (True, False):
            k = norm(claim, folding)
            for cand in quotes:
                if norm(cand, folding) == k:
                    for q in quotes[cand]:
                        if len(norm(q, folding)) >= MINQ:
                            return q
        return ""

    rows = []
    unresolved = 0
    for ask_id, mid, role, seq, ts, relation in links:
        hit = utt_by_mid.get(mid)
        ns = "phonemsg"
        if hit is None:
            hit = utt_by_id.get(mid)
            ns = "utt" if hit else "absent"
        claim = (asks.get(ask_id) or "").strip()
        if hit is None:
            unresolved += 1
            continue
        uid, cid, body, urole = hit
        body = body or ""
        if not body.strip() or not claim:
            unresolved += 1
            continue
        rows.append({
            "unit_id": uid,
            "ask_id": ask_id,
            "unit_text": body[:UNIT_CHARS],
            "ask_claim": claim[:CLAIM_CHARS],
            "channel": channel_of(cid),
            "unit_role": urole,
            "link_role": role,
            "relation": relation,
            "seq": seq,
            "ts": ts,
            "resolved_by": ns,
            "quote": quote_for(claim),
        })

    if len(rows) < N:
        print(f"BLOCKED: only {len(rows)} eligible cited pairs, need {N}")
        return 1

    seen = set()
    pop = []
    for r in sorted(rows, key=lambda x: (x["ask_id"], x["unit_id"])):
        k = (r["unit_id"], r["ask_id"])
        if k in seen:
            continue
        seen.add(k)
        pop.append(r)

    sample = random.Random(SEED).sample(pop, N)
    ts_now = now()

    sheet_items = []
    key_rows = []
    for idx, r in enumerate(sample):
        sheet_items.append({
            "idx": idx,
            "unit_id": r["unit_id"],
            "ask_id": r["ask_id"],
            "unit_text": r["unit_text"],
            "ask_claim": r["ask_claim"],
            "verdict": None,
            "why": "",
        })
        s_ok, f_ok = fidelity(r["quote"], r["unit_text"])
        key_rows.append({
            "idx": idx,
            "unit_id": r["unit_id"],
            "ask_id": r["ask_id"],
            "channel": r["channel"],
            "unit_role": r["unit_role"],
            "link_role": r["link_role"],
            "relation": r["relation"],
            "resolved_by": r["resolved_by"],
            "fidelity_strict": s_ok,
            "fidelity_fold": f_ok,
            "fidelity_basis": ("computed at generation time with "
                               "verify_ask_links.py normalisation; no per-row "
                               "field exists in ask_link_verification.json"),
        })

    sheet = {
        "generated_at_utc": ts_now,
        "seed": SEED,
        "n": N,
        "population": {
            "cited_pairs": len(pop),
            "source_file": f"{LEDGER} :: reg_ask_messages (relation='origin') "
                           f"joined to reg_asks / reg_utterances",
            "links_read": len(links),
            "ineligible": len(links) - len(rows),
            "note": "cited pairs are the register's origin links; each is one "
                    "(unit id, ask id) citation the register counted",
        },
        "instructions": RUBRIC,
        "items": sheet_items,
    }
    key = {
        "generated_at_utc": ts_now,
        "seed": SEED,
        "note": "withheld from the labeller",
        "rows": key_rows,
    }

    json.dump(sheet, open(SHEET, "w"), indent=2)
    json.dump(key, open(KEY, "w"), indent=2)
    print(f"population={len(pop)} sampled={N} ineligible={len(links)-len(rows)} "
          f"unresolved={unresolved}")
    print(f"wrote {os.path.basename(SHEET)} {os.path.getsize(SHEET)}B, "
          f"{os.path.basename(KEY)} {os.path.getsize(KEY)}B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
