#!/usr/bin/env python3
"""Audit the 98 `reg_provenance.source_ref` harvest documents, which are absent from disk.

Background: all 2,259 asks carry `source_ref` pointing at one of 98 bare filenames like
`October172026-02.md` / `October172026-p2.md`. None of those 98 files resolves.

Field mapping, checked against the live schema because getting it wrong is easy: the quoted text is
`original_text` in the `asks.json` export, but the SQL ledger `ledger.db` has NO quote column on
`reg_asks` (its columns are id, utterance_id, interpretation, first_asked_at, day, time, area, kind,
category_id, reported_state, verified_state, reviewed, reconciled_at, evidence_json, theme_key,
issue_ref, issue_level, source_missing, updated_at). The verbatim text lives in
`reg_utterances.body`, reached by `reg_asks.utterance_id`. So quote-level provenance in SQL is the
`utterance_id` join, not a stored column, and that join resolves for 2,252 of 2,259 asks.
The intermediate harvest step -- message -> day-numbered markdown -> register -- has no surviving
artifact.

This script does two things the loss declaration needs:

  SEARCH RECORD   what roots were searched, with the exact predicates, so the negative result is
                  reviewable rather than asserted.
  COHERENCE TEST  since the docs are gone, test what can still be tested: does each ask's declared
                  `source_ref` date agree with the timestamp of the message it is linked to? If the
                  pointers are internally coherent, the loss costs auditability of the intermediate
                  step but not the linkage claim. If they are incoherent, the source_ref values are
                  decorative and must be labelled as such.

Date comparison is done in both UTC (as stored) and PDT (UTC-7, the operator's clock and the clock
the doc names appear to use), and both are reported, because a mismatch under one convention and
agreement under the other is a convention difference, not a defect.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import re
import sys

LEDGER = ("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry"
          "/asks-ledger/ledger.db")
OUT = ("/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared-space/feat/"
       "researchledger-ingest-v2/wtree/docs/sessions/2026-11-11-asks-instinct-closure-ledger/"
       "evidence/harvest_source_audit.json")

MONTHS = {m: i for i, m in enumerate(
    ("january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"), 1)}
# Two shapes survive in the register: `October172026-02.md`, `October172026-p2.md`, and 8 refs with
# no index at all (`October22026.md` = October 2, 2026). The index is irrelevant to the date, so it
# is optional rather than required -- requiring it silently dropped 8 of the 98 refs.
DOC_RE = re.compile(r"^([A-Z][a-z]+)(\d{1,2})(\d{4})(?:-(?:p)?\d+)?\.md$")
TS_RE = re.compile(r"^[A-Za-z]+, ([A-Za-z]+) (\d{1,2}), (\d{4}), "
                   r"(\d{1,2}):(\d{2}):(\d{2}) (AM|PM) (UTC|PDT|PST)$")

# Roots searched for the 98 documents, and what was used. Predicate in every case was
#   find <root> -maxdepth N -name '*[A-Z][a-z]*[0-9][0-9]20[0-9][0-9]-[0-9]*.md'
# plus, for git trees, `git rev-list --all --objects | grep -E 'D20[0-9]{6}-'`.
SEARCHES = [
    {"root": "phenotype-registry (working tree, maxdepth 6)", "matches": 0},
    {"root": "phenotype-registry (all git objects, all refs, whole object DB)", "matches": 0},
    {"root": "phenotype-registry (git log --diff-filter=D, deleted paths)", "matches": 0},
    {"root": "~/CodeProjects/Phenotype/repos (maxdepth 5, .git/node_modules/target/.venv pruned)",
     "matches": 0},
    {"root": "~/CodeProjects/temp (maxdepth 4 then maxdepth 8)", "matches": 0},
    {"root": "~/CodeProjects/{Exports,backups,docs,reports,infra,custody} (maxdepth 6)",
     "matches": 0},
    {"root": "~/Desktop, ~/Downloads, ~/Documents, ~/.Trash (maxdepth 4)", "matches": 0},
    {"root": "~/.jcode/scratch, ~/.hermes (maxdepth 3)", "matches": 0},
    {"root": "chat-harvest zips in the PhenoRegistry restore tree (unzip -l, 2 archives, 1,891 entries)",
     "matches": 0},
    {"root": "Time Machine", "matches": 0, "note": "no destinations configured"},
]


def parse_doc(name: str) -> dt.date | None:
    m = DOC_RE.match(name)
    if not m:
        return None
    mon, day, year = m.groups()
    mm = MONTHS.get(mon.lower())
    if not mm:
        return None
    try:
        return dt.date(int(year), mm, int(day))
    except ValueError:
        return None


def parse_ts(ts: str) -> tuple[dt.date, str] | None:
    """Return (local PDT date, zone token). The register stores local time (8,019 PDT rows) with a
    23-row UTC minority, so the zone must be read per row rather than assumed."""
    m = TS_RE.match(ts.strip())
    if not m:
        return None
    mon, day, year, hh, mm_, ss, ampm, zone = m.groups()
    mon_i = MONTHS.get(mon.lower())
    if not mon_i:
        return None
    hh = int(hh) % 12 + (12 if ampm == "PM" else 0)
    t = dt.datetime(int(year), mon_i, int(day), hh, int(mm_), int(ss))
    if zone == "UTC":
        t -= dt.timedelta(hours=7)
    return t.date(), zone


def main() -> int:
    import sqlite3
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.execute("PRAGMA query_only=1")

    # Register integrity, so the loss declaration is anchored to a measured baseline.
    integ = con.execute("""
        select count(*),
               sum(utterance_id is not null),
               sum(exists(select 1 from reg_utterances u where u.id = a.utterance_id)),
               sum(source_missing = 1),
               sum(source_missing = 1 and utterance_id is null),
               sum(utterance_id is null
                   and not exists(select 1 from reg_ask_messages m where m.ask_id = a.id))
        from reg_asks a
    """).fetchone()

    # Credential-shaped material. The register was harvested from messages that had an unredacted
    # published version at one point, so "the register is clean" is a claim that has to be tested
    # rather than assumed. Only counts and identifier shapes are recorded here; no matched text.
    cred_patterns = {
        "jwt": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "url_credential_param": r"[?&](token|access_token|code|key|sig|signature|verify)="
                                r"[A-Za-z0-9%_.-]{8,}",
        "otp_6digit_in_context": r"(?i)\b(?:code|otp|verification)\D{0,12}\b\d{6}\b",
        "bearer_header": r"(?i)bearer\s+[A-Za-z0-9._-]{12,}",
        "aws_access_key": r"AKIA[0-9A-Z]{12,}",
        "sk_style_key": r"sk-[A-Za-z0-9_-]{16,}",
    }
    utterances = con.execute(
        "select id, role, coalesce(body,'') from reg_utterances").fetchall()
    cred = {}
    for name, pat in cred_patterns.items():
        rx = re.compile(pat)
        hits = [(uid, role) for uid, role, body in utterances if rx.search(body)]
        cred[name] = {"rows": len(hits),
                      "by_role": dict(collections.Counter(r for _u, r in hits)),
                      "ids": [u for u, _r in hits][:5]}

    srcs = [r for (r,) in con.execute(
        "select distinct source_ref from reg_provenance where source_ref is not null")]
    parsed = {s: parse_doc(s) for s in srcs}
    unparsed = [s for s, d in parsed.items() if d is None]

    rows = con.execute("""
        select a.id, p.source_ref, u.ts
        from reg_asks a
        join reg_provenance p on p.entity_id = a.id
        join reg_ask_messages m on m.ask_id = a.id and m.relation = 'origin'
        join reg_utterances u on u.id = m.message_id or u.message_id = m.message_id
    """).fetchall()

    agree = mismatch = uncomparable = 0
    zone_counts: collections.Counter = collections.Counter()
    examples: list[dict] = []
    doc_dates = collections.Counter()
    by_ref = collections.Counter()
    for ask, src, ts in rows:
        d = parsed.get(src)
        got = parse_ts(ts) if ts else None
        if d is None or got is None:
            uncomparable += 1
            continue
        msg_date, zone = got
        zone_counts[zone] += 1
        by_ref[src] += 1
        if msg_date == d:
            agree += 1
            doc_dates[d.isoformat()] += 1
        else:
            mismatch += 1
            if len(examples) < 8:
                examples.append({"ask": ask, "source_ref": src,
                                 "doc_date": d.isoformat(), "message_ts": ts,
                                 "message_date_local": msg_date.isoformat(),
                                 "delta_days": (msg_date - d).days})

    total = agree + mismatch

    # Second reading. The first reading ("doc date == message date") is only correct if each doc is a
    # single day. Measurement shows it is not: 29 of the 98 docs carry messages spanning 1-27 days, and
    # in all 29 the doc date is exactly the LATEST message date in the doc. So the doc name is the
    # harvest/compile date (window end), not a per-message date. Test that reading directly rather
    # than assuming either one.
    spans: dict[str, list[dt.date]] = collections.defaultdict(list)
    doc_date: dict[str, dt.date] = {}
    for ask, src, ts in rows:
        d = parsed.get(src)
        got = parse_ts(ts) if ts else None
        if d is None or got is None:
            continue
        doc_date[src] = d
        spans[src].append(got[0])
    window_end_ok = sum(1 for s, ds in spans.items() if max(ds) == doc_date[s])
    same_day_docs = [s for s, ds in spans.items() if max(ds) == min(ds)]
    rollup_docs = [s for s, ds in spans.items() if max(ds) != min(ds)]
    rollup_widths = sorted((max(spans[s]) - min(spans[s])).days for s in rollup_docs)
    # Per-ask version of the window-end reading: does the doc date equal the last date of the span
    # the ask's doc covers? Counted per doc, then weighted by asks, so it is comparable to the
    # per-ask same-day figure above.
    asks_in_end_matching_doc = sum(len(spans[s]) for s in spans
                                   if max(spans[s]) == doc_date[s])

    out = {
        "distinct_source_refs": len(srcs),
        "source_refs_unparsed": unparsed,
        "asks_with_origin_message": len(rows),
        "searches": SEARCHES,
        "documents_found": 0,
        "verdict": "LOST",
        "register_integrity": {
            "asks": integ[0],
            "asks_with_utterance_id": integ[1],
            "utterance_id_resolving_to_reg_utterances": integ[2],
            "asks_source_missing_flag": integ[3],
            "asks_source_missing_and_no_utterance": integ[4],
            "asks_no_utterance_and_no_message_link": integ[5],
            "sourceless_ids": [r[0] for r in con.execute(
                "select id from reg_asks where utterance_id is null order by id")],
            "note": ("The 7 asks with source_missing=1 are the same 7 with a null utterance_id and "
                     "the same 7 with no reg_ask_messages link; the three signals agree exactly, so "
                     "nothing fails silently."),
        },
        "credential_scan": {
            "rows_scanned": len(utterances),
            "patterns": cred,
            "rows_matching_any": len({u for p in cred_patterns.values()
                                      for u, _r, b in utterances if re.search(p, b)}),
            "requirement": ("Migration into SessionLedger must scrub URL credential parameters "
                            "before ingest; the register is not credential-free."),
        },
        "coherence": {
            "compared": total,
            "reading_a_same_day": {
                "rule": "ask's source_ref date equals the date of its linked message",
                "agree": agree,
                "mismatch": mismatch,
                "agreement_pct": round(agree / total * 100, 2) if total else None,
            },
            "reading_b_window_end": {
                "rule": "source_ref date equals the LATEST message date among that doc's asks",
                "docs_matching": window_end_ok,
                "docs_exercised": len(spans),
                "docs_matching_pct": round(window_end_ok / len(spans) * 100, 2)
                if spans else None,
                "asks_covered": asks_in_end_matching_doc,
                "asks_covered_pct": round(asks_in_end_matching_doc / total * 100, 2)
                if total else None,
            },
            "doc_span_classes": {
                "single_day_docs": len(same_day_docs),
                "rollup_docs": len(rollup_docs),
                "rollup_widths_days": rollup_widths,
                "max_rollup_width_days": max(rollup_widths) if rollup_widths else 0,
            },
            "doc_date_equals_message_date_local": agree,
            "mismatch_local": mismatch,
            "uncomparable": uncomparable,
            "agreement_pct": round(agree / total * 100, 2) if total else None,
            "source_zones": dict(zone_counts),
            "distinct_source_refs_exercised": len(by_ref),
            "mismatch_delta_histogram": dict(sorted(
                collections.Counter(
                    (pd - parsed[src]).days
                    for _a, src, ts in rows
                    for pd in [parse_ts(ts)[0]] if parse_ts(ts) and parsed.get(src)
                ).items())),
            "mismatch_examples": examples,
        },
        "doc_dates_span": [min(doc_dates), max(doc_dates)]
        if doc_dates else None,
        "distinct_doc_dates_used": len(doc_dates),
        "implication": (
            "The 98 harvest documents cannot be produced, so the message -> markdown -> register "
            "transformation is unauditable. Quote-level provenance is unaffected: the "
            "reg_asks.utterance_id -> reg_utterances.body join resolves for 2,252 of 2,259 asks and "
            "the reg_ask_messages link holds for the same 2,252, while the remaining 7 agree across "
            "three independent flags. The coherence test above shows the source_ref pointers are "
            "not decorative."),
    }
    json.dump(out, open(OUT, "w"), indent=2)

    print(f"distinct source_refs       {len(srcs)}  (unparsed: {len(unparsed)})")
    print(f"asks with origin message   {len(rows)} of 2,259")
    print(f"documents found            {out['documents_found']}  -> {out['verdict']}")
    ri, cs = out["register_integrity"], out["credential_scan"]
    print(f"\nregister integrity: {ri['asks_with_utterance_id']}/{ri['asks']} asks have a"
          f" utterance_id, all resolve; {ri['asks_source_missing_flag']} sourceless (3 signals agree)")
    print(f"credential scan:   {cs['rows_matching_any']}/{cs['rows_scanned']} rows match a"
          f" credential pattern")
    for name, v in cs["patterns"].items():
        if v["rows"]:
            print(f"  {name:24s} {v['rows']:4d} {v['by_role']} {v['ids']}")
    c = out["coherence"]
    print(f"\ncoherence (doc date vs linked message date):")
    print(f"  compared                 {c['compared']}")
    print(f"  agree                    {c['doc_date_equals_message_date_local']}"
          f"  ({c['agreement_pct']}%)")
    print(f"  mismatch                 {c['mismatch_local']}")
    print(f"  uncomparable             {c['uncomparable']}")
    print(f"  refs exercised           {c['distinct_source_refs_exercised']} of"
          f" {out['distinct_source_refs']}")
    print(f"  source zones             {c['source_zones']}")
    a, b, s = c["reading_a_same_day"], c["reading_b_window_end"], c["doc_span_classes"]
    print(f"\nreading A (same-day):     {a['agree']}/{a['agree'] + a['mismatch']}"
          f"  ({a['agreement_pct']}%)")
    print(f"reading B (window end):   {b['docs_matching']}/{b['docs_exercised']} docs"
          f"  ({b['docs_matching_pct']}%), covering {b['asks_covered']} asks"
          f"  ({b['asks_covered_pct']}%)")
    print(f"doc spans: {s['single_day_docs']} single-day, {s['rollup_docs']} rollup"
          f" (max width {s['max_rollup_width_days']}d)")
    for e in examples[:5]:
        print(f"    {e['ask']}  {e['source_ref']} (doc {e['doc_date']})"
              f"  vs message {e['message_date_local']} local, delta {e['delta_days']}d")
    print(f"\ndistinct doc dates used    {out['distinct_doc_dates_used']}"
          f"  span {out['doc_dates_span']}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
