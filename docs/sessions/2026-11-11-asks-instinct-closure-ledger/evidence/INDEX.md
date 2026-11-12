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

## Addendum 2 — every channel mined, union and coverage (2026-11-12T02:52Z)

Rev 4 of `VERDICT.md` sized the union from two channels and had never mined iMessage or KCode.
Both are now mined at occurrence level. These artifacts are the only durable record.

| Artifact | What it establishes |
|---|---|
| `recount_imessage_kcode.py` | Occurrence-level miners for both channels. iMessage is opened `mode=ro` with `PRAGMA query_only=1`; **chat.db is never copied**. KCode `content` is a list of typed blocks and `display_role == 'system'` marks injected context — both facts were needed before it would parse. |
| `imessage_kcode_recount.json` | iMessage **6,363** distinct substantive (9,011 text-bearing outbound rows). KCode **2,457** occurrences collapsing to **166** distinct across 1,253 session files. |
| `union_channels.py` | The single script behind every figure in `VERDICT.md` §3c: channel sizes, both-direction containment, greedy long-first overlap, citation counts, union. |
| `union_channels.json` | harness 5,799 · iMessage 6,363 · KCode 166 · overlaps 517/58/1 · **union 11,752** · cited 1,764 · **coverage 15.0%**. |
| `register_channel_attribution.json` | Register-side proof: of 2,018 distinct quotes, 1,952 (**96.7%**) appear in a mined channel — phone 96.6%, iMessage 92.4%, harness 23.1%, KCode 0.1%. |

Corrections to figures this directory previously carried:

- **6,085 was never an output of `collapse_intents.py`.** Its `clean_distinct` is **5,799**
  (`8,506 − 2,707 noise`). Rev 4 attributed the gap to noise-pass ordering; that explanation
  was wrong.
- **iMessage "911" was a deduped artifact**, not the channel size. The channel has 9,011
  text-bearing outbound rows.
- **KCode "196" was roughly right** (166 actual distinct). Its 2,457 occurrences genuinely
  collapse because most sessions are canary stubs that repeat the same prompts.
- The phone channel is **not a separate channel**: 2,049 of 2,077 of its bodies appear verbatim
  in iMessage. It is an iMessage subset.
- `29.4%` register/union is superseded by **15.0%** citation-based coverage over a union that is
  11,752, not 7,661.

## Addendum 3 — ask→message link verification (2026-11-12T02:58Z)

The carried claim was "118 suspect ask→message links open". Every link is now tested.

| Artifact | What it establishes |
|---|---|
| `verify_ask_links.py` | Tests each `reg_ask_messages` link: does the ask's quoted text appear in the message it names? Two normalisation passes (strict / fold) so quote-serialisation damage is separated from wrong links. |
| `ask_link_verification.json` | strict 2,107 verified / 62 mismatched (97.14%); fold 2,151 / 18 (**99.17%**). Residual 18 = 6 sharing 60 chars, 3 at 40, 6 at 25, and **3 sharing nothing** — the only candidate genuinely wrong links. |

Method corrections recorded here:

- `reg_asks.utterance_id` (`UTT-000001`) does **not** join to `reg_utterances.id` (`phonemsg-<ULID>`).
  Comparing them yields a spurious "2,229 disagree". The working join is
  `reg_ask_messages.message_id` → `reg_utterances.message_id`.
- The 5-point strict→fold gap is the register storing escaped `\n` where the source message has a
  space, plus `" / "`-joined multi-part quotes. It is a defect in quote serialisation, not in linkage.
