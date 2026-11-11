# Lane A — Full ChatGPT/Dot conversation export coverage

**Lane:** A (gpt-full)
**Date:** 2026-11-10
**Scope:** Measure how much of the FULL ChatGPT/Dot conversation export is usable for deriving operator asks.
**Method:** bounded, non-recursive scans of `/Users/kooshapari/Downloads` and `/Users/kooshapari/CodeProjects` (max-depth 5), plus direct file analysis of every JSON/JSONL/MD conversation candidate. No `$HOME` or `/` recursive search.

## Candidate inventory (all discovered conversation artifacts)

| # | path | size (bytes) | format | role |
|---|---|---|---|---|
| 1 | `/Users/kooshapari/Downloads/dot-conversation-PARTIAL-2026-10-09-to-2026-10-30.json` | 1,743,875 | JSON, dict with `messages` + embedded `manifest` | Dot export (repackaged) |
| 2 | `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/dot-conversation/messages.jsonl` | 1,368,491 | JSONL, 1 record/line | Dot export (source, same 2247 records) |
| 3 | `/Users/kooshapari/Downloads/ChatGPT-[Platform] Repo scope and recovery plan - active-20261106-1543(2).json` | 121,360 | JSON, dict with `messages` + `metadata` | ChatGPT Exporter, single conversation |
| 4 | `/Users/kooshapari/Downloads/ChatGPT-Reevaluate Repository Count-20261108-2255.json` | 36,426 | JSON, dict with `messages` + `metadata` | ChatGPT Exporter, single conversation |
| 5 | `/Users/kooshapari/CodeProjects/temp/keep-bundles/work-small/zz-Parpoura-rb-archive-20261106-verify/ChatGPT_Conversation_2026-02-21.md` | 550,569 | Markdown, `### **You**` / `### **ChatGPT**` turns | ChatGPT web conversation, Feb 2026 |
| 6 | `/Users/kooshapari/CodeProjects/docs/phenotype_control_systems_docset_v0.3-2/evidence/session/conversation-index.json` | 345,156 | JSON list, 81 conversations | Forge `.forge.writes.db` index, Sep 2026 |

No official OpenAI `conversations.json` / `ChatHistory` full-account export exists anywhere on disk. The only ChatGPT-native JSON is two third-party "ChatGPT Exporter" (`chatgptexporter.com`) single-conversation dumps.

## Results table

| path | size | records | user_msgs | usable_user_msgs | date_min | date_max | has_post_2026_10_10 |
|---|---|---|---|---|---|---|---|
| `/Users/kooshapari/Downloads/dot-conversation-PARTIAL-2026-10-09-to-2026-10-30.json` | 1,743,875 | 2,247 messages (0 conversations — flat message list) | 460 (`observed_author.label == "user"`) | **98** (362 redacted/unavailable sentinels) | 2026-10-09 | 2026-10-30 | **YES** (448 user msgs ≥ 2026-10-10) |
| `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-registry/dot-conversation/messages.jsonl` | 1,368,491 | 2,247 | 460 | **98** (same dataset) | 2026-10-09 | 2026-10-30 | **YES** (448) |
| `/Users/kooshapari/Downloads/ChatGPT-[Platform] Repo scope and recovery plan - active-20261106-1543(2).json` | 121,360 | 100 messages (50 `Prompt` / 50 `Response`) | 50 | **49** (1 sentinel) | 2026-10-11 | 2026-10-27 | **YES** (50) |
| `/Users/kooshapari/Downloads/ChatGPT-Reevaluate Repository Count-20261108-2255.json` | 36,426 | 14 messages (7 `Prompt` / 7 `Response`) | 7 | **7** | 2026-11-06 | 2026-11-08 | **YES** (7) |
| `/Users/kooshapari/CodeProjects/temp/keep-bundles/.../ChatGPT_Conversation_2026-02-21.md` | 550,569 | 139 turn blocks (7 `You` / 132 `ChatGPT`) | 7 | **7** (all non-empty, ~45.4 KB total) | 2026-02-21 | 2026-02-21 | NO (pre-window) |
| `/Users/kooshapari/CodeProjects/docs/.../evidence/session/conversation-index.json` | 345,156 | 81 conversations | 81 (one `title` prompt per conv) | 81 (titles only, not full bodies) | 2026-09-11 | 2026-09-11 | NO (pre-window) |

### Format notes (measured, not assumed)

- The two Dot files are **the same dataset**: identical record count (2,247), identical author split (`aeon` 1,787 / `user` 460), identical usable count (98). The Downloads JSON is a repackaging of the registry JSONL with the manifest embedded. Its `manifest.latest_returned` is `2026-10-31T00:27:53Z`, which is an **`aeon` message**; the last **user** message is `2026-10-30T23:57:06Z`. `manifest.complete = false`, `manifest.inception_proven = false`.
- Dot file top-level keys: `complete, coverage_note, format, manifest, messages, schema, source_jsonl_sha256, source_url`. `coverage_note` states explicitly: *"Existing sanitized export only. Not a complete or current Dot dump."* `source_url` points back at the PhenoRegistry `dot-conversation/messages.jsonl` blob — i.e. it is a **re-download of the registry artifact, not a fresh dump**.
- Redaction accounting on the Dot dataset: 2,063 whole-message redactions, 38 unavailable bodies, only **146 preserved available bodies** (of which 98 are user-role). Sentinel markers observed: `[REDACTED...]` / `[UNAVAILABLE:MESSAGE_BODY]`.
- The ChatGPT Exporter JSONs use `role` ∈ {`Prompt`, `Response`} (not `user`/`assistant`) and text in `say`, timestamps in `M/D/YYYY, h:mm:ss AM/PM` under `metadata.dates` (`created`/`updated`/`exported`). They carry the **full unredacted prompt text**.
- The Feb-2026 Markdown export uses `### **You**` for operator turns and `### **ChatGPT**` for assistant turns, single conversation `6996c2ff-a110-8320-bd45-e50b5181badb`.

## Comparison against `dot-conversation-PARTIAL-2026-10-09-to-2026-10-30.json`

| criterion | verdict |
|---|---|
| Larger in byte size | **NO** — nothing found exceeds 1,743,875 B among all discovered conversation artifacts |
| Later max date | **YES, but only in a different, tiny source** — the two ChatGPT Exporter dumps reach 2026-11-08, past the Dot export's 2026-10-30 user-message max (and 2026-10-31 all-role max). Combined they add only 57 operator prompts / 56 usable. |
| Fuller Dot coverage | **NO** — the only other Dot artifact is the byte-smaller registry JSONL holding the identical 2,247 records. No newer, larger, or less-redacted Dot export exists on disk. |

## Conclusions

- **No single fuller export exists.** The Dot dataset's largest copy is the one already analysed; the registry `messages.jsonl` is the same 2,247-record payload in a smaller container, and there is no unredacted or later-dated Dot dump. Coverage is **fragmented across sources**, not suppliable by one bigger file: the only post-2026-10-30 material anywhere is 57 prompts from two small third-party ChatGPT Exporter JSONs (49 + 7 usable).
- **Usable-operator-ask yield is far lower than raw message volume suggests.** The Dot export holds 460 user messages but only **98 usable bodies (21%)** because 362 bodies are whole-message redaction/unavailable sentinels; across the whole dataset only 146 of 2,247 bodies survived (6.5%). Conversely the ChatGPT Exporter JSONs are **~99% usable** (56/57 prompts) but tiny. Any ask-mining run should treat the Dot export as a chronology/attribution skeleton and the ChatGPT Exporter dumps as the actual text-yield source.
- **Post-2026-10-10 operator asks are thinly covered.** 448 of 460 Dot user messages fall on/after 2026-10-10 and 57 ChatGPT prompts do too, but usable text in that window is 98 + 56 = **154 operator messages total** across the whole host, with a hard gap after 2026-11-08 and no evidence of an official full ChatGPT account export. A full ChatGPT-side ask corpus is therefore **not obtainable from local artifacts**; it would require a fresh official export.

## Blockers / follow-ups

- No official OpenAI `conversations.json` / `ChatHistory` export present — the "FULL export" premise is **unavailable locally**. Only a fresh export from chatgpt.com would close the gap.
- The Dot export's `manifest.coverage_gaps` (2 bounded gaps) and `inception_proven: false` mean even the October window is not provably complete.
- Redaction is conservative whole-message masking, so text mining on the Dot dataset cannot recover masked content by other means.
