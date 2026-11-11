# Evidence Index — asks/instinct coverage corpus

Copy date (UTC): `2026-11-11T12:36:26Z`
Source root: `~/CodeProjects/temp/asks-coverage/`
Destination root: `docs/sessions/2026-11-11-asks-instinct-closure-ledger/evidence/`

## Why this directory exists

The entire evidence base for this work previously lived only under
`~/CodeProjects/temp/asks-coverage`, which is a **volatile scratch path**: it may be
wiped periodically and on reboot. This directory makes the *derivable* parts of that
corpus durable and repo-tracked.

**The full mined corpus is NOT copied.** It is roughly 612 MB on disk across the
`mined/*.jsonl` files (the largest are `intent.jsonl` ~224 MB, `forge_clean.jsonl`
~186 MB, `forge.jsonl` ~186 MB, `jcode.jsonl` ~39 MB). Those remain volatile and are
not recoverable from this repo. What is preserved here is the **schema, the per-source
manifests, and the human-readable analysis reports**, which are sufficient to describe,
re-validate and re-derive the corpus from the original local sources.

## Copied files (21)

### From `~/CodeProjects/temp/asks-coverage/mined/`

| File | Bytes |
| --- | --- |
| `SCHEMA.md` | 1487 |
| `KCODE-VERDICT.md` | 8986 |
| `_MANIFEST.json` | 2294 |
| `_MANIFEST.backup.forge.json` | 2243 |
| `codex_MANIFEST.json` | 888 |
| `forge_MANIFEST.json` | 2294 |
| `forge_clean_MANIFEST.json` | 7530 |
| `herdr_MANIFEST.json` | 8484 |
| `imessage_MANIFEST.json` | 1794 |
| `intent_MANIFEST.json` | 3268 |
| `jcode_MANIFEST.json` | 354 |
| `kcode_MANIFEST.json` | 3961 |

### From `~/CodeProjects/temp/asks-coverage/`

| File | Bytes |
| --- | --- |
| `A-gpt-full.md` | 7747 |
| `B-gpt-partial.md` | 4991 |
| `C-claude-gemini.md` | 5332 |
| `COVERAGE-REPORT.md` | 5448 |
| `D-harness.md` | 3579 |
| `E-imessage-register.md` | 10016 |
| `G-provenance.md` | 6737 |
| `H-other-channels.md` | 8465 |
| `LEDGER-AUDIT.md` | 9358 |

Total copied: 105,256 bytes (0.10 MB) across 21 files, measured with `stat -f%z`.

## Deliberately NOT copied

| Path | Bytes | Reason |
| --- | --- | --- |
| `mined/intent.jsonl` | 224,242,675 | Large corpus; volatile by policy |
| `mined/forge_clean.jsonl` | 185,831,404 | Large corpus |
| `mined/forge.jsonl` | 185,704,748 | Large corpus |
| `mined/jcode.jsonl` | 38,693,298 | Large corpus |
| `mined/imessage.jsonl` | 3,651,550 | Large corpus |
| `mined/codex.jsonl` | 1,868,115 | Large corpus |
| `mined/kcode.jsonl` | 511,971 | Large corpus |
| `mined/forge_recovered_prompts.jsonl` | 563,349 | Corpus extract, not a manifest/report |
| `mined/herdr.jsonl` | 2,675 | Corpus extract |
| `mined/scripts/` | (dir) | Regenerable tooling, not evidence |
| `B-preserved-human-messages.json` | 18,075 | Data extract, not a manifest/report |
| `analyze_exports.py`, `chatgpt.py`, `chatgpt2.py`, `final.py`, `probe.py`, `sample_codex.py`, `stats.py` | 410-6126 | Scripts; regenerable tooling |
| `chat.txt`, `chat2.txt`, `ledger2.txt`-`ledger5.txt`, `probe.txt` | 227-7358 | Ad-hoc console captures, superseded by the reports |

## Note on the manifests

`_MANIFEST.json` and `_MANIFEST.backup.forge.json` are byte-identical in intent but the
backup was written before the `forge_clean` pass. `forge_MANIFEST.json` is likewise the
pre-clean version. All three are retained so the clean/raw distinction stays auditable.

## Reproducing the corpus

Regeneration depends on local source artifacts at their original locations (jcode/kcode
session stores, Codex rollouts, Forge/Herdr/iMessage exports). Those sources are outside
this repo and unchanged by this copy. If the volatile JSONL is lost, it can be re-mined
from those sources; the manifests here record what the previous run contained.

## Addendum — corrected counts (2026-11-11T12:59Z)

These four artifacts supersede every per-source record count in the earlier manifests.
They are copied verbatim from `~/CodeProjects/temp/asks-coverage/` and are the only
durable record of the following measurements.

| Artifact | What it establishes |
|---|---|
| `CODEX-VERIFY.md` | 2,567 `~/.codex/sessions` files: 180 plain `.jsonl`, 2,380 `.jsonl.zst`, 7 `.jsonl.zst.zst`. A `*.jsonl` glob reads 7% of the corpus. |
| `CODEX-REEXTRACT.md` | Full zstd-aware pass: **9,650** user-turn occurrences, not 401 (24.1x). 3,942 are injected context, leaving **5,708** genuine, **405** distinct non-injected. |
| `JCODE-REEXTRACT.md` | **55,119** user-role occurrences, 24,715 distinct, **2.23x** repeat factor. Injected share 38.44%. Human non-injected: **30,234** occurrences, **8,290** distinct. `messages[].display_role` is the decisive field. |
| `OCCURRENCE-RECOUNT.md` | Every previously mined file has `records == distinct`, i.e. all were globally deduped. No file-level repeat factor is recoverable; jcode/herdr have no pre-dedupe evidence. |

Corrections to earlier figures in this directory:

- The jcode sessions directory is **2.9 GB / 8,667 files**, not the ~38.7 MB previously stated.
- `16,887` (old jcode count) is a deduped, partially-filtered figure and is not reproducible
  from either distinct count; it must not be used as a volume baseline.
- herdr cannot be recovered at occurrence level: its manifest records
  `persists_operator_prompt_text: false`, so the 8 records are a data limitation, not a bug.
