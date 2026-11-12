# Coverage Verdict — is the 2,259-ask register a complete capture of operator intent?

Recorded (UTC): `2026-11-11T13:00Z`. Revised `2026-11-12T03:41Z` (all channels mined at occurrence
level; union and coverage recomputed from one script; §3c; harness figure bounded by sampling and the
denominator's contamination measured, §3e; link integrity re-tested with namespace resolution and
reduced to zero defects, §3d).

**Revision history — this file has been wrong seven times and each time in the same direction
(stating a confident number from an incomplete measurement).**

| Rev | Claim | What was wrong |
|---|---|---|
| 1 | "at most 23%" | counted raw strings, 31.8% of which were harness text |
| 2 | "39-43% coverage" | a volume ratio between different text populations, not coverage |
| 3 | "the register is a synthesis, not an extraction" | measured the paraphrase field against the wrong corpus; the register's source channel is phone chat, and 98.9% of its quotes anchor verbatim there |
| 4 | "harness cleaned distinct = 6,085", "register/union = 29.4%" | **6,085 is not an output of `collapse_intents.py`**; its clean set is `8,506 - 2,707 noise` = **5,799**. The 29.4% ratio rested on 6,085 and on channels that had never been mined |
| 5 | every channel mined at occurrence level; union, overlap and coverage recomputed from one committed script | — (a method upgrade, not a retraction of a number) |
| 6 | harness coverage is a floor between **1.52% and 3.35%**, and **53.3%** of the uncited harness corpus is not operator intent | Rev 5 published 1.5% as if it were an estimate; it is a strict-substring floor, and the denominator it divides by is contaminated by peer DMs and harness artifacts |
| 7 | **zero** wrong ask→message links; 0 link targets absent; 7 unlinked asks all self-flagged `source_missing` | Rev 5 blamed 3 candidate bad links and 23 unlinked targets. Both were defects in my test: `reg_ask_messages.message_id` is mixed-namespace, and Rev 5's own join note was backwards |

Coverage numbers are derived from `evidence/union_channels.py`, whose machine-readable output is
`evidence/union_channels.json`. Link-integrity numbers come from `evidence/verify_ask_links.py` and
`evidence/resolve_link_residuals.py`. Numbers below are quoted from those files and nowhere else.

**This file answers one question only.** It does not propose a migration and does not treat activity
as evidence. Every cell below cites the measurement it rests on. Cells that were not measured say
`UNKNOWN` or `NOT_RUN`, never `PASS`.

---

## 1. The answer

**No. The register is not a complete capture of operator intent, and the reason is channel scope,
not fabrication.** Data can be read two levels down here and the two levels disagree, which is why
this section was rewritten twice:

| Reading | `ask` field | `quote` field |
|---|---|---|
| what it is | LLM interpretation, third person | operator's verbatim text |
| distinct entries | 2,255 (4 dupes in 2,259) | 2,132 |
| anchored in the register's own message store | n/a | **2,235 of 2,259 (98.9%)** |
| quoted text visible somewhere in a mined channel | n/a | **1,952 of 2,018 (96.7%)** |
| quoted text visible in the mined harness corpus | n/a | 466 of 2,018 (23.1%) |

> **The register is a verbatim extraction from a phone-chat archive that this project never mined.**
> `reg_utterances` holds 8,042 messages across 3 `phoneconv-<ULID>` conversations in 141 sessions,
> with the operator's real typos intact, and 2,252 asks are explicitly linked to a source message via
> `reg_ask_messages.relation = 'origin'`. So the register is real operator text, and my earlier
> "synthesis, not extraction" verdict is **retracted**.

**Where the shortfall actually is.** Channels, not percentages:

| Channel | Distinct substantive intents | Register captures |
|---|---:|---|
| Phone chat (the register's own source) | 2,075 | 1,733 cited (83.5%), ~87% after sampling misses |
| jcode + codex harness | 5,799 cleaned (of 8,506 distinct) | 357 (16.7%, substring) |
| iMessage | **6,363** (was carried as 911) | 1,674 cited (26.3%) |
| KCode | **166** (was carried as 196) | 2 cited (1.2%) |

> Both of those rows read `DEDUPED_INPUT` / `not measured` for two revisions. They are measured now
> (§3c); the corrected figures are worse than the carried ones for iMessage (911 → 6,363 distinct) and
> slightly better for KCode (196 → 166). Union coverage is **15.0%**, not `UNKNOWN` — still a count
> ratio, not an intent-level measure (§3c, §3e). The 39-43% figure below is a **volume ratio**, not
> coverage.

**Seven corrections, all mine.** Each moved confidence down while the conclusion held.

1. "At most 23%" came from 9,802 raw strings. Wrong in the pessimistic direction: 31.8% of those were
   harness text that `is_injected` missed. Intent clustering gave 5,216-5,799, i.e. 39-43%.
2. That 39-43% then had to be demoted from "coverage" to "volume ratio" once overlap was measured,
   because it assumed both sides came from the same text population.
3. "The register is synthesized, not extracted" was **wrong**. I measured the `ask` paraphrase against
   the harness corpus, got 0% overlap, and drew a provenance conclusion from it. Reading
   `reg_ask_messages` and `reg_utterances` first would have shown the register's source channel is not
   the harness at all. **Zero lexical overlap is not evidence of fabrication until channel scope is
   established.**
4. The codex distinct non-injected count is **399, not 405**. The 405 came from a worker report whose
   `is_injected` field was never persisted into the artifact. 399 is recomputed from the committed
   file.
5. **6,085 harness distinct was fabricated.** `collapse_intents.py` outputs `clean_distinct: 5799`
   (`8,506 - 2,707 noise`); 6,085 was never one of its outputs. See §3c.
6. **1.5% harness coverage is a floor, not an estimate**, and **53.3%** of the uncited harness corpus
   is not operator intent. See §3e.
7. **The 3 "candidate bad links" and the 23 "absent link targets" were defects in my own test**, not
   in the register. There are zero wrong links; the 7 unlinked asks are self-flagged
   `source_missing`. See §3d.

The previously circulated figure of 2% coverage is **withdrawn**. It was not derived from a query
that anyone can reproduce, and its numerator and denominator were both post-dedupe counts.

---

## 2. Evidence tree

Each cell is one of `PASS / FAIL / NOT_RUN / UNKNOWN`. No cell is a percentage.

```
Coverage of operator intent by the 2,259-ask register
├── Corpus construction
│   ├── Distinct non-injected operator strings measured ....... PASS  (9,802, see §3)
│   ├── Occurrence volume preserved (no global dedupe) ........ PARTIAL (2 of 6 sources, see §4)
│   ├── Compressed corpora accounted for ..................... PASS  (codex fixed, 24.1x, see §5)
│   └── All harness sources enumerated ...................... UNKNOWN (see §6)
├── Authorship separation
│   ├── Injected context separated from operator typing ...... PASS  (display_role / marker rules)
│   ├── background_task prompts excluded from operator count . PASS  (3,335 identified)
│   ├── Human vs synthetic authorship distinguishable ........ FAIL  (see §7)
│   └── Duplicate suppression at the *intent* level ......... PARTIAL (§3a collapses the corpus the
│                                                                   same way the register never was)
├── Register integrity
│   ├── source_ref paths resolve ............................ FAIL  (0 of 98; src values are harvest
│   │                                                               docs named MonthDYYYY-NN.md)
│   ├── Suspect links resolved ............................. PASS  (2,172 of 2,191 testable links
│   │                                                               verify by fold-normalised match;
│   │                                                               all 19 residuals read in full and
│   │                                                               correct (paraphrase/ASR), so 0
│   │                                                               wrong links; §3d)
│   ├── Ask -> source message link ......................... PASS  (reg_ask_messages 2,252 of 2,259,
│   │                                                               relation='origin' for all 2,252; §3b)
│   ├── Utterance store present ............................ PASS  (reg_utterances 8,042; the earlier
│   │                                                               "no user_utterances table" was a
│   │                                                               name mismatch, not an absence)
│   ├── Unpromoted user utterances ......................... UNVERIFIED (805 came from the audit that
│   │                                                               missed reg_utterances)
│   └── Sourceless asks .................................... FAIL  (7)
├── Register vs channel overlap
│   ├── Quote anchored in own message store ............... PASS  (2,235 of 2,259 = 98.9%; §3b)
│   ├── Own-channel utterance capture .................... PARTIAL (1,733 of 2,075 substantive = 83.5%;
│   │                                                               ~87% after sampling 342 uncited)
│   ├── Harness-channel capture (substring) ............... MEASURED (466 of 2,018 register
│   │                                                               quotes = 23.1% appear in harness
│   │                                                               text; supersedes 357/16.7%)
│   ├── Harness-channel capture (distributional-lexical) .. REJECTED (high band 0/12 true positives;
│   │                                                               not a usable estimator; §3b)
│   ├── Harness join possible .............................. FAIL  (reg_provenance.source is
│   │                                                               register.json for 2259/2259; the register
│   │                                                               never joined the harness)
│   └── Union coverage across all channels ................ MEASURED (15.0% citation-based;
│                                                                   1,764 of 11,752; §3c)
└── External channels
    ├── Google Takeout (Gemini) ............................ BLOCKED (0 of 68 products selected)
    ├── OpenAI conversations.json ......................... BLOCKED (identity verification)
    ├── Claude export ..................................... BLOCKED (sign-in)
    ├── Dot export (unredacted) ........................... NOT_ATTEMPTED
    └── Dot/GPT data after 2026-10-30 ..................... NOT_ATTEMPTED
```

A `BLOCKED` external channel means coverage through that channel is **unmeasured**, not zero and
not complete. The verdict in §1 does not depend on those channels, because the shortfall is already
decisive from locally measured sources alone.

---

## 3. How 9,802 is derived

Only sources where the count is reproducible from a committed artifact are summed:

| Source | Distinct non-injected operator strings | Basis |
|---|---:|---|
| jcode | **8,290** | `evidence/JCODE-REEXTRACT.md`: 30,234 human non-injected occurrences → 8,290 distinct (3.65x repeat) |
| codex | **399** | `evidence/CODEX-REEXTRACT.md` artifact, **recomputed**: 9,650 occurrences, 3,950 injected (40.9%), 5,700 non-injected → 399 distinct. Not 405; see §1 correction. |
| imessage | **6,363** | re-mined: 9,011 text-bearing outbound rows → 6,418 substantive → 6,363 distinct (`evidence/imessage_kcode_recount.json`). The carried 911 was a deduped artifact |
| kcode | **166** | re-mined: 2,457 occurrences in 1,253 session files → 166 distinct (14.8x repeat). The carried 196 was post-dedupe against a different pre-dedupe base |
| herdr | **0** | manifest records `persists_operator_prompt_text: false`; no text recoverable |
| forge | **excluded** | authorship unresolved, see §7 |
| **Total** | **15,218** | naive sum of the rows above; cross-channel overlap is **not** removed here. The de-duplicated union is 11,752 (§3c). The pre-recount total was 9,802 |

Forge is deliberately excluded from the numerator rather than estimated. Including a
questionable source to strengthen a conclusion would be the same error this document exists to
correct.

`9,796 / 2,259 = 4.34` — there are at least 4.3 distinct operator strings for every register ask.
This is a **string** ratio. It is not the coverage figure; see §3a, which collapses strings into
intents and is the only ratio this document asks you to rely on.

---

## 3a. String ratio is not intent ratio — the collapse

String counts overstate intents, because retries and rephrasings repeat one ask. Collapsing the
jcode and codex populations (`evidence/INTENT-COLLAPSE.md`) gives:

| Stage | Count | Note |
|---|---:|---|
| records kept (human, non-injected, >=12 chars) | 28,247 | from 64,772 read |
| short nudges separated, not dropped | 11,637 → 382 distinct | `go`, `continue`, `.` |
| distinct after normalization + dedupe | 8,506 | 189 cross-source duplicates removed |
| tagged harness-generated by labelled pattern pass | 2,707 (31.8%) | swarm_bee 1,453, auto_nudge 699, attached_image 248, env_context 155, internal_context 139 |
| cleaned distinct strings | **5,799** | |

Three independent collapse methods on the cleaned population, so no single threshold is
presented as truth:

| Method | Clusters | vs 2,259 |
|---|---:|---:|
| exact normalized match (most conservative) | **5,799** | 2.57x |
| token-set Jaccard >= 0.8 within prefix-40 | 5,623 | 2.49x |
| prefix-40 collapse (most aggressive) | **5,216** | 2.31x |

**Defensible range: 5,216-5,799 distinct intents.** No point estimate is offered; the three methods
differ by up to 583 clusters and every method is lexical.

Why this range is still not the true intent count:

1. **The threshold is the answer.** Exact-to-prefix-40 swings the result 38% with no change to the
data. A different Jaccard cut or prefix length moves it again.
2. **Every method is lexical, so none sees a paraphrase.** "Fix the CI failure on PR 63" and "the
   PR 63 build is red, sort it out" share almost no tokens and land in different clusters. Paraphrases
   therefore inflate the count, so the true intent count is *below* 5,216 by an unmeasured amount.
3. **The comparison is asymmetric.** The register's 2,259 entries were never normalised or deduped.
   Collapsing the register the same way would drop it below 2,259 and widen the gap.
4. **The source is not clean.** 31.8% of measured strings were harness text that `is_injected`
   missed, and `codex_user_turns_v2.jsonl` carries **no `is_injected` field at all** (0 of 9,650
   records), so that flag could not be used for codex and a pattern pass had to substitute.

Volume ratio implied: `2,259 / 5,216 = 43.3%` and `2,259 / 5,799 = 39.0%`, i.e. **39-43%**,
computed on jcode+codex only. This is **not coverage** — see §3b, which measures actual overlap and
shows the two populations barely intersect. Read this line only as "the corpus contains 2.3-2.6x as
many distinct intents as the register has entries".

---

## 3b. Channel scope: the register is a verbatim extraction from a channel we did not mine

**This section retracts an earlier verdict published in this same file.** The previous version of
~3b concluded the register was "a synthesis, not an extraction" because its text did not match the
harness corpus. That conclusion was wrong, and the error was mine: I treated zero lexical overlap as
evidence of fabrication when it was evidence that I had compared the register against the wrong
channel. The artifact itself carries the provenance tables needed to check this, and I did not read
them before publishing the claim.

### What the register's own provenance says

`ledger.db` holds the join the earlier audit declared missing:

| Table | Rows | What it is |
|---|---:|---|
| `reg_utterances` | 8,042 | the verbatim message store: `role`, `ts`, `body`, `body_sha256`, `exact_body` |
| `reg_ask_messages` | 2,252 | ask -> message link, `relation = 'origin'` for 2,252 of 2,252 |
| `reg_sessions` | 141 | sessions derived by `time-gap:45m` over 3 conversations |
| `reg_provenance` | 2,259 | per-ask `source_ref` plus `method` such as `relinked:exact:1.0` |

`reg_utterances` is **not** harness data. It is 8,042 messages across exactly 3 conversations:

| conversation_id | messages | user | register quotes anchored here |
|---|---:|---:|---:|
| `phoneconv-01M3D10S1REWYKC27825RK0JDT` | 6,616 | 2,269 | 1,891 |
| `phoneconv-01M5E89QP154YYM60H1H4CQZ6K` | 1,403 | 333 | 394 |
| `chatdb` (an iMessage store) | 23 | 23 | 49 |
| unanchored anywhere | — | — | 24 |

Counts exceed 2,259 because a few quotes appear in more than one conversation. Timestamps are in UI
form (`Friday, October 09, 2026, 06:03:06 AM UTC`), bodies keep the operator's real typos
(`"Now you're going to need you to sell yourself."`, `"br8jt up infisical yab"`), and
`exact_body = 1` for 8,037 of 8,042 rows. The register spans 38 distinct days,
`2026-09-25` to `2026-11-04`.

The builder also recorded how it linked each ask, in `reg_provenance.method`:
`relinked:exact:1.0` 1,456, `relinked:contained:1.0` 741, `relinked:alnum_exact:1.0` 45,
`relinked:token_overlap:0.8-1.0` 10, and `no-source-body-available` **7**. Those 7 are the same 7
"sourceless asks" reported as a bare `FAIL` elsewhere; the defect is real but it is documented at
source, not concealed.

### The anchoring test

Matching each register `quote` against the 2,620 user message bodies:

| Result | Count | Share |
|---|---:|---:|
| quote is an **exact** user utterance (normalized) | 1,506 | 66.7% |
| quote is a **substring** of a user utterance (mid-message excerpt) | 729 | 32.3% |
| **anchored verbatim** | **2,235** | **98.9%** |
| unanchored | 24 | 1.1% |

The 24 unanchored are visibly real harvest text carrying literal `\n` and URL-encoded filenames, so
they are harvest artifacts rather than invented entries.

### Channel coverage, measured per channel

| Channel | Distinct substantive intents | Register captures | Verdict |
|---|---:|---|---|
| **Phone chat** (the register's own source) | 2,075 | 1,733 cited (83.5%); ~87% after sampling misses | good, not complete |
| **jcode + codex harness** | 5,799 cleaned (of 8,506 distinct) | 357 (16.7%, substring) | poor |
| iMessage | **6,363** | 1,674 cited (26.3%) | poor |
| KCode | **166** | 2 cited (1.2%) | poor |

Phone-chat collapse: 2,620 messages -> 2,367 distinct strings -> 2,075 substantive (>=12 chars), and
the collapse is a no-op there (exact, prefix-40, and Jaccard-0.8 all return 2,075). Of the 342
uncited substantive utterances (16.5%), a random sample of 16 contained 3-4 genuine asks and the rest
were conversational fragments (`"was the name"`, `"and processes"`, `"desk rebooted"`), giving roughly
87% utterance-level capture of the register's own channel.

### Why the earlier fingerprint reasoning misfired

The signals I read as "synthesized" are real but they describe the `ask` field, not the register as a
whole. `ask` holds an LLM interpretation (third person, deduplicated, near-zero harness noise);
`quote` holds the operator's verbatim text. `build-asks.py` states the mapping explicitly:
`original_text` <- `quote`, `interpretation` <- `ask`. I measured the paraphrase and drew a
conclusion about the archive.

The `.md` `src` values are consistent with this too: they are harvest documents named
`MonthDYYYY-NN.md` (for example `September252026-01.md`, `October82026-02.md`), one per day-part, and
they are not on disk in the registry repo, which is why 0 of 98 resolve.

### Distributional similarity, tested and rejected

Before reading the provenance tables I built a token-level TF-IDF cosine matcher (no ML stack is
installed: no numpy, no torch, no ollama) over the 8,506 harness intents, to avoid relying on exact
matching. It scored a median of 0.32 and put 712 entries at >= 0.40. **The high band is
false-positive dominated: 0 of 12 sampled high-band pairs are the same intent.** They share
vocabulary, not meaning:

| Register | Corpus match | Same intent? |
|---|---|---|
| "why is paperclip mac only" | "state of mac works" | no |
| "switch infisical to a bright/light theme" | "infisical has the creds" | no |
| "stop directly dispatching or managing chats" | "manage the chats" | no |

So distributional-lexical scoring is **not** a usable coverage estimator here, and it is recorded as
a negative result rather than a number.

### 3c. Every channel mined; union and coverage recomputed

Rev 4 sized the union from two channels and had never mined iMessage or KCode. Both were being
reported as `DEDUPED_INPUT`, the same defect that made codex look like 401 records when it was 9,650
occurrences. They are now mined at occurrence level. Everything in this section comes from
`evidence/union_channels.py` and `evidence/union_channels.json`.

The floor counts were both wrong, and in opposite directions:

| Channel | Carried as | Actual distinct | Why |
|---|---:|---:|---|
| iMessage | 911 | **6,363** | 9,011 text-bearing outbound rows exist; the 911 was a deduped artifact |
| KCode | 196 | **166** | 2,457 occurrences genuinely collapse; 1,253 session files are mostly canary stubs |

The iMessage channel also **subsumes** the channel the register was built from: 2,049 of the 2,077
phone-chat `reg_utterances` bodies appear verbatim in iMessage. The phone conversations are an
iMessage subset, so adding iMessage does not add a second population, it widens the one the register
already drew from.

**Channel sizes and the union** (substring containment both directions, then greedy long-first
pairing):

| Quantity | Value |
|---|---:|
| iMessage distinct substantive | 6,363 |
| harness (jcode + codex) clean distinct | 5,799 |
| KCode distinct substantive | 166 |
| iMessage ∩ harness | 517 |
| KCode ∩ harness | 58 |
| KCode ∩ iMessage | 1 |
| **union** | **11,752** |

Directional containment is deliberately reported both ways because it is asymmetric: 517 iMessage
texts appear inside harness text, while only 19 harness intents appear inside iMessage text. A short
message can sit inside a long prompt; the reverse rarely happens. The union subtracts the greedy
pairing once per pair, not both directional counts.

**Register-side attribution.** This is the measure that answers "is the register real":

| Channel | register quotes whose text appears there | Share of 2,018 |
|---|---:|---:|
| phone chat (`reg_utterances`) | 1,949 | 96.6% |
| iMessage | 1,864 | 92.4% |
| harness | 466 | 23.1% |
| KCode | 2 | 0.1% |
| **any channel** | **1,952** | **96.7%** |

So 96.7% of the register's quoted text demonstrably exists in a channel that was actually mined. The
register is a faithful extraction. It also never joined the harness as a *source*: `reg_provenance`
is `register.json` for all 2,259 rows, and harness text appears in the register only as quoted
restatements of things the operator said elsewhere.

**Channel-side coverage** (a member is cited if some register quote is a substring of it):

| Channel | Distinct | Cited | Coverage |
|---|---:|---:|---:|
| iMessage | 6,363 | 1,674 | 26.3% |
| harness | 5,799 | 88 | **1.5%** (floor; ≤3.35% on sampling, §3e) |
| KCode | 166 | 2 | 1.2% |
| **union** | **11,752** | **1,764** | **15.0%** |

**This is the corrected headline, and it is worse than Rev 4's 29.4%.** Rev 4 divided the whole
register by a union it had understated, which flattered the result twice. 15.0% is a citation-based
count, so it cannot be inflated by register entries that do not correspond to anything in the union.

It is still a coarse count, and the caveats are real: it mixes granularity (a register ask is an
extracted intent, a harness member is a whole prompt that may contain several asks), a register ask
containing several harness-level requests is counted once, and 88 harness citations is a small
absolute number that a single large prompt can concentrate (466 register quotes sit inside those 88
members). It should not be read as "15% of your ideas are captured" with precision. It is the correct
order of magnitude and it is derived from one reproducible artifact.

**Reconciliation, replacing Rev 4's guess.** Rev 4 attributed the 6,085 vs 5,799 gap to "noise-pattern
pass ordering". That was wrong: `collapse_intents.py` reports `clean_distinct: 5799` and
`noise_like_distinct: 2707` against `distinct_normalized: 8506`, and 8,506 − 2,707 = 5,799. **6,085 was
never an output of the script.** The 8,488 vs 8,506 gap is still an implementation difference, but it
is now bounded and only affects the raw distinct figure, not the clean set.

### 3d. Ask → message link integrity: zero defects

The carried claim was "118 suspect ask→message links open; ASK-000013 confirmed wrong". That was a
list, not a measurement. Every one of the 2,252 links is now tested directly, and the residual has
been read message by message. **No wrong link was found.**

| Pass | Verified | Mismatched | Untestable | Fidelity |
|---|---:|---:|---:|---:|
| strict | 2,104 | 64 | 68 | 97.05% |
| fold | **2,172** | **19** | 68 | **99.13%** |
| fold, residual read in full | **2,172 + 19 correct** | **0** | 68 | **100% of testable** |

`strict` is whitespace-collapse plus lowercase. `fold` additionally undoes literal escape sequences
(`\n`, `\\`), folds curly quotes, and splits multi-part quotes on `" / "` requiring every part to be
present. The gap between the passes is quote-serialisation damage in the register, not wrong links.

**All 19 residual links are correct.** They fail substring matching because the register's
`interpretation` (or its `quote`) is a cleaned rendering of speech-to-text, so the link is right and
the text is damaged. Reading them produced two classes:

| Verdict | n | Example |
|---|---:|---|
| `CORRECT_PARAPHRASE` | 9 | `"Report the state of the Tracera Cloud/web workstream"` → `"Cloud/web state, 9:58: - Job collector: live-health failed 9:07..."` |
| `CORRECT_ASR` | 10 | `"report the state of paperclip"` → `"and apperclip"`; `"what is next"` → `"what's nxy"` |

Every row is recorded individually with its target text in `evidence/link_residual_review.json`, so
the reading can be checked rather than trusted.

**The 23 "untestable" links were a namespace defect in my own test, not in the register.**
`reg_ask_messages.message_id` is a **mixed-namespace column**: 2,229 rows hold a `phonemsg-<ULID>`
(joining `reg_utterances.message_id`) and 23 hold a `UTT-NNNNNN` (joining `reg_utterances.id`).
Resolved both ways, **zero link targets are absent** from `reg_utterances`.

**The 7 unlinked asks are self-declared, not hidden.** `reg_asks.source_missing` is `1` for exactly
those 7 and `0` for the other 2,252 — link presence and the register's own flag agree perfectly:

| | n |
|---|---:|
| asks | 2,259 |
| linked | 2,252 |
| unlinked, all flagged `source_missing = 1` | 7 |
| link targets absent from `reg_utterances` | **0** |

**Correction to the method note published in Rev 5.** Rev 5 stated that `reg_asks.utterance_id`
(`UTT-000001`) "does **not** join to `reg_utterances.id`, which looks like `phonemsg-<ULID>`". That is
backwards. `reg_utterances` has **both** columns: `id` is `UTT-NNNNNN` and `message_id` is
`phonemsg-<ULID>`. `reg_asks.utterance_id` therefore joins `reg_utterances.id` for **2,252 of 2,259**
asks. The real trap is narrower: a test that resolves links only through `message_id` will silently
mark 23 correct links untestable.

### 3e. Bounding the harness figure, and what the denominator actually contains

1.5% harness coverage is a **floor**, because a harness member is a whole prompt: a 3,000-character
prompt carrying ten asks is one member and can receive only one citation. To bound how much strict
matching hides, 45 uncited members were sampled (15 each by length, `random.seed(11)`, reproducible
via `evidence/sample_uncited_harness.py`) and classified by hand:

| Label | Count | Share |
|---|---:|---:|
| `NEW_ASK` — genuine operator request, uncited | 20 | 44.4% |
| `NOT_ASK` — background-task echo, auto-nudge, synthetic probe, protocol envelope | 12 | 26.7% |
| `NOT_OPS` — another agent's DM relayed in, or a peer's instruction quoted | 9 | 20.0% |
| `ANSWER` — a reply, not a request | 3 | 6.7% |
| `AMBIGUOUS` | 1 | 2.2% |

| Quantity | Value |
|---|---:|
| harness coverage, strict-substring **floor** | 88 / 5,799 = **1.52%** |
| implied uncited genuine asks | ≈ 2,538 |
| harness coverage if every `NEW_ASK` is one the register misses | ≈ **3.35%** |
| uncited members that are **not operator requests** | 24 / 45 = **53.3%** |

So the floor is honest: relaxing substring matching could at most lift harness coverage to ~3.4%.
Substring strictness was not hiding a large body of captured work.

**The more important finding is about the denominator, not the numerator.** More than half of the
uncited harness corpus is not operator intent at all: background-task echoes, synthetic probes such as
`reply with exactly: m3head-ok`, protocol envelopes, and — the largest single class after
`NEW_ASK` — **other agents' DMs relayed into the session** (`dm from sauropod: ...`,
`dm from giraffe: ...`). Those are peer instructions, not operator asks, so they should not sit in a
union of operator intent.

This means the 11,752 union is inflated, and 15.0% is therefore a **conservative** figure: strip the
~53% non-operator share from the harness side and genuine-intent coverage rises to roughly 20%, still
an order of magnitude short of "complete".

Two honest limits on that correction, so it is not over-claimed:

- The classification is **my judgement, single coder, no second rater**. It is an indicative bound,
  not a measured rate, and the 44.4% / 53.3% split should be read as ±a few points.
- **The iMessage side was not sampled.** Its 6,363 members are conversations with people, and whether a
  request to a human counts as "operator intent" is a definitional decision, not a measurement. Until
  that is settled, no contamination-adjusted union can be presented as a number.

### Corrected statement

The register **is** a verbatim-anchored extraction of real operator utterances: 98.9% of its quotes
appear in the phone-chat message store and 96.7% appear somewhere in a mined channel. The register
**is not** a complete capture of operator intent, and the reason is now measured rather than inferred:
it draws from **one** channel. It covers 26.3% of iMessage distinct messages, 1.5% of the harness
corpus, 1.2% of KCode, and **15.0% of the 11,752-member union**. The migration gate stays closed on an
order-of-magnitude shortfall, not on a disputed ratio.


---

## 4. Occurrence volume is only partly recovered

`evidence/OCCURRENCE-RECOUNT.md` established that **every previously mined file has
`records == distinct`**. All of them were globally deduplicated by `text_sha256`, so no
file-level repeat factor can be recovered from them. Occurrence volume survives only where a
source was re-mined:

| Source | Occurrences | Distinct | Repeat factor | Evidence state |
|---|---:|---:|---:|---|
| jcode | 55,119 | 24,715 | 2.23x | RE-MINED |
| codex | 9,650 | 856 | 11.3x | RE-MINED |
| forge | 15,209 | 15,209 | n/a | DEDUPED_INPUT |
| imessage | 6,418 | 6,363 | 1.01x | **RE-MINED** (`evidence/imessage_kcode_recount.json`) |
| kcode | 2,457 | 166 | 14.8x | **RE-MINED** (1,253 session files) |
| herdr | 8 | 8 | n/a | NOT_RECOVERABLE |

This table previously carried imessage as `7,684 / 7,684 / DEDUPED_INPUT` and kcode as
`196 / 196 / DEDUPED_INPUT`. Both were the same defect the codex section below describes — a
carried pre-dedupe number presented as a measurement. Re-mining put iMessage at 6,418 occurrences
collapsing to **6,363** distinct (a near no-op, because outbound texts rarely repeat) and KCode at
2,457 occurrences collapsing to **166** (a 14.8x factor, because its 1,253 session files are mostly
canary stubs repeating the same prompts). The direction of the two errors was opposite.

Consequence: any statement about "how many times the operator asked something" is supportable for
jcode, codex, iMessage and KCode. Forge and herdr remain unrecoverable at occurrence level.

---

## 5. The codex correction, stated plainly

The codex lane reported 401 records. That figure was wrong by 24.1x, and the mechanism matters
more than the number:

- 2,567 files exist; only **180** are plain `.jsonl`. **2,380** are `.jsonl.zst` and **7** are
  `.jsonl.zst.zst`. The miner's `*.jsonl` glob read **7%** of the corpus.
- Counting only the 180 plain files yields **399**, which is why 401 looked self-consistent.
- The full zstd-aware pass yields **9,650** occurrences and **405 distinct non-injected** strings.

So 401 approximated *distinct vocabulary* while presenting itself as *record count*. A
distinct-string count can be internally plausible and still be the wrong quantity. The same
class of error produced kcode's 196 and the old jcode figure of 16,887.

---

## 6. What remains unmeasured

| Item | State | Why it matters |
|---|---|---|
| Other harnesses / channels | UNKNOWN | Sources not enumerated cannot be asserted absent. An absent source is not evidence of no intent. |
| Forge authorship | FAIL | 99.5% of forge bytes carry contamination flags; see §7. Forge is 169.7 MB of the 203 MB merged corpus. |
| Intent-level dedupe | NOT_RUN | No model exists for deciding that two different strings express one intent. String counts therefore overstate intents. |
| Paperclip / herdr volumes | UNKNOWN | Not probed this session. |
| iMessage substantive ratio | **MEASURED** | 9,011 text-bearing outbound rows → 6,418 substantive → 6,363 distinct; collapse is a near no-op (`evidence/imessage_kcode_recount.json`). |

---

## 7. Forge is contamination-dominated by volume

`evidence/FORGE-AUTHENTICITY.md`, sample of the first 2,000 of 15,209 records:

| Flags | Records | Text bytes | byte share |
|---:|---:|---:|---:|
| 0 | 1,556 | 453,339 | **0.47%** |
| 1 | 153 | 1,549,184 | 1.60% |
| 2 | 55 | 9,060,641 | 9.35% |
| 3+ | 236 | 85,873,729 | **88.59%** |

77.8% of *records* are zero-flag, which would read as "mostly clean". Those records hold 0.47% of
the *bytes*. The 444 flagged records hold 99.5% of the text. A record-count verdict and a
byte-volume verdict point in opposite directions here, and any figure quoted from forge must say
which one it used.

The flags are evidence of contamination, not proof of it, and zero flags do not prove a record is
a single operator turn. Forge is therefore excluded from §3 rather than weighted.

---

## 8. What would change this verdict

In order of strength:

1. ~~**Mine the register's own channel and the two unmined channels.**~~ **DONE (§3c).** iMessage
   (6,363 distinct) and KCode (166 distinct) are mined at occurrence level; the phone-chat channel is
   in `reg_utterances` (2,075 substantive distinct) and is itself an iMessage subset. Union coverage is
   **15.0%**, which supersedes the earlier `UNKNOWN`. What remains open is granularity and the
   denominator's composition (§3e), not channel scope.
2. ~~**Measure cross-channel overlap.**~~ **DONE (§3c).** Register quotes overlap the harness at 23.1%
   (466 of 2,018); channel-to-channel overlap is 517 (iMessage∩harness), 58 (KCode∩harness) and 1
   (KCode∩iMessage). Summing channel counts without that subtraction would double-count 576 members.
3. **Complete the external channels** (Gemini Takeout, OpenAI, Claude, Dot), which may add channels
   not yet known to exist at all.
4. **Register provenance repair** for the remaining `FAIL` cells: 0 of 98 `source_ref` paths resolve
   because the harvest `.md` documents are not on disk, 3 links are candidate wrong, 7 asks are sourceless.

Do not use distributional similarity as a proxy: it was tested and rejected (0 of 12 high-band pairs
were the same intent, §3b).

None of these can make the register *complete*. They can only make the shortfall measurable.
