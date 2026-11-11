# Codex Session Extraction Verification

Date: 2026-11-11. Scope: `~/.codex/sessions`. Read-only. No git, no repo edits.

## 1. Corpus composition (this is the whole story)

| Kind | Count |
|---|---|
| `*.jsonl` (plain, immediately readable) | **180** |
| `*.jsonl.zst` (zstd-compressed) | **2,380** |
| `*.jsonl.zst.zst` (double-compressed) | **7** |
| **Total** | **2,567** |

Directory layout is `sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl[.zst]`, depth 5.
Volume ~637 MB, so no full scan was performed: 40-file samples only.

**93% of the corpus is compressed.** A reader that globs `*.jsonl` and skips `.zst` sees
only 180 of 2,567 files.

## 2. Record shapes (observed, not assumed)

Top-level `type` values across a 40-file newest sample and a 40-file stratified sample:

| top-level `type` | newest-40 | stratified-40 |
|---|---|---|
| `response_item` | 1,218 | 3,502 |
| `event_msg` | 648 | 2,638 |
| `token_usage_record` | 198 | 763 |
| `world_state` | 95 | 161 |
| `inter_agent_communication_metadata` | 28 | 161 |
| `turn_context` | 54 | 117 |
| `session_meta` | 54 | 50 |
| `compacted` | 0 | 6 |

Nested `payload.type` values: `message`, `item_completed`, `token_count`, `function_call`,
`function_call_output`, `reasoning`, `task_started`, `task_complete`, `agent_message`,
`custom_tool_call`, `custom_tool_call_output`, `turn_aborted`, `thread_settings_applied`,
`additional_tools`, `configuration_update`.

`payload.role` counts: `developer` (system-injected boilerplate, NOT human input),
`user`, `assistant`.

### The record that carries user text

```json
{"type":"response_item","payload":{"type":"message","role":"user","content":[...]}}
```

So `type == "response_item" AND payload.role == "user"` is the human-turn predicate.
`payload.role == "developer"` looks tempting (it is the single largest role) but it is
injected instruction text, not a user turn. `event_msg` sub-types `user_message` /
`user_input` were also accepted but did not occur in these samples.

## 3. Sample counts

| Sample | Files | User turns | Mean/file | Min | Max |
|---|---|---|---|---|---|
| Newest 40 by mtime | 40 | 80 | 2.00 | 2 | 2 |
| Stratified across corpus | 40 | 95 | 2.38 | 0 | 11 |

Parse failures: 0 in both samples (every line valid JSON).

The newest 40 are uniformly 2 turns (recent automated/subagent runs). The stratified
sample shows the real spread: interactive historical sessions reach 7 and 11 turns,
and a few are 0.

## 4. Projection to 2,567 files

- Mean 2.38/file x 2,567 = **~6,097 user turns**
- Per-file spread 0-11 gives an extreme envelope of 0 - 28,237 (not meaningful as a point estimate)
- Median 2/file gives a conservative floor of ~5,134

Realistic estimate: **5,100 - 6,100 user turns**, i.e. an order of magnitude above 401.

## 5. Root cause, confirmed by direct measurement

Counting user turns in the 180 plain `*.jsonl` files alone yields **399**.

The miner reported **401**. That is a match within counting-rule noise (2 records). The
miner read only the 180 uncompressed files and never decompressed the 2,380 `.zst` +
7 `.zst.zst` files.

## VERDICT

UNDER-EXTRACTED

401 reflects the 180-file uncompressed subset (399 measured directly), not the 2,567-file
corpus. Fix: zstd-decompress `.jsonl.zst` (and `.zst.zst` recursively) before parsing, then
re-count. Expected yield ~5,100-6,100 user turns, roughly 13x the current 401.
