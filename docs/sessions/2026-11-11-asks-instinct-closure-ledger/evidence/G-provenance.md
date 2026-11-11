# G — Provenance: can the 2259-ask register be traced to verbatim source text?

Read-only inspection of `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/asks-ledger/ledger.db`
(sqlite3 `mode=ro`). No recursive search of `$HOME` or `/`; only exact paths named by the DB or the build script.

## 1. Schemas

### reg_provenance (2259 rows)
| column | type |
|---|---|
| entity | TEXT |
| entity_id | TEXT |
| source | TEXT |
| source_ref | TEXT |
| method | TEXT |
| observed_at | TEXT |

### reg_utterances (8042 rows)
| column | type |
|---|---|
| id | TEXT |
| session_id | TEXT |
| conversation_id | TEXT |
| message_id | TEXT |
| seq | INTEGER |
| ts | TEXT |
| body | TEXT |
| body_sha256 | TEXT |
| exact_body | INTEGER |
| role | TEXT |

### reg_sessions (141 rows)
| column | type |
|---|---|
| id | TEXT |
| conversation_id | TEXT |
| started_at | TEXT |
| ended_at | TEXT |
| message_count | INTEGER |
| gap_minutes | INTEGER |
| derivation | TEXT |

Related: `reg_ask_messages(ask_id, message_id, role, seq, ts, relation)` and
`reg_asks(..., utterance_id, interpretation, source_missing, evidence_json, ...)`.

## 2. Where the verbatim text actually lives

`reg_utterances.body` **is** the verbatim message text, with `body_sha256` and `exact_body`.
Sample (UTT-000001, SES-0001, role=user, exact_body=1, 544 chars) is the raw iMessage body:
`"Thanks.\n\nNow you're going to need you to sell yourself.\n\nI joined via \"I only have 10 invites..."`.
SHA-256 recomputed in Python matched the stored `body_sha256` on every sampled row.

Sample provenance rows:
```
{'entity':'reg_asks','entity_id':'ASK-000001','source':'register.json',
 'source_ref':'September252026-01.md','method':'relinked:contained:1.0','observed_at':'2026-11-05T21:24:22'}
{'entity':'reg_asks','entity_id':'ASK-000002','source':'register.json',
 'source_ref':'September252026-01.md','method':'relinked:exact:1.0',...}
```
So the provenance table has **no path and no row id into the DB**. It points at
`register.json` plus a per-session markdown filename (`<Month><Day><Year>-<nn>.md`). The
authoritative link is the *separate* `reg_asks.utterance_id -> reg_utterances.id` foreign key.

## 3. `reg_asks.source_missing` distribution

| source_missing | count |
|---|---|
| 0 | 2252 |
| 1 | 7 |

The 7 with no source body: ASK-000345, ASK-000637, ASK-000664, ASK-001844, ASK-002254,
ASK-002255, ASK-002256. All have `utterance_id = NULL` and `evidence_json = '[]'`.

## 4. Pointer resolution — `source_ref` markdown files are DANGLING

`reg_provenance.source_ref` holds 98 distinct filenames (September252026-01.md …
November…md). Existence tested with bounded `os.path.exists`/`ls` on the exact named paths
only, against every plausible base:

| base | refs resolved |
|---|---|
| `asks-ledger/` | 0 / 98 |
| `asks-ledger/{source,sources,raw,exports,register,md}/` | dirs do not exist |
| `phenotype-registry/` | 0 / 98 |
| `register.json` `src` values in cwd | 0 / 98 |

**0 of 98 resolve.** The markdown session exports that `source_ref`/`src` name are not on disk
in this repo or its parent. Those pointers are dangling. (Per build-asks-db.py the real upstream
inputs are an `$EXPORT` iMessage JSON and, as second source, `$CHAT_DB` = `~/Library/Messages/chat.db`;
the .md files are a derived register artifact, not the message store.)

Session ids, by contrast, resolve perfectly: 8019/8019 utterance `session_id` values join
`reg_sessions`, and `reg_sessions.derivation = 'time-gap:45m'` states plainly that sessions are a
*derivation*, not a source artifact.

## 5. The 8042 / 2252 / 2259 discrepancy

- **8042 `reg_utterances`** = every message in the export (5417 assistant + 2625 user) across 141
  derived sessions. This is the raw grain: one row per message. It is not a list of asks, and
  only 2625 of them are operator (user) messages.
- **2252 `reg_ask_messages`** = exactly one `relation='origin'` row per *linked* ask
  (2252 distinct `ask_id`, no orphans). It is a bridge table, cardinality 1:1 with linked asks,
  not an independent count.
- **2259 `reg_asks`** = the distilled register; each ask is one interpreted intent, deduped from
  quotes. 2252 link to a user utterance which resolves to **1843 distinct** user messages, i.e.
  one operator message can yield more than one ask (2,252 asks over 1,843 messages).

**Dedup grain: `reg_asks` (one row per interpreted intent) is the ask grain; `reg_utterances` is
the message grain.** 2259 − 2252 = 7 = the `source_missing=1` asks.

## 6. Verdict

**PARTIALLY traceable — 2,252 of 2,259 asks (99.7%) trace to verbatim operator text stored in
the DB; 7 are untraceable; 2,134 are verbatim-verifiable by direct string containment.**

Evidence, positional join `records[i] -> ASK-{i:06d}` between `register.json` and `reg_asks`:

| result | count |
|---|---|
| register `quote` found verbatim inside linked `reg_utterances.body` | 2134 |
| quote present but not matching (whitespace/escaping, or mis-linked) | 118 |
| no linked utterance at all | 7 |

Notes on the 118:
- Benign: escaping/normalisation only. ASK-000052 quote `"1 and 2 I apply for CA do all the opt
  outs / removal requests."` vs body `"1 and 2 I apply for CA  do all the opt outs..."` (double
  space); ASK-000167 quote contains a literal `\n\n` where the body has a real newline.
- Not benign: ASK-000013's quote (`"you just need valid justifications + my approval..."`) is
  absent from the body it is linked to (`"If you need private / acc connected sources..."`). That
  is a wrong link, not a formatting difference. Treat the `relinked:contained` and
  `relinked:token_overlap` methods as suspect: provenance method distribution is
  exact 1456, contained 741, alnum_exact 45, token_overlap 10, none 7.

Integrity positives: 0 asks point at a non-existent utterance id; 8037/8042 utterances are
`exact_body=1` (5 are chat.db-sourced reconstructions with `exact_body=0`, and 5 of those are
referenced by asks); 23 asks depend on a chat.db-sourced utterance with `message_id = NULL`.
SHA-256 recomputation matches stored hashes.

**Practical answer:** no external file needs to be recovered to read the verbatim operator text —
it is embedded in `reg_utterances.body` with a hash. What is broken is the `reg_provenance`
pointer layer (98/98 dangling `source_ref` markdown names, no row-id column) and the ~118
claims whose "verbatim" quote does not appear in the row it is joined to. The 7 `source_missing`
asks cannot be traced to any operator text today.

## Reproduce
```
DB=.../asks-ledger/ledger.db
sqlite3 "file:$DB?mode=ro" "select source_missing,count(*) from reg_asks group by 1;"
python3 - # recompute sha256 of reg_utterances.body vs body_sha256; positional register join
```
