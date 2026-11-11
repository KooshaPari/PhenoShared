# Codex Human-Turn Re-Extraction (compressed corpus included)

Date: 2026-11-11. Scope: `~/.codex/sessions`, **read-only**. No git, no repo edits.
Script: `~/CodeProjects/temp/asks-coverage/reextract_codex.py`
Output: `~/CodeProjects/temp/asks-coverage/codex_user_turns_v2.jsonl`
Extends / supersedes the count in `CODEX-VERIFY.md`.

## Status: **FULL** run (not partial)

Full corpus attempted in 11 s. **2,567 / 2,567 files read OK, 0 read errors, 0 parse failures.**
No reduction to a 600-file subset was needed.

## Files per extension (read, not merely seen)

| Kind | Files | Read OK |
|---|---|---|
| `*.jsonl` | 180 | 180 |
| `*.jsonl.zst` | 2,380 | 2,380 |
| `*.jsonl.zst.zst` | 7 | 7 |
| **Total** | **2,567** | **2,567** |

Decompression was in-memory only. No decompressed copy of any file was written to disk.
`.zst.zst` files are genuinely double-compressed (single pass yields another zstd frame,
verified by the `28 b5 2f fd` magic), so they are decompressed twice. The `zstandard`
one-shot API rejects these multi-frame streams, so the reader falls back to a
`stream_reader` pass (and finally the `zstd` CLI); after that fix all 7 read cleanly.

## Record counts

| Measure | Value |
|---|---|
| User-turn **occurrences** (`response_item` / `message` / `role=user`) | **9,650** |
| ... from the 180 plain `.jsonl` files | 399 |
| ... from the 2,387 compressed files | **9,251** |
| Distinct `text_sha256` (occurrence vocabulary) | 856 |
| Distinct `session_id` | 2,482 |
| Parse failures | 0 |

Role census across `payload.type == "message"`: `developer` 76,996, `user` 9,650,
`assistant` 14,987. Per the predicate, `developer` is excluded from the user count
(kept out deliberately; it is injected boilerplate).

## Occurrence vs the old 401

**9,650 / 401 = 24.1x.** The old miner saw only the 180 uncompressed files, whose user
turns measure **399** directly here - within counting-rule noise of the reported 401.
The compressed 2,387 files alone contribute **9,251** occurrences, i.e. **23.2x** what the
entire old run contained.

## Honest caveat: not all `role=user` records are typed by the operator

9,650 is the count under the agreed predicate. It is an **occurrence** count, and the
corpus contains user-role records that are machine-injected context rather than human typing:

| Bucket | Occurrences | Distinct strings |
|---|---|---|
| Injected-context shaped (`# AGENTS.md instructions`, `<codex_internal_context>`, `<environment_context>`, `<user_instructions>`, `<turn_context>`) | 3,942 | 451 |
| Non-injected user-role records | **5,708** | **405** |
| ... of which substantive (>= 12 chars) | 2,794 | - |
| ... appearing exactly once | 171 | - |

The heaviest repeated strings are genuine operator nudges and automated heartbeat prompts
(`go` 899, `proc` 897, `.` 577, two project-management heartbeat templates ~1,328 combined).
These are real occurrences; they are not new distinct asks.

Notable coincidence worth flagging: the **distinct non-injected strings = 405**, almost
exactly the old `401`. That is why the old figure "looked right" - it approximated the
*distinct human prompt vocabulary*, while the real *occurrence volume* is 24x larger.
If the downstream ledger needs "how many asks happened", use **9,650**; if it needs
"how many distinct ask strings", use **856 distinct (405 non-injected)**.

## Projected total

None needed. This was a full pass over all 2,567 files, so **9,650 is a measured actual,
not a projection**. `CODEX-VERIFY.md` projected 5,100-6,100; the actual is 9,650, about 1.6x
above the top of that range because the stratified sample under-represented long interactive
sessions (and heartbeat/nudge prompts).

## Reproduce

```
python3 ~/CodeProjects/temp/asks-coverage/reextract_codex.py            # full
python3 ~/CodeProjects/temp/asks-coverage/reextract_codex.py --limit 600 # newest 600, PARTIAL
```
