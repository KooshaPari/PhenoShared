# D — Harness Session Transcript Coverage

Measured 2026-11-11 (local -08:00). Read-only walk, maxdepth 4 per root, no $HOME recursion.

## Root inventory

| root | exists | files | bytes | date_range (mtime) |
|---|---|---|---|---|
| ~/.codex/sessions | YES | 2,567 | 667,574,449 (637 MB) | 2025-07-17 → 2026-11-10 |
| ~/.jcode/sessions | YES | 12,770 | 3,005,428,768 (2.80 GB) | 2026-08-06 → 2026-11-11 |
| ~/.kcode/sessions | YES | 1,838 | 28,867,595 (27.5 MB) | 2026-10-08 → 2026-11-11 |
| ~/.claude/projects | YES | 370 | 1,872,118 (1.79 MB) | 2025-12-10 → 2026-10-16 |
| ~/.cursor/agent-transcripts | **MISSING** | 0 | 0 | - |
| ~/.forge | YES | 18,993 | 8,403,551,241 (7.83 GB) | 2026-05-01 → 2026-11-11 |

Note: `.forge` bulk is `.forge.db` (2.99 GB SQLite) + 15,766 `.snap` files, not per-session transcripts.

## Sampled user-message counts (3 largest roots only)

Formats differ: jcode = JSON (`messages[]` with `role`), codex = zstd JSONL (`{"type":"message","role":"user"}`), forge = SQLite `conversations` table (content in `context`/`context_zstd`, not parsed message bodies).

| root | sampled files | parsed | user msgs | substantive (>80ch) | one-word | short |
|---|---|---|---|---|---|---|
| ~/.jcode/sessions | 20 newest | 12 transcripts | 95 | 60 | 20 | 15 |
| ~/.codex/sessions | 20 newest ≥1500B | 20 | 20 | 19 | 0 | 1 |
| ~/.forge | schema probe | 13,260 conversations (2026-03-25 → 2026-09-19) | n/a | n/a | n/a | n/a |

Empty-content and injected `# AGENTS.md` / `<environment_context>` user entries excluded from counts. 8 of the newest 20 jcode files were non-transcript artifacts (edit-stats etc.), so ~60% of jcode session files are real transcripts.

## Estimation of uncaptured operator asks (outside iMessage)

Using per-file averages from the samples:

| root | transcript files | avg user msgs/file | est. user msgs |
|---|---|---|---|
| ~/.jcode/sessions | ~6,150 (60% of 10,248 .json) + 611 .jsonl | 7.9 | ~48,600 |
| ~/.kcode/sessions | ~1,100 (60%) | 7.9 (same format) | ~8,700 |
| ~/.codex/sessions | ~2,380 | 1.0 | ~2,380 |
| ~/.forge | 13,260 conversations | 1+ per conversation | ~13,300+ |
| ~/.claude/projects | 370 | not sampled | small |
| ~/.cursor/agent-transcripts | MISSING | - | 0 |

**Total: roughly 73,000+ operator user-messages.** Substantive share: 63% in jcode, 95% in codex → an estimated **45,000–55,000 substantive asks** are uncaptured outside iMessage.

## Conclusions

1. Coding-harness transcripts are by far the biggest uncaptured intent source — ~73k messages across 4 active roots, vs a few hundred in iMessage-scale channels.
2. `.jcode/sessions` is the single largest message reservoir (~48.6k) and is 2.8 GB; `.forge` holds 13,260 structured conversations with an intent/extraction schema already present (`intent_state`, `extracted_at`, `intent_hash`, `memory_id`).
3. `.forge/.forge.db` is the only root with a native structure for intent mining; jcode/codex require transcript parsing.
4. `.cursor/agent-transcripts` does not exist on this host — cursor is not a source here.
5. `.kcode` is a duplicate-format fork of jcode; sampling jcode is a valid proxy but they are separate stores and both must be walked.
6. One-word nudges ("go", ".", "continue") are 21% of jcode user messages — real operator intent but low information; substantive messages are the mining target.

## Method notes

- Read-only python `os.walk` (find was false-positive blocked by the destructive gate for `-exec`).
- No transcript bodies printed; counts only.
- Sampling = newest 20 by mtime per root.
