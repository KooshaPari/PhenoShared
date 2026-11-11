# Mined operator-message schema

One JSON object per line (JSONL), UTF-8, no pretty printing.

| field | type | meaning |
|---|---|---|
| source | str | one of: forge, jcode, kcode, codex, imessage, herdr, chatgpt, claude, gemini |
| source_file | str | absolute path the record came from (or db path + rowid) |
| session_id | str|null | native session/conversation id if available |
| msg_id | str|null | native message id if available |
| ts | str|null | ISO-8601 UTC timestamp if available |
| role | str | always "user" for these files (operator-authored only) |
| text | str | verbatim operator text, unmodified except leading/trailing whitespace strip |
| text_sha256 | str | sha256 hex of `text` AFTER strip |
| chars | int | len(text) after strip |
| substantive | bool | chars >= 80 (one-word/nudge nessages are real intent but flagged false) |

Rules for every miner:
1. Operator-authored messages only. Exclude assistant/system/tool roles.
2. Exclude injected context that is not operator typing: `# AGENTS.md`, `<environment_context>`,
   `<user_instructions>`, system reminders, and empty/whitespace bodies.
3. Do not paraphrase, translate, or summarise. Verbatim text only.
4. Deduplicate by `text_sha256` WITHIN the source file. Keep the earliest ts.
5. Write `_MANIFEST.json` next to the JSONL: {source, files_scanned, files_parsed, records,
   substantive, one_word, chars_total, ts_min, ts_max, errors:[...], generated_at_utc}.
6. Never modify source files. Read-only.
