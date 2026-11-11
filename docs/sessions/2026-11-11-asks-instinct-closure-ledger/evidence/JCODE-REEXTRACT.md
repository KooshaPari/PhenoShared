# JCODE-REEXTRACT — occurrence-level re-mine (no dedupe)

Date: 2026-11-11T12:53Z
Corpus: `~/.jcode/sessions/*.json` (read-only). No `$HOME`/`scratch` scan.
Script: `~/CodeProjects/temp/asks-coverage/reextract_jcode.py`
Output: `~/CodeProjects/temp/asks-coverage/jcode-occurrences.jsonl`
Stats: `~/CodeProjects/temp/asks-coverage/jcode-reextract-stats.json`

## Corpus / schema

| Item | Value |
|---|---|
| session files found | 8,667 |
| files read OK | 8,667 |
| read errors | 0 |
| dir size | 2.9 GB (not 38.7 MB as previously estimated) |
| run time | 15.5 s |

Session JSON top-level keys: `id, parent_id, title, created_at, updated_at, messages,
model_usage_turn_id, provider_key, model, is_canary, working_dir, short_name, status,
last_pid, last_active_at, is_debug, saved, env_snapshots`.

**The text payload field is `messages[].content`**, a list of blocks
`{"type": "text", "text": "..."}`. The role field is `messages[].role`, and
**`messages[].display_role` is the decisive signal** (values seen: `user` 38,638,
`system` 13,146, `background_task` 3,335). jcode writes session-context and
`<system-reminder>` blocks as `role="user"` with `display_role="system"`; those are
injected context, not operator input.

## Occurrence volume (user-role messages, no dedupe)

| Metric | Value |
|---|---|
| **total occurrences** | **55,119** |
| distinct `text_sha256` | 24,715 |
| **repeat factor** | **2.23x** |
| injected occurrences | 21,186 |
| **injected share** | **38.44%** |
| human occurrences (`display_role != system`) | 41,973 |
| human & non-injected occurrences | 30,234 |
| human & non-injected distinct | 8,290 |
| human & non-injected repeat factor | 3.65x |
| human & non-injected, substantive (>=12 chars) | 21,531 |

Injected-marker hit counts (a message can match more than one):
`system-reminder` 21,052; `AGENTS.md` 364; `Available Skills` 182;
`<environment_context>` 10; `codex_internal_context` 1; `Project Instructions` 1;
`# Claude AI Agent Guide` 1; `Project Prompt Overlay` 1.

`background_task` display_role: 3,335 occurrences (scheduled/agent-injected prompts,
counted inside "human occurrences" only because role=="user"; they are not typed
operator input and should be excluded from any operator-intent corpus).

## Reconciliation with the earlier 16,887 figure

The earlier jcode lane reported 16,887 records, all of which were distinct strings
(`records == distinct`). That number sits **between** this run's two distinct counts:

- all-distinct (incl. injected): **24,715** — 1.47x the 16,887
- human non-injected distinct: **8,290** — the earlier number is 2.04x this

So 16,887 is not reproducible from either definition. It is consistent with a corpus
that deduped across **all** user-role occurrences but excluded only part of the injected
set (e.g. dropped `display_role=="system"` blocks but kept `system-reminder` text that
appeared under a user display_role). Treat 16,887 as a *deduped, partially-filtered*
count and do not use it as a volume baseline.

## Honest comparison to KCode (14.97x) and Codex (19.53x)

jcode's inflation is **2.23x** on all occurrences and **3.65x** on the
human-non-injected subset — an order of magnitude *less* than KCode or Codex. jcode
session files store one message row per turn and do not appear to replay the full
conversation history into each session, which is what drives the near-20x inflation
in Codex. So the "jcode volume is unknown and could be much larger" hypothesis is
**falsified**: jcode was already close to its occurrence volume after dedupe.

## Caveats

- Only `role == "user"` messages are emitted. Assistant and tool messages are excluded
  by design (they are not operator asks), so 55,119 is not the total message count of
  the corpus.
- `is_injected` is a marker-substring test over the whole message text. A genuine
  operator message that happens to mention `AGENTS.md` would be flagged injected
  (364 hits on `AGENTS.md` are suspiciously high for that reason and should be
  spot-checked before exclusion).
- `substantive` is `chars >= 12`, a crude length proxy, not a semantic judgement.
- Sessions dir measured 2.9 GB, not the ~38.7 MB in the task brief. The brief's figure
  is wrong; 8,667 files totalling 2.9 GB were read in 15 s, so the read cost is fine,
  but any future sizing estimate must use 2.9 GB.
