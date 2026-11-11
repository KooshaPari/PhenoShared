# C — Claude / Gemini export coverage for deriving operator asks

Scanned: 2026-11-11T07:43-07:45Z. Bounded to the five named locations, every find used `-maxdepth` 3 or 4.
No recursive scan of `$HOME` or `/`.

## VERDICT

| Source | Verdict |
|---|---|
| **CLAUDE** | **ABSENT as a conversation export.** No `conversations.json`, no Claude conversation dump, no Claude Takeout. Only artifacts are a PDF (`~/Downloads/Claude.pdf`) and unrelated CLAUDE.md instruction files. Adjacent usable data exists outside the bounded scope (Claude Code local sessions, see below). |
| **GEMINI** | **ABSENT.** No Google Takeout, no `MyActivity.json`, no `conversations.json`, no bard/gemini export anywhere in the five locations. `~/.gemini` does not exist. Task item 3 (NDJSON prompt-like counting) is **not applicable** because no Takeout exists. |

## Candidates found (path, size, mtime)

| source | path | size | mtime | records | usable |
|---|---|---|---|---|---|
| Claude (PDF only) | `~/Downloads/Claude.pdf` | 3,767,734 B | 2025-09-04 | n/a (PDF) | NO — marketing/doc PDF, not a conversation export |
| n/a (ChatGPT, not in scope) | `~/Downloads/ChatGPT-[Platform] Repo scope and recovery plan - active-20261106-1543(2).json` | 121,360 B | 2026-11-08 | dict, n=0 mapping | Adjacent; not Claude/Gemini |
| n/a (ChatGPT, not in scope) | `~/Downloads/ChatGPT-Reevaluate Repository Count-20261108-2255.json` | 36,426 B | 2026-11-08 | dict, n=0 mapping | Adjacent; not Claude/Gemini |
| Dot (operator asks) | `~/Downloads/dot-conversation-PARTIAL-2026-10-09-to-2026-10-30.json` | 1,743,875 B | 2026-11-10 23:34 | 2,247 messages | YES — but it is a **Dot** partial export, not Claude/Gemini |
| ledger | `phenotype-registry/asks-ledger/asks.json` | 2,139,794 B | 2026-11-09 | 2,259 asks | YES — normalized asks ledger (see below) |
| ledger db | `phenotype-registry/asks-ledger/asks.db` | 11,694,080 B | 2026-11-09 | (sqlite) | YES |
| ledger db | `phenotype-registry/asks-ledger/ledger.db` | 11,718,656 B | 2026-11-10 | (sqlite) | YES |
| harvest | `phenotype-registry/chat-harvest/` (dir) | 26 MB | 2026-11-08 | zips: operations-digest, Research-Ledger, decisions/, reading-shortlist/ | PARTIAL — session digests, not raw Claude/Gemini |
| misc | `~/Desktop/job-chats/` | 3 files | 2025-2026 | txt/als only | NO |
| misc | `~/CodeProjects/Exports/analysis/` | dir, 19 entries | 2026-11-10 | — | no conversation exports |

Nothing matching `*takeout*`, `*MyActivity*`, `*bard*`, `conversations.json`, or `*gemini*` was found in:
`~/Downloads`, `~/Documents` (maxdepth 4), `~/Desktop`, `~/CodeProjects/Exports`,
`~/CodeProjects/Phenotype/repos/phenotype-registry`.

## `dot-conversation-PARTIAL` shape

```
top: dict
keys: format, complete, coverage_note, source_url, source_jsonl_sha256, manifest, schema, messages
format="dot-conversation-partial-json", complete=False
manifest: {schema_version, audience, requested_cutoff, earliest_returned,
           latest_returned, message_count, unique_ids, inception_proven, complete}
messages: list, len=2247
coverage_note: "Existing sanitized export only. Not a complete or current Dot dump."
```
Usable for asks (2026-10-09 → 2026-10-30 window only), and explicitly self-declared incomplete.

## asks.json (the actual coverage surface today)

- top: dict, 2,259 records
- fields: `day, domain, evidence, first_asked_at, group, id, interpretation, issue_level, issue_ref, kind, original_text, reconciled_at, reported_state, reviewed, source_refs_json`
- kind: TASK 1999, STATUS_REQUEST 195, POLICY 65
- domain: code 926, harness 286, product 274, infra 238, docs 181, security 118, process 113, research 72, data 51
- **No `source`/`harness`/`provider` field.** Provenance is only inside `source_refs_json`, which currently
  points at `*.md` day dumps (e.g. `"src": "September252026-01.md"`).
- Keyword scan of `source_refs_json` for claude/gemini/codex/jcode/kcode/cursor/imessage/chatgpt/dot: **zero hits**
  across all 2,259 records — so the ledger does not yet attribute any ask to a Claude or Gemini conversation.

## Adjacent (out of bounded scope, non-recursive existence probes)

| path | state | note |
|---|---|---|
| `~/.claude/projects` | PRESENT, 2.6 MB, 6 `*.jsonl` at maxdepth 2 | Real Claude Code session transcripts. **The only genuine Claude ask source on this host**, but it is local session data, not a platform conversation export. Small (6 files) so coverage is thin. |
| `~/.claude` | PRESENT, 323 MB | Mostly history/cache, no `conversations.json` |
| `~/Library/Application Support/Claude` | PRESENT, 929 MB | Desktop app data/storage; no conversation export artifact |
| `~/.gemini` | ABSENT | no Gemini CLI state, no Gemini auth/session store |

## Recommendation

1. Treat **CLAUDE: absent (export)** / **GEMINI: absent** and do not plan asks derivation from either until an export is actually produced.
2. If Claude coverage is wanted, harvest `~/.claude/projects/*.jsonl` (6 files) — cheap, local, already parseable — rather than requesting a platform export.
3. Gemini requires a manual Google Takeout request; nothing on disk can substitute.
4. Add a `source`/`harness` column to `asks.json`; today provenance lives only in free-text `source_refs_json` pointing at markdown day dumps, which is why no ask is attributable to Claude or Gemini.
