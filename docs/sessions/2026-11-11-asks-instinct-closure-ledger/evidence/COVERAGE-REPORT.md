# Asks / Intent Coverage — consolidated findings

Generated 2026-11-11T08:02Z from seven parallel bounded lanes (A–H).
Per-lane detail: `A-gpt-full.md`, `B-gpt-partial.md`, `C-claude-gemini.md`, `D-harness.md`,
`E-imessage-register.md`, `G-provenance.md`, `H-other-channels.md` in this directory.

## 1. What the 2,259-ask register actually is

Independently re-verified against `asks-ledger/ledger.db` (read-only):

| fact | value |
|---|---|
| `reg_provenance.source` | `register.json` for **2,259 / 2,259** rows (single source value) |
| Content lineage | `phoneconv-01M3D10S1REWYKC27825RK0JDT` (2,269 user + 4,347 assistant), `phoneconv-01M5E89QP154YYM60H1H4CQZ6K` (333 user + 1,070 assistant), `chatdb` (23 user, **0 asks**) |
| Capture window | 2026-09-25 → 2026-11-04; 38 distinct days of 41 (missing 2026-10-03, 2026-10-04, 2026-11-01) |
| Asks | 2,259 |
| Distinct operator messages behind them | 1,843 (2,252 links ⇒ 238 utterances split into 2+ asks) |
| User utterances in the source never promoted | 805 |
| Asks with no source at all | 7 (`ASK-000345, 000637, 000664, 001844, 002254, 002255, 002256`) |
| Verbatim-verified quotes | 2,134 |
| Suspect links (quote absent from joined body) | 118 (e.g. `ASK-000013` is a genuine wrong link) |
| `reg_provenance.source_ref` markdown files resolving on disk | **0 / 98** |

**The register is not an iMessage capture.** It captures two phone-assistant conversations.
`chat.db` is an entirely uncaptured source.

## 2. Coverage by source

| Source | Volume | Operator messages | Captured in register | Verdict |
|---|---|---|---|---|
| iMessage `chat.db` | 248,532 messages (2019-03-19 → 2026-11-11) | 121,247 outbound, **8,983 with text** | **0** | UNCAPPED |
| iMessage, pre-window | — | 5,289 text-bearing outbound before 2026-09-25 | 0 | UNCAPPED |
| iMessage, post-cutoff | — | 89 text-bearing outbound 2026-11-05 → 11-11 | 0 | UNCAPPED |
| Dot / GPT partial export | 2,247 messages | 460 human, only **98 usable** (21%) | 0 | 79% unrecoverable |
| ChatGPT Exporter (2 small dumps) | 107 messages | 56 usable, 2026-10-11 → 2026-11-08 | 0 | thin but 99% usable |
| Official OpenAI `conversations.json` | — | — | — | ABSENT |
| Claude platform export | — | — | — | ABSENT (only `~/.claude/projects`, 370 files / 1.79 MB) |
| Gemini | — | — | — | ABSENT (needs Google Takeout) |
| `~/.jcode/sessions` | 12,770 files / 2.80 GB | est. **~48,600** | 0 | UNCAPPED |
| `~/.kcode/sessions` | 1,838 files / 27.5 MB | est. ~8,700 | 0 | UNCAPPED |
| `~/.forge` | 18,993 files / 7.83 GB | 13,260 conversations (2026-03-25 → 09-19) | 0 | UNCAPPED, has native intent schema |
| `~/.codex/sessions` | 2,567 files / 637 MB | est. ~2,380 | 0 | UNCAPPED |
| `~/.cursor/agent-transcripts` | — | — | — | MISSING |
| herdr `session-history.json` + 48 snapshots | 245 MB, live (2026-11-10 23:56) | unknown, high | 0 | UNCAPPED, cheapest to harvest |
| Paperclip Postgres | 1.5 GB, live, HTTP 200 | unknown | 0 | UNCAPPED |
| GitHub PhenoRegistry issues | 31 (2026-05-07 → 11-08) | ~6 non-boilerplate | 0 | UNCAPPED |
| Kiro session index | 99 JSONL pointers (10-27 → 11-06) | unknown | 0 | bodies unprobed (`~/.kiro/crew`) |
| Slack | not installed | — | — | N/A |
| Discord | 440 MB local, last activity 2026-09-02 | — | — | local profile dead, needs API |

## 3. Order of magnitude

- Register: **1,843** distinct operator messages.
- Already-local uncaptured: **~73,000** harness user messages (~45,000–55,000 substantive) +
  **8,983** text-bearing iMessage + ~154 usable chat-export messages + unknown herdr/Paperclip.
- **The register represents roughly 2% of the operator's typed intent on this host.**

## 4. Data actually needed from the operator

Only four items are genuinely external; everything else is already on disk.

| # | Needed | Why it cannot be derived locally |
|---|---|---|
| 1 | Fresh **Dot** export (unredacted) | 362 of 460 human bodies are whole-message redactions in the only copy; no larger or less-redacted Dot dump exists on disk |
| 2 | Dot/GPT records **after 2026-10-30** | latest user record is 2026-10-30T23:57:06Z; only 56 usable prompts reach 11-08 via side dumps |
| 3 | Official **OpenAI** `conversations.json` | no full-account export present; needs an export from chatgpt.com |
| 4 | **Gemini** Google Takeout | no export and no `~/.gemini` state anywhere |

Optional / conditional:
- **Discord** history needs an authenticated session or bot token (local dir is a dead Chromium profile).
- **Paperclip** row counts need permission to query the embedded Postgres read-only.

Not needed: iMessage history (local, 8,983 text-bearing), harness transcripts (local, ~73k), herdr
(local, live), GitHub issues (local via `gh`). These are mining jobs, not acquisition jobs.

## 5. Recommended sequencing

1. Mine the local harness corpus first (`~/.forge` has a native intent schema; `~/.jcode` is the
   largest but needs transcript parsing). Highest yield, zero external dependency.
2. Rebuild the iMessage lane properly from `chat.db` (8,983 text-bearing outbound) and merge it in.
3. Harvest herdr, then Paperclip, then GitHub issues across the other repos.
4. Ask the operator only for the four external items above, in that order.
5. Repair the register's provenance layer (98/98 dangling `source_ref`, 118 suspect links,
   805 dropped utterances, 7 sourceless asks) before treating it as the Instinct spine.
