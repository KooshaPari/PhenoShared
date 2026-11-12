# Channel scope: what the register is actually a capture of

> **PARTLY SUPERSEDED (2026-11-12).** This document establishes the channel scope and the
> register's verbatim anchoring, both of which still hold. Its iMessage (`911`) and KCode (`196`)
> rows were `DEDUPED_INPUT` placeholders; they are now measured at **6,363** and **166** distinct.
> The union and coverage figures here are superseded by `VERDICT.md` section 3c and section 3e
> (union 11,752, citation coverage 15.0%).

Measured 2026-11-12 with `verify_channel_anchor.py` (read-only on `ledger.db`,
`PRAGMA query_only=1`). Raw output: `channel_anchor_output.txt`.

## The finding

The 2,259-ask register is a **verbatim extraction**, not a synthesis. 2,235 of its 2,259 `quote`
values (98.9%) appear in the register's own message store, 1,506 exactly and 729 as mid-message
excerpts. The 24 unanchored hold literal `\n` escapes and URL-encoded filenames, i.e. harvest
artifacts.

That store is **not** the harness corpus:

| conversation_id | messages | user | register quotes anchored |
|---|---:|---:|---:|
| `phoneconv-01M3D10S1REWYKC27825RK0JDT` | 6,616 | 2,269 | 1,891 |
| `phoneconv-01M5E89QP154YYM60H1H4CQZ6K` | 1,403 | 333 | 394 |
| `chatdb` (iMessage) | 23 | 23 | 49 |
| unanchored | — | — | 24 |

Counts exceed 2,259 because a few quotes appear in more than one conversation. Register span:
38 distinct days, 2026-09-25 to 2026-11-04.

## Per-channel coverage

| Channel | Distinct substantive intents | Register captures |
|---|---:|---|
| Phone chat (the register's own source) | 2,075 | 1,733 cited (83.5%); ~87% after sampling |
| jcode + codex harness | 5,799 cleaned (of 8,506 distinct) | 357 (16.7%, substring) |
| iMessage | 911 (`DEDUPED_INPUT`) | not measured |
| KCode | 196 (`DEDUPED_INPUT`) | not measured |

Phone-chat collapse is a no-op: 2,620 user messages -> 2,367 distinct -> 2,075 substantive (>=12
chars); exact, prefix-40, and Jaccard-0.8 all return 2,075. The 342 uncited substantive utterances
(16.5%) sampled 3-4 genuine asks in 16, the rest being conversational fragments
(`"was the name"`, `"and processes"`, `"desk rebooted"`).

## Methods tested and rejected

Token-level TF-IDF cosine over the 8,506 harness intents (`measure_similarity.py`,
`similarity_results.json`): median 0.32, 712 entries at >=0.40, **but 0 of 12 sampled high-band pairs
are the same intent**. Examples: "why is paperclip mac only" -> "state of mac works";
"switch infisical to a bright/light theme" -> "infisical has the creds". Recorded as a negative
result. No ML stack is installed locally (no numpy, torch, or ollama), so true embedding similarity
would require an install or an API.

## Why the earlier verdict was wrong

Rev 3 of `VERDICT.md` concluded "synthesis, not extraction" from zero lexical overlap between the
register and the harness corpus. Zero overlap was evidence of a **channel mismatch**, not of
fabrication. The register's own provenance tables (`reg_ask_messages`, `reg_utterances`) answer the
question directly and were not read before that claim was published.

## Provenance defects that remain real

- `reg_provenance.source` is `register.json` for 2,259/2,259, so the register never joined the harness.
- 0 of 98 `source_ref` paths resolve: the harvest documents are named `MonthDYYYY-NN.md`
  (`September252026-01.md`) and are not on disk in the registry repo.
- `reg_provenance.method` records `no-source-body-available` for exactly 7 asks; that is the same 7
  "sourceless asks" defect, documented at source.
- 118 suspect ask->message links remain open; `ASK-000013` is confirmed wrong.
