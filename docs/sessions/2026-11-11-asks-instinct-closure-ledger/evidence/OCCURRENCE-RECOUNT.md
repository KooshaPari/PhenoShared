# Occurrence Recount — asks corpora (2026-11-11)

Scope: `~/CodeProjects/temp/asks-coverage/mined/` only. Read-only on the mined files and on every
source directory. Nothing was re-mined, no mined file was modified.

Script: `recount_occurrences.py` (re-run any time; writes `recount_occurrences.json`).

Headline: **no pre-dedupe raw corpus exists on disk.** Every per-source JSONL is exactly
`records == distinct`, i.e. it is already a deduped set. Therefore a repeat factor computed
*from the files* is not obtainable and is reported as `n/a (DEDUPED_INPUT)` rather than as a
fake `1.00`. The only occurrence evidence that survives is what each miner wrote into its own
manifest, and that exists for 4 of 6 sources.

## Table 1 — file-level recount (measured by this script)

| Source | File used | Total records | Distinct text_sha256 | Repeat factor | Input state |
|---|---|---:|---:|---:|---|
| forge | `forge_clean.jsonl` | 15,209 | 15,209 | n/a | DEDUPED_INPUT |
| forge (pre-clean) | `forge.jsonl` | 15,201 | 15,201 | n/a | DEDUPED_INPUT |
| forge (recovered sidecar) | `forge_recovered_prompts.jsonl` | 1,112 | 1,112 | n/a | DEDUPED_INPUT |
| jcode | `jcode.jsonl` | 16,889 | 16,889 | n/a | DEDUPED_INPUT |
| kcode | `kcode.jsonl` | 196 | 196 | n/a | DEDUPED_INPUT |
| codex | `codex.jsonl` | 401 | 401 | n/a | DEDUPED_INPUT |
| imessage | `imessage.jsonl` | 7,684 | 7,684 | n/a | DEDUPED_INPUT |
| herdr | `herdr.jsonl` | 8 | 8 | n/a | DEDUPED_INPUT |
| intent (merged) | `intent.jsonl` | 40,098 | 40,098 | n/a | DEDUPED_INPUT |

0 bad-JSON rows and 0 text-less rows in every file. `forge.jsonl` and `forge_clean.jsonl` differ
by 8 rows because one oversized record was split into 9 during cleaning (`forge_clean_MANIFEST`).

## Table 2 — manifest-declared pre-dedupe counts (the only real occurrence evidence)

These numbers were recorded by the miners at scan time, before collapsing. They are MANIFEST_ONLY:
this script cannot independently re-derive them, because the pre-dedupe rows were never written to
disk.

| Source | Pre-dedupe rows (manifest) | Rows retained | Repeat factor | Collapsed | Input state |
|---|---:|---:|---:|---:|---|
| forge | 19,762 | 15,201 | 1.30x | 4,561 | MANIFEST_ONLY |
| codex | 7,830 | 401 | 19.53x | 7,429 | MANIFEST_ONLY |
| kcode | 2,934 | 196 | 14.97x | 2,738 | MANIFEST_ONLY |
| imessage | 8,585 | 7,684 | 1.12x | 901 | MANIFEST_ONLY |
| jcode | — | 16,889 | unknown | — | MISSING_PREDEDUPE |
| herdr | — | 8 | unknown | — | MISSING_PREDEDUPE |

- `jcode_MANIFEST.json` has no `records_before_dedup` / `duplicate_text_occurrences_collapsed`
  field. Its 16,889 rows are a deduped set and the true occurrence count is unknown from artifacts.
- `herdr_MANIFEST.json` records `persists_operator_prompt_text: false`: herdr's session history
  keeps ANSI scrollback with prompt echoes, not typed prompts, so 8 rows is a capture limit, not
  an occurrence count.
- `intent.jsonl` (40,098) is the global text_sha256 dedupe over 40,379 per-source rows
  (forge 15,201 + jcode 16,889 + kcode 196 + codex 401 + imessage 7,684 + herdr 8), i.e. 281 rows
  collapsed across sources. That is a *cross-source* collapse only; it inherits every per-source
  dedupe loss.

### Largest repeat factor observed

**19.53x — codex** (7,830 raw prompts → 401 rows). kcode is 14.97x. Both are global
`text_sha256` collapses, which is exactly the mechanism `KCODE-VERDICT.md` named as destroying
volume.

## Old manifest totals vs new occurrence totals

| View | Rows | Note |
|---|---:|---|
| Old: per-source manifest `records` summed | 40,379 | what `intent.jsonl` was merged from |
| Old: `intent.jsonl` after global dedupe | 40,098 | 281 collapsed across sources |
| New: manifest-declared occurrence rows, 4 sources with evidence | 39,111 | forge + codex + kcode + imessage only |
| — same 4 sources, retained rows | 23,482 | |
| **Delta on those 4 sources** | **+15,629 (+66.5%)** | 39,111 occurrences vs 23,482 distinct-retained |
| New: total occurrence rows, all 6 sources | **≥ 39,111** | a floor, not a total: jcode and herdr contribute 16,897 rows of unknown multiplicity |

So even on the four sources where volume can be proven, the deduped corpus understates operator
typing by roughly 1.7x. For codex and kcode specifically the understatement is ~15-20x. The
true global occurrence count cannot be stated without re-running the miners with occurrence
keeping; treat 40,098 as a **floor on distinct strings**, not a count of operator utterances.

## What this does not tell us

- **Occurrence counts are not intent counts.** Typing "go" 200 times is 200 occurrences and
  plausibly 1-3 intents. Nothing here measures intent.
- **Repeated identical text may be retries, not separate intents.** A prompt re-sent because a
  provider returned 429, or a session resumed and replayed, inflates occurrences with no new ask.
  Conversely, a fork chain that copies parent `messages[]` into children inflates occurrences
  while the operator typed once.
- **Machine-generated turns are not separated out.** Dispatcher-written subagent briefs
  (`TASK: …`, `READ-ONLY …`, `RESEARCH-ONLY TASK …`), injected `# AGENTS.md` preambles, cron and
  loop prompts, and test fixtures all sit in these counts unlabelled. `substantive` is a length
  flag (chars >= 80), not an authorship or intent flag.
- Nothing here is deduplicated *by meaning*. Paraphrases of the same ask count as separate strings.
- The `MANIFEST_ONLY` factors are only as trustworthy as the miners that wrote them; they cannot be
  re-derived from what is on disk.
